"""Label checks."""

from __future__ import annotations

import math
from collections.abc import Callable

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

LabelCheck = Callable[[DatasetContext], list[Issue]]


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
        if not {"track_id", "class", "timestamp"}.issubset(frame.columns):
            continue
        for track_id, group in frame.groupby("track_id", dropna=False):
            ordered = _sort_by_timestamp(group)
            class_values = [str(value) for value in ordered["class"].tolist() if pd.notna(value)]
            classes = sorted(set(class_values))
            switch_count = sum(
                1
                for previous, current in zip(class_values, class_values[1:], strict=False)
                if previous != current
            )
            if switch_count > ctx.config.label_class_switch_threshold:
                issues.append(
                    make_issue(
                        "check_track_id_consistency",
                        "warning",
                        "Track ID changes class more often than configured.",
                        file=relative_path(ctx.path, ctx.label_files[name]),
                        metadata={
                            "track_id": str(track_id),
                            "classes": classes,
                            "class_switches": switch_count,
                            "threshold": ctx.config.label_class_switch_threshold,
                        },
                    )
                )
    return issues


def check_label_bbox_jumps(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    required = {"timestamp", "track_id", "x", "y", "width", "height"}
    threshold = ctx.config.label_max_position_jump_px
    for name, frame in ctx.label_frames.items():
        if not required.issubset(frame.columns):
            continue
        numeric = _numeric_label_frame(frame)
        for track_id, group in numeric.groupby("track_id", dropna=False):
            ordered = _sort_by_timestamp(group).dropna(
                subset=["timestamp", "x", "y", "width", "height"]
            )
            if len(ordered) < 2:
                continue
            centers_x = ordered["x"] + (ordered["width"] / 2.0)
            centers_y = ordered["y"] + (ordered["height"] / 2.0)
            for position in range(1, len(ordered)):
                previous_index = ordered.index[position - 1]
                current_index = ordered.index[position]
                dx = float(centers_x.loc[current_index] - centers_x.loc[previous_index])
                dy = float(centers_y.loc[current_index] - centers_y.loc[previous_index])
                distance = math.hypot(dx, dy)
                if distance > threshold:
                    issues.append(
                        make_issue(
                            "check_label_bbox_jumps",
                            "warning",
                            "Bounding box center jumps more than configured between frames.",
                            file=relative_path(ctx.path, ctx.label_files[name]),
                            row=int(current_index) + 2,
                            metadata={
                                "track_id": str(track_id),
                                "jump_px": distance,
                                "threshold_px": threshold,
                            },
                        )
                    )
    return issues


def check_label_missing_timestamps(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    for name, frame in ctx.label_frames.items():
        if not {"timestamp", "track_id"}.issubset(frame.columns):
            continue
        timestamps = pd.to_numeric(frame["timestamp"], errors="coerce")
        work = frame[["track_id"]].copy()
        work["timestamp"] = timestamps
        for track_id, group in work.groupby("track_id", dropna=False):
            ordered = _sort_by_timestamp(group).dropna(subset=["timestamp"])
            if len(ordered) < 3:
                continue
            diffs = ordered["timestamp"].diff()
            positive_diffs = diffs[diffs > 0]
            if positive_diffs.empty:
                continue
            expected_gap = float(positive_diffs.min())
            threshold = expected_gap * 1.5
            missing = diffs[diffs > threshold]
            for index, gap in missing.items():
                estimated_missing = max(1, int(round(float(gap) / expected_gap)) - 1)
                issues.append(
                    make_issue(
                        "check_label_missing_timestamps",
                        "warning",
                        "Track has a timestamp gap that suggests missing labels.",
                        file=relative_path(ctx.path, ctx.label_files[name]),
                        row=int(index) + 2,
                        metadata={
                            "track_id": str(track_id),
                            "gap_sec": float(gap),
                            "expected_gap_sec": expected_gap,
                            "estimated_missing_labels": estimated_missing,
                        },
                    )
                )
    return issues


def check_duplicate_track_id_timestamp(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    for name, frame in ctx.label_frames.items():
        if not {"timestamp", "track_id"}.issubset(frame.columns):
            continue
        duplicates = frame[frame.duplicated(subset=["timestamp", "track_id"], keep=False)]
        for index, row in duplicates.iterrows():
            issues.append(
                make_issue(
                    "check_duplicate_track_id_timestamp",
                    "error",
                    "Duplicate track_id appears at the same timestamp.",
                    file=relative_path(ctx.path, ctx.label_files[name]),
                    row=int(index) + 2,
                    metadata={
                        "track_id": str(row["track_id"]),
                        "timestamp": _metadata_float(row["timestamp"]),
                    },
                )
            )
    return issues


def check_short_tracks(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    minimum = ctx.config.label_min_track_length
    if minimum <= 1:
        return issues
    for name, frame in ctx.label_frames.items():
        if "track_id" not in frame.columns:
            continue
        for track_id, group in frame.groupby("track_id", dropna=False):
            length = len(group)
            if length < minimum:
                issues.append(
                    make_issue(
                        "check_short_tracks",
                        "warning",
                        "Track is shorter than configured minimum length.",
                        file=relative_path(ctx.path, ctx.label_files[name]),
                        metadata={
                            "track_id": str(track_id),
                            "track_length": length,
                            "minimum_track_length": minimum,
                        },
                    )
                )
    return issues


def check_label_size_changes(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    required = {"timestamp", "track_id", "width", "height"}
    threshold = ctx.config.label_max_size_change_ratio
    for name, frame in ctx.label_frames.items():
        if not required.issubset(frame.columns):
            continue
        numeric = _numeric_label_frame(frame)
        for track_id, group in numeric.groupby("track_id", dropna=False):
            ordered = _sort_by_timestamp(group).dropna(subset=["timestamp", "width", "height"])
            if len(ordered) < 2:
                continue
            for position in range(1, len(ordered)):
                previous_index = ordered.index[position - 1]
                current_index = ordered.index[position]
                width_ratio = _size_ratio(
                    float(ordered.loc[previous_index, "width"]),
                    float(ordered.loc[current_index, "width"]),
                )
                height_ratio = _size_ratio(
                    float(ordered.loc[previous_index, "height"]),
                    float(ordered.loc[current_index, "height"]),
                )
                if width_ratio > threshold or height_ratio > threshold:
                    issues.append(
                        make_issue(
                            "check_label_size_changes",
                            "warning",
                            "Bounding box size changes more than configured between frames.",
                            file=relative_path(ctx.path, ctx.label_files[name]),
                            row=int(current_index) + 2,
                            metadata={
                                "track_id": str(track_id),
                                "width_change_ratio": width_ratio,
                                "height_change_ratio": height_ratio,
                                "threshold": threshold,
                            },
                        )
                    )
    return issues


def check_label_consistency(ctx: DatasetContext) -> list[Issue]:
    """Run all label consistency checks against a loaded dataset context."""

    issues: list[Issue] = []
    for check in LABEL_CONSISTENCY_CHECKS:
        issues.extend(check(ctx))
    return issues


LABEL_CONSISTENCY_CHECKS: tuple[LabelCheck, ...] = (
    check_label_columns,
    check_label_confidence_range,
    check_label_geometry,
    check_label_timestamps_match_sensor_range,
    check_track_id_consistency,
    check_label_bbox_jumps,
    check_label_missing_timestamps,
    check_duplicate_track_id_timestamp,
    check_short_tracks,
    check_label_size_changes,
)


def _numeric_label_frame(frame: pd.DataFrame) -> pd.DataFrame:
    numeric = frame.copy()
    for column in ("timestamp", "x", "y", "width", "height", "confidence"):
        if column in numeric.columns:
            numeric[column] = pd.to_numeric(numeric[column], errors="coerce")
    return numeric


def _sort_by_timestamp(frame: pd.DataFrame) -> pd.DataFrame:
    if "timestamp" not in frame.columns:
        return frame
    return frame.sort_values("timestamp", kind="stable")


def _size_ratio(previous: float, current: float) -> float:
    if previous <= 0 or current <= 0:
        return 1.0
    return max(previous / current, current / previous)


def _metadata_float(value: object) -> float | str:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return value
    return str(value)
