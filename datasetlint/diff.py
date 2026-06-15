"""Dataset comparison reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from datasetlint.core import lint_dataset, load_config
from datasetlint.io.json import read_json
from datasetlint.schemas import LintConfig, Severity
from datasetlint.stats import DatasetStats, compute_dataset_stats


class DatasetChange(BaseModel):
    """A single dataset diff entry."""

    category: str
    name: str
    old_value: Any = None
    new_value: Any = None
    delta: Any = None
    severity: Severity = "info"
    message: str


class DatasetDiffReport(BaseModel):
    """Structured result returned by ``compare_datasets``."""

    old_path: str
    new_path: str
    changes: list[DatasetChange] = Field(default_factory=list)
    regressions: list[DatasetChange] = Field(default_factory=list)
    improvements: list[DatasetChange] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(), indent=2, sort_keys=True)

    def to_markdown(self) -> str:
        lines = [
            "# DatasetLint Diff",
            "",
            f"- Old: `{self.old_path}`",
            f"- New: `{self.new_path}`",
            f"- Changes: `{len(self.changes)}`",
            f"- Regressions: `{len(self.regressions)}`",
            f"- Improvements: `{len(self.improvements)}`",
            "",
            "| Severity | Category | Name | Old | New | Delta | Message |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        if not self.changes:
            lines.append("| info | none | none |  |  |  | No differences found. |")
        else:
            for change in self.changes:
                old_value = _escape(str(change.old_value))
                new_value = _escape(str(change.new_value))
                delta = _escape(str(change.delta))
                lines.append(
                    f"| {change.severity} | {_escape(change.category)} | "
                    f"{_escape(change.name)} | `{old_value}` | `{new_value}` | "
                    f"`{delta}` | {_escape(change.message)} |"
                )
        return "\n".join(lines) + "\n"


def compare_datasets(
    old_path: str | Path,
    new_path: str | Path,
    config: str | Path | dict[str, Any] | LintConfig | None = None,
) -> DatasetDiffReport:
    """Compare two folder datasets and classify regressions."""

    old_dataset = Path(old_path).expanduser().resolve()
    new_dataset = Path(new_path).expanduser().resolve()
    lint_config = load_config(new_dataset, config)
    old_stats = compute_dataset_stats(old_dataset, config=lint_config)
    new_stats = compute_dataset_stats(new_dataset, config=lint_config)
    old_report = lint_dataset(old_dataset, config=lint_config)
    new_report = lint_dataset(new_dataset, config=lint_config)

    changes: list[DatasetChange] = []
    regressions: list[DatasetChange] = []
    improvements: list[DatasetChange] = []

    _compare_json_object(
        changes,
        regressions,
        "metadata",
        "metadata.json",
        _read_json_object(old_dataset / "metadata.json"),
        _read_json_object(new_dataset / "metadata.json"),
        lint_config.issue_regression_severity,
    )
    _compare_sensor_sets(changes, regressions, improvements, old_stats, new_stats)
    _compare_duration(changes, regressions, old_stats, new_stats, lint_config)
    _compare_frame_counts(changes, regressions, improvements, old_stats, new_stats, lint_config)
    _compare_frequency(changes, old_stats, new_stats)
    _compare_json_object(
        changes,
        regressions,
        "calibration",
        "calibration.json",
        _read_json_object(old_dataset / "calibration.json"),
        _read_json_object(new_dataset / "calibration.json"),
        lint_config.issue_regression_severity,
    )
    _compare_label_classes(changes, regressions, improvements, old_stats, new_stats, lint_config)
    _compare_issue_counts(
        changes,
        regressions,
        improvements,
        old_report.count_by_severity(),
        new_report.count_by_severity(),
        lint_config.issue_regression_severity,
    )
    _compare_check_counts(
        changes,
        regressions,
        improvements,
        _issue_counts_by_check(old_report.issues),
        _issue_counts_by_check(new_report.issues),
        lint_config.issue_regression_severity,
    )
    _compare_trajectory_stats(changes, regressions, old_stats, new_stats, lint_config)

    summary = {
        "change_count": len(changes),
        "regression_count": len(regressions),
        "improvement_count": len(improvements),
        "old_issue_count": len(old_report.issues),
        "new_issue_count": len(new_report.issues),
    }
    return DatasetDiffReport(
        old_path=str(old_dataset),
        new_path=str(new_dataset),
        changes=changes,
        regressions=regressions,
        improvements=improvements,
        summary=summary,
    )


def _compare_json_object(
    changes: list[DatasetChange],
    regressions: list[DatasetChange],
    category: str,
    name: str,
    old_value: dict[str, Any],
    new_value: dict[str, Any],
    regression_severity: Severity,
) -> None:
    if old_value == new_value:
        return
    change = DatasetChange(
        category=category,
        name=name,
        old_value=old_value,
        new_value=new_value,
        severity=regression_severity if category == "calibration" else "info",
        message=f"{name} changed.",
    )
    changes.append(change)
    if category == "calibration":
        regressions.append(change)


def _compare_sensor_sets(
    changes: list[DatasetChange],
    regressions: list[DatasetChange],
    improvements: list[DatasetChange],
    old_stats: DatasetStats,
    new_stats: DatasetStats,
) -> None:
    old_sensors = set(old_stats.sensors)
    new_sensors = set(new_stats.sensors)
    for sensor in sorted(old_sensors - new_sensors):
        change = DatasetChange(
            category="sensors",
            name=sensor,
            old_value="present",
            new_value="removed",
            severity="warning",
            message=f"Sensor '{sensor}' was removed.",
        )
        changes.append(change)
        regressions.append(change)
    for sensor in sorted(new_sensors - old_sensors):
        change = DatasetChange(
            category="sensors",
            name=sensor,
            old_value="absent",
            new_value="present",
            severity="info",
            message=f"Sensor '{sensor}' was added.",
        )
        changes.append(change)
        improvements.append(change)


def _compare_duration(
    changes: list[DatasetChange],
    regressions: list[DatasetChange],
    old_stats: DatasetStats,
    new_stats: DatasetStats,
    config: LintConfig,
) -> None:
    if old_stats.duration_sec is None or new_stats.duration_sec is None:
        return
    delta = new_stats.duration_sec - old_stats.duration_sec
    if delta == 0:
        return
    drop_ratio = (
        abs(delta) / old_stats.duration_sec
        if delta < 0 and old_stats.duration_sec > 0
        else 0.0
    )
    severity: Severity = "warning" if drop_ratio > config.duration_drop_ratio_warning else "info"
    change = DatasetChange(
        category="duration",
        name="duration_sec",
        old_value=old_stats.duration_sec,
        new_value=new_stats.duration_sec,
        delta=delta,
        severity=severity,
        message="Dataset duration changed.",
    )
    changes.append(change)
    if severity == "warning":
        regressions.append(change)


def _compare_frame_counts(
    changes: list[DatasetChange],
    regressions: list[DatasetChange],
    improvements: list[DatasetChange],
    old_stats: DatasetStats,
    new_stats: DatasetStats,
    config: LintConfig,
) -> None:
    for sensor in sorted(set(old_stats.frame_counts) | set(new_stats.frame_counts)):
        old_count = old_stats.frame_counts.get(sensor, 0)
        new_count = new_stats.frame_counts.get(sensor, 0)
        delta = new_count - old_count
        if delta == 0:
            continue
        drop_ratio = abs(delta) / old_count if delta < 0 and old_count > 0 else 0.0
        severity: Severity = (
            "warning" if drop_ratio > config.frame_count_drop_ratio_warning else "info"
        )
        change = DatasetChange(
            category="frame_counts",
            name=sensor,
            old_value=old_count,
            new_value=new_count,
            delta=delta,
            severity=severity,
            message=f"Frame count changed for sensor '{sensor}'.",
        )
        changes.append(change)
        if severity == "warning":
            regressions.append(change)
        elif delta > 0:
            improvements.append(change)


def _compare_frequency(
    changes: list[DatasetChange],
    old_stats: DatasetStats,
    new_stats: DatasetStats,
) -> None:
    for sensor in sorted(set(old_stats.inferred_rates_hz) | set(new_stats.inferred_rates_hz)):
        old_rate = old_stats.inferred_rates_hz.get(sensor)
        new_rate = new_stats.inferred_rates_hz.get(sensor)
        if old_rate == new_rate:
            continue
        delta = None if old_rate is None or new_rate is None else new_rate - old_rate
        changes.append(
            DatasetChange(
                category="frequency",
                name=sensor,
                old_value=old_rate,
                new_value=new_rate,
                delta=delta,
                severity="info",
                message=f"Inferred frequency changed for sensor '{sensor}'.",
            )
        )


def _compare_label_classes(
    changes: list[DatasetChange],
    regressions: list[DatasetChange],
    improvements: list[DatasetChange],
    old_stats: DatasetStats,
    new_stats: DatasetStats,
    config: LintConfig,
) -> None:
    for class_name in sorted(
        set(old_stats.label_class_counts) | set(new_stats.label_class_counts)
    ):
        old_count = old_stats.label_class_counts.get(class_name, 0)
        new_count = new_stats.label_class_counts.get(class_name, 0)
        delta = new_count - old_count
        if delta == 0:
            continue
        severity: Severity = (
            config.issue_regression_severity if old_count > 0 and new_count == 0 else "info"
        )
        change = DatasetChange(
            category="labels",
            name=class_name,
            old_value=old_count,
            new_value=new_count,
            delta=delta,
            severity=severity,
            message=f"Label class count changed for '{class_name}'.",
        )
        changes.append(change)
        if old_count > 0 and new_count == 0:
            regressions.append(change)
        elif old_count == 0 and new_count > 0:
            improvements.append(change)


def _compare_issue_counts(
    changes: list[DatasetChange],
    regressions: list[DatasetChange],
    improvements: list[DatasetChange],
    old_counts: dict[str, int],
    new_counts: dict[str, int],
    regression_severity: Severity,
) -> None:
    for severity in ("error", "warning", "info"):
        old_count = old_counts.get(severity, 0)
        new_count = new_counts.get(severity, 0)
        delta = new_count - old_count
        if delta == 0:
            continue
        change_severity: Severity = regression_severity if delta > 0 else "info"
        change = DatasetChange(
            category="issues",
            name=severity,
            old_value=old_count,
            new_value=new_count,
            delta=delta,
            severity=change_severity,
            message=f"{severity.title()} issue count changed.",
        )
        changes.append(change)
        if delta > 0 and severity in {"error", "warning"}:
            regressions.append(change)
        elif delta < 0:
            improvements.append(change)


def _compare_check_counts(
    changes: list[DatasetChange],
    regressions: list[DatasetChange],
    improvements: list[DatasetChange],
    old_counts: dict[str, int],
    new_counts: dict[str, int],
    regression_severity: Severity,
) -> None:
    watched = {
        "check_sensor_time_overlap",
        "check_pairwise_sync_gap",
        "check_unrealistic_speed",
        "check_unrealistic_acceleration",
    }
    for check_name in sorted(watched):
        old_count = old_counts.get(check_name, 0)
        new_count = new_counts.get(check_name, 0)
        delta = new_count - old_count
        if delta == 0:
            continue
        change = DatasetChange(
            category="issue_checks",
            name=check_name,
            old_value=old_count,
            new_value=new_count,
            delta=delta,
            severity=regression_severity if delta > 0 else "info",
            message=f"Issue count changed for {check_name}.",
        )
        changes.append(change)
        if delta > 0:
            regressions.append(change)
        else:
            improvements.append(change)


def _compare_trajectory_stats(
    changes: list[DatasetChange],
    regressions: list[DatasetChange],
    old_stats: DatasetStats,
    new_stats: DatasetStats,
    config: LintConfig,
) -> None:
    pairs = [
        ("speed_max", old_stats.speed_summary.max, new_stats.speed_summary.max),
        (
            "acceleration_max",
            old_stats.acceleration_summary.max,
            new_stats.acceleration_summary.max,
        ),
    ]
    for name, old_value, new_value in pairs:
        if old_value is None or new_value is None or old_value == new_value:
            continue
        delta = new_value - old_value
        change = DatasetChange(
            category="trajectories",
            name=name,
            old_value=old_value,
            new_value=new_value,
            delta=delta,
            severity=config.issue_regression_severity if delta > 0 else "info",
            message=f"Trajectory {name} changed.",
        )
        changes.append(change)
        if delta > 0:
            regressions.append(change)


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    value = read_json(path)
    if isinstance(value, dict):
        return value
    return {}


def _issue_counts_by_check(issues: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for issue in issues:
        check_name = str(issue.check_name)
        counts[check_name] = counts.get(check_name, 0) + 1
    return counts


def _escape(value: str) -> str:
    return value.replace("|", "\\|")
