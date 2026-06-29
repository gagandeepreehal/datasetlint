"""Waymo Open Dataset adapter with lightweight TFRecord indexing."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from datasetlint.adapters.base import (
    AdapterValidationReport,
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
    """Index Waymo TFRecord segments without importing TensorFlow."""

    name = "waymo"
    supported_formats = ("waymo-open-dataset", "tfrecord")
    optional_dependencies = ("waymo_open_dataset",)
    description = "Waymo TFRecord index adapter; detailed parsing uses optional Waymo dependencies."

    def can_load(self, path: str | Path) -> bool:
        dataset_path = Path(path)
        if dataset_path.is_file():
            return _is_tfrecord(dataset_path)
        if not dataset_path.is_dir():
            return False
        return any(_is_tfrecord(file_path) for file_path in dataset_path.rglob("*"))

    def load(self, root: str | Path, **kwargs: Any) -> DatasetManifest:
        parse_records = bool(kwargs.get("parse_records", False))
        if parse_records:
            raise AdapterDependencyError(
                "Detailed Waymo parsing requires the optional waymo-open-dataset package."
            )
        dataset_root = Path(root)
        files = _tfrecord_files(dataset_root)
        warnings = [
            "Waymo adapter default mode indexes TFRecord files without parsing frames or labels."
        ]
        sequences = [
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
        return DatasetManifest(
            dataset_name=dataset_root.name if dataset_root.is_dir() else dataset_root.stem,
            adapter_name=self.name,
            dataset_root=str(dataset_root),
            sequences=sequences,
            frames=[
                FrameRecord(
                    frame_id=file_path.stem,
                    sequence_id=file_path.stem,
                    file_path=relative_to_root(dataset_root, file_path),
                    metadata={"indexed_tfrecord": True},
                )
                for file_path in files
            ],
            sensors=[
                SensorStream(
                    sensor_id="unknown",
                    sensor_type="unknown",
                    name="unknown",
                    modality="tfrecord",
                    frame_count=len(files),
                )
            ]
            if files
            else [],
            annotations=[],
            calibration=[],
            splits=_splits(dataset_root, files),
            metadata={
                "tfrecord_files": [relative_to_root(dataset_root, file_path) for file_path in files]
            },
            limitations=[
                (
                    "Detailed frame, label, and calibration parsing requires optional "
                    "Waymo dependencies."
                ),
                "Binary TFRecord contents are not loaded in lightweight mode.",
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
        if kwargs.get("parse_records", False):
            errors.append("Optional dependency missing for detailed parsing.")
        return AdapterValidationReport(
            adapter_name=self.name,
            dataset_root=str(root),
            detected=self.detect(root),
            valid=not errors,
            **validation_scope(self.name, manifest.limitations),
            errors=errors,
            warnings=warnings,
            coverage={"sequences": bool(manifest.sequences), "index_only": True},
            stats={"tfrecord_count": len(files), "sequence_count": len(manifest.sequences)},
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
        del path, sensor_name
        return pd.Series(dtype=float)


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
