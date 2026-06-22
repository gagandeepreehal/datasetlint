"""Sensor synchronization checks."""

from __future__ import annotations

from collections.abc import Callable
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from datasetlint.schemas import DatasetContext, Issue, make_issue, relative_path

SyncCheck = Callable[[DatasetContext], list[Issue]]


def check_sensor_time_overlap(ctx: DatasetContext) -> list[Issue]:
    timestamps = _sensor_timestamps(ctx)
    timings = _sensor_timings(timestamps)
    if len(timings) < 2:
        return []

    overlap_start = max(timing["start_time"] for timing in timings.values())
    overlap_end = min(timing["end_time"] for timing in timings.values())
    if overlap_start > overlap_end:
        return [
            make_issue(
                "check_sensor_time_overlap",
                "error",
                "Sensor timestamp ranges do not overlap; align sensor streams before training.",
                metadata={"sensors": timings},
            )
        ]

    overlap_duration = overlap_end - overlap_start
    overlap_ratios = {
        sensor: _safe_ratio(overlap_duration, timing["duration_sec"])
        for sensor, timing in timings.items()
    }
    low_overlap = {
        sensor: ratio
        for sensor, ratio in overlap_ratios.items()
        if ratio < ctx.config.min_overlap_ratio
    }
    if not low_overlap:
        return []
    return [
        make_issue(
            "check_sensor_time_overlap",
            "warning",
            "Sensor timestamp overlap is smaller than configured; trim or align the streams.",
            metadata={
                "sensors": timings,
                "overlap_duration_sec": overlap_duration,
                "overlap_ratios": low_overlap,
                "min_overlap_ratio": ctx.config.min_overlap_ratio,
            },
        )
    ]


def check_timestamp_offset(ctx: DatasetContext) -> list[Issue]:
    timestamps = _sensor_timestamps(ctx)
    timings = _sensor_timings(timestamps)
    issues: list[Issue] = []
    threshold = ctx.config.max_pairwise_sync_gap_sec
    for left, right in combinations(sorted(timings), 2):
        start_offset = abs(timings[left]["start_time"] - timings[right]["start_time"])
        if start_offset > threshold:
            issues.append(
                make_issue(
                    "check_timestamp_offset",
                    "warning",
                    "Sensor stream start times differ more than configured.",
                    metadata={
                        "sensor_a": left,
                        "sensor_b": right,
                        "start_offset_sec": start_offset,
                        "threshold_sec": threshold,
                    },
                )
            )
    return issues


def check_pairwise_sync_gap(ctx: DatasetContext) -> list[Issue]:
    timestamps = _sensor_timestamps(ctx)
    issues: list[Issue] = []
    threshold = ctx.config.max_pairwise_sync_gap_sec
    for left, right in combinations(sorted(timestamps), 2):
        gaps = _nearest_timestamp_gaps(timestamps[left], timestamps[right])
        if gaps.size == 0:
            continue
        median_gap = float(np.median(gaps))
        max_gap = float(np.max(gaps))
        if median_gap > threshold:
            issues.append(
                make_issue(
                    "check_pairwise_sync_gap",
                    "warning",
                    "Pairwise sensor timestamp gap exceeds configured median threshold.",
                    metadata={
                        "sensor_a": left,
                        "sensor_b": right,
                        "median_gap_sec": median_gap,
                        "max_gap_sec": max_gap,
                        "threshold_sec": threshold,
                    },
                )
            )
    return issues


