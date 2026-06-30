"""Typed schemas shared by DatasetLint checks."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

Severity = Literal["info", "warning", "error"]


class Issue(BaseModel):
    """A single lint finding."""

    check_name: str
    severity: Severity
    message: str
    file: str | None = None
    row: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuleSelectionConfig(BaseModel):
    """Config-file rule selection and severity overrides."""

    model_config = ConfigDict(extra="forbid")

    enabled: list[str] | None = None
    disabled: list[str] = Field(default_factory=list)
    severity: dict[str, Severity] = Field(default_factory=dict)


class LintConfig(BaseModel):
    """Configuration knobs for checks."""

    model_config = ConfigDict(extra="forbid")

    timestamp_gap_threshold_sec: float = 0.5
    frequency_tolerance_fraction: float = 0.30
    missing_frame_gap_multiplier: float = 1.5
    max_speed_mps: float = 70.0
    max_accel_mps2: float = 12.0
    stationary_distance_threshold_m: float = 0.05
    duration_tolerance_sec: float = 1.0
    label_max_position_jump_px: float = 200.0
    label_max_size_change_ratio: float = 3.0
    label_min_track_length: int = 3
    label_class_switch_threshold: int = 0
    max_pairwise_sync_gap_sec: float = 0.05
    min_overlap_ratio: float = 0.8
    frequency_jitter_ratio: float = 0.2
    frame_count_drop_ratio_warning: float = 0.1
    duration_drop_ratio_warning: float = 0.1
    issue_regression_severity: Severity = "warning"
    rules: RuleSelectionConfig = Field(default_factory=RuleSelectionConfig)
    expected_sensor_rates: dict[str, float] = Field(
        default_factory=lambda: {
            "camera_front": 10.0,
            "camera_rear": 10.0,
            "imu": 100.0,
            "gps": 10.0,
        }
    )


@dataclass(slots=True)
class DatasetContext:
    """Loaded dataset data shared by checks."""

    path: Path
    config: LintConfig
    metadata: dict[str, Any] | None
    calibration: dict[str, Any] | None
    sensor_frames: dict[str, pd.DataFrame]
    sensor_files: dict[str, Path]
    label_frames: dict[str, pd.DataFrame]
    label_files: dict[str, Path]
    trajectory_frames: dict[str, pd.DataFrame]
    trajectory_files: dict[str, Path]
    load_issues: list[Issue]

    def declared_sensors(self) -> list[str]:
        if not isinstance(self.metadata, dict):
            return []
        sensors = self.metadata.get("sensors", [])
        if not isinstance(sensors, list):
            return []
        return [sensor for sensor in sensors if isinstance(sensor, str)]

    def iter_frames(self) -> Iterator[tuple[str, Path, pd.DataFrame]]:
        for name, frame in self.sensor_frames.items():
            yield f"sensors/{name}", self.sensor_files[name], frame
        for name, frame in self.label_frames.items():
            yield f"labels/{name}", self.label_files[name], frame
        for name, frame in self.trajectory_frames.items():
            yield f"trajectories/{name}", self.trajectory_files[name], frame


def make_issue(
    check_name: str,
    severity: Severity,
    message: str,
    *,
    file: str | None = None,
    row: int | None = None,
    metadata: dict[str, Any] | None = None,
    suggestion: str | None = None,
) -> Issue:
    """Create an issue with a consistent default metadata mapping."""

    issue_metadata = dict(metadata or {})
    resolved_suggestion = suggestion or _DEFAULT_SUGGESTIONS.get(check_name)
    if resolved_suggestion and "suggestion" not in issue_metadata:
        issue_metadata["suggestion"] = resolved_suggestion
    return Issue(
        check_name=check_name,
        severity=severity,
        message=_format_issue_message(message, file=file, row=row, suggestion=resolved_suggestion),
        file=file,
        row=row,
        metadata=issue_metadata,
    )


def relative_path(base: Path, path: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def _format_issue_message(
    message: str,
    *,
    file: str | None,
    row: int | None,
    suggestion: str | None,
) -> str:
    parts = [message.rstrip()]
    if file is not None:
        location = f"{file}:{row}" if row is not None else file
        parts.append(f"Location: {location}.")
    if suggestion:
        parts.append(f"Fix: {suggestion}")
    return " ".join(parts)


_DEFAULT_SUGGESTIONS: dict[str, str] = {
    "load_dataset": "check that the dataset path points at the expected dataset root.",
    "load_json": "open the referenced JSON file and fix invalid syntax or top-level structure.",
    "load_csv": "open the referenced CSV row range and fix malformed delimiters or values.",
    "select_checks": "use a configured rule group or check name from datasetlint rules.",
    "check_required_files": "add the missing file or use an adapter for this layout.",
    "check_empty_files": "replace empty files with exported data or remove stale references.",
    "check_missing_sensor_files": "add the sensor CSV or remove the stale declaration.",
    "check_broken_paths": "fix the relative path so it resolves inside the dataset root.",
    "check_duplicate_filenames": "rename duplicate files or move them under unique logical paths.",
    "check_metadata_schema": "update metadata.json to match the documented DatasetLint schema.",
    "check_declared_sensors_exist": "add declared sensor CSVs or remove stale metadata entries.",
    "check_duration_matches_timestamps": "recompute duration from timestamps or trim streams.",
    "check_dataset_version_present": "add a dataset version field to metadata.json.",
    "check_monotonic_timestamps": "sort rows by timestamp and remove clock resets.",
    "check_duplicate_timestamps": "deduplicate rows or add unique frame timestamps.",
    "check_large_timestamp_gaps": "inspect dropped frames, logging stalls, or the threshold.",
    "check_sensor_columns": "add missing sensor columns or rename to the expected schema.",
    "check_sensor_dimensions": "fix non-positive or non-numeric camera width and height values.",
    "check_sensor_frequency": "update expected_sensor_rates or inspect dropped samples.",
    "check_missing_frames": "inspect the gap and regenerate the sensor index if needed.",
    "check_sensor_time_overlap": "trim streams to a shared time window or correct clock offsets.",
    "check_timestamp_offset": "align stream start times or correct sensor clock synchronization.",
    "check_pairwise_sync_gap": "resync the sensors or tune max_pairwise_sync_gap_sec.",
    "check_missing_frame_bursts": "inspect dropped frame bursts around the reported CSV row.",
    "check_frequency_stability": "inspect frame jitter or tune frequency_jitter_ratio.",
    "check_calibration_exists": "add calibration.json or disable calibration checks.",
    "check_intrinsics_shape": "write camera intrinsics as numeric 3x3 matrices.",
    "check_intrinsics_values": "fix focal length or principal point values.",
    "check_extrinsics_shape": "write sensor extrinsics as numeric 4x4 matrices.",
    "check_quaternion_norm": "normalize quaternions or regenerate calibration.",
    "check_label_columns": "add missing label columns or map the label export.",
    "check_label_confidence_range": "clamp confidence values to [0, 1] or fix the label exporter.",
    "check_label_geometry": "fix non-positive bounding-box width or height values.",
    "check_label_timestamps_match_sensor_range": "drop out-of-range labels or add sensor rows.",
    "check_track_id_consistency": "split reused track IDs or correct class labels.",
    "check_label_bbox_jumps": "inspect the reported track for tracking ID switches or bad boxes.",
    "check_label_missing_timestamps": "fill missing labels or split tracks across visibility gaps.",
    "check_duplicate_track_id_timestamp": "keep one label row per track and timestamp.",
    "check_short_tracks": "remove one-off tracks or lower label_min_track_length deliberately.",
    "check_label_size_changes": "inspect abrupt box scale changes for bad labels or ID switches.",
    "check_trajectory_columns": "add missing columns or export ego motion in DatasetLint format.",
    "check_trajectory_finite_values": "replace NaN or infinite trajectory values before linting.",
    "check_unrealistic_speed": "verify units/timestamps or raise max_speed_mps.",
    "check_unrealistic_acceleration": "verify units/timestamps or raise max_accel_mps2.",
    "check_yaw_range": "normalize yaw values into radians within [-pi, pi].",
    "check_stationary_dataset": "confirm stationary data or inspect trajectory export.",
}
