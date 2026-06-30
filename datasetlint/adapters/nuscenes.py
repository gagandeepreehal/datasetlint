"""Lightweight nuScenes adapter with direct metadata-table and payload summaries."""

from __future__ import annotations

from collections import Counter
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
        dataset_root = Path(root)
        deep = bool(kwargs.get("deep", False) or kwargs.get("parse_payloads", False))
        max_rows = _positive_int(kwargs.get("max_rows"), default=1000)
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
        ego_poses = _read_table(metadata_dir, "ego_pose.json")
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
            filename = _normalize_sample_data_path(
                dataset_root,
                metadata_dir,
                str(item.get("filename")) if item.get("filename") is not None else None,
            )
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
                sequence_id=_annotation_sequence_id(samples_by_token, annotation),
                category=str(annotation.get("category_name"))
                if annotation.get("category_name") is not None
                else None,
                annotation_type="bbox_3d",
                values=dict(annotation),
                metadata={
                    "sample_token": str(annotation.get("sample_token"))
                    if annotation.get("sample_token") is not None
                    else None,
                    "instance_token": str(annotation.get("instance_token"))
                    if annotation.get("instance_token") is not None
                    else None,
                },
            )
            for annotation in annotations
        ]
        payload_metadata: dict[str, Any] = {}
        if deep:
            payload_metadata = _apply_payload_summaries(
                dataset_root,
                frame_records,
                sensor_types={sensor.sensor_id: sensor.sensor_type for sensor in sensor_records},
                max_rows=max_rows,
            )
            warnings.extend(payload_metadata.get("warnings", []))
        limitations = [
            "nuScenes devkit is optional; this adapter parses metadata JSON tables directly."
        ]
        if deep:
            limitations.append(
                "Deep nuScenes validation summarizes referenced sensor payload headers; "
                "it does not decode full image pixels, point clouds, radar sweeps, map layers, "
                "or devkit metrics."
            )
        else:
            limitations.append(
                "Use --deep to inspect referenced camera, lidar, and radar payload summaries."
            )
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
                "parse_mode": "deep" if deep else "manifest",
                "scene_tokens": sorted(scenes_by_token),
                "sample_tokens": sorted(samples_by_token),
                "sensor_tokens": sorted(sensors_by_token),
                "calibrated_sensor_tokens": sorted(calibrated_by_token),
                "ego_pose_tokens": _tokens(ego_poses),
                **payload_metadata,
            },
            limitations=limitations,
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
        deep = manifest.metadata.get("parse_mode") == "deep"
        errors: list[str] = []
        warnings = list(manifest.provenance.warnings)
        if metadata_dir is None:
            errors.append("No nuScenes metadata folder found.")
        elif metadata_dir.name.startswith("v") and not metadata_dir.name.startswith("v1.0-"):
            warnings.append(f"Unsupported version folder: {metadata_dir.name}.")
        for frame in manifest.frames:
            if frame.file_path and not _local_frame_path(dataset_root, frame.file_path).is_file():
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
        _check_table_links(manifest, errors)
        _check_monotonic_scene_times(manifest, errors)
        scope = _nuscenes_scope(deep, manifest.limitations)
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
        if deep:
            diagnostics = _nuscenes_deep_diagnostics(manifest)
            scope["checked"] = [*scope["checked"], *diagnostics["checked"]]
            errors.extend(diagnostics["errors"])
            warnings.extend(diagnostics["warnings"])
            coverage.update(diagnostics["coverage"])
            stats.update(diagnostics["stats"])
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


def _normalize_sample_data_path(
    dataset_root: Path, metadata_dir: Path, filename: str | None
) -> str | None:
    if filename is None:
        return None
    path = Path(filename)
    if path.is_absolute() or (dataset_root / path).is_file():
        return path.as_posix()
    if metadata_dir == dataset_root and path.parts and path.parts[0] == metadata_dir.name:
        return Path(*path.parts[1:]).as_posix()
    return path.as_posix()


def _local_frame_path(dataset_root: Path, file_path: str) -> Path:
    path = Path(file_path)
    if path.is_absolute():
        return path
    return dataset_root / path


def _tokens(rows: list[dict[str, Any]]) -> list[str]:
    return sorted(str(row.get("token")) for row in rows if row.get("token") is not None)


def _annotation_sequence_id(
    samples_by_token: dict[str, dict[str, Any]], annotation: dict[str, Any]
) -> str | None:
    sample_token = annotation.get("sample_token")
    if sample_token is None:
        return None
    scene_token = samples_by_token.get(str(sample_token), {}).get("scene_token")
    return str(scene_token) if scene_token is not None else None


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


def _nuscenes_scope(deep: bool, limitations: list[str]) -> dict[str, Any]:
    if not deep:
        return validation_scope("nuscenes", limitations)
    return {
        "validation_mode": "deep",
        "checked": [
            "nuScenes metadata table parsing",
            "sample/sample_data/ego_pose references",
            "annotation and calibration metadata",
            "camera image header summaries",
            "lidar and radar payload summaries",
        ],
        "not_checked": [
            "full nuScenes devkit validation",
            "image pixel decoding",
            "full point cloud decoding",
            "radar sweep semantics",
            "map layers",
            "nuScenes metric evaluation",
        ],
        "limitations": limitations,
    }


