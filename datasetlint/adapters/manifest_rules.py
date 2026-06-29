"""Common validation rules for normalized adapter manifests."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median
from typing import Any

from datasetlint.adapters.base import DatasetManifest, FrameRecord, SensorStream

MAX_PAIRWISE_SYNC_GAP_SEC = 0.05
LARGE_TIMESTAMP_GAP_SEC = 1.0
CALIBRATION_EXPECTED_ADAPTERS = {"folder", "kitti", "nuscenes", "waymo"}
ANNOTATION_FRAME_LINK_ADAPTERS = {"coco", "folder", "generic", "kitti", "waymo"}


@dataclass(slots=True)
class ManifestRuleResult:
    """Findings produced by common rules over normalized manifest records."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked: list[str] = field(default_factory=list)
    coverage: dict[str, Any] = field(default_factory=dict)
    stats: dict[str, Any] = field(default_factory=dict)


def run_manifest_rules(manifest: DatasetManifest, root: str | Path) -> ManifestRuleResult:
    """Run common lightweight rules over semantic manifest records."""

    result = ManifestRuleResult()
    frames = _semantic_frames(manifest)
    sensors = _semantic_sensors(manifest, frames)
    result.checked.append("common manifest input summary")
    result.coverage = {
        "frames": bool(frames),
        "sensors": bool(sensors),
        "annotations": bool(manifest.annotations),
        "calibration": bool(manifest.calibration),
        "splits": bool(manifest.splits),
        "timestamps": any(frame.timestamp is not None for frame in frames),
    }
    result.stats = {
        "frame_count": len(frames),
        "sensor_count": len(sensors),
        "annotation_count": len(manifest.annotations),
        "calibration_count": len(manifest.calibration),
    }

    _check_frame_references(manifest, root, frames, result)
    _check_sensor_links(sensors, frames, result)
    _check_timestamps(frames, result)
    _check_annotations(manifest, result)
    _check_calibration(manifest, frames, sensors, result)
    _check_splits(manifest, result)
    return result


def merge_common_rule_result(
    *,
    scope: dict[str, Any],
    errors: list[str],
    warnings: list[str],
    coverage: dict[str, Any],
    stats: dict[str, Any],
    result: ManifestRuleResult,
) -> tuple[dict[str, Any], list[str], list[str], dict[str, Any], dict[str, Any]]:
    """Merge common-rule output into an adapter validation report payload."""

    merged_scope = dict(scope)
    merged_scope["checked"] = _unique_strings(
        [*list(scope.get("checked", [])), *result.checked]
    )
    coverage = {**coverage, "common_rule_inputs": result.coverage}
    stats = {**stats, "common_rule_stats": result.stats}
    return (
        merged_scope,
        _unique_strings([*errors, *result.errors]),
        _unique_strings([*warnings, *result.warnings]),
        coverage,
        stats,
    )


def _check_frame_references(
    manifest: DatasetManifest,
    root: str | Path,
    frames: list[FrameRecord],
    result: ManifestRuleResult,
) -> None:
    if not frames:
        return
    result.checked.append("common frame references")
    sequence_ids = {sequence.sequence_id for sequence in manifest.sequences}
    frame_ids = [frame.frame_id for frame in frames]
    for frame_id in _duplicates(frame_ids):
        result.errors.append(f"Duplicate frame id in manifest: {frame_id}.")
    for frame in frames:
        if frame.sequence_id and sequence_ids and frame.sequence_id not in sequence_ids:
            result.errors.append(
                f"Frame {frame.frame_id} references missing sequence {frame.sequence_id}."
            )
        missing_file = _missing_local_file(root, frame.file_path)
        if missing_file is not None:
            result.errors.append(f"Frame file does not exist: {missing_file}.")


def _check_sensor_links(
    sensors: list[SensorStream],
    frames: list[FrameRecord],
    result: ManifestRuleResult,
) -> None:
    if not sensors and not frames:
        return
    result.checked.append("common sensor links")
    sensor_ids = {sensor.sensor_id for sensor in sensors}
    frames_by_sensor = Counter(
        frame.sensor_id for frame in frames if frame.sensor_id is not None
    )
    for frame in frames:
        if frame.sensor_id and sensor_ids and frame.sensor_id not in sensor_ids:
            result.errors.append(
                f"Frame {frame.frame_id} references missing sensor {frame.sensor_id}."
            )
    for sensor in sensors:
        observed = frames_by_sensor.get(sensor.sensor_id)
        if observed and sensor.frame_count is not None and observed != sensor.frame_count:
            result.warnings.append(
                f"Sensor {sensor.sensor_id} declares {sensor.frame_count} frames, "
                f"but common manifest records contain {observed}."
            )


