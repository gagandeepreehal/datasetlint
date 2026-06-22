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


def _numeric_timestamps(frame: pd.DataFrame) -> pd.Series | None:
    if "timestamp" not in frame.columns:
        return None
    return pd.to_numeric(frame["timestamp"], errors="coerce")