def _check_table_links(manifest: DatasetManifest, errors: list[str]) -> None:
    sample_tokens = _metadata_token_set(manifest, "sample_tokens")
    ego_pose_tokens = _metadata_token_set(manifest, "ego_pose_tokens")
    for frame in manifest.frames:
        sample_token = frame.metadata.get("sample_token")
        if sample_token is not None and sample_tokens and str(sample_token) not in sample_tokens:
            errors.append(
                f"sample_data {frame.frame_id} references missing sample {sample_token}."
            )
        ego_pose_token = frame.metadata.get("ego_pose_token")
        if (
            ego_pose_token is not None
            and ego_pose_tokens
            and str(ego_pose_token) not in ego_pose_tokens
        ):
            errors.append(
                f"sample_data {frame.frame_id} references missing ego_pose {ego_pose_token}."
            )
    for annotation in manifest.annotations:
        sample_token = annotation.metadata.get("sample_token") or annotation.frame_id
        if sample_token is not None and sample_tokens and str(sample_token) not in sample_tokens:
            errors.append(
                f"sample_annotation {annotation.annotation_id} references missing sample "
                f"{sample_token}."
            )


def _metadata_token_set(manifest: DatasetManifest, name: str) -> set[str]:
    values = manifest.metadata.get(name, [])
    if not isinstance(values, list):
        return set()
    return {str(value) for value in values}


def _apply_payload_summaries(
    dataset_root: Path,
    frames: list[FrameRecord],
    *,
    sensor_types: dict[str, str],
    max_rows: int,
) -> dict[str, Any]:
    checked = 0
    warnings: list[str] = []
    payload_types: Counter[str] = Counter()
    truncated = False
    for frame in frames:
        if checked >= max_rows:
            truncated = True
            break
        sensor_type = sensor_types.get(frame.sensor_id or "", "unknown")
        if sensor_type not in {"camera", "lidar", "radar"} or frame.file_path is None:
            continue
        path = _local_frame_path(dataset_root, frame.file_path)
        if not path.is_file():
            continue
        summary = _payload_summary(path, frame, sensor_type)
        payload_type = str(summary.get("payload_type", sensor_type))
        payload_types[payload_type] += 1
        frame.metadata["payload_checked"] = True
        frame.metadata["payload_valid"] = bool(summary.get("valid"))
        if summary.get("error") is not None:
            frame.metadata["payload_error"] = summary["error"]
        frame.metadata["payload_summary"] = summary
        checked += 1
    if truncated:
        warnings.append(f"nuScenes payload diagnostics stopped at max_rows={max_rows}.")
    return {
        "payload_sample_count": checked,
        "payload_type_counts": dict(sorted(payload_types.items())),
        "payload_sampling_truncated": truncated,
        "max_rows": max_rows,
        "warnings": warnings,
    }


def _payload_summary(path: Path, frame: FrameRecord, sensor_type: str) -> dict[str, Any]:
    if sensor_type == "camera":
        return _camera_payload_summary(path, frame)
    if sensor_type in {"lidar", "radar"}:
        return _point_payload_summary(path, sensor_type)
    return {
        "payload_type": sensor_type,
        "valid": False,
        "size_bytes": _file_size(path),
        "error": f"unsupported nuScenes payload type {sensor_type}",
    }


def _camera_payload_summary(path: Path, frame: FrameRecord) -> dict[str, Any]:
    size_bytes = _file_size(path)
    dimensions = _image_dimensions(path)
    if dimensions is None:
        return {
            "payload_type": "camera_image",
            "valid": False,
            "size_bytes": size_bytes,
            "error": "camera file does not expose a recognized image header",
        }
    width, height, image_format = dimensions
    if frame.width is not None and frame.width != width:
        return {
            "payload_type": "camera_image",
            "valid": False,
            "size_bytes": size_bytes,
            "width": width,
            "height": height,
            "image_format": image_format,
            "error": f"camera width {width} does not match sample_data width {frame.width}",
        }
    if frame.height is not None and frame.height != height:
        return {
            "payload_type": "camera_image",
            "valid": False,
            "size_bytes": size_bytes,
            "width": width,
            "height": height,
            "image_format": image_format,
            "error": f"camera height {height} does not match sample_data height {frame.height}",
        }
    return {
        "payload_type": "camera_image",
        "valid": True,
        "size_bytes": size_bytes,
        "width": width,
        "height": height,
        "image_format": image_format,
    }


