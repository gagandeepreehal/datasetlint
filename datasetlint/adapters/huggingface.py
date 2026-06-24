"""Hugging Face datasets adapter with safe sampling defaults."""

from __future__ import annotations

import importlib.util
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
    read_json_object,
)


class HuggingFaceAdapter(DatasetAdapter):
    """Load or index Hugging Face datasets with explicit row limits."""

    name = "huggingface"
    supported_formats = ("hf://", "huggingface-datasets-cache")
    optional_dependencies = ("datasets",)
    description = "Hugging Face datasets adapter with streaming and max-row safeguards."

    def can_load(self, path: str | Path) -> bool:
        raw = str(path)
        if raw.startswith("hf://"):
            return True
        local = Path(raw)
        if local.is_dir() and (
            (local / "dataset_info.json").is_file() or (local / "state.json").is_file()
        ):
            return True
        if local.exists():
            return False
        return "/" in raw and " " not in raw and not raw.startswith(".")

    def load(self, root: str | Path, **kwargs: Any) -> DatasetManifest:
        split = kwargs.get("split")
        streaming = bool(kwargs.get("streaming", False))
        max_rows = kwargs.get("max_rows", 1000)
        if isinstance(max_rows, str):
            max_rows = int(max_rows)
        if max_rows is not None and not isinstance(max_rows, int):
            raise ValueError("max_rows must be an integer or None.")
        if (
            max_rows is not None
            and max_rows > 1000
            and not bool(kwargs.get("allow_large_sample", False))
        ):
            raise ValueError("Too many rows requested without allow_large_sample=True.")
        raw_root = str(root)
        local = Path(raw_root)
        if local.is_dir():
            return self._load_cache_like(local)
        if importlib.util.find_spec("datasets") is None:
            return self._missing_dependency_manifest(raw_root, split, streaming, max_rows)
        return self._load_with_datasets(raw_root, split, streaming, max_rows)

    def validate(self, root: str | Path, **kwargs: Any) -> AdapterValidationReport:
        errors: list[str] = []
        warnings: list[str] = []
        if not Path(str(root)).exists() and importlib.util.find_spec("datasets") is None:
            errors.append(
                "datasets dependency missing; install datasetlint[hf] to load remote datasets."
            )
        try:
            manifest = self.load(root, **kwargs)
        except Exception as exc:
            return AdapterValidationReport(
                adapter_name=self.name,
                dataset_root=str(root),
                detected=self.detect(root),
                valid=False,
                errors=[str(exc)],
                warnings=warnings,
                coverage={},
                stats={},
            )
        warnings.extend(manifest.provenance.warnings)
        warnings.extend(manifest.limitations)
        if not manifest.sequences:
            errors.append("Empty dataset or no split metadata available.")
        if not manifest.sensors:
            warnings.append("Unsupported or unknown feature types; no media/text streams inferred.")
        return AdapterValidationReport(
            adapter_name=self.name,
            dataset_root=str(root),
            detected=self.detect(root),
            valid=not errors,
            errors=errors,
            warnings=warnings,
            coverage={"sequences": bool(manifest.sequences), "sensors": bool(manifest.sensors)},
            stats={
                "sequence_count": len(manifest.sequences),
                "frame_count": len(manifest.frames),
                "sensor_count": len(manifest.sensors),
            },
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
        del path, sensor_name
        return pd.Series(dtype=float)

    def _load_cache_like(self, root: Path) -> DatasetManifest:
        metadata: dict[str, Any] = {}
        if (root / "dataset_info.json").is_file():
            metadata["dataset_info"] = read_json_object(root / "dataset_info.json")
        if (root / "state.json").is_file():
            metadata["state"] = read_json_object(root / "state.json")
        features = _features_from_metadata(metadata)
        sensors = _sensors_from_features(features, None)
        return DatasetManifest(
            dataset_name=root.name,
            adapter_name=self.name,
            dataset_root=str(root),
            sequences=[SequenceRecord(sequence_id="cache", name=root.name, metadata=metadata)],
            frames=[],
            sensors=sensors,
            annotations=[],
            calibration=[],
            splits={},
            metadata=metadata,
            limitations=[
                "Cache-like Hugging Face dataset metadata was indexed without loading rows."
            ],
            provenance=manifest_provenance(
                root,
                source_format="huggingface-cache",
                adapter_version=self.adapter_version,
                warnings=[],
            ),
        )

    def _missing_dependency_manifest(
        self, root: str, split: object, streaming: bool, max_rows: int | None
    ) -> DatasetManifest:
        return DatasetManifest(
            dataset_name=root.removeprefix("hf://"),
            adapter_name=self.name,
            dataset_root=root,
            sequences=[
                SequenceRecord(
                    sequence_id=str(split or "unspecified"),
                    name=str(split or "unspecified"),
                    metadata={"streaming": streaming, "max_rows": max_rows},
                )
            ],
            frames=[],
            sensors=[],
            annotations=[],
            calibration=[],
            splits={},
            metadata={"dataset_id": root.removeprefix("hf://"), "dependency": "datasets"},
            limitations=[
                "Install datasetlint[hf] to inspect Hugging Face dataset rows and features."
            ],
            provenance=manifest_provenance(
                root,
                source_format="huggingface",
                adapter_version=self.adapter_version,
                warnings=["datasets dependency is not installed."],
            ),
        )

    def _load_with_datasets(
        self, root: str, split: object, streaming: bool, max_rows: int | None
    ) -> DatasetManifest:
        import datasets  # type: ignore[import-not-found]

        dataset_id = root.removeprefix("hf://")
        loaded = datasets.load_dataset(dataset_id, split=split, streaming=streaming)
        features = getattr(loaded, "features", {}) or {}
        row_count = 0
        frames: list[FrameRecord] = []
        for row_count, row in enumerate(
            loaded.take(max_rows)
            if streaming
            else loaded.select(range(min(len(loaded), max_rows or len(loaded))))
        ):
            frames.append(
                FrameRecord(
                    frame_id=str(row_count),
                    sequence_id=str(split or "default"),
                    metadata=_row_summary(row),
                )
            )
        sensors = _sensors_from_features(features, len(frames))
        return DatasetManifest(
            dataset_name=dataset_id,
            adapter_name=self.name,
            dataset_root=root,
            sequences=[
                SequenceRecord(
                    sequence_id=str(split or "default"),
                    name=str(split or "default"),
                    frame_count=len(frames),
                )
            ],
            frames=frames,
            sensors=sensors,
            annotations=[],
            calibration=[],
            splits={str(split): [frame.frame_id for frame in frames]} if split else {},
            metadata={"features": {str(key): str(value) for key, value in dict(features).items()}},
            limitations=[
                "Rows are sampled according to max_rows; large datasets are not fully materialized."
            ],
            provenance=manifest_provenance(
                root,
                source_format="huggingface",
                adapter_version=self.adapter_version,
                warnings=[],
            ),
        )


def _features_from_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    info = metadata.get("dataset_info")
    if isinstance(info, dict):
        features = info.get("features")
        if isinstance(features, dict):
            return features
    return {}


def _sensors_from_features(features: dict[str, Any], frame_count: int | None) -> list[SensorStream]:
    sensors: list[SensorStream] = []
    for name, feature in features.items():
        feature_text = str(feature).lower()
        sensor_type = _feature_type(name, feature_text)
        if sensor_type == "unknown":
            continue
        sensors.append(
            SensorStream(
                sensor_id=str(name),
                sensor_type=sensor_type,
                name=str(name),
                modality=sensor_type,
                frame_count=frame_count,
                metadata={"feature": str(feature)},
            )
        )
    return sensors


def _feature_type(name: str, feature_text: str) -> str:
    lowered = name.lower()
    if "image" in lowered or "image" in feature_text:
        return "camera"
    if "video" in lowered or "video" in feature_text:
        return "video"
    if "audio" in lowered or "audio" in feature_text:
        return "audio"
    if "text" in lowered or "language" in lowered or "string" in feature_text:
        return "language"
    if "label" in lowered or "class" in lowered:
        return "label"
    if "bbox" in lowered or "box" in lowered:
        return "annotation"
    return "unknown"


def _row_summary(row: object) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {"type": type(row).__name__}
    return {str(key): type(value).__name__ for key, value in row.items()}
