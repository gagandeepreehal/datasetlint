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
) -> Issue:
    """Create an issue with a consistent default metadata mapping."""

    return Issue(
        check_name=check_name,
        severity=severity,
        message=message,
        file=file,
        row=row,
        metadata=metadata or {},
    )


def relative_path(base: Path, path: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)