def _point_payload_summary(path: Path, sensor_type: str) -> dict[str, Any]:
    size_bytes = _file_size(path)
    if size_bytes <= 0:
        return {
            "payload_type": f"{sensor_type}_points",
            "valid": False,
            "size_bytes": size_bytes,
            "error": f"{sensor_type} payload is empty",
        }
    bytes_per_point = 20 if sensor_type == "lidar" else 4
    if size_bytes % bytes_per_point != 0:
        return {
            "payload_type": f"{sensor_type}_points",
            "valid": False,
            "size_bytes": size_bytes,
            "error": (
                f"{sensor_type} payload size {size_bytes} is not divisible by "
                f"{bytes_per_point} bytes per point"
            ),
        }
    return {
        "payload_type": f"{sensor_type}_points",
        "valid": True,
        "size_bytes": size_bytes,
        "point_count": size_bytes // bytes_per_point,
        "bytes_per_point": bytes_per_point,
    }


def _nuscenes_deep_diagnostics(manifest: DatasetManifest) -> dict[str, Any]:
    sampled = [frame for frame in manifest.frames if frame.metadata.get("payload_checked") is True]
    invalid = [frame for frame in sampled if frame.metadata.get("payload_valid") is not True]
    payload_counts = Counter(
        str(frame.metadata.get("payload_summary", {}).get("payload_type", "unknown"))
        for frame in sampled
    )
    valid_payload_counts = Counter(
        str(frame.metadata.get("payload_summary", {}).get("payload_type", "unknown"))
        for frame in sampled
        if frame.metadata.get("payload_valid") is True
    )
    errors: list[str] = []
    warnings: list[str] = []
    if not manifest.frames:
        errors.append("Deep nuScenes validation decoded no sample_data records.")
    elif not sampled:
        errors.append(
            "Deep nuScenes validation inspected no camera, lidar, or radar payload files."
        )
    for frame in invalid:
        errors.append(
            f"nuScenes payload for frame {frame.frame_id} ({frame.file_path}) is invalid: "
            f"{frame.metadata.get('payload_error', 'unknown payload error')}."
        )
    if manifest.metadata.get("payload_sampling_truncated") is True:
        warnings.append(
            f"nuScenes deep payload diagnostics inspected "
            f"{manifest.metadata.get('payload_sample_count', 0)} payload file(s) and stopped "
            f"at max_rows={manifest.metadata.get('max_rows')}."
        )
    return {
        "checked": ["nuScenes deep payload diagnostics"],
        "errors": errors,
        "warnings": warnings,
        "coverage": {
            "payload_metadata": bool(sampled),
            "camera_payload_headers": valid_payload_counts["camera_image"] > 0,
            "lidar_payload_points": valid_payload_counts["lidar_points"] > 0,
            "radar_payload_points": valid_payload_counts["radar_points"] > 0,
        },
        "stats": {
            "payload_sample_count": len(sampled),
            "camera_image_payload_count": payload_counts["camera_image"],
            "lidar_payload_count": payload_counts["lidar_points"],
            "radar_payload_count": payload_counts["radar_points"],
            "invalid_payload_count": len(invalid),
        },
    }


def _file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _image_dimensions(path: Path) -> tuple[int, int, str] | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        width = int.from_bytes(data[16:20], "big")
        height = int.from_bytes(data[20:24], "big")
        return width, height, "png"
    if data.startswith((b"GIF87a", b"GIF89a")) and len(data) >= 10:
        width = int.from_bytes(data[6:8], "little")
        height = int.from_bytes(data[8:10], "little")
        return width, height, "gif"
    if data.startswith(b"\xff\xd8"):
        jpeg = _jpeg_dimensions(data)
        if jpeg is not None:
            width, height = jpeg
            return width, height, "jpeg"
    return None


def _jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
    index = 2
    start_of_frame_markers = {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }
    while index + 8 < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        while index < len(data) and data[index] == 0xFF:
            index += 1
        if index >= len(data):
            return None
        marker = data[index]
        index += 1
        if marker in {0x01, *range(0xD0, 0xD8), 0xD9}:
            continue
        if index + 2 > len(data):
            return None
        segment_length = int.from_bytes(data[index : index + 2], "big")
        if segment_length < 2 or index + segment_length > len(data):
            return None
        if marker in start_of_frame_markers and segment_length >= 7:
            height = int.from_bytes(data[index + 3 : index + 5], "big")
            width = int.from_bytes(data[index + 5 : index + 7], "big")
            return width, height
        index += segment_length
    return None


def _positive_int(value: object, *, default: int) -> int:
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str):
        try:
            parsed = int(value)
        except ValueError:
            return default
        return parsed if parsed > 0 else default
    return default


def _check_monotonic_scene_times(manifest: DatasetManifest, errors: list[str]) -> None:
    by_sequence: dict[str, list[float]] = {}
    for frame in manifest.frames:
        if frame.sequence_id is not None and frame.timestamp is not None:
            by_sequence.setdefault(frame.sequence_id, []).append(frame.timestamp)
    for sequence_id, timestamps in by_sequence.items():
        if any(timestamps[index] > timestamps[index + 1] for index in range(len(timestamps) - 1)):
            errors.append(f"Non-monotonic sample timestamps in scene {sequence_id}.")
