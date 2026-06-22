"""Dataset statistics and distribution analysis."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from datasetlint.core import _load_context, lint_dataset, load_config
from datasetlint.schemas import LintConfig


class NumericSummary(BaseModel):
    """Summary statistics for a numeric distribution."""

    count: int = 0
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    median: float | None = None


class DatasetStats(BaseModel):
    """Dataset-level statistics returned by ``compute_dataset_stats``."""

    dataset_path: str
    duration_sec: float | None = None
    sensors: list[str] = Field(default_factory=list)
    frame_counts: dict[str, int] = Field(default_factory=dict)
    inferred_rates_hz: dict[str, float] = Field(default_factory=dict)
    label_class_counts: dict[str, int] = Field(default_factory=dict)
    confidence_summary: NumericSummary = Field(default_factory=NumericSummary)
    track_length_summary: NumericSummary = Field(default_factory=NumericSummary)
    speed_summary: NumericSummary = Field(default_factory=NumericSummary)
    acceleration_summary: NumericSummary = Field(default_factory=NumericSummary)
    missing_frame_counts: dict[str, int] = Field(default_factory=dict)
    issue_summary: dict[str, int] = Field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(_model_dict(self), indent=2, sort_keys=True)

    def to_markdown(self) -> str:
        lines = [
            "# DatasetLint Stats",
            "",
            f"- Dataset: `{self.dataset_path}`",
            f"- Duration seconds: `{_format_optional(self.duration_sec)}`",
            f"- Sensors: `{len(self.sensors)}`",
            "",
            "## Sensors",
            "",
            "| Sensor | Frames | Rate Hz | Missing Frames |",
            "| --- | ---: | ---: | ---: |",
        ]
        for sensor in self.sensors:
            frames = self.frame_counts.get(sensor, 0)
            rate = _format_rate(self.inferred_rates_hz.get(sensor))
            missing = self.missing_frame_counts.get(sensor, 0)
            lines.append(
                f"| {sensor} | {frames} | {rate} | {missing} |"
            )
        if not self.sensors:
            lines.append("| none | 0 |  | 0 |")
        lines.extend(
            [
                "",
                "## Labels",
                "",
                f"- Classes: `{self.label_class_counts}`",
                f"- Confidence: `{self.confidence_summary.model_dump()}`",
                f"- Track lengths: `{self.track_length_summary.model_dump()}`",
                "",
                "## Trajectories",
                "",
                f"- Speed: `{self.speed_summary.model_dump()}`",
                f"- Acceleration: `{self.acceleration_summary.model_dump()}`",
                "",
                "## Issues",
                "",
                f"- Summary: `{self.issue_summary}`",
            ]
        )
        return "\n".join(lines) + "\n"


def compute_dataset_stats(
    path: str | Path,
    config: str | Path | dict[str, Any] | LintConfig | None = None,
) -> DatasetStats:
    """Compute dataset statistics without changing lint pass/fail semantics."""

    dataset_path = Path(path).expanduser().resolve()
    lint_config = load_config(dataset_path, config)
    ctx = _load_context(dataset_path, lint_config)
    report = lint_dataset(dataset_path, config=lint_config)

    frame_counts = {sensor: len(frame) for sensor, frame in ctx.sensor_frames.items()}
    inferred_rates = {
        sensor: rate
        for sensor, frame in ctx.sensor_frames.items()
        if (rate := _inferred_rate(frame)) is not None
    }
    label_classes = _label_class_counts(ctx.label_frames)
    confidence = _confidence_values(ctx.label_frames)
    track_lengths = _track_lengths(ctx.label_frames)
    speeds, accelerations = _trajectory_motion(ctx.trajectory_frames)
    issue_summary = report.count_by_severity()

    return DatasetStats(
        dataset_path=str(dataset_path),
        duration_sec=_observed_duration(ctx.sensor_frames),
        sensors=sorted(ctx.sensor_frames),
        frame_counts=frame_counts,
        inferred_rates_hz=inferred_rates,
        label_class_counts=label_classes,
        confidence_summary=_numeric_summary(confidence),
        track_length_summary=_numeric_summary(pd.Series(track_lengths, dtype=float)),
        speed_summary=_numeric_summary(pd.Series(speeds, dtype=float)),
        acceleration_summary=_numeric_summary(pd.Series(accelerations, dtype=float)),
        missing_frame_counts=_missing_frame_counts(ctx.sensor_frames, lint_config),
        issue_summary=issue_summary,
    )


def _observed_duration(sensor_frames: dict[str, pd.DataFrame]) -> float | None:
    starts: list[float] = []
    ends: list[float] = []
    for frame in sensor_frames.values():
        timestamps = _timestamps(frame)
        if timestamps.empty:
            continue
        starts.append(float(timestamps.min()))
        ends.append(float(timestamps.max()))
    if not starts or not ends:
        return None
    return max(0.0, max(ends) - min(starts))


def _inferred_rate(frame: pd.DataFrame) -> float | None:
    timestamps = _timestamps(frame).sort_values()
    if len(timestamps) < 2:
        return None
    gaps = timestamps.diff().dropna()
    gaps = gaps[gaps > 0]
    if gaps.empty:
        return None
    return round(float(1.0 / gaps.median()), 6)


def _label_class_counts(label_frames: dict[str, pd.DataFrame]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for frame in label_frames.values():
        if "class" not in frame.columns:
            continue
        for value in frame["class"].dropna():
            counts[str(value)] += 1
    return dict(sorted(counts.items()))


def _confidence_values(label_frames: dict[str, pd.DataFrame]) -> pd.Series:
    values: list[float] = []
    for frame in label_frames.values():
        if "confidence" not in frame.columns:
            continue
        confidence = pd.to_numeric(frame["confidence"], errors="coerce").dropna()
        values.extend(float(value) for value in confidence.tolist())
    return pd.Series(values, dtype=float)


def _track_lengths(label_frames: dict[str, pd.DataFrame]) -> list[int]:
    lengths: list[int] = []
    for frame in label_frames.values():
        if "track_id" not in frame.columns:
            continue
        groups = frame.groupby("track_id", dropna=False)
        lengths.extend(int(len(group)) for _track_id, group in groups)
    return lengths


def _trajectory_motion(
    trajectory_frames: dict[str, pd.DataFrame],
) -> tuple[list[float], list[float]]:
    speeds: list[float] = []
    accelerations: list[float] = []
    for frame in trajectory_frames.values():
        if {"vx", "vy"}.issubset(frame.columns):
            vx = pd.to_numeric(frame["vx"], errors="coerce")
            vy = pd.to_numeric(frame["vy"], errors="coerce")
            speed_values = np.hypot(vx, vy)
            speeds.extend(float(value) for value in pd.Series(speed_values).dropna().tolist())
            if "timestamp" in frame.columns:
                timestamps = pd.to_numeric(frame["timestamp"], errors="coerce")
                dt = timestamps.diff()
                acceleration = pd.Series(speed_values).diff() / dt
                valid = acceleration[(dt > 0) & acceleration.notna()]
                accelerations.extend(float(abs(value)) for value in valid.tolist())
    return speeds, accelerations


def _missing_frame_counts(
    sensor_frames: dict[str, pd.DataFrame],
    config: LintConfig,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for sensor, frame in sensor_frames.items():
        timestamps = _timestamps(frame).sort_values()
        if len(timestamps) < 2:
            counts[sensor] = 0
            continue
        gaps = timestamps.diff().dropna()
        counts[sensor] = int((gaps > config.max_timestamp_gap_sec).sum())
    return counts


def _timestamps(frame: pd.DataFrame) -> pd.Series:
    if "timestamp" not in frame.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(frame["timestamp"], errors="coerce").dropna()


def _numeric_summary(values: pd.Series) -> NumericSummary:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return NumericSummary()
    return NumericSummary(
        count=int(len(clean)),
        min=float(clean.min()),
        max=float(clean.max()),
        mean=float(clean.mean()),
        median=float(clean.median()),
    )


def _model_dict(model: BaseModel) -> dict[str, Any]:
    return model.model_dump()


def _format_optional(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.6g}"


def _format_rate(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.3f}"
