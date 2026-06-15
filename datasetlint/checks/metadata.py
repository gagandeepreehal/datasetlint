"""Metadata checks."""

from __future__ import annotations

from datasetlint.schemas import DatasetContext, Issue, make_issue


def check_metadata_schema(ctx: DatasetContext) -> list[Issue]:
    if ctx.metadata is None:
        return []
    if not isinstance(ctx.metadata, dict):
        return [
            make_issue(
                "check_metadata_schema",
                "error",
                "metadata.json must contain a JSON object.",
                file="metadata.json",
            )
        ]
    issues: list[Issue] = []
    if not isinstance(ctx.metadata.get("dataset_name"), str) or not ctx.metadata.get(
        "dataset_name"
    ):
        issues.append(
            make_issue(
                "check_metadata_schema",
                "error",
                "metadata.json must include a non-empty string dataset_name.",
                file="metadata.json",
            )
        )
    sensors = ctx.metadata.get("sensors")
    if not isinstance(sensors, list) or not all(isinstance(sensor, str) for sensor in sensors):
        issues.append(
            make_issue(
                "check_metadata_schema",
                "error",
                "metadata.json must include sensors as a list of strings.",
                file="metadata.json",
            )
        )
    duration = ctx.metadata.get("duration_sec")
    if not isinstance(duration, (int, float)) or duration < 0:
        issues.append(
            make_issue(
                "check_metadata_schema",
                "error",
                "metadata.json must include non-negative numeric duration_sec.",
                file="metadata.json",
            )
        )
    return issues


def check_declared_sensors_exist(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    for sensor in ctx.declared_sensors():
        if sensor not in ctx.sensor_files:
            issues.append(
                make_issue(
                    "check_declared_sensors_exist",
                    "error",
                    f"Declared sensor '{sensor}' has no matching CSV in sensors/.",
                    file="metadata.json",
                    metadata={"sensor": sensor},
                )
            )
    return issues


def check_duration_matches_timestamps(ctx: DatasetContext) -> list[Issue]:
    if not isinstance(ctx.metadata, dict):
        return []
    raw_duration = ctx.metadata.get("duration_sec")
    if not isinstance(raw_duration, (int, float)):
        return []
    duration = float(raw_duration)
    ranges: list[tuple[float, float]] = []
    for _name, _path, frame in ctx.iter_frames():
        if "timestamp" not in frame.columns or frame.empty:
            continue
        timestamps = frame["timestamp"].dropna()
        if timestamps.empty:
            continue
        ranges.append((float(timestamps.min()), float(timestamps.max())))
    if not ranges:
        return []
    observed_duration = max(end for _start, end in ranges) - min(start for start, _end in ranges)
    if abs(duration - observed_duration) > ctx.config.duration_tolerance_sec:
        return [
            make_issue(
                "check_duration_matches_timestamps",
                "warning",
                "metadata duration_sec does not match observed timestamp span.",
                file="metadata.json",
                metadata={
                    "declared_duration_sec": duration,
                    "observed_duration_sec": observed_duration,
                },
            )
        ]
    return []


def check_dataset_version_present(ctx: DatasetContext) -> list[Issue]:
    if not isinstance(ctx.metadata, dict):
        return []
    version = ctx.metadata.get("version")
    if not isinstance(version, str) or not version:
        return [
            make_issue(
                "check_dataset_version_present",
                "warning",
                "metadata.json should include a non-empty version string.",
                file="metadata.json",
            )
        ]
    return []
