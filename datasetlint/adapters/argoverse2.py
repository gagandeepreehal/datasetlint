"""Argoverse 2 adapter for common sensor and scenario layouts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

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
from datasetlint.adapters.manifest_rules import merge_common_rule_result, run_manifest_rules

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
LIDAR_EXTENSIONS = {".feather", ".pcd", ".bin", ".ply"}
SCENARIO_EXTENSIONS = {".parquet"}


class Argoverse2Adapter(DatasetAdapter):
    """Index Argoverse 2 sensor logs and motion-forecasting scenarios."""

    name = "argoverse2"
    supported_formats = ("argoverse-2", "av2")
    description = "Argoverse 2 sensor/scenario adapter for logs, sensors, maps, and tables."

    def can_load(self, path: str | Path) -> bool:
        root = Path(path)
        return root.is_dir() and bool(_log_dirs(root))

    def load(self, root: str | Path, **kwargs: Any) -> DatasetManifest:
        del kwargs
        dataset_root = Path(root)
        logs = _log_dirs(dataset_root)
        frames: list[FrameRecord] = []
        annotations: list[AnnotationRecord] = []
        calibration: list[CalibrationRecord] = []
        sequences: list[SequenceRecord] = []
        sensors_by_id: dict[str, SensorStream] = {}
        warnings: list[str] = []

        for log_dir in logs:
            sequence_id = relative_to_root(dataset_root, log_dir)
            log_frames = _frames_for_log(dataset_root, log_dir, sequence_id)
            frames.extend(log_frames)
            annotations.extend(_annotations_for_log(dataset_root, log_dir, sequence_id))
            calibration.extend(_calibration_for_log(dataset_root, log_dir, sequence_id))
            for frame in log_frames:
                if frame.sensor_id is None:
                    continue
                _upsert_sensor(sensors_by_id, frame.sensor_id, frame.metadata)
            sequences.append(
                SequenceRecord(
                    sequence_id=sequence_id,
                    name=log_dir.name,
                    frame_count=len(log_frames) or None,
                    start_time=_min_timestamp(log_frames),
                    end_time=_max_timestamp(log_frames),
                    metadata={
                        "source": relative_to_root(dataset_root, log_dir),
                        "layout": _layout_name(log_dir),
                    },
                )
            )

        for sensor_id, sensor in list(sensors_by_id.items()):
            count = sum(1 for frame in frames if frame.sensor_id == sensor_id)
            sensors_by_id[sensor_id] = sensor.model_copy(update={"frame_count": count})

        if not frames:
            warnings.append(
                "No Argoverse 2 sensor or scenario files were indexed. "
                "Location: dataset root. Fix: point the adapter at an AV2 log root or "
                "a directory containing log/scenario subdirectories."
            )

        return DatasetManifest(
            dataset_name=dataset_root.name,
            adapter_name=self.name,
            dataset_root=str(dataset_root),
            sequences=sequences,
            frames=frames,
            sensors=sorted(sensors_by_id.values(), key=lambda item: item.sensor_id),
            annotations=annotations,
            calibration=calibration,
            splits={},
            metadata={
                "log_count": len(logs),
                "layouts": sorted({_layout_name(log_dir) for log_dir in logs}),
            },
            limitations=[
                "Argoverse 2 payload tables are indexed without requiring av2 or pyarrow.",
                "Sensor images, lidar sweeps, maps, and parquet/feather rows are not decoded.",
            ],
            provenance=manifest_provenance(
                dataset_root,
                source_format="argoverse2",
                adapter_version=self.adapter_version,
                warnings=warnings,
            ),
        )

    def validate(self, root: str | Path, **kwargs: Any) -> AdapterValidationReport:
        manifest = self.load(root, **kwargs)
        errors: list[str] = []
        warnings = list(manifest.provenance.warnings)
        if not manifest.sequences:
            errors.append(
                "No Argoverse 2 logs or scenarios found. Location: dataset root. "
                "Fix: use a root containing AV2 log directories, sensors/, "
                "annotations.feather, or scenario parquet files."
            )
        if manifest.frames and not manifest.calibration:
            warnings.append(
                "No calibration files indexed for Argoverse 2 frames. Location: calibration/. "
                "Fix: include each log's calibration directory when validating sensor data."
            )
        scope = validation_scope(self.name, manifest.limitations)
        coverage = {
            "sequences": bool(manifest.sequences),
            "frames": bool(manifest.frames),
            "sensors": bool(manifest.sensors),
            "annotations": bool(manifest.annotations),
            "calibration": bool(manifest.calibration),
        }
        stats = {
            "sequence_count": len(manifest.sequences),
            "frame_count": len(manifest.frames),
            "sensor_count": len(manifest.sensors),
            "annotation_count": len(manifest.annotations),
            "calibration_count": len(manifest.calibration),
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
            sensors=[sensor.sensor_id for sensor in manifest.sensors],
            raw=manifest.metadata,
        )

    def list_sensors(self, path: str | Path) -> list[SensorInfo]:
        return [
            SensorInfo(
                name=sensor.sensor_id,
                frame_count=sensor.frame_count,
                start_time=_sensor_start(self.load(path).frames, sensor.sensor_id),
                end_time=_sensor_end(self.load(path).frames, sensor.sensor_id),
            )
            for sensor in self.load(path).sensors
        ]

    def load_timestamps(self, path: str | Path, sensor_name: str) -> pd.Series:
        manifest = self.load(path)
        return pd.Series(
            [
                frame.timestamp
                for frame in manifest.frames
                if frame.sensor_id == sensor_name and frame.timestamp is not None
            ],
            dtype=float,
        )


def _log_dirs(root: Path) -> list[Path]:
    if _is_log_dir(root):
        return [root]
    return sorted(child for child in root.iterdir() if child.is_dir() and _is_log_dir(child))


def _is_log_dir(path: Path) -> bool:
    if (path / "sensors" / "cameras").is_dir() or (path / "sensors" / "lidar").is_dir():
        return True
    if (path / "annotations.feather").is_file() or (path / "calibration").is_dir():
        return True
    if any(path.glob("scenario*.parquet")):
        return True
    return (path / "map").is_dir() and any(path.rglob("*.json"))


def _layout_name(log_dir: Path) -> str:
    if any(log_dir.glob("scenario*.parquet")):
        return "motion-forecasting"
    if (log_dir / "sensors").is_dir():
        return "sensor"
    return "metadata"


def _frames_for_log(root: Path, log_dir: Path, sequence_id: str) -> list[FrameRecord]:
    frames: list[FrameRecord] = []
    timestamp_origin = _timestamp_origin_for_log(log_dir)
    camera_root = log_dir / "sensors" / "cameras"
    if camera_root.is_dir():
        for file_path in sorted(path for path in camera_root.rglob("*") if path.is_file()):
            if file_path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            camera_name = file_path.parent.name
            sensor_id = f"{sequence_id}/camera/{camera_name}"
            frames.append(
                _frame(
                    root,
                    file_path,
                    sequence_id,
                    sensor_id,
                    "camera",
                    "image",
                    timestamp_origin,
                )
            )

    lidar_root = log_dir / "sensors" / "lidar"
    if lidar_root.is_dir():
        for file_path in sorted(path for path in lidar_root.rglob("*") if path.is_file()):
            if file_path.suffix.lower() not in LIDAR_EXTENSIONS:
                continue
            sensor_id = f"{sequence_id}/lidar"
            frames.append(
                _frame(
                    root,
                    file_path,
                    sequence_id,
                    sensor_id,
                    "lidar",
                    "point_cloud",
                    timestamp_origin,
                )
            )

    for file_path in sorted(log_dir.glob("scenario*.parquet")):
        sensor_id = f"{sequence_id}/scenario"
        frames.append(
            _frame(root, file_path, sequence_id, sensor_id, "tabular", "scenario", timestamp_origin)
        )
    return frames


def _frame(
    root: Path,
    file_path: Path,
    sequence_id: str,
    sensor_id: str,
    sensor_type: str,
    modality: str,
    timestamp_origin: float | None,
) -> FrameRecord:
    return FrameRecord(
        frame_id=f"{sensor_id}/{file_path.stem}",
        sequence_id=sequence_id,
        timestamp=_timestamp_from_stem(file_path.stem, origin=timestamp_origin),
        sensor_id=sensor_id,
        file_path=relative_to_root(root, file_path),
        metadata={
            "extension": file_path.suffix.lower(),
            "sensor_type": sensor_type,
            "modality": modality,
        },
    )


def _annotations_for_log(root: Path, log_dir: Path, sequence_id: str) -> list[AnnotationRecord]:
    annotations: list[AnnotationRecord] = []
    annotation_file = log_dir / "annotations.feather"
    if annotation_file.is_file():
        annotations.append(
            AnnotationRecord(
                annotation_id=f"{sequence_id}/annotations",
                sequence_id=sequence_id,
                annotation_type="av2_feather_table",
                values={"file_path": relative_to_root(root, annotation_file)},
                metadata={"source": relative_to_root(root, annotation_file)},
            )
        )
    return annotations


def _calibration_for_log(root: Path, log_dir: Path, sequence_id: str) -> list[CalibrationRecord]:
    calibration_dir = log_dir / "calibration"
    if not calibration_dir.is_dir():
        return []
    records: list[CalibrationRecord] = []
    for file_path in sorted(path for path in calibration_dir.rglob("*") if path.is_file()):
        records.append(
            CalibrationRecord(
                sensor_id=f"{sequence_id}/{file_path.stem}",
                metadata={"source": relative_to_root(root, file_path)},
            )
        )
    return records


def _upsert_sensor(
    sensors: dict[str, SensorStream], sensor_id: str, metadata: dict[str, Any]
) -> None:
    sensor_type = str(metadata.get("sensor_type", "unknown"))
    modality = str(metadata.get("modality", "unknown"))
    sensors.setdefault(
        sensor_id,
        SensorStream(
            sensor_id=sensor_id,
            sensor_type=sensor_type,
            name=sensor_id,
            modality=modality,
        ),
    )


def _timestamp_origin_for_log(log_dir: Path) -> float | None:
    values: list[float] = []
    roots = [log_dir / "sensors" / "cameras", log_dir / "sensors" / "lidar"]
    for root in roots:
        if root.is_dir():
            for file_path in root.rglob("*"):
                if file_path.is_file():
                    value = _numeric_stem(file_path.stem)
                    if value is not None:
                        values.append(value)
    for file_path in log_dir.glob("scenario*.parquet"):
        value = _numeric_stem(file_path.stem)
        if value is not None:
            values.append(value)
    return min(values) if values else None


def _timestamp_from_stem(stem: str, *, origin: float | None = None) -> float | None:
    value = _numeric_stem(stem)
    if value is None:
        return None
    raw_value = value
    if origin is not None:
        value -= origin
    if raw_value > 1_000_000_000_000 or (origin is not None and origin > 1_000_000_000_000):
        return value / 1_000_000_000.0
    return value


def _numeric_stem(stem: str) -> float | None:
    try:
        return float(stem)
    except ValueError:
        return None


def _min_timestamp(frames: list[FrameRecord]) -> float | None:
    values = [frame.timestamp for frame in frames if frame.timestamp is not None]
    return min(values) if values else None


def _max_timestamp(frames: list[FrameRecord]) -> float | None:
    values = [frame.timestamp for frame in frames if frame.timestamp is not None]
    return max(values) if values else None


def _sensor_start(frames: list[FrameRecord], sensor_id: str) -> float | None:
    values = [
        frame.timestamp
        for frame in frames
        if frame.sensor_id == sensor_id and frame.timestamp is not None
    ]
    return min(values) if values else None


def _sensor_end(frames: list[FrameRecord], sensor_id: str) -> float | None:
    values = [
        frame.timestamp
        for frame in frames
        if frame.sensor_id == sensor_id and frame.timestamp is not None
    ]
    return max(values) if values else None
