"""Trajectory checks."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from datasetlint.schemas import DatasetContext, Issue, make_issue, relative_path

REQUIRED_TRAJECTORY_COLUMNS = {"timestamp", "x", "y", "yaw", "vx", "vy"}


def check_trajectory_columns(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    for name, frame in ctx.trajectory_frames.items():
        missing = sorted(REQUIRED_TRAJECTORY_COLUMNS - set(frame.columns))
        if missing:
            issues.append(
                make_issue(
                    "check_trajectory_columns",
                    "error",
                    f"Trajectory file '{name}' is missing required columns: {', '.join(missing)}.",
                    file=relative_path(ctx.path, ctx.trajectory_files[name]),
                    metadata={"missing_columns": missing},
                )
            )
    return issues


def check_trajectory_finite_values(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    for name, frame in ctx.trajectory_frames.items():
        numeric = _numeric_frame(frame)
        bad_mask = ~np.isfinite(numeric.to_numpy(dtype=float, na_value=np.nan))
        bad_rows = sorted(set(np.where(bad_mask)[0].tolist()))
        for row_index in bad_rows:
            issues.append(
                make_issue(
                    "check_trajectory_finite_values",
                    "error",
                    "Trajectory numeric values must be finite.",
                    file=relative_path(ctx.path, ctx.trajectory_files[name]),
                    row=int(frame.index[row_index]) + 2,
                )
            )
    return issues


def check_unrealistic_speed(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    for name, frame in ctx.trajectory_frames.items():
        if not {"vx", "vy"}.issubset(frame.columns):
            continue
        speeds = _speeds(frame)
        bad = speeds[speeds > ctx.config.max_speed_mps]
        for index, speed in bad.items():
            issues.append(
                make_issue(
                    "check_unrealistic_speed",
                    "warning",
                    "Trajectory speed exceeds configured maximum.",
                    file=relative_path(ctx.path, ctx.trajectory_files[name]),
                    row=int(index) + 2,
                    metadata={"speed_mps": float(speed), "max_speed_mps": ctx.config.max_speed_mps},
                )
            )
    return issues


def check_unrealistic_acceleration(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    for name, frame in ctx.trajectory_frames.items():
        if not {"timestamp", "vx", "vy"}.issubset(frame.columns):
            continue
        timestamps = pd.to_numeric(frame["timestamp"], errors="coerce")
        speeds = _speeds(frame)
        dt = timestamps.diff()
        acceleration = speeds.diff() / dt
        bad = acceleration[(dt > 0) & (acceleration.abs() > ctx.config.max_accel_mps2)]
        for index, accel in bad.items():
            issues.append(
                make_issue(
                    "check_unrealistic_acceleration",
                    "warning",
                    "Trajectory acceleration exceeds configured maximum.",
                    file=relative_path(ctx.path, ctx.trajectory_files[name]),
                    row=int(index) + 2,
                    metadata={
                        "acceleration_mps2": float(accel),
                        "max_accel_mps2": ctx.config.max_accel_mps2,
                    },
                )
            )
    return issues


def check_yaw_range(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    for name, frame in ctx.trajectory_frames.items():
        if "yaw" not in frame.columns:
            continue
        yaw = pd.to_numeric(frame["yaw"], errors="coerce")
        bad = frame[(yaw < -math.pi) | (yaw > math.pi)]
        for index in bad.index:
            issues.append(
                make_issue(
                    "check_yaw_range",
                    "warning",
                    "Yaw should be in [-pi, pi].",
                    file=relative_path(ctx.path, ctx.trajectory_files[name]),
                    row=int(index) + 2,
                )
            )
    return issues


def check_stationary_dataset(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    for name, frame in ctx.trajectory_frames.items():
        if not {"x", "y"}.issubset(frame.columns) or frame.empty:
            continue
        x = pd.to_numeric(frame["x"], errors="coerce")
        y = pd.to_numeric(frame["y"], errors="coerce")
        if x.isna().all() or y.isna().all():
            continue
        distance = float(np.hypot(x.max() - x.min(), y.max() - y.min()))
        if distance <= ctx.config.stationary_distance_threshold_m:
            issues.append(
                make_issue(
                    "check_stationary_dataset",
                    "warning",
                    "Trajectory appears stationary or nearly stationary.",
                    file=relative_path(ctx.path, ctx.trajectory_files[name]),
                    metadata={
                        "distance_m": distance,
                        "threshold_m": ctx.config.stationary_distance_threshold_m,
                    },
                )
            )
    return issues


def _numeric_frame(frame: pd.DataFrame) -> pd.DataFrame:
    numeric_columns = [column for column in frame.columns if column in REQUIRED_TRAJECTORY_COLUMNS]
    return frame[numeric_columns].apply(pd.to_numeric, errors="coerce")


def _speeds(frame: pd.DataFrame) -> pd.Series:
    vx = pd.to_numeric(frame["vx"], errors="coerce")
    vy = pd.to_numeric(frame["vy"], errors="coerce")
    return np.hypot(vx, vy)
