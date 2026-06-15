"""Timestamp checks."""

from __future__ import annotations

import pandas as pd

from datasetlint.schemas import DatasetContext, Issue, make_issue, relative_path


def check_monotonic_timestamps(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    for _name, path, frame in ctx.iter_frames():
        timestamps = _numeric_timestamps(frame)
        if timestamps is None:
            continue
        diffs = timestamps.diff()
        bad = diffs[diffs < 0]
        for index, diff in bad.items():
            issues.append(
                make_issue(
                    "check_monotonic_timestamps",
                    "error",
                    "Timestamps must be monotonically increasing.",
                    file=relative_path(ctx.path, path),
                    row=int(index) + 2,
                    metadata={"delta_sec": float(diff)},
                )
            )
    return issues


def check_duplicate_timestamps(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    for _name, path, frame in ctx.iter_frames():
        timestamps = _numeric_timestamps(frame)
        if timestamps is None:
            continue
        duplicates = timestamps[timestamps.duplicated()]
        for index, timestamp in duplicates.items():
            issues.append(
                make_issue(
                    "check_duplicate_timestamps",
                    "warning",
                    "Duplicate timestamp.",
                    file=relative_path(ctx.path, path),
                    row=int(index) + 2,
                    metadata={"timestamp": float(timestamp)},
                )
            )
    return issues


def check_large_timestamp_gaps(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    threshold = ctx.config.timestamp_gap_threshold_sec
    for _name, path, frame in ctx.iter_frames():
        timestamps = _numeric_timestamps(frame)
        if timestamps is None:
            continue
        diffs = timestamps.diff()
        gaps = diffs[diffs > threshold]
        for index, gap in gaps.items():
            issues.append(
                make_issue(
                    "check_large_timestamp_gaps",
                    "warning",
                    f"Timestamp gap exceeds {threshold:.3f}s.",
                    file=relative_path(ctx.path, path),
                    row=int(index) + 2,
                    metadata={"gap_sec": float(gap), "threshold_sec": threshold},
                )
            )
    return issues


def check_sensor_time_overlap(ctx: DatasetContext) -> list[Issue]:
    ranges: dict[str, tuple[float, float]] = {}
    for sensor, frame in ctx.sensor_frames.items():
        timestamps = _numeric_timestamps(frame)
        if timestamps is None or timestamps.empty:
            continue
        ranges[sensor] = (float(timestamps.min()), float(timestamps.max()))
    if len(ranges) < 2:
        return []
    overlap_start = max(start for start, _end in ranges.values())
    overlap_end = min(end for _start, end in ranges.values())
    if overlap_start > overlap_end:
        return [
            make_issue(
                "check_sensor_time_overlap",
                "error",
                "Sensor timestamp ranges do not overlap.",
                metadata={"ranges": ranges},
            )
        ]
    return []


def check_sensor_frequency_stability(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    threshold = ctx.config.frequency_jitter_fraction
    for sensor, frame in ctx.sensor_frames.items():
        timestamps = _numeric_timestamps(frame)
        if timestamps is None or len(timestamps) < 3:
            continue
        diffs = timestamps.diff().dropna()
        diffs = diffs[diffs > 0]
        if len(diffs) < 2:
            continue
        mean_gap = float(diffs.mean())
        if mean_gap <= 0:
            continue
        jitter = float(diffs.std(ddof=0) / mean_gap)
        if jitter > threshold:
            issues.append(
                make_issue(
                    "check_sensor_frequency_stability",
                    "warning",
                    "Sensor frame intervals are unstable.",
                    file=relative_path(ctx.path, ctx.sensor_files[sensor]),
                    metadata={"sensor": sensor, "jitter_fraction": jitter, "threshold": threshold},
                )
            )
    return issues


def _numeric_timestamps(frame: pd.DataFrame) -> pd.Series | None:
    if "timestamp" not in frame.columns:
        return None
    return pd.to_numeric(frame["timestamp"], errors="coerce")