def _check_timestamps(frames: list[FrameRecord], result: ManifestRuleResult) -> None:
    groups: dict[str, list[tuple[int, float]]] = defaultdict(list)
    for index, frame in enumerate(frames):
        if frame.timestamp is not None:
            groups[frame.sensor_id or "unknown"].append((index, frame.timestamp))
    if not groups:
        return
    result.checked.append("common timestamp consistency")
    timestamp_stats: dict[str, Any] = {}
    for sensor_id, indexed_values in sorted(groups.items()):
        values = [value for _, value in indexed_values]
        timestamp_stats[sensor_id] = {
            "count": len(values),
            "start_time": min(values),
            "end_time": max(values),
        }
        duplicate_count = len(values) - len(set(values))
        if duplicate_count:
            result.warnings.append(
                f"Sensor {sensor_id} has {duplicate_count} duplicate timestamp(s)."
            )
        ordered_values = [value for _, value in sorted(indexed_values)]
        if any(
            ordered_values[index] > ordered_values[index + 1]
            for index in range(len(ordered_values) - 1)
        ):
            result.errors.append(f"Sensor {sensor_id} has non-monotonic timestamps.")
        sorted_values = sorted(set(values))
        gaps = [
            sorted_values[index + 1] - sorted_values[index]
            for index in range(len(sorted_values) - 1)
        ]
        large_gaps = [gap for gap in gaps if gap > LARGE_TIMESTAMP_GAP_SEC]
        if large_gaps:
            result.warnings.append(
                f"Sensor {sensor_id} has timestamp gap {max(large_gaps):.6g}s."
            )
            timestamp_stats[sensor_id]["max_gap_sec"] = max(large_gaps)
    result.stats["timestamp_streams"] = timestamp_stats
    _check_sync(groups, result)


def _check_sync(
    groups: dict[str, list[tuple[int, float]]], result: ManifestRuleResult
) -> None:
    usable = {
        sensor_id: sorted(value for _, value in values)
        for sensor_id, values in groups.items()
        if values
    }
    if len(usable) < 2:
        return
    result.checked.append("common sensor sync summary")
    sync_stats: dict[str, Any] = {}
    sensor_ids = sorted(usable)
    for left_index, left_sensor in enumerate(sensor_ids):
        left = usable[left_sensor]
        for right_sensor in sensor_ids[left_index + 1 :]:
            right = usable[right_sensor]
            overlap_start = max(left[0], right[0])
            overlap_end = min(left[-1], right[-1])
            pair_name = f"{left_sensor}:{right_sensor}"
            if overlap_start > overlap_end:
                result.warnings.append(
                    f"Sensors {left_sensor} and {right_sensor} have no timestamp overlap."
                )
                sync_stats[pair_name] = {"overlap": False}
                continue
            gaps = [_nearest_gap(value, right) for value in left]
            median_gap = median(gaps) if gaps else 0.0
            max_gap = max(gaps) if gaps else 0.0
            sync_stats[pair_name] = {
                "overlap": True,
                "median_gap_sec": median_gap,
                "max_gap_sec": max_gap,
            }
            if median_gap > MAX_PAIRWISE_SYNC_GAP_SEC:
                result.warnings.append(
                    f"Sensors {left_sensor} and {right_sensor} median sync gap "
                    f"{median_gap:.6g}s exceeds {MAX_PAIRWISE_SYNC_GAP_SEC:.6g}s."
                )
    result.stats["sync_pairs"] = sync_stats


