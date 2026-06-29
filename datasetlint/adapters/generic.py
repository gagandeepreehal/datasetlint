"""Generic folder adapter for common ad hoc dataset layouts."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any

from datasetlint.adapters.base import (
    AdapterValidationReport,
    AnnotationRecord,
    DatasetAdapter,
    DatasetManifest,
    DatasetMetadata,
    FrameRecord,
    SensorInfo,
    SensorStream,
    SequenceRecord,
    manifest_provenance,
    read_json_object,
    relative_to_root,
    validation_scope,
)
from datasetlint.adapters.manifest_rules import merge_common_rule_result, run_manifest_rules

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}
LABEL_EXTENSIONS = {".json", ".jsonl", ".csv", ".txt"}
POINT_CLOUD_EXTENSIONS = {".pcd", ".bin", ".ply"}
METADATA_EXTENSIONS = {".yaml", ".yml", ".json"}
SUPPORTED_EXTENSIONS = (
    IMAGE_EXTENSIONS
    | VIDEO_EXTENSIONS
    | LABEL_EXTENSIONS
    | POINT_CLOUD_EXTENSIONS
    | METADATA_EXTENSIONS
)
SPLIT_NAMES = {"train", "val", "test"}


class GenericFolderAdapter(DatasetAdapter):
    """Infer a manifest from common folder, file, split, and timestamp conventions."""

    name = "generic"
    supported_formats = ("folder", "images", "videos", "point-clouds", "labels")
    description = "Generic recursive folder adapter with inferred sensors, splits, and labels."

    def can_load(self, path: str | Path) -> bool:
        root = Path(path)
        if not root.is_dir():
            return False
        if (root / "images").is_dir() and (root / "labels").is_dir():
            return True
        if any((root / split).is_dir() for split in SPLIT_NAMES):
            return True
        if (root / "data").is_dir() and (root / "annotations.json").is_file():
            return True
        if (root / "videos").is_dir() or (root / "timestamps.csv").is_file():
            return True
        return any(
            file_path.suffix.lower() in SUPPORTED_EXTENSIONS for file_path in root.rglob("*")
        )

    def load(self, root: str | Path, **kwargs: Any) -> DatasetManifest:
        del kwargs
        dataset_root = Path(root)
        files = sorted(path for path in dataset_root.rglob("*") if path.is_file())
        warnings: list[str] = []
        limitations = [
            "Generic adapter infers sensor semantics from folders and file extensions.",
            (
                "Unsupported fields are represented in metadata or limitations when "
                "semantics are unknown."
            ),
        ]
        timestamps = _load_timestamps(dataset_root / "timestamps.csv")
        frames: list[FrameRecord] = []
        sensors_by_id: dict[str, SensorStream] = {}
        splits: dict[str, list[str]] = {}
        unsupported = [
            relative_to_root(dataset_root, file_path)
            for file_path in files
            if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS
        ]
        if unsupported:
            warnings.append(f"Unsupported file types indexed but not parsed: {len(unsupported)}.")

        for file_path in files:
            suffix = file_path.suffix.lower()
            if suffix in IMAGE_EXTENSIONS:
                frame = _frame_for_file(dataset_root, file_path, "camera", timestamps)
                frames.append(frame)
                _upsert_sensor(sensors_by_id, frame.sensor_id or "camera", "camera", "image")
                _record_split(dataset_root, file_path, frame.frame_id, splits)
            elif suffix in POINT_CLOUD_EXTENSIONS:
                frame = _frame_for_file(dataset_root, file_path, "lidar", timestamps)
                frames.append(frame)
                _upsert_sensor(sensors_by_id, frame.sensor_id or "lidar", "lidar", "point_cloud")
                _record_split(dataset_root, file_path, frame.frame_id, splits)
            elif suffix in VIDEO_EXTENSIONS:
                sensor_id = _sensor_id_for_file(dataset_root, file_path, "video")
                _upsert_sensor(sensors_by_id, sensor_id, "video", "video")
                _record_split(dataset_root, file_path, file_path.stem, splits)

        annotations, broken_paths = _load_generic_annotations(dataset_root)
        if broken_paths:
            warnings.append(f"Broken relative annotation paths: {len(broken_paths)}.")
        if not annotations and (dataset_root / "labels").is_dir():
            annotations = _index_label_files(dataset_root)
            limitations.append("Label files were indexed but not semantically parsed.")

        for sensor_id, sensor in list(sensors_by_id.items()):
            count = sum(1 for frame in frames if frame.sensor_id == sensor_id)
            sensors_by_id[sensor_id] = sensor.model_copy(
                update={"frame_count": count or sensor.frame_count}
            )

        sequence = SequenceRecord(
            sequence_id="root",
            name=dataset_root.name,
            frame_count=len(frames) or None,
            metadata={"file_count": len(files), "unsupported_files": unsupported},
        )
        return DatasetManifest(
            dataset_name=dataset_root.name,
            adapter_name=self.name,
            dataset_root=str(dataset_root),
            sequences=[sequence],
            frames=frames,
            sensors=sorted(sensors_by_id.values(), key=lambda item: item.sensor_id),
            annotations=annotations,
            calibration=[],
            splits=splits,
            metadata={
                "supported_files": len(files) - len(unsupported),
                "unsupported_files": unsupported,
            },
            limitations=limitations,
            provenance=manifest_provenance(
                dataset_root,
                source_format="generic-folder",
                adapter_version=self.adapter_version,
                warnings=warnings,
            ),
        )

    def validate(self, root: str | Path, **kwargs: Any) -> AdapterValidationReport:
        manifest = self.load(root, **kwargs)
        dataset_root = Path(root)
        errors: list[str] = []
        warnings = list(manifest.provenance.warnings)
        files = (
            [path for path in dataset_root.rglob("*") if path.is_file()]
            if dataset_root.exists()
            else []
        )
        if not files:
            errors.append("Empty dataset: no files found.")
        if manifest.frames and not manifest.annotations:
            warnings.append("Missing labels: no annotations or label files were parsed.")
        names = [path.name for path in files]
        duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
        if duplicates:
            warnings.append(f"Duplicate filenames found: {', '.join(duplicates)}.")
        timestamp_count = _timestamp_count(dataset_root / "timestamps.csv")
        if (
            timestamp_count is not None
            and manifest.frames
            and timestamp_count != len(manifest.frames)
        ):
            warnings.append(
                f"Timestamp count mismatch: timestamps.csv has {timestamp_count}, "
                f"manifest has {len(manifest.frames)} frames."
            )
        scope = validation_scope(self.name, manifest.limitations)
        coverage = {
            "frames": bool(manifest.frames),
            "sensors": bool(manifest.sensors),
            "annotations": bool(manifest.annotations),
            "calibration": bool(manifest.calibration),
            "splits": bool(manifest.splits),
        }
        stats = {
            "file_count": len(files),
            "frame_count": len(manifest.frames),
            "sensor_count": len(manifest.sensors),
            "annotation_count": len(manifest.annotations),
        }
        scope, errors, warnings, coverage, stats = merge_common_rule_result(
            scope=scope,
            errors=errors,
            warnings=warnings,
            coverage=coverage,
            stats=stats,
            result=run_manifest_rules(manifest, root),
        )
        return AdapterValidationReport(
            adapter_name=self.name,
            dataset_root=str(root),
            detected=self.detect(root),
            valid=not errors,
            **scope,
            errors=errors,
            warnings=warnings,
            coverage=coverage,
            stats=stats,
        )

    def load_metadata(self, path: str | Path) -> DatasetMetadata:
        manifest = self.load(path)
        return DatasetMetadata(
            dataset_path=manifest.dataset_root,
            name=manifest.dataset_name,
            version=manifest.version,
            sensors=[sensor.sensor_id for sensor in manifest.sensors],
            raw=manifest.metadata,
        )

    def list_sensors(self, path: str | Path) -> list[SensorInfo]:
        return [
            SensorInfo(name=sensor.sensor_id, frame_count=sensor.frame_count)
            for sensor in self.load(path).sensors
        ]


def _frame_for_file(
    root: Path,
    file_path: Path,
    fallback_sensor_type: str,
    timestamps: dict[str, float],
) -> FrameRecord:
    rel = relative_to_root(root, file_path)
    sensor_id = _sensor_id_for_file(root, file_path, fallback_sensor_type)
    return FrameRecord(
        frame_id=file_path.stem,
        sequence_id="root",
        timestamp=timestamps.get(rel)
        or timestamps.get(file_path.name)
        or timestamps.get(file_path.stem),
        sensor_id=sensor_id,
        file_path=rel,
        metadata={"extension": file_path.suffix.lower()},
    )


def _sensor_id_for_file(root: Path, file_path: Path, fallback: str) -> str:
    rel_parts = file_path.relative_to(root).parts
    if len(rel_parts) >= 2:
        parent = rel_parts[-2].lower()
        if parent in {"images", "image_2", "camera", "camera_front"}:
            return parent if parent != "images" else "camera"
        if parent in {"velodyne", "lidar", "pointclouds", "point_clouds"}:
            return parent if parent != "pointclouds" else "lidar"
        if parent in {"videos", "video"}:
            return "video"
    return fallback


def _upsert_sensor(
    sensors: dict[str, SensorStream], sensor_id: str, sensor_type: str, modality: str
) -> None:
    sensors.setdefault(
        sensor_id,
        SensorStream(
            sensor_id=sensor_id,
            sensor_type=sensor_type,
            name=sensor_id,
            modality=modality,
        ),
    )


def _record_split(root: Path, file_path: Path, frame_id: str, splits: dict[str, list[str]]) -> None:
    for part in file_path.relative_to(root).parts:
        if part in SPLIT_NAMES:
            splits.setdefault(part, []).append(frame_id)
            return


def _load_timestamps(path: Path) -> dict[str, float]:
    if not path.is_file():
        return {}
    timestamps: dict[str, float] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader):
            raw_timestamp = row.get("timestamp") or row.get("time")
            if raw_timestamp is None:
                continue
            try:
                timestamp = float(raw_timestamp)
            except ValueError:
                continue
            key = row.get("file_path") or row.get("path") or row.get("frame_id") or str(index)
            timestamps[key] = timestamp
    return timestamps


def _timestamp_count(path: Path) -> int | None:
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def _load_generic_annotations(root: Path) -> tuple[list[AnnotationRecord], list[str]]:
    path = root / "annotations.json"
    if not path.is_file():
        return [], []
    raw = read_json_object(path)
    records = raw.get("annotations", raw.get("labels", []))
    if not isinstance(records, list):
        return [], []
    annotations: list[AnnotationRecord] = []
    broken_paths: list[str] = []
    for index, item in enumerate(records):
        if not isinstance(item, dict):
            continue
        rel_path = item.get("file_path") or item.get("path") or item.get("image")
        if isinstance(rel_path, str) and not (root / rel_path).exists():
            broken_paths.append(rel_path)
        annotation_id = str(item.get("id", item.get("annotation_id", f"annotation-{index}")))
        annotations.append(
            AnnotationRecord(
                annotation_id=annotation_id,
                frame_id=str(item.get("frame_id")) if item.get("frame_id") is not None else None,
                sequence_id="root",
                category=str(item.get("category")) if item.get("category") is not None else None,
                annotation_type=str(item.get("type", "unknown")),
                values=dict(item),
            )
        )
    return annotations, broken_paths


def _index_label_files(root: Path) -> list[AnnotationRecord]:
    annotations: list[AnnotationRecord] = []
    labels_dir = root / "labels"
    for index, file_path in enumerate(
        sorted(path for path in labels_dir.rglob("*") if path.is_file())
    ):
        annotations.append(
            AnnotationRecord(
                annotation_id=f"label-file-{index}",
                sequence_id="root",
                annotation_type="unknown",
                values={"file_path": relative_to_root(root, file_path)},
            )
        )
    return annotations
