"""Sensor checks."""

from __future__ import annotations

import pandas as pd

from datasetlint.schemas import DatasetContext, Issue, make_issue, relative_path


def check_sensor_columns(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    for sensor, frame in ctx.sensor_frames.items():
        missing = sorted(_required_columns(sensor) - set(frame.columns))
        if missing:
            issues.append(
                make_issue(
                    "check_sensor_columns",
                    "error",
                    f"Sensor '{sensor}' is missing required columns: {', '.join(missing)}.",
                    file=relative_path(ctx.path, ctx.sensor_files[sensor]),
                    metadata={"sensor": sensor, "missing_columns": missing},
                )
            )
    return issues


def check_sensor_dimensions(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    for sensor, frame in ctx.sensor_frames.items():
        if "camera" not in sensor or not {"width", "height"}.issubset(frame.columns):
            continue
        widths = pd.to_numeric(frame["width"], errors="coerce")
        heights = pd.to_numeric(frame["height"], errors="coerce")
        bad = frame[(widths <= 0) | (heights <= 0) | widths.isna() | heights.isna()]
        for index in bad.index:
            issues.append(
                make_issue(
                    "check_sensor_dimensions",
                    "error",
                    "Camera width and height must be positive numbers.",
                    file=relative_path(ctx.path, ctx.sensor_files[sensor]),
                    row=int(index) + 2,
                    metadata={"sensor": sensor},
                )
            )
    return issues


def check_sensor_frequency(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    for sensor, expected_rate in ctx.config.expected_sensor_rates.items():
        frame = ctx.sensor_frames.get(sensor)
        if frame is None or "timestamp" not in frame.columns:
            continue
        timestamps = pd.to_numeric(frame["timestamp"], errors="coerce").dropna()
        if len(timestamps) < 2:
            continue
        gaps = timestamps.diff().dropna()
        gaps = gaps[gaps > 0]
        if gaps.empty:
            continue
        observed_rate = float(1.0 / gaps.mean())
        relative_delta = abs(observed_rate - expected_rate) / expected_rate
        if relative_delta > ctx.config.frequency_tolerance_fraction:
            issues.append(
                make_issue(
                    "check_sensor_frequency",
                    "warning",
                    "Observed sensor rate differs from expected rate.",
                    file=relative_path(ctx.path, ctx.sensor_files[sensor]),
                    metadata={
                        "sensor": sensor,
                        "expected_hz": expected_rate,
                        "observed_hz": observed_rate,
                    },
                )
            )
    return issues


def check_missing_frames(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    for sensor, frame in ctx.sensor_frames.items():
        if "timestamp" not in frame.columns:
            continue
        timestamps = pd.to_numeric(frame["timestamp"], errors="coerce").dropna()
        if len(timestamps) < 3:
            continue
        gaps = timestamps.diff().dropna()
        positive_gaps = gaps[gaps > 0]
        if positive_gaps.empty:
            continue
        fallback_rate = 1.0 / positive_gaps.median()
        expected_rate = ctx.config.expected_sensor_rates.get(sensor, fallback_rate)
        expected_gap = 1.0 / expected_rate
        threshold = expected_gap * ctx.config.missing_frame_gap_multiplier
        missing = gaps[gaps > threshold]
        for index, gap in missing.items():
            issues.append(
                make_issue(
                    "check_missing_frames",
                    "warning",
                    "Likely missing frame based on timestamp gap.",
                    file=relative_path(ctx.path, ctx.sensor_files[sensor]),
                    row=int(index) + 2,
                    metadata={
                        "sensor": sensor,
                        "gap_sec": float(gap),
                        "expected_gap_sec": expected_gap,
                    },
                )
            )
    return issues


def _required_columns(sensor: str) -> set[str]:
    if "camera" in sensor:
        return {"timestamp", "path", "width", "height"}
    if sensor == "imu" or sensor.endswith("_imu"):
        return {"timestamp", "ax", "ay", "az", "gx", "gy", "gz"}
    if sensor == "gps" or sensor.endswith("_gps"):
        return {"timestamp", "lat", "lon", "alt"}
    return {"timestamp"}
