"""Core DatasetLint API."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.errors import EmptyDataError, ParserError

from datasetlint.adapters import DatasetAdapter, FolderAdapter, get_adapter
from datasetlint.checks import (
    calibration,
    files,
    labels,
    metadata,
    sensors,
    sync,
    timestamps,
    trajectories,
)
from datasetlint.io.csv import read_csv
from datasetlint.io.filesystem import stemmed_csv_files
from datasetlint.io.json import read_json
from datasetlint.report import LintReport
from datasetlint.schemas import DatasetContext, Issue, LintConfig, make_issue, relative_path

Check = Callable[[DatasetContext], list[Issue]]

FILE_CHECKS: tuple[Check, ...] = (
    files.check_required_files,
    files.check_empty_files,
    files.check_missing_sensor_files,
    files.check_broken_paths,
    files.check_duplicate_filenames,
)
METADATA_CHECKS: tuple[Check, ...] = (
    metadata.check_metadata_schema,
    metadata.check_declared_sensors_exist,
    metadata.check_duration_matches_timestamps,
    metadata.check_dataset_version_present,
)
TIMESTAMP_CHECKS: tuple[Check, ...] = (
    timestamps.check_monotonic_timestamps,
    timestamps.check_duplicate_timestamps,
    timestamps.check_large_timestamp_gaps,
)
SENSOR_CHECKS: tuple[Check, ...] = (
    sensors.check_sensor_columns,
    sensors.check_sensor_dimensions,
    sensors.check_sensor_frequency,
    sensors.check_missing_frames,
)
SYNC_CHECKS: tuple[Check, ...] = sync.SENSOR_SYNC_CHECKS
CALIBRATION_CHECKS: tuple[Check, ...] = (
    calibration.check_calibration_exists,
    calibration.check_intrinsics_shape,
    calibration.check_intrinsics_values,
    calibration.check_extrinsics_shape,
    calibration.check_quaternion_norm,
)
LABEL_CHECKS: tuple[Check, ...] = labels.LABEL_CONSISTENCY_CHECKS
TRAJECTORY_CHECKS: tuple[Check, ...] = (
    trajectories.check_trajectory_columns,
    trajectories.check_trajectory_finite_values,
    trajectories.check_unrealistic_speed,
    trajectories.check_unrealistic_acceleration,
    trajectories.check_yaw_range,
    trajectories.check_stationary_dataset,
)

CHECK_GROUPS: dict[str, tuple[Check, ...]] = {
    "files": FILE_CHECKS,
    "metadata": METADATA_CHECKS,
    "timestamps": TIMESTAMP_CHECKS,
    "sensors": SENSOR_CHECKS,
    "sync": SYNC_CHECKS,
    "calibration": CALIBRATION_CHECKS,
    "labels": LABEL_CHECKS,
    "trajectories": TRAJECTORY_CHECKS,
}
CHECKS: tuple[Check, ...] = (
    FILE_CHECKS
    + METADATA_CHECKS
    + TIMESTAMP_CHECKS
    + SENSOR_CHECKS
    + SYNC_CHECKS
    + CALIBRATION_CHECKS
    + LABEL_CHECKS
    + TRAJECTORY_CHECKS
)


def lint_dataset(
    path: str | Path,
    config: str | Path | dict[str, Any] | LintConfig | None = None,
    checks: str | list[str] | tuple[str, ...] | None = None,
    adapter: str = "folder",
) -> LintReport:
    """Validate a folder-based robotics dataset."""

    dataset_path = Path(path).expanduser().resolve()
    lint_config = load_config(dataset_path, config)
    try:
        selected_checks = _select_checks(checks)
    except ValueError as exc:
        issue = make_issue(
            "select_checks",
            "error",
            str(exc),
            file=str(dataset_path),
        )
        return LintReport(
            dataset_path=str(dataset_path),
            issues=[issue],
            stats={
                "issue_count": 1,
                "issue_count_by_severity": {"info": 0, "warning": 0, "error": 1},
            },
            passed=False,
            checks_run=[],
            adapter={"name": adapter},
            config=_config_dict(lint_config),
            dataset_fingerprint=_dataset_fingerprint(dataset_path),
        )
    selected_adapter = _select_adapter(dataset_path, adapter)
    if not isinstance(selected_adapter, FolderAdapter):
        issue = make_issue(
            "load_dataset",
            "error",
            f"Adapter '{selected_adapter.name}' is detection-only in DatasetLint v0; "
            "convert the dataset to the folder CSV format before linting.",
            file=str(dataset_path),
            metadata={"adapter": selected_adapter.name},
        )
        return LintReport(
            dataset_path=str(dataset_path),
            issues=[issue],
            stats={"issue_count": 1},
            passed=False,
            checks_run=[],
            adapter={
                "name": selected_adapter.name,
                "mode": "detection-only",
            },
            config=_config_dict(lint_config),
            dataset_fingerprint=_dataset_fingerprint(dataset_path),
        )

    ctx = _load_context(dataset_path, lint_config)

    issues: list[Issue] = []
    issues.extend(ctx.load_issues)
    for check in selected_checks:
        issues.extend(check(ctx))

    stats = _build_stats(ctx, issues)
    passed = not any(issue.severity == "error" for issue in issues)
    return LintReport(
        dataset_path=str(dataset_path),
        issues=issues,
        stats=stats,
        passed=passed,
        dataset_summary=_dataset_summary(ctx),
        checks_run=[check.__name__ for check in selected_checks],
        adapter={"name": selected_adapter.name, "mode": "folder"},
        config=_config_dict(lint_config),
        dataset_fingerprint=_dataset_fingerprint(dataset_path),
    )


def load_config(
    dataset_path: Path,
    config: str | Path | dict[str, Any] | LintConfig | None,
) -> LintConfig:
    if isinstance(config, LintConfig):
        return config
    if isinstance(config, dict):
        return LintConfig(**config)
    config_path: Path | None
    if config is None:
        candidate = dataset_path / "datasetlint.yaml"
        config_path = candidate if candidate.is_file() else None
    else:
        config_path = Path(config).expanduser()
    if config_path is None:
        return LintConfig()
    return LintConfig(**_parse_simple_yaml(config_path))


def _load_context(dataset_path: Path, config: LintConfig) -> DatasetContext:
    load_issues: list[Issue] = []
    if not dataset_path.exists():
        load_issues.append(
            make_issue(
                "load_dataset",
                "error",
                "Dataset path does not exist.",
                file=str(dataset_path),
            )
        )
    elif not dataset_path.is_dir():
        load_issues.append(
            make_issue(
                "load_dataset",
                "error",
                "Dataset path must be a directory.",
                file=str(dataset_path),
            )
        )

    metadata_doc = _load_json_doc(dataset_path, "metadata.json", load_issues)
    calibration_doc = _load_json_doc(dataset_path, "calibration.json", load_issues)
    sensor_frames, sensor_files = _load_csv_dir(dataset_path, "sensors", load_issues)
    label_frames, label_files = _load_csv_dir(dataset_path, "labels", load_issues)
    trajectory_frames, trajectory_files = _load_csv_dir(dataset_path, "trajectories", load_issues)
    return DatasetContext(
        path=dataset_path,
        config=config,
        metadata=metadata_doc if isinstance(metadata_doc, dict) else metadata_doc,
        calibration=calibration_doc if isinstance(calibration_doc, dict) else calibration_doc,
        sensor_frames=sensor_frames,
        sensor_files=sensor_files,
        label_frames=label_frames,
        label_files=label_files,
        trajectory_frames=trajectory_frames,
        trajectory_files=trajectory_files,
        load_issues=load_issues,
    )


def _load_json_doc(dataset_path: Path, filename: str, issues: list[Issue]) -> dict[str, Any] | None:
    json_path = dataset_path / filename
    if not json_path.is_file():
        return None
    try:
        value = read_json(json_path)
    except ValueError as exc:
        issues.append(
            make_issue(
                "load_json",
                "error",
                f"Could not parse {filename}: {exc}.",
                file=filename,
            )
        )
        return None
    if not isinstance(value, dict):
        issues.append(
            make_issue(
                "load_json",
                "error",
                f"{filename} must contain a JSON object.",
                file=filename,
            )
        )
        return None
    return value


def _load_csv_dir(
    dataset_path: Path,
    folder_name: str,
    issues: list[Issue],
) -> tuple[dict[str, pd.DataFrame], dict[str, Path]]:
    frames: dict[str, pd.DataFrame] = {}
    paths = stemmed_csv_files(dataset_path / folder_name)
    for name, path in paths.items():
        try:
            frame = read_csv(path)
            if (
                folder_name == "sensors"
                and "camera" in name
                and "path" not in frame.columns
                and "filename" in frame.columns
            ):
                frame = frame.rename(columns={"filename": "path"})
            frames[name] = frame
        except EmptyDataError:
            continue
        except (ParserError, UnicodeDecodeError, ValueError) as exc:
            issues.append(
                make_issue(
                    "load_csv",
                    "error",
                    f"Could not parse CSV file: {exc}.",
                    file=relative_path(dataset_path, path),
                )
            )
    return frames, paths


def _build_stats(ctx: DatasetContext, issues: list[Issue]) -> dict[str, Any]:
    by_severity = {"info": 0, "warning": 0, "error": 0}
    for issue in issues:
        by_severity[issue.severity] += 1
    return {
        "issue_count": len(issues),
        "issue_count_by_severity": by_severity,
        "sensor_count": len(ctx.sensor_frames),
        "label_file_count": len(ctx.label_frames),
        "trajectory_file_count": len(ctx.trajectory_frames),
        "declared_sensor_count": len(ctx.declared_sensors()),
        "sync": sync.sensor_sync_diagnostics(ctx),
    }


def _dataset_summary(ctx: DatasetContext) -> dict[str, Any]:
    return {
        "declared_sensors": ctx.declared_sensors(),
        "available_modalities": _available_modalities(ctx),
        "sensor_count": len(ctx.sensor_frames),
        "label_file_count": len(ctx.label_frames),
        "trajectory_file_count": len(ctx.trajectory_frames),
        "sensor_frame_counts": {name: len(frame) for name, frame in ctx.sensor_frames.items()},
        "label_row_counts": {name: len(frame) for name, frame in ctx.label_frames.items()},
        "trajectory_row_counts": {
            name: len(frame) for name, frame in ctx.trajectory_frames.items()
        },
    }


def _available_modalities(ctx: DatasetContext) -> list[str]:
    modalities: list[str] = []
    if ctx.sensor_frames:
        modalities.append("sensors")
    if ctx.label_frames:
        modalities.append("labels")
    if ctx.trajectory_frames:
        modalities.append("trajectories")
    if ctx.calibration is not None:
        modalities.append("calibration")
    if ctx.metadata is not None:
        modalities.append("metadata")
    return modalities


def _config_dict(config: LintConfig) -> dict[str, Any]:
    if hasattr(config, "model_dump"):
        return config.model_dump()
    return config.dict()


def _dataset_fingerprint(dataset_path: Path) -> str | None:
    if not dataset_path.exists() or not dataset_path.is_dir():
        return None
    digest = hashlib.sha256()
    for path in sorted(item for item in dataset_path.rglob("*") if item.is_file()):
        relative = path.relative_to(dataset_path).as_posix()
        try:
            stat = path.stat()
        except OSError:
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(str(stat.st_size).encode("ascii"))
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _select_checks(checks: str | list[str] | tuple[str, ...] | None) -> tuple[Check, ...]:
    if checks is None:
        return _deduplicate_overlapping_checks(CHECKS)
    names: list[str] = []
    if isinstance(checks, str):
        names.extend(name.strip().lower() for name in checks.split(",") if name.strip())
    else:
        for item in checks:
            names.extend(name.strip().lower() for name in item.split(",") if name.strip())
    if not names or names == ["all"]:
        return _deduplicate_overlapping_checks(CHECKS)

    selected: list[Check] = []
    seen: set[Check] = set()
    for name in names:
        group: tuple[Check, ...]
        if name == "all":
            group = CHECKS
        else:
            maybe_group = CHECK_GROUPS.get(name)
            if maybe_group is None:
                valid = ", ".join(sorted([*CHECK_GROUPS, "all"]))
                raise ValueError(f"Unknown check group '{name}'. Valid groups: {valid}.")
            group = maybe_group
        for check in group:
            if check not in seen:
                selected.append(check)
                seen.add(check)
    return _deduplicate_overlapping_checks(tuple(selected))


def _deduplicate_overlapping_checks(selected: tuple[Check, ...]) -> tuple[Check, ...]:
    if (
        timestamps.check_large_timestamp_gaps not in selected
        or sync.check_missing_frame_bursts not in selected
    ):
        return selected
    return tuple(check for check in selected if check is not sync.check_missing_frame_bursts)


def validate_checks(checks: str | list[str] | tuple[str, ...] | None) -> None:
    """Raise ``ValueError`` when a check selection is not valid."""

    _select_checks(checks)


def _select_adapter(dataset_path: Path, adapter: str) -> DatasetAdapter:
    if adapter == "folder":
        return FolderAdapter()
    if adapter == "auto" and not dataset_path.exists():
        return FolderAdapter()
    return get_adapter(dataset_path, adapter)


def _parse_simple_yaml(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_map: dict[str, Any] | None = None
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.split("#", 1)[0].rstrip()
            if not line.strip():
                continue
            if line.startswith((" ", "\t")):
                if current_map is None:
                    continue
                key, value = _split_yaml_pair(line.strip(), path)
                current_map[key] = _parse_scalar(value)
                continue
            key, value = _split_yaml_pair(line, path)
            if value == "":
                current_map = {}
                data[key] = current_map
            else:
                data[key] = _parse_scalar(value)
                current_map = None
    return data


def _split_yaml_pair(line: str, path: Path) -> tuple[str, str]:
    if ":" not in line:
        raise ValueError(f"Unsupported config line in {path}: {line}")
    key, value = line.split(":", 1)
    return key.strip(), value.strip()


def _parse_scalar(value: str) -> Any:
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    stripped = value.strip("\"'")
    try:
        if any(char in stripped for char in (".", "e", "E")):
            return float(stripped)
        return int(stripped)
    except ValueError:
        return stripped
