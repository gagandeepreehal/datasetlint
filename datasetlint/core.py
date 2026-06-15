"""Core DatasetLint API."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.errors import EmptyDataError, ParserError

from datasetlint.checks import (
    calibration,
    files,
    labels,
    metadata,
    sensors,
    timestamps,
    trajectories,
)
from datasetlint.io.csv import read_csv
from datasetlint.io.filesystem import stemmed_csv_files
from datasetlint.io.json import read_json
from datasetlint.report import LintReport
from datasetlint.schemas import DatasetContext, Issue, LintConfig, make_issue, relative_path

Check = Callable[[DatasetContext], list[Issue]]

CHECKS: tuple[Check, ...] = (
    files.check_required_files,
    files.check_empty_files,
    files.check_missing_sensor_files,
    files.check_broken_paths,
    files.check_duplicate_filenames,
    metadata.check_metadata_schema,
    metadata.check_declared_sensors_exist,
    metadata.check_duration_matches_timestamps,
    metadata.check_dataset_version_present,
    timestamps.check_monotonic_timestamps,
    timestamps.check_duplicate_timestamps,
    timestamps.check_large_timestamp_gaps,
    timestamps.check_sensor_time_overlap,
    timestamps.check_sensor_frequency_stability,
    sensors.check_sensor_columns,
    sensors.check_sensor_dimensions,
    sensors.check_sensor_frequency,
    sensors.check_missing_frames,
    calibration.check_calibration_exists,
    calibration.check_intrinsics_shape,
    calibration.check_intrinsics_values,
    calibration.check_extrinsics_shape,
    calibration.check_quaternion_norm,
    labels.check_label_columns,
    labels.check_label_confidence_range,
    labels.check_label_geometry,
    labels.check_label_timestamps_match_sensor_range,
    labels.check_track_id_consistency,
    trajectories.check_trajectory_columns,
    trajectories.check_trajectory_finite_values,
    trajectories.check_unrealistic_speed,
    trajectories.check_unrealistic_acceleration,
    trajectories.check_yaw_range,
    trajectories.check_stationary_dataset,
)


def lint_dataset(
    path: str | Path,
    config: str | Path | dict[str, Any] | LintConfig | None = None,
) -> LintReport:
    """Validate a folder-based robotics dataset."""

    dataset_path = Path(path).expanduser().resolve()
    lint_config = load_config(dataset_path, config)
    ctx = _load_context(dataset_path, lint_config)

    issues: list[Issue] = []
    issues.extend(ctx.load_issues)
    for check in CHECKS:
        issues.extend(check(ctx))

    stats = _build_stats(ctx, issues)
    passed = not any(issue.severity == "error" for issue in issues)
    return LintReport(
        dataset_path=str(dataset_path),
        issues=issues,
        stats=stats,
        passed=passed,
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
            frames[name] = read_csv(path)
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
    return {
        "issue_count": len(issues),
        "sensor_count": len(ctx.sensor_frames),
        "label_file_count": len(ctx.label_frames),
        "trajectory_file_count": len(ctx.trajectory_frames),
        "declared_sensor_count": len(ctx.declared_sensors()),
    }


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
