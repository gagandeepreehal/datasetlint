"""Waymo Open Dataset adapter with lightweight indexing and optional frame parsing."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from typing import Any, cast

import pandas as pd

from datasetlint.adapters.base import (
    AdapterValidationReport,
    AnnotationRecord,
    CalibrationRecord,
    DatasetAdapter,
    DatasetManifest,
    DatasetMetadata,
    FrameRecord,
    SensorInfo,
    SensorStream,
    SequenceRecord,
    manifest_provenance,
    relative_to_root,
    validation_scope,
)
from datasetlint.adapters.errors import AdapterDependencyError


class WaymoAdapter(DatasetAdapter):
    """Index Waymo TFRecord segments, with optional protobuf frame parsing."""

    name = "waymo"
    supported_formats = ("waymo-open-dataset", "tfrecord")
    optional_dependencies = ("waymo_open_dataset", "tensorflow")
    description = "Waymo TFRecord index adapter; detailed parsing uses optional Waymo dependencies."

    def can_load(self, path: str | Path) -> bool:
        dataset_path = Path(path)
        if dataset_path.is_file():
            return _is_tfrecord(dataset_path)
        if not dataset_path.is_dir():
            return False
        return any(_is_tfrecord(file_path) for file_path in dataset_path.rglob("*"))

    def load(self, root: str | Path, **kwargs: Any) -> DatasetManifest:
        dataset_root = Path(root)
        files = _tfrecord_files(dataset_root)
        deep = bool(kwargs.get("deep", False) or kwargs.get("parse_records", False))
        max_frames = _positive_int(kwargs.get("max_rows"), default=1000)
        if deep:
            parsed = _parse_waymo_files(dataset_root, files, max_frames=max_frames)
            return DatasetManifest(
                dataset_name=dataset_root.name if dataset_root.is_dir() else dataset_root.stem,
                adapter_name=self.name,
                dataset_root=str(dataset_root),
                sequences=parsed.sequences,
                frames=parsed.frames,
                sensors=parsed.sensors,
                annotations=parsed.annotations,
                calibration=parsed.calibration,
                splits=_splits(dataset_root, files),
                metadata=parsed.metadata,
                limitations=parsed.limitations,
                provenance=manifest_provenance(
                    dataset_root,
                    source_format="waymo",
                    adapter_version=self.adapter_version,
                    warnings=parsed.warnings,
                ),
            )
        warnings = ["Waymo adapter indexed TFRecord files without parsing frame records."]
        return DatasetManifest(
            dataset_name=dataset_root.name if dataset_root.is_dir() else dataset_root.stem,
            adapter_name=self.name,
            dataset_root=str(dataset_root),
            sequences=_index_sequences(dataset_root, files),
            frames=_index_frames(dataset_root, files),
            sensors=_index_sensors(files),
            annotations=[],
            calibration=[],
            splits=_splits(dataset_root, files),
            metadata={
                "parse_mode": "index",
                "tfrecord_files": [relative_to_root(dataset_root, file_path) for file_path in files]
            },
            limitations=[
                (
                    "Use --deep with optional Waymo dependencies to parse frame, label, "
                    "and calibration metadata."
                ),
                "Index mode does not load binary TFRecord contents.",
            ],
            provenance=manifest_provenance(
                dataset_root,
                source_format="waymo",
                adapter_version=self.adapter_version,
                warnings=warnings,
            ),
        )

    def validate(self, root: str | Path, **kwargs: Any) -> AdapterValidationReport:
        manifest = self.load(root, **kwargs)
        files = [Path(root) / path for path in manifest.metadata.get("tfrecord_files", [])]
        errors: list[str] = []
        warnings = list(manifest.provenance.warnings)
        if not files:
            errors.append("No TFRecord files found.")
        empty = [str(path) for path in files if path.exists() and path.stat().st_size == 0]
        if empty:
            warnings.append(f"Empty TFRecord files: {', '.join(empty)}.")
        names = [path.stem for path in files]
        duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
        if duplicates:
            errors.append(f"Duplicate segment names: {', '.join(duplicates)}.")
        deep = manifest.metadata.get("parse_mode") == "deep"
        if deep:
            parse_errors = _parse_errors(warnings)
            errors.extend(parse_errors)
            warnings = [warning for warning in warnings if warning not in parse_errors]
        scope = _waymo_scope(deep, manifest.limitations)
        parsed_frame_count = len(manifest.frames) if deep else 0
        parsed_sensor_count = len(manifest.sensors) if deep else 0
        return AdapterValidationReport(
            adapter_name=self.name,
            dataset_root=str(root),
            detected=self.detect(root),
            valid=not errors,
            **scope,
            errors=errors,
            warnings=warnings,
            coverage={
                "sequences": bool(manifest.sequences),
                "frames": bool(parsed_frame_count),
                "sensors": bool(parsed_sensor_count),
                "annotations": bool(manifest.annotations),
                "calibration": bool(manifest.calibration),
                "index_only": not deep,
            },
            stats={
                "tfrecord_count": len(files),
                "sequence_count": len(manifest.sequences),
                "frame_count": parsed_frame_count,
                "sensor_count": parsed_sensor_count,
                "annotation_count": len(manifest.annotations),
                "calibration_count": len(manifest.calibration),
            },
        )

    def load_metadata(self, path: str | Path) -> DatasetMetadata:
        manifest = self.load(path)
        return DatasetMetadata(
            dataset_path=manifest.dataset_root,
            name=manifest.dataset_name,
            sensors=[sensor.sensor_id for sensor in manifest.sensors],
            raw=manifest.metadata,
        )

    def list_sensors(self, path: str | Path) -> list[SensorInfo]:
        return [
            SensorInfo(name=sensor.sensor_id, frame_count=sensor.frame_count)
            for sensor in self.load(path).sensors
        ]

    def load_timestamps(self, path: str | Path, sensor_name: str) -> pd.Series:
        manifest = self.load(path, deep=True)
        return pd.Series(
            [
                frame.timestamp
                for frame in manifest.frames
                if frame.sensor_id == sensor_name and frame.timestamp is not None
            ],
            dtype=float,
        )


@dataclass(slots=True)
class _ParsedWaymo:
    sequences: list[SequenceRecord]
    frames: list[FrameRecord]
    sensors: list[SensorStream]
    annotations: list[AnnotationRecord]
    calibration: list[CalibrationRecord]
    metadata: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


def _index_sequences(dataset_root: Path, files: list[Path]) -> list[SequenceRecord]:
    return [
        SequenceRecord(
            sequence_id=file_path.stem,
            name=file_path.stem,
            split=_split_for_path(dataset_root, file_path),
            frame_count=None,
            metadata={
                "file_path": relative_to_root(dataset_root, file_path),
                "size_bytes": file_path.stat().st_size,
            },
        )
        for file_path in files
    ]


def _index_frames(dataset_root: Path, files: list[Path]) -> list[FrameRecord]:
    return [
        FrameRecord(
            frame_id=file_path.stem,
            sequence_id=file_path.stem,
            file_path=relative_to_root(dataset_root, file_path),
            metadata={"indexed_tfrecord": True},
        )
        for file_path in files
    ]


def _index_sensors(files: list[Path]) -> list[SensorStream]:
    if not files:
        return []
    return [
        SensorStream(
            sensor_id="unknown",
            sensor_type="unknown",
            name="unknown",
            modality="tfrecord",
            frame_count=len(files),
        )
    ]


def _parse_waymo_files(dataset_root: Path, files: list[Path], *, max_frames: int) -> _ParsedWaymo:
    tf_record_dataset, frame_cls = _waymo_parser()
    frames: list[FrameRecord] = []
    annotations: list[AnnotationRecord] = []
    calibration: list[CalibrationRecord] = []
    sensor_counts: Counter[str] = Counter()
    sequence_counts: Counter[str] = Counter()
    warnings: list[str] = []
    truncated = False

    for file_path in files:
        sequence_id = file_path.stem
        try:
            dataset = tf_record_dataset(str(file_path), compression_type="")
            for raw_record in dataset:
                if len(frames) >= max_frames:
                    truncated = True
                    break
                frame = frame_cls()
                frame.ParseFromString(bytes(raw_record.numpy()))
                frame_id = _waymo_frame_id(file_path, frame, len(frames))
                timestamp = _micros_to_seconds(_object_int(frame, "timestamp_micros"))
                sensor_id = _primary_sensor_id(frame)
                frames.append(
                    FrameRecord(
                        frame_id=frame_id,
                        sequence_id=sequence_id,
                        timestamp=timestamp,
                        sensor_id=sensor_id,
                        file_path=relative_to_root(dataset_root, file_path),
                        metadata={
                            "context_name": _context_name(frame),
                            "camera_image_count": len(_iter_objects(frame, "images")),
                            "laser_count": len(_iter_objects(frame, "lasers")),
                        },
                    )
                )
                sequence_counts[sequence_id] += 1
                _collect_waymo_sensors(frame, sensor_counts)
                annotations.extend(_waymo_annotations(frame, frame_id, sequence_id))
                calibration.extend(_waymo_calibration(frame))
            if truncated:
                break
        except Exception as exc:
            warnings.append(f"Could not parse {relative_to_root(dataset_root, file_path)}: {exc}.")

    if truncated:
        warnings.append(f"Waymo frame parsing stopped at max_rows={max_frames}.")

    sensors = [
        SensorStream(
            sensor_id=sensor_id,
            sensor_type=_sensor_type(sensor_id),
            name=sensor_id,
            modality=_sensor_type(sensor_id),
            frame_count=count,
            metadata={"source": "waymo_frame"},
        )
        for sensor_id, count in sorted(sensor_counts.items())
    ]
    sequences = [
        SequenceRecord(
            sequence_id=file_path.stem,
            name=file_path.stem,
            split=_split_for_path(dataset_root, file_path),
            frame_count=sequence_counts.get(file_path.stem, 0),
            metadata={
                "file_path": relative_to_root(dataset_root, file_path),
                "size_bytes": file_path.stat().st_size,
            },
        )
        for file_path in files
    ]
    return _ParsedWaymo(
        sequences=sequences,
        frames=frames,
        sensors=sensors,
        annotations=annotations,
        calibration=_deduplicate_calibration(calibration),
        metadata={
            "parse_mode": "deep",
            "tfrecord_files": [relative_to_root(dataset_root, file_path) for file_path in files],
            "frame_count": len(frames),
            "annotation_count": len(annotations),
            "calibration_count": len(calibration),
            "truncated": truncated,
        },
        warnings=warnings,
        limitations=[
            (
                "Waymo TFRecord frames, labels, and calibration metadata are parsed; camera "
                "images, lidar ranges, and metric evaluation are not decoded."
            )
        ],
    )


def _is_tfrecord(path: Path) -> bool:
    name = path.name.lower()
    return path.suffix.lower() == ".tfrecord" or "segment-" in name and name.endswith(".tfrecord")


def _tfrecord_files(path: Path) -> list[Path]:
    if path.is_file() and _is_tfrecord(path):
        return [path]
    if path.is_dir():
        return sorted(
            file_path
            for file_path in path.rglob("*")
            if file_path.is_file() and _is_tfrecord(file_path)
        )
    return []


def _parse_errors(warnings: list[str]) -> list[str]:
    return [warning for warning in warnings if warning.startswith("Could not parse ")]


def _split_for_path(root: Path, path: Path) -> str | None:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return None
    for part in parts:
        if part.lower() in {"training", "validation", "testing", "train", "val", "test"}:
            return part.lower()
    return None


def _splits(root: Path, files: list[Path]) -> dict[str, list[str]]:
    splits: dict[str, list[str]] = {}
    for file_path in files:
        split = _split_for_path(root, file_path)
        if split:
            splits.setdefault(split, []).append(file_path.stem)
    return splits


def _waymo_parser() -> tuple[Any, Any]:
    try:
        tensorflow = import_module("tensorflow")
        dataset_pb2 = import_module("waymo_open_dataset.dataset_pb2")
    except ImportError as exc:
        raise AdapterDependencyError(
            "Deep Waymo parsing requires optional Waymo and TensorFlow packages. "
            "Install with `python -m pip install -e '.[waymo]'`."
        ) from exc
    return cast(Any, tensorflow).data.TFRecordDataset, cast(Any, dataset_pb2).Frame


def _waymo_scope(deep: bool, limitations: list[str]) -> dict[str, Any]:
    if not deep:
        return validation_scope("waymo", limitations)
    return {
        "validation_mode": "deep",
        "checked": [
            "TFRecord frame parsing",
            "camera and lidar sensor metadata",
            "label metadata",
            "calibration metadata",
        ],
        "not_checked": ["camera image bytes", "lidar range images", "Waymo metric evaluation"],
        "limitations": limitations,
    }


def _context_name(frame: object) -> str:
    context = getattr(frame, "context", None)
    return _object_text(context, "name") if context is not None else ""


def _waymo_frame_id(file_path: Path, frame: object, index: int) -> str:
    context_name = _context_name(frame)
    timestamp = _object_int(frame, "timestamp_micros")
    if context_name and timestamp:
        return f"{context_name}:{timestamp}"
    return f"{file_path.stem}:{index}"


def _primary_sensor_id(frame: object) -> str | None:
    images = _iter_objects(frame, "images")
    if images:
        return _sensor_id("camera", _object_int(images[0], "name"))
    lasers = _iter_objects(frame, "lasers")
    if lasers:
        return _sensor_id("laser", _object_int(lasers[0], "name"))
    return None


def _collect_waymo_sensors(frame: object, sensor_counts: Counter[str]) -> None:
    for image in _iter_objects(frame, "images"):
        sensor_counts[_sensor_id("camera", _object_int(image, "name"))] += 1
    for laser in _iter_objects(frame, "lasers"):
        sensor_counts[_sensor_id("laser", _object_int(laser, "name"))] += 1
    context = getattr(frame, "context", None)
    if context is None:
        return
    for calibration in _iter_objects(context, "camera_calibrations"):
        sensor_counts.setdefault(_sensor_id("camera", _object_int(calibration, "name")), 0)
    for calibration in _iter_objects(context, "laser_calibrations"):
        sensor_counts.setdefault(_sensor_id("laser", _object_int(calibration, "name")), 0)


def _waymo_annotations(
    frame: object, frame_id: str, sequence_id: str | None
) -> list[AnnotationRecord]:
    annotations: list[AnnotationRecord] = []
    for label in _iter_objects(frame, "laser_labels"):
        label_id = _object_text(label, "id", default=f"{frame_id}:laser:{len(annotations)}")
        annotations.append(
            AnnotationRecord(
                annotation_id=label_id,
                frame_id=frame_id,
                sequence_id=sequence_id,
                category=str(_object_int(label, "type")),
                annotation_type="waymo_laser_label",
                values={
                    "num_lidar_points_in_box": _object_int(label, "num_lidar_points_in_box"),
                    "detection_difficulty_level": _object_int(
                        label, "detection_difficulty_level"
                    ),
                },
                metadata={"source": "laser_labels"},
            )
        )
    for camera_group in _iter_objects(frame, "camera_labels"):
        camera_id = _sensor_id("camera", _object_int(camera_group, "name"))
        for label in _iter_objects(camera_group, "labels"):
            label_id = _object_text(label, "id", default=f"{frame_id}:{camera_id}:label")
            annotations.append(
                AnnotationRecord(
                    annotation_id=label_id,
                    frame_id=frame_id,
                    sequence_id=sequence_id,
                    category=str(_object_int(label, "type")),
                    annotation_type="waymo_camera_label",
                    values={"box": _box_dict(getattr(label, "box", None))},
                    metadata={"camera": camera_id},
                )
            )
    return annotations


def _waymo_calibration(frame: object) -> list[CalibrationRecord]:
    context = getattr(frame, "context", None)
    if context is None:
        return []
    records: list[CalibrationRecord] = []
    for calibration in _iter_objects(context, "camera_calibrations"):
        sensor_id = _sensor_id("camera", _object_int(calibration, "name"))
        extrinsic = _object_value(_object_value(calibration, "extrinsic", None), "transform", [])
        records.append(
            CalibrationRecord(
                sensor_id=sensor_id,
                intrinsic=_matrix3(_object_value(calibration, "intrinsic", [])),
                extrinsic=_matrix4(extrinsic),
                metadata={"source": "waymo_camera_calibration"},
            )
        )
    for calibration in _iter_objects(context, "laser_calibrations"):
        sensor_id = _sensor_id("laser", _object_int(calibration, "name"))
        extrinsic = _object_value(_object_value(calibration, "extrinsic", None), "transform", [])
        records.append(
            CalibrationRecord(
                sensor_id=sensor_id,
                extrinsic=_matrix4(extrinsic),
                metadata={"source": "waymo_laser_calibration"},
            )
        )
    return records


def _deduplicate_calibration(records: list[CalibrationRecord]) -> list[CalibrationRecord]:
    seen: set[tuple[str, str | None]] = set()
    unique: list[CalibrationRecord] = []
    for record in records:
        key = (record.sensor_id, record.target_sensor_id)
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique


def _iter_objects(value: object, name: str) -> list[object]:
    items = getattr(value, name, [])
    if isinstance(items, list | tuple):
        return list(items)
    try:
        return list(items)
    except TypeError:
        return []


def _object_int(value: object, name: str) -> int:
    item = getattr(value, name, 0)
    return int(item) if isinstance(item, int) else 0


def _object_float(value: object, name: str) -> float | None:
    item = getattr(value, name, None)
    if isinstance(item, int | float):
        return float(item)
    return None


def _object_text(value: object, name: str, *, default: str = "") -> str:
    item = getattr(value, name, default)
    return item if isinstance(item, str) else default


def _object_value(value: object, name: str, default: object) -> object:
    return getattr(value, name, default)


def _sensor_id(prefix: str, name: int) -> str:
    return f"{prefix}_{name}" if name else f"{prefix}_unknown"


def _sensor_type(sensor_id: str) -> str:
    if sensor_id.startswith("camera"):
        return "camera"
    if sensor_id.startswith("laser"):
        return "lidar"
    return "unknown"


def _box_dict(box: object) -> dict[str, float | None]:
    return {
        "center_x": _object_float(box, "center_x"),
        "center_y": _object_float(box, "center_y"),
        "length": _object_float(box, "length"),
        "width": _object_float(box, "width"),
    }


def _matrix3(values: object) -> list[list[float]] | None:
    flattened = _float_list(values)
    if len(flattened) < 9:
        return None
    return [flattened[0:3], flattened[3:6], flattened[6:9]]


def _matrix4(values: object) -> list[list[float]] | None:
    flattened = _float_list(values)
    if len(flattened) < 16:
        return None
    return [
        flattened[0:4],
        flattened[4:8],
        flattened[8:12],
        flattened[12:16],
    ]


def _float_list(values: object) -> list[float]:
    if not isinstance(values, Iterable) or isinstance(values, str):
        return []
    output: list[float] = []
    for value in values:
        try:
            output.append(float(value))
        except (TypeError, ValueError):
            return []
    return output


def _micros_to_seconds(value: int) -> float | None:
    if value <= 0:
        return None
    return value / 1_000_000.0


def _positive_int(value: object, *, default: int) -> int:
    if isinstance(value, int) and value > 0:
        return value
    return default
