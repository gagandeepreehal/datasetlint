"""Lightweight nuScenes adapter with direct metadata-table parsing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from datasetlint.adapters.base import (
    AdapterInfo,
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
    read_json_list,
    relative_to_root,
    validation_scope,
)
from datasetlint.adapters.manifest_rules import merge_common_rule_result, run_manifest_rules

TABLES = (
    "sample.json",
    "sample_data.json",
    "scene.json",
    "calibrated_sensor.json",
    "sensor.json",
    "ego_pose.json",
)


class NuScenesAdapter(DatasetAdapter):
    """Parse nuScenes metadata JSON tables without requiring the devkit."""

    name = "nuscenes"
    supported_formats = ("nuscenes", "v1.0-mini", "v1.0-trainval", "v1.0-test")
    optional_dependencies = ("nuscenes",)
    description = "nuScenes metadata adapter for scenes, sample_data, sensors, and calibration."

    def availability(self) -> AdapterInfo:
        info = super().availability()
        return AdapterInfo(
            name=info.name,
            supported_formats=info.supported_formats,
            availability="available",
            optional_dependencies=info.optional_dependencies,
            description=info.description,
        )

    def can_load(self, path: str | Path) -> bool:
        root = Path(path)
        if not root.is_dir():
            return False
        metadata_dir = _metadata_dir(root)
        return metadata_dir is not None and any(
            (metadata_dir / table).is_file() for table in TABLES
        )

    def load(self, root: str | Path, **kwargs: Any) -> DatasetManifest:
        del kwargs
        dataset_root = Path(root)
        metadata_dir = _metadata_dir(dataset_root)
        if metadata_dir is None:
            raise ValueError("No nuScenes metadata folder found.")
        version = metadata_dir.name if metadata_dir.name.startswith("v1.0-") else None
        warnings: list[str] = []
        scenes = _read_table(metadata_dir, "scene.json")
        samples = _read_table(metadata_dir, "sample.json")
        sample_data = _read_table(metadata_dir, "sample_data.json")
        calibrated_sensors = _read_table(metadata_dir, "calibrated_sensor.json")
        sensors = _read_table(metadata_dir, "sensor.json")
        annotations = _read_table(metadata_dir, "sample_annotation.json")

        scenes_by_token = {str(scene.get("token")): scene for scene in scenes}
        samples_by_token = {str(sample.get("token")): sample for sample in samples}
        calibrated_by_token = {str(item.get("token")): item for item in calibrated_sensors}
        sensors_by_token = {str(sensor.get("token")): sensor for sensor in sensors}
        sequence_records = [
            SequenceRecord(
                sequence_id=str(scene.get("token")),
                name=str(scene.get("name")) if scene.get("name") is not None else None,
                frame_count=_optional_int(scene.get("nbr_samples")),
                start_time=None,
                end_time=None,
                metadata=dict(scene),
            )
            for scene in scenes
        ]
        frame_records: list[FrameRecord] = []
        sensor_counts: dict[str, int] = {}
        for item in sample_data:
            calibrated = calibrated_by_token.get(str(item.get("calibrated_sensor_token")))
            sensor = (
                sensors_by_token.get(str(calibrated.get("sensor_token"))) if calibrated else None
            )
            sensor_id = str(
                item.get("channel")
                or (sensor or {}).get("channel")
                or item.get("calibrated_sensor_token")
            )
            sample = samples_by_token.get(str(item.get("sample_token")))
            sequence_id = str(sample.get("scene_token")) if sample else None
            filename = str(item.get("filename")) if item.get("filename") is not None else None
            frame_records.append(
                FrameRecord(
                    frame_id=str(item.get("token")),
                    sequence_id=sequence_id,
                    timestamp=_timestamp_seconds(item.get("timestamp")),
                    sensor_id=sensor_id,
                    file_path=filename,
                    width=_optional_int(item.get("width")),
                    height=_optional_int(item.get("height")),
                    metadata=dict(item),
                )
            )
            sensor_counts[sensor_id] = sensor_counts.get(sensor_id, 0) + 1

        sensor_records = [
            SensorStream(
                sensor_id=str(sensor.get("channel", sensor.get("token"))),
                sensor_type=_nuscenes_sensor_type(str(sensor.get("modality", "unknown"))),
                name=str(sensor.get("channel", sensor.get("token"))),
                modality=str(sensor.get("modality"))
                if sensor.get("modality") is not None
                else None,
                frame_count=sensor_counts.get(str(sensor.get("channel", sensor.get("token")))),
                metadata=dict(sensor),
            )
            for sensor in sensors
        ]
        calibration_records = [
            CalibrationRecord(
                sensor_id=str(
                    (sensors_by_token.get(str(item.get("sensor_token"))) or {}).get(
                        "channel", item.get("token")
                    )
                ),
                intrinsic=item.get("camera_intrinsic")
                if isinstance(item.get("camera_intrinsic"), list)
                else None,
                extrinsic=None,
                metadata=dict(item),
            )
            for item in calibrated_sensors
        ]
        annotation_records = [
            AnnotationRecord(
                annotation_id=str(annotation.get("token")),
                frame_id=str(annotation.get("sample_token"))
                if annotation.get("sample_token") is not None
                else None,
                sequence_id=str(
                    samples_by_token.get(str(annotation.get("sample_token")), {}).get("scene_token")
                ),
                category=str(annotation.get("category_name"))
                if annotation.get("category_name") is not None
                else None,
                annotation_type="bbox_3d",
                values=dict(annotation),
            )
            for annotation in annotations
        ]
        return DatasetManifest(
            dataset_name=dataset_root.name,
            adapter_name=self.name,
            dataset_root=str(dataset_root),
            version=version,
            sequences=sequence_records,
            frames=frame_records,
            sensors=sensor_records,
            annotations=annotation_records,
            calibration=calibration_records,
            splits={},
            metadata={
                "metadata_dir": relative_to_root(dataset_root, metadata_dir),
                "scene_tokens": sorted(scenes_by_token),
            },
            limitations=[
                "nuScenes devkit is optional; this adapter parses metadata JSON tables directly."
            ],
            provenance=manifest_provenance(
                dataset_root,
                source_format="nuscenes",
                adapter_version=self.adapter_version,
                warnings=warnings,
            ),
        )

    def validate(self, root: str | Path, **kwargs: Any) -> AdapterValidationReport:
        manifest = self.load(root, **kwargs)
        dataset_root = Path(root)
        metadata_dir = _metadata_dir(dataset_root)
        errors: list[str] = []
        warnings = list(manifest.provenance.warnings)
        if metadata_dir is None:
            errors.append("No nuScenes metadata folder found.")
        elif metadata_dir.name.startswith("v") and not metadata_dir.name.startswith("v1.0-"):
            warnings.append(f"Unsupported version folder: {metadata_dir.name}.")
        for frame in manifest.frames:
            if frame.file_path and not (dataset_root / frame.file_path).is_file():
                errors.append(f"Missing sample_data file: {frame.file_path}.")
        sensor_ids = {sensor.sensor_id for sensor in manifest.sensors}
        calibration_ids = {record.sensor_id for record in manifest.calibration}
        for frame in manifest.frames:
            if frame.sensor_id and frame.sensor_id not in sensor_ids:
                errors.append(f"Missing sensor entry for {frame.sensor_id}.")
            if frame.sensor_id and frame.sensor_id not in calibration_ids:
                errors.append(f"Missing calibrated sensor for {frame.sensor_id}.")
        if metadata_dir is not None and not (metadata_dir / "ego_pose.json").is_file():
            errors.append("Missing ego_pose.json.")
        _check_monotonic_scene_times(manifest, errors)
        scope = validation_scope(self.name, manifest.limitations)
        coverage = {
            "sequences": bool(manifest.sequences),
            "frames": bool(manifest.frames),
            "sensors": bool(manifest.sensors),
            "calibration": bool(manifest.calibration),
            "annotations": bool(manifest.annotations),
        }
        stats = {
            "sequence_count": len(manifest.sequences),
            "sample_data_count": len(manifest.frames),
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

    def load_timestamps(self, path: str | Path, sensor_name: str) -> pd.Series:
        values = [
            frame.timestamp for frame in self.load(path).frames if frame.sensor_id == sensor_name
        ]
        return pd.Series([value for value in values if value is not None], dtype=float)


def _metadata_dir(root: Path) -> Path | None:
    if all((root / table).is_file() for table in ("sample.json", "sample_data.json")):
        return root
    version_dirs = sorted(
        child for child in root.iterdir() if child.is_dir() and child.name.startswith("v")
    )
    for version_dir in version_dirs:
        if all((version_dir / table).is_file() for table in ("sample.json", "sample_data.json")):
            return version_dir
    return None


def _read_table(root: Path, filename: str) -> list[dict[str, Any]]:
    path = root / filename
    if not path.is_file():
        return []
    return read_json_list(path)


def _timestamp_seconds(value: object) -> float | None:
    if not isinstance(value, str | bytes | bytearray | int | float):
        return None
    try:
        return float(value) / 1_000_000.0
    except (TypeError, ValueError):
        return None


def _optional_int(value: object) -> int | None:
    if not isinstance(value, str | bytes | bytearray | int | float):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _nuscenes_sensor_type(modality: str) -> str:
    normalized = modality.lower()
    if normalized in {"camera", "lidar", "radar"}:
        return normalized
    return "unknown"


def _check_monotonic_scene_times(manifest: DatasetManifest, errors: list[str]) -> None:
    by_sequence: dict[str, list[float]] = {}
    for frame in manifest.frames:
        if frame.sequence_id is not None and frame.timestamp is not None:
            by_sequence.setdefault(frame.sequence_id, []).append(frame.timestamp)
    for sequence_id, timestamps in by_sequence.items():
        if any(timestamps[index] > timestamps[index + 1] for index in range(len(timestamps) - 1)):
            errors.append(f"Non-monotonic sample timestamps in scene {sequence_id}.")