def check_missing_frame_bursts(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    threshold = ctx.config.timestamp_gap_threshold_sec
    for sensor, timestamps in _sensor_timestamps(ctx).items():
        if len(timestamps) < 2:
            continue
        gaps = timestamps.diff().dropna()
        bursts = gaps[gaps > threshold]
        median_gap = _median_positive_gap(timestamps)
        for index, gap in bursts.items():
            estimated_missing = _estimated_missing_frames(float(gap), median_gap)
            issues.append(
                make_issue(
                    "check_missing_frame_bursts",
                    "warning",
                    "Sensor has a burst-sized timestamp gap; inspect dropped frames "
                    "or logging stalls.",
                    file=relative_path(ctx.path, ctx.sensor_files[sensor]),
                    row=int(index) + 2,
                    metadata={
                        "sensor": sensor,
                        "gap_sec": float(gap),
                        "threshold_sec": threshold,
                        "estimated_missing_frames": estimated_missing,
                    },
                )
            )
    return issues


def check_frequency_stability(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    threshold = ctx.config.frequency_jitter_ratio
    for sensor, timestamps in _sensor_timestamps(ctx).items():
        if len(timestamps) < 3:
            continue
        gaps = timestamps.diff().dropna()
        gaps = gaps[gaps > 0]
        if len(gaps) < 2:
            continue
        mean_gap = float(gaps.mean())
        if mean_gap <= 0:
            continue
        jitter = float(gaps.std(ddof=0) / mean_gap)
        if jitter > threshold:
            issues.append(
                make_issue(
                    "check_frequency_stability",
                    "warning",
                    "Sensor frame interval jitter exceeds configured ratio.",
                    file=relative_path(ctx.path, ctx.sensor_files[sensor]),
                    metadata={
                        "sensor": sensor,
                        "jitter_ratio": jitter,
                        "threshold": threshold,
                    },
                )
            )
    return issues


def check_sensor_synchronization(ctx: DatasetContext) -> list[Issue]:
    """Run all sensor synchronization checks against a loaded dataset context."""

    issues: list[Issue] = []
    for check in SENSOR_SYNC_CHECKS:
        issues.extend(check(ctx))
    return issues


def sensor_sync_diagnostics(ctx: DatasetContext) -> dict[str, Any]:
    """Return lightweight synchronization diagnostics for reports and stats."""

    timestamps = _sensor_timestamps(ctx)
    timings = _sensor_timings(timestamps)
    pairwise_gaps: dict[str, dict[str, float]] = {}
    for left, right in combinations(sorted(timestamps), 2):
        gaps = _nearest_timestamp_gaps(timestamps[left], timestamps[right])
        if gaps.size == 0:
            continue
        pairwise_gaps[f"{left}:{right}"] = {
            "median_gap_sec": float(np.median(gaps)),
            "max_gap_sec": float(np.max(gaps)),
        }

    overlap_duration: float | None = None
    if len(timings) >= 2:
        overlap_start = max(timing["start_time"] for timing in timings.values())
        overlap_end = min(timing["end_time"] for timing in timings.values())
        overlap_duration = max(0.0, overlap_end - overlap_start)

    return {
        "sensors": timings,
        "overlap_duration_sec": overlap_duration,
        "pairwise_gaps": pairwise_gaps,
    }


SENSOR_SYNC_CHECKS: tuple[SyncCheck, ...] = (
    check_sensor_time_overlap,
    check_timestamp_offset,
    check_pairwise_sync_gap,
    check_missing_frame_bursts,
    check_frequency_stability,
)


def _sensor_timestamps(ctx: DatasetContext) -> dict[str, pd.Series]:
    result: dict[str, pd.Series] = {}
    for sensor, frame in ctx.sensor_frames.items():
        if "timestamp" not in frame.columns:
            continue
        timestamps = pd.to_numeric(frame["timestamp"], errors="coerce").dropna().sort_values()
        if not timestamps.empty:
            result[sensor] = timestamps
    return result


def _sensor_timings(timestamps: dict[str, pd.Series]) -> dict[str, dict[str, float]]:
    timings: dict[str, dict[str, float]] = {}
    for sensor, values in timestamps.items():
        start_time = float(values.iloc[0])
        end_time = float(values.iloc[-1])
        duration = max(0.0, end_time - start_time)
        median_gap = _median_positive_gap(values)
        max_gap = _max_positive_gap(values)
        inferred_frequency = 1.0 / median_gap if median_gap and median_gap > 0 else 0.0
        timings[sensor] = {
            "start_time": start_time,
            "end_time": end_time,
            "duration_sec": duration,
            "frame_count": float(len(values)),
            "inferred_frequency_hz": inferred_frequency,
            "median_dt_sec": median_gap or 0.0,
            "max_dt_sec": max_gap or 0.0,
        }
    return timings


def _nearest_timestamp_gaps(left: pd.Series, right: pd.Series) -> NDArray[np.float64]:
    if left.empty or right.empty:
        return np.asarray([], dtype=float)
    source = left.to_numpy(dtype=float)
    target = right.to_numpy(dtype=float)
    if len(source) > len(target):
        source, target = target, source
    insertions = np.searchsorted(target, source)
    gaps: list[float] = []
    for index, timestamp in zip(insertions, source, strict=True):
        candidates: list[float] = []
        if index < len(target):
            candidates.append(abs(float(target[index] - timestamp)))
        if index > 0:
            candidates.append(abs(float(target[index - 1] - timestamp)))
        if candidates:
            gaps.append(min(candidates))
    return np.asarray(gaps, dtype=float)


def _median_positive_gap(timestamps: pd.Series) -> float | None:
    gaps = timestamps.diff().dropna()
    gaps = gaps[gaps > 0]
    if gaps.empty:
        return None
    return float(gaps.median())


def _max_positive_gap(timestamps: pd.Series) -> float | None:
    gaps = timestamps.diff().dropna()
    gaps = gaps[gaps > 0]
    if gaps.empty:
        return None
    return float(gaps.max())


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 1.0
    return numerator / denominator


def _estimated_missing_frames(gap: float, expected_gap: float | None) -> int:
    if expected_gap is None or expected_gap <= 0:
        return 1
    return max(1, int(round(gap / expected_gap)) - 1)
