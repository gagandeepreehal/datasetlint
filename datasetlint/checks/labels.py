"""Label checks."""

from __future__ import annotations

import pandas as pd

from datasetlint.schemas import DatasetContext, Issue, make_issue, relative_path

REQUIRED_LABEL_COLUMNS = {
    "timestamp",
    "track_id",
    "class",
    "x",
    "y",
    "width",
    "height",
    "confidence",
}


def check_label_columns(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    for name, frame in ctx.label_frames.items():
        missing = sorted(REQUIRED_LABEL_COLUMNS - set(frame.columns))
        if missing:
            issues.append(
                make_issue(
                    "check_label_columns",
                    "error",
                    f"Label file '{name}' is missing required columns: {', '.join(missing)}.",
                    file=relative_path(ctx.path, ctx.label_files[name]),
                    metadata={"missing_columns": missing},
                )
            )
    return issues


def check_label_confidence_range(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    for name, frame in ctx.label_frames.items():
        if "confidence" not in frame.columns:
            continue
        confidence = pd.to_numeric(frame["confidence"], errors="coerce")
        bad = frame[(confidence < 0) | (confidence > 1) | confidence.isna()]
        for index in bad.index:
            issues.append(
                make_issue(
                    "check_label_confidence_range",
                    "error",
                    "Label confidence must be in [0, 1].",
                    file=relative_path(ctx.path, ctx.label_files[name]),
                    row=int(index) + 2,
                )
            )
    return issues


def check_label_geometry(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    for name, frame in ctx.label_frames.items():
        if not {"width", "height"}.issubset(frame.columns):
            continue
        widths = pd.to_numeric(frame["width"], errors="coerce")
        heights = pd.to_numeric(frame["height"], errors="coerce")
        bad = frame[(widths <= 0) | (heights <= 0) | widths.isna() | heights.isna()]
        for index in bad.index:
            issues.append(
                make_issue(
                    "check_label_geometry",
                    "error",
                    "Label width and height must be positive.",
                    file=relative_path(ctx.path, ctx.label_files[name]),
                    row=int(index) + 2,
                )
            )
    return issues


def check_label_timestamps_match_sensor_range(ctx: DatasetContext) -> list[Issue]:
    sensor_ranges: list[tuple[float, float]] = []
    for frame in ctx.sensor_frames.values():
        if "timestamp" not in frame.columns or frame.empty:
            continue
        timestamps = pd.to_numeric(frame["timestamp"], errors="coerce").dropna()
        if not timestamps.empty:
            sensor_ranges.append((float(timestamps.min()), float(timestamps.max())))
    if not sensor_ranges:
        return []
    min_sensor_time = min(start for start, _end in sensor_ranges)
    max_sensor_time = max(end for _start, end in sensor_ranges)
    issues: list[Issue] = []
    for name, frame in ctx.label_frames.items():
        if "timestamp" not in frame.columns:
            continue
        timestamps = pd.to_numeric(frame["timestamp"], errors="coerce")
        bad = frame[
            (timestamps < min_sensor_time) | (timestamps > max_sensor_time) | timestamps.isna()
        ]
        for index in bad.index:
            issues.append(
                make_issue(
                    "check_label_timestamps_match_sensor_range",
                    "error",
                    "Label timestamp is outside the observed sensor timestamp range.",
                    file=relative_path(ctx.path, ctx.label_files[name]),
                    row=int(index) + 2,
                    metadata={
                        "min_sensor_time": min_sensor_time,
                        "max_sensor_time": max_sensor_time,
                    },
                )
            )
    return issues


def check_track_id_consistency(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    for name, frame in ctx.label_frames.items():
        if not {"track_id", "class"}.issubset(frame.columns):
            continue
        for track_id, group in frame.groupby("track_id", dropna=False):
            classes = sorted(str(value) for value in group["class"].dropna().unique())
            if len(classes) > 1:
                issues.append(
                    make_issue(
                        "check_track_id_consistency",
                        "warning",
                        "Track ID is associated with multiple class names.",
                        file=relative_path(ctx.path, ctx.label_files[name]),
                        metadata={"track_id": str(track_id), "classes": classes},
                    )
                )
    return issues
