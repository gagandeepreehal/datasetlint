"""Dataset adapter interfaces and normalized manifest models."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from datasetlint.adapters.errors import UnsupportedDatasetFeature


class SerializableModel(BaseModel):
    """Base model with stable JSON helpers."""

    model_config = ConfigDict(extra="forbid")

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)


class DatasetMetadata(SerializableModel):
    """Normalized metadata returned by legacy adapters."""

    dataset_path: str
    name: str | None = None
    version: str | None = None
    sensors: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class SensorInfo(SerializableModel):
    """Basic sensor stream information used by existing checks."""

    name: str
    path: str | None = None
    frame_count: int | None = None
    start_time: float | None = None
    end_time: float | None = None
    inferred_frequency_hz: float | None = None


class AdapterDetection(SerializableModel):
    """Adapter detection result for CLI reporting."""

    name: str
    can_load: bool
    message: str


class AdapterProvenance(SerializableModel):
    """How an adapter produced a manifest."""

    source_format: str
    adapter_version: str
    loaded_at: str
    root_hash: str | None
    files_indexed: int
    warnings: list[str] = Field(default_factory=list)


class SequenceRecord(SerializableModel):
    sequence_id: str
    name: str | None = None
    split: str | None = None
    frame_count: int | None = None
    start_time: float | None = None
    end_time: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class FrameRecord(SerializableModel):
    frame_id: str
    sequence_id: str | None = None
    timestamp: float | None = None
    sensor_id: str | None = None
    file_path: str | None = None
    width: int | None = None
    height: int | None = None
    checksum: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SensorStream(SerializableModel):
    sensor_id: str
    sensor_type: str
    name: str | None = None
    modality: str | None = None
    frequency_hz: float | None = None
    frame_count: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnnotationRecord(SerializableModel):
    annotation_id: str
    frame_id: str | None = None
    sequence_id: str | None = None
    category: str | None = None
    annotation_type: str
    values: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CalibrationRecord(SerializableModel):
    sensor_id: str
    target_sensor_id: str | None = None
    intrinsic: list[list[float]] | None = None
    extrinsic: list[list[float]] | None = None
    distortion: list[float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DatasetManifest(SerializableModel):
    dataset_name: str
    adapter_name: str
    dataset_root: str
    version: str | None = None
    sequences: list[SequenceRecord] = Field(default_factory=list)
    frames: list[FrameRecord] = Field(default_factory=list)
    sensors: list[SensorStream] = Field(default_factory=list)
    annotations: list[AnnotationRecord] = Field(default_factory=list)
    calibration: list[CalibrationRecord] = Field(default_factory=list)
    splits: dict[str, list[str]] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    provenance: AdapterProvenance


class AdapterValidationReport(SerializableModel):
    adapter_name: str
    dataset_root: str
    detected: bool
    valid: bool
    validation_mode: str = "manifest-level"
    checked: list[str] = Field(default_factory=list)
    not_checked: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    coverage: dict[str, Any] = Field(default_factory=dict)
    stats: dict[str, Any] = Field(default_factory=dict)


class AdapterInfo(SerializableModel):
    name: str
    supported_formats: list[str]
    availability: str
    optional_dependencies: dict[str, bool]
    description: str


class DatasetAdapter:
    """Base class for dataset adapters.

    Existing lint checks use the legacy CSV-oriented methods. New dataset-format
    support uses ``detect``, ``load``, and ``validate`` to produce normalized
    manifests without forcing every dataset into the native folder format.
    """

    name = "base"
    supported_formats: tuple[str, ...] = ()
    optional_dependencies: tuple[str, ...] = ()
    description = "Base adapter."
    adapter_version = "0.1"

    @property
    def adapter_name(self) -> str:
        return self.name

    def can_load(self, path: str | Path) -> bool:
        raise NotImplementedError

    def detect(self, root: str | Path) -> bool:
        return self.can_load(root)

    def load(self, root: str | Path, **kwargs: Any) -> DatasetManifest:
        raise UnsupportedDatasetFeature(
            f"Adapter '{self.name}' does not implement normalized manifest loading."
        )

    def validate(self, root: str | Path, **kwargs: Any) -> AdapterValidationReport:
        detected = self.detect(root)
        errors: list[str] = []
        warnings: list[str] = []
        manifest: DatasetManifest | None = None
        if not detected:
            errors.append(f"Adapter '{self.name}' did not detect this dataset.")
        else:
            try:
                manifest = self.load(root, **kwargs)
            except Exception as exc:
                errors.append(str(exc))
        if manifest is not None:
            warnings.extend(manifest.provenance.warnings)
            warnings.extend(manifest.limitations)
        return AdapterValidationReport(
            adapter_name=self.name,
            dataset_root=str(root),
            detected=detected,
            valid=not errors,
            **validation_scope(self.name, manifest.limitations if manifest is not None else []),
            errors=errors,
            warnings=warnings,
            coverage=_coverage_for_manifest(manifest),
            stats=_stats_for_manifest(manifest),
        )

    def availability(self) -> AdapterInfo:
        deps = {
            dependency: _module_available(dependency) for dependency in self.optional_dependencies
        }
        status = "available" if all(deps.values()) else "available-index-only"
        if not deps:
            status = "available"
        return AdapterInfo(
            name=self.name,
            supported_formats=list(self.supported_formats),
            availability=status,
            optional_dependencies=deps,
            description=self.description,
        )

    def iter_sequences(self, root: str | Path, **kwargs: Any) -> list[SequenceRecord]:
        return self.load(root, **kwargs).sequences

    def iter_frames(
        self, root: str | Path, sequence_id: str | None = None, **kwargs: Any
    ) -> list[FrameRecord]:
        frames = self.load(root, **kwargs).frames
        if sequence_id is None:
            return frames
        return [frame for frame in frames if frame.sequence_id == sequence_id]

    def iter_annotations(
        self, root: str | Path, sequence_id: str | None = None, **kwargs: Any
    ) -> list[AnnotationRecord]:
        annotations = self.load(root, **kwargs).annotations
        if sequence_id is None:
            return annotations
        return [annotation for annotation in annotations if annotation.sequence_id == sequence_id]

    def get_sensor_streams(self, root: str | Path, **kwargs: Any) -> list[SensorStream]:
        return self.load(root, **kwargs).sensors

    def get_calibration(self, root: str | Path, **kwargs: Any) -> list[CalibrationRecord]:
        return self.load(root, **kwargs).calibration

    def get_metadata(self, root: str | Path, **kwargs: Any) -> dict[str, Any]:
        return self.load(root, **kwargs).metadata

    def load_metadata(self, path: str | Path) -> DatasetMetadata:
        raise NotImplementedError

    def list_sensors(self, path: str | Path) -> list[SensorInfo]:
        raise NotImplementedError

    def load_timestamps(self, path: str | Path, sensor_name: str) -> pd.Series:
        raise NotImplementedError

    def load_labels(self, path: str | Path) -> pd.DataFrame | None:
        raise NotImplementedError

    def load_trajectory(self, path: str | Path) -> pd.DataFrame | None:
        raise NotImplementedError

    def load_calibration(self, path: str | Path) -> dict[str, Any] | None:
        raise NotImplementedError


def manifest_provenance(
    root: str | Path,
    *,
    source_format: str,
    adapter_version: str = "0.1",
    warnings: list[str] | None = None,
) -> AdapterProvenance:
    root_path = Path(root)
    files = indexed_files(root_path)
    return AdapterProvenance(
        source_format=source_format,
        adapter_version=adapter_version,
        loaded_at=datetime.now(timezone.utc).isoformat(),
        root_hash=root_hash(root_path),
        files_indexed=len(files),
        warnings=warnings or [],
    )


def indexed_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    if not root.is_dir():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file())


def root_hash(root: Path) -> str | None:
    files = indexed_files(root)
    if not files:
        return None
    digest = hashlib.sha256()
    base = root if root.is_dir() else root.parent
    for file_path in files:
        try:
            relative = file_path.relative_to(base).as_posix()
            stat = file_path.stat()
        except OSError:
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(stat.st_size).encode("ascii"))
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def read_json_object(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return raw


def read_json_list(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, list):
        raise ValueError(f"{path} must contain a JSON list.")
    return [item for item in raw if isinstance(item, dict)]


def relative_to_root(root: Path, path: Path) -> str:
    base = root if root.is_dir() else root.parent
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def validation_scope(adapter_name: str, limitations: list[str] | None = None) -> dict[str, Any]:
    scope = _VALIDATION_SCOPES.get(adapter_name, _VALIDATION_SCOPES["generic"])
    merged_limitations = [*scope["limitations"], *(limitations or [])]
    return {
        "validation_mode": scope["validation_mode"],
        "checked": list(scope["checked"]),
        "not_checked": list(scope["not_checked"]),
        "limitations": _unique_strings(merged_limitations),
    }


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value not in seen:
            unique.append(value)
            seen.add(value)
    return unique


_VALIDATION_SCOPES: dict[str, dict[str, Any]] = {
    "folder": {
        "validation_mode": "manifest-level",
        "checked": [
            "native folder manifest extraction",
            "metadata, sensor, label, trajectory, and calibration file discovery",
        ],
        "not_checked": [
            "deep lint rules; use datasetlint lint or datasetlint DATASET for full native checks"
        ],
        "limitations": [
            "Adapter validation for native folders is manifest-level; lint commands run deep rules."
        ],
    },
    "generic": {
        "validation_mode": "manifest-level",
        "checked": ["recursive file index", "media/label/timestamp filename patterns"],
        "not_checked": ["format-specific schemas", "sensor synchronization", "label geometry"],
        "limitations": ["Generic folder validation infers structure from filenames and extensions."],
    },
    "coco": {
        "validation_mode": "manifest-level",
        "checked": [
            "COCO JSON structure",
            "image references",
            "category references",
            "basic bbox dimensions",
        ],
        "not_checked": ["image payload decoding", "robotics calibration", "sensor synchronization"],
        "limitations": ["COCO validation is manifest-level and does not decode image contents."],
    },
    "kitti": {
        "validation_mode": "manifest-level",
        "checked": [
            "KITTI object/odometry layout",
            "image/lidar file pairing",
            "label row shape",
            "calibration file presence",
            "odometry timestamp monotonicity",
        ],
        "not_checked": ["binary point cloud contents", "camera image decoding", "3D geometry realism"],
        "limitations": ["KITTI validation parses text metadata and indexes binary sensor files."],
    },
    "nuscenes": {
        "validation_mode": "manifest-level",
        "checked": [
            "nuScenes metadata tables",
            "sample/sample_data references",
            "annotation references",
            "calibrated sensor references",
        ],
        "not_checked": ["sensor payload decoding", "map layers", "full devkit evaluation checks"],
        "limitations": ["nuScenes validation uses metadata tables and lightweight file checks."],
    },
    "waymo": {
        "validation_mode": "index-level",
        "checked": ["TFRecord file discovery", "file sizes", "duplicate segment names"],
        "not_checked": ["frame parsing", "labels", "calibration", "sensor synchronization"],
        "limitations": ["Waymo validation is index-level unless optional parsers are implemented."],
    },
    "rosbag": {
        "validation_mode": "index-level",
        "checked": [
            "ROS bag file discovery",
            "ROS2 metadata.yaml presence",
            "empty bag files",
            "lightweight topic summaries when metadata is available",
        ],
        "not_checked": ["message payloads", "topic schemas", "timestamp synchronization"],
        "limitations": ["ROS bag validation is index-level without optional ROS bag parsers."],
    },
    "mcap": {
        "validation_mode": "index-level",
        "checked": ["MCAP file discovery", "file sizes", "empty file detection"],
        "not_checked": ["messages", "channels", "schemas", "timestamp synchronization"],
        "limitations": ["MCAP validation is index-level unless optional parsers are implemented."],
    },
    "huggingface": {
        "validation_mode": "manifest-level",
        "checked": ["cache metadata or remote dataset metadata", "split/sample availability"],
        "not_checked": [
            "full dataset scan",
            "robotics calibration",
            "sensor synchronization",
            "label geometry",
        ],
        "limitations": ["Hugging Face validation samples or indexes dataset metadata."],
    },
}


def _coverage_for_manifest(manifest: DatasetManifest | None) -> dict[str, Any]:
    if manifest is None:
        return {}
    return {
        "sequences": bool(manifest.sequences),
        "frames": bool(manifest.frames),
        "sensors": bool(manifest.sensors),
        "annotations": bool(manifest.annotations),
        "calibration": bool(manifest.calibration),
        "splits": bool(manifest.splits),
    }


def _stats_for_manifest(manifest: DatasetManifest | None) -> dict[str, Any]:
    if manifest is None:
        return {}
    return {
        "sequence_count": len(manifest.sequences),
        "frame_count": len(manifest.frames),
        "sensor_count": len(manifest.sensors),
        "annotation_count": len(manifest.annotations),
        "calibration_count": len(manifest.calibration),
        "split_count": len(manifest.splits),
        "limitations_count": len(manifest.limitations),
    }


def _module_available(module_name: str) -> bool:
    import importlib.util

    return importlib.util.find_spec(module_name) is not None
