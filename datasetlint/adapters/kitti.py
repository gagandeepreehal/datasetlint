"""KITTI object and odometry dataset adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

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

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


class KittiAdapter(DatasetAdapter):
    """Parse common KITTI object-detection and odometry layouts."""

    name = "kitti"
    supported_formats = ("kitti-object", "kitti-odometry")
    description = "KITTI camera, lidar, label_2, calib, and odometry sequence adapter."

    def can_load(self, path: str | Path) -> bool:
        root = Path(path)
        if not root.is_dir():
            return False
        object_like = (root / "image_2").is_dir() or (root / "velodyne").is_dir()
        odometry_like = (root / "sequences").is_dir() and any(
            (root / "sequences").glob("*/image_2")
        )
        return object_like or odometry_like

    def load(self, root: str | Path, **kwargs: Any) -> DatasetManifest:
        del kwargs
        dataset_root = Path(root)
        warnings: list[str] = []
        if (dataset_root / "sequences").is_dir():
            return self._load_odometry(dataset_root, warnings)
        return self._load_object(dataset_root, warnings)

    def validate(self, root: str | Path, **kwargs: Any) -> AdapterValidationReport:
        manifest = self.load(root, **kwargs)
        dataset_root = Path(root)
        errors: list[str] = []
        warnings = list(manifest.provenance.warnings)
        image_ids = {
            _logical_frame_id(frame)
            for frame in manifest.frames
            if frame.sensor_id and "image" in frame.sensor_id
        }
        lidar_ids = {
            _logical_frame_id(frame)
            for frame in manifest.frames
            if frame.sensor_id and "velodyne" in frame.sensor_id
        }
        if image_ids and lidar_ids:
            missing_lidar = sorted(image_ids - lidar_ids)
            missing_images = sorted(lidar_ids - image_ids)
            if missing_lidar:
                warnings.append(f"Missing velodyne files for frames: {', '.join(missing_lidar)}.")
            if missing_images:
                errors.append(f"Missing image files for lidar frames: {', '.join(missing_images)}.")
        if (dataset_root / "label_2").is_dir():
            label_ids = {
                path.stem for path in (dataset_root / "label_2").glob("*.txt") if path.is_file()
            }
            missing_labels = sorted(image_ids - label_ids)
            if missing_labels:
                warnings.append(f"Missing label files for frames: {', '.join(missing_labels)}.")
        if not manifest.calibration:
            warnings.append("Calibration missing.")
        invalid_labels = [
            annotation.annotation_id
            for annotation in manifest.annotations
            if annotation.metadata.get("invalid_row_length") is True
        ]
        if invalid_labels:
            errors.append(f"Invalid KITTI label row length: {', '.join(invalid_labels)}.")
        for sequence in manifest.sequences:
            times = sequence.metadata.get("timestamps")
            if isinstance(times, list) and any(
                times[index] >= times[index + 1] for index in range(len(times) - 1)
            ):
                errors.append(f"Non-monotonic timestamps in sequence {sequence.sequence_id}.")
            expected = sequence.frame_count
            if isinstance(times, list) and expected is not None and len(times) != expected:
                warnings.append(
                    f"Timestamp count mismatch in sequence {sequence.sequence_id}: "
                    f"{len(times)} timestamps for {expected} frames."
                )
        scope = validation_scope(self.name, manifest.limitations)
        coverage = {
            "frames": bool(manifest.frames),
            "annotations": bool(manifest.annotations),
            "calibration": bool(manifest.calibration),
            "lidar": bool(lidar_ids),
        }
        stats = {
            "sequence_count": len(manifest.sequences),
            "frame_count": len(manifest.frames),
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
            SensorInfo(name=sensor.sensor_id, frame_count=sensor.frame_count)
            for sensor in self.load(path).sensors
        ]

    def _load_object(self, root: Path, warnings: list[str]) -> DatasetManifest:
        image_files = _image_files(root / "image_2")
        velodyne_files = (
            sorted((root / "velodyne").glob("*.bin")) if (root / "velodyne").is_dir() else []
        )
        frames = _frames_for_files(root, image_files, "image_2") + _frames_for_files(
            root, velodyne_files, "velodyne"
        )
        annotations = _labels(root, root / "label_2")
        calibration = _calibration_records(root, root / "calib")
        sensors = _sensor_streams(frames)
        sequence = SequenceRecord(
            sequence_id="object",
            name=root.name,
            frame_count=len(image_files) or None,
            metadata={"layout": "object"},
        )
        return DatasetManifest(
            dataset_name=root.name,
            adapter_name=self.name,
            dataset_root=str(root),
            sequences=[sequence],
            frames=frames,
            sensors=sensors,
            annotations=annotations,
            calibration=calibration,
            splits={},
            metadata={"layout": "object"},
            limitations=["KITTI point clouds are indexed without loading binary data."],
            provenance=manifest_provenance(
                root, source_format="kitti", adapter_version=self.adapter_version, warnings=warnings
            ),
        )

    def _load_odometry(self, root: Path, warnings: list[str]) -> DatasetManifest:
        frames: list[FrameRecord] = []
        sequences: list[SequenceRecord] = []
        calibration: list[CalibrationRecord] = []
        for sequence_dir in sorted((root / "sequences").iterdir()):
            if not sequence_dir.is_dir():
                continue
            sequence_id = sequence_dir.name
            timestamps = _times(sequence_dir / "times.txt")
            image_files = _image_files(sequence_dir / "image_2")
            velodyne_files = (
                sorted((sequence_dir / "velodyne").glob("*.bin"))
                if (sequence_dir / "velodyne").is_dir()
                else []
            )
            frames.extend(
                _frames_for_files(root, image_files, f"{sequence_id}/image_2", timestamps)
            )
            frames.extend(
                _frames_for_files(root, velodyne_files, f"{sequence_id}/velodyne", timestamps)
            )
            calibration.extend(_calibration_file_records(sequence_id, sequence_dir / "calib.txt"))
            sequences.append(
                SequenceRecord(
                    sequence_id=sequence_id,
                    name=sequence_id,
                    frame_count=len(image_files) or None,
                    metadata={"layout": "odometry", "timestamps": timestamps},
                )
            )
        return DatasetManifest(
            dataset_name=root.name,
            adapter_name=self.name,
            dataset_root=str(root),
            sequences=sequences,
            frames=frames,
            sensors=_sensor_streams(frames),
            annotations=[],
            calibration=calibration,
            splits={},
            metadata={"layout": "odometry"},
            limitations=["KITTI odometry labels are not part of the common raw layout."],
            provenance=manifest_provenance(
                root, source_format="kitti", adapter_version=self.adapter_version, warnings=warnings
            ),
        )


def _image_files(path: Path) -> list[Path]:
    if not path.is_dir():
        return []
    return sorted(
        file_path for file_path in path.iterdir() if file_path.suffix.lower() in IMAGE_EXTENSIONS
    )


def _frames_for_files(
    root: Path, files: list[Path], sensor_id: str, timestamps: list[float] | None = None
) -> list[FrameRecord]:
    records: list[FrameRecord] = []
    for index, file_path in enumerate(files):
        records.append(
            FrameRecord(
                frame_id=_sensor_frame_id(sensor_id, file_path),
                sequence_id=sensor_id.split("/", 1)[0] if "/" in sensor_id else "object",
                timestamp=timestamps[index]
                if timestamps is not None and index < len(timestamps)
                else None,
                sensor_id=sensor_id,
                file_path=relative_to_root(root, file_path),
                metadata={
                    "extension": file_path.suffix.lower(),
                    "logical_frame_id": file_path.stem,
                },
            )
        )
    return records


def _labels(root: Path, labels_dir: Path) -> list[AnnotationRecord]:
    if not labels_dir.is_dir():
        return []
    annotations: list[AnnotationRecord] = []
    for label_file in sorted(labels_dir.glob("*.txt")):
        for row_index, line in enumerate(label_file.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            parts = line.split()
            values: dict[str, Any] = {"raw": line, "fields": parts}
            if len(parts) >= 15:
                values.update(
                    {
                        "bbox_2d": [float(value) for value in parts[4:8]],
                        "dimensions_hwl": [float(value) for value in parts[8:11]],
                        "location_xyz": [float(value) for value in parts[11:14]],
                        "rotation_y": float(parts[14]),
                    }
                )
            annotations.append(
                AnnotationRecord(
                    annotation_id=f"{label_file.stem}-{row_index}",
                    frame_id=f"image_2/{label_file.stem}",
                    sequence_id="object",
                    category=parts[0] if parts else None,
                    annotation_type="bbox_3d" if len(parts) >= 15 else "unknown",
                    values=values,
                    metadata={
                        "source": relative_to_root(root, label_file),
                        "invalid_row_length": len(parts) < 15,
                    },
                )
            )
    return annotations


def _calibration_records(root: Path, calib_dir: Path) -> list[CalibrationRecord]:
    if not calib_dir.is_dir():
        return []
    records: list[CalibrationRecord] = []
    for calib_file in sorted(calib_dir.glob("*.txt")):
        records.extend(_calibration_file_records(calib_file.stem, calib_file, root=root))
    return records


def _calibration_file_records(
    frame_id: str, calib_file: Path, root: Path | None = None
) -> list[CalibrationRecord]:
    if not calib_file.is_file():
        return []
    metadata = {
        "frame_id": frame_id,
        "source": str(calib_file if root is None else relative_to_root(root, calib_file)),
    }
    sensor_prefix = f"{frame_id}/" if root is None else ""
    return [
        CalibrationRecord(
            sensor_id=f"{sensor_prefix}image_2",
            target_sensor_id=f"{sensor_prefix}velodyne",
            intrinsic=_parse_projection(calib_file),
            metadata=metadata,
        )
    ]


def _sensor_frame_id(sensor_id: str, file_path: Path) -> str:
    return f"{sensor_id}/{file_path.stem}"


def _logical_frame_id(frame: FrameRecord) -> str:
    value = frame.metadata.get("logical_frame_id")
    return str(value) if value is not None else frame.frame_id.rsplit("/", 1)[-1]


def _parse_projection(path: Path) -> list[list[float]] | None:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(("P2:", "P_rect_02:")):
            values = [float(value) for value in line.split(":", 1)[1].split()]
            if len(values) >= 12:
                return [values[0:3], values[4:7], values[8:11]]
    return None


def _times(path: Path) -> list[float]:
    if not path.is_file():
        return []
    times: list[float] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            times.append(float(line.strip()))
        except ValueError:
            continue
    return times


def _sensor_streams(frames: list[FrameRecord]) -> list[SensorStream]:
    sensors: list[SensorStream] = []
    for sensor_id in sorted({frame.sensor_id for frame in frames if frame.sensor_id is not None}):
        frame_count = sum(1 for frame in frames if frame.sensor_id == sensor_id)
        sensor_type = "lidar" if "velodyne" in sensor_id else "camera"
        modality = "point_cloud" if sensor_type == "lidar" else "image"
        sensors.append(
            SensorStream(
                sensor_id=sensor_id,
                sensor_type=sensor_type,
                name=sensor_id,
                modality=modality,
                frame_count=frame_count,
            )
        )
    return sensors