def _check_annotations(manifest: DatasetManifest, result: ManifestRuleResult) -> None:
    if not manifest.annotations:
        return
    result.checked.append("common annotation links")
    annotation_ids = [annotation.annotation_id for annotation in manifest.annotations]
    for annotation_id in _duplicates(annotation_ids):
        result.errors.append(f"Duplicate annotation id in manifest: {annotation_id}.")
    sequence_ids = {sequence.sequence_id for sequence in manifest.sequences}
    frame_ids = {frame.frame_id for frame in _semantic_frames(manifest)}
    check_frame_links = manifest.adapter_name in ANNOTATION_FRAME_LINK_ADAPTERS
    for annotation in manifest.annotations:
        if (
            check_frame_links
            and annotation.frame_id
            and frame_ids
            and annotation.frame_id not in frame_ids
        ):
            result.errors.append(
                f"Annotation {annotation.annotation_id} references missing frame "
                f"{annotation.frame_id}."
            )
        if (
            annotation.sequence_id
            and sequence_ids
            and annotation.sequence_id not in sequence_ids
        ):
            result.errors.append(
                f"Annotation {annotation.annotation_id} references missing sequence "
                f"{annotation.sequence_id}."
            )


def _check_calibration(
    manifest: DatasetManifest,
    frames: list[FrameRecord],
    sensors: list[SensorStream],
    result: ManifestRuleResult,
) -> None:
    if not manifest.calibration and not sensors:
        return
    if (
        not manifest.calibration
        and manifest.adapter_name not in CALIBRATION_EXPECTED_ADAPTERS
    ):
        return
    result.checked.append("common calibration shape")
    calibration_ids = {record.sensor_id for record in manifest.calibration}
    calibration_ids.update(
        record.target_sensor_id
        for record in manifest.calibration
        if record.target_sensor_id is not None
    )
    framed_sensor_ids = {frame.sensor_id for frame in frames if frame.sensor_id is not None}
    for sensor in sensors:
        if (
            manifest.adapter_name in CALIBRATION_EXPECTED_ADAPTERS
            and sensor.sensor_type in {"camera", "lidar"}
            and sensor.sensor_id in framed_sensor_ids
            and sensor.sensor_id not in calibration_ids
        ):
            result.warnings.append(f"Missing calibration for sensor {sensor.sensor_id}.")
    for record in manifest.calibration:
        if record.intrinsic is not None and not _valid_intrinsic(record.intrinsic):
            result.errors.append(
                f"Calibration intrinsic for sensor {record.sensor_id} must be a numeric 3x3 matrix."
            )


def _check_splits(manifest: DatasetManifest, result: ManifestRuleResult) -> None:
    if not manifest.splits:
        return
    result.checked.append("common split references")
    frame_ids = {frame.frame_id for frame in _semantic_frames(manifest)}
    if not frame_ids:
        return
    for split_name, split_frames in sorted(manifest.splits.items()):
        missing = sorted(frame_id for frame_id in split_frames if frame_id not in frame_ids)
        if missing:
            result.errors.append(
                f"Split {split_name} references missing frame ids: {', '.join(missing)}."
            )


def _semantic_frames(manifest: DatasetManifest) -> list[FrameRecord]:
    return [
        frame
        for frame in manifest.frames
        if frame.metadata.get("indexed_tfrecord") is not True
    ]


def _semantic_sensors(
    manifest: DatasetManifest, frames: list[FrameRecord]
) -> list[SensorStream]:
    if manifest.adapter_name == "waymo" and manifest.metadata.get("parse_mode") == "index":
        return []
    if manifest.adapter_name == "waymo" and not frames:
        return []
    return manifest.sensors


def _missing_local_file(root: str | Path, file_path: str | None) -> str | None:
    if not file_path or "://" in file_path:
        return None
    root_text = str(root)
    if "://" in root_text:
        return None
    path = Path(file_path)
    candidate = path if path.is_absolute() else Path(root_text) / path
    return file_path if not candidate.is_file() else None


def _duplicates(values: list[str]) -> list[str]:
    counts = Counter(values)
    return sorted(value for value, count in counts.items() if count > 1)


def _nearest_gap(value: float, candidates: list[float]) -> float:
    return min(abs(value - candidate) for candidate in candidates)


def _valid_intrinsic(value: list[list[float]]) -> bool:
    if len(value) != 3:
        return False
    for row in value:
        if len(row) != 3:
            return False
        for item in row:
            if not isinstance(item, int | float):
                return False
    return True


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value not in seen:
            unique.append(value)
            seen.add(value)
    return unique
