"""Hugging Face datasets adapter with safe sampling defaults."""

from __future__ import annotations

import importlib.util
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

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
)
from datasetlint.adapters.errors import AdapterDependencyError
from datasetlint.adapters.manifest_rules import merge_common_rule_result, run_manifest_rules


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
        deep = bool(kwargs.get("deep", False) or kwargs.get("sample_rows", False))
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
            if deep:
                if importlib.util.find_spec("datasets") is None:
                    return self._missing_dependency_manifest(
                        raw_root, split, streaming, max_rows, deep
                    )
                return self._load_local_with_datasets(local, split, max_rows)
            return self._load_cache_like(local)
        if not deep:
            return self._remote_index_manifest(raw_root, split, streaming, max_rows)
        if importlib.util.find_spec("datasets") is None:
            return self._missing_dependency_manifest(raw_root, split, streaming, max_rows, deep)
        return self._load_with_datasets(raw_root, split, streaming, max_rows)

    def validate(self, root: str | Path, **kwargs: Any) -> AdapterValidationReport:
        errors: list[str] = []
        warnings: list[str] = []
        deep = bool(kwargs.get("deep", False) or kwargs.get("sample_rows", False))
        if deep and importlib.util.find_spec("datasets") is None:
            return AdapterValidationReport(
                adapter_name=self.name,
                dataset_root=str(root),
                detected=self.detect(root),
                valid=False,
                **_huggingface_scope(deep, []),
                errors=[
                    "datasets dependency missing; install datasetlint[hf] to run deep "
                    "Hugging Face row diagnostics."
                ],
                warnings=[],
                coverage={},
                stats={},
            )
        elif not Path(str(root)).exists() and importlib.util.find_spec("datasets") is None:
            errors.append(
                "datasets dependency missing; install datasetlint[hf] to load remote datasets."
            )
        try:
            manifest = self.load(root, **kwargs)
        except AdapterDependencyError as exc:
            return AdapterValidationReport(
                adapter_name=self.name,
                dataset_root=str(root),
                detected=self.detect(root),
                valid=False,
                **_huggingface_scope(deep, []),
                errors=[str(exc)],
                warnings=warnings,
                coverage={},
                stats={},
            )
        except Exception as exc:
            return AdapterValidationReport(
                adapter_name=self.name,
                dataset_root=str(root),
                detected=self.detect(root),
                valid=False,
                **_huggingface_scope(deep, []),
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
        deep = manifest.metadata.get("parse_mode") == "deep"
        scope = _huggingface_scope(deep, manifest.limitations)
        coverage = {
            "sequences": bool(manifest.sequences),
            "frames": bool(manifest.frames),
            "sensors": bool(manifest.sensors),
            "annotations": bool(manifest.annotations),
            "index_only": not deep,
        }
        stats = {
            "sequence_count": len(manifest.sequences),
            "frame_count": len(manifest.frames),
            "sensor_count": len(manifest.sensors),
            "annotation_count": len(manifest.annotations),
        }
        if deep:
            diagnostics = _huggingface_deep_diagnostics(manifest)
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
        del path, sensor_name
        return pd.Series(dtype=float)

    def _load_cache_like(self, root: Path) -> DatasetManifest:
        metadata: dict[str, Any] = {}
        if (root / "dataset_info.json").is_file():
            metadata["dataset_info"] = read_json_object(root / "dataset_info.json")
        if (root / "state.json").is_file():
            metadata["state"] = read_json_object(root / "state.json")
        features = _features_from_metadata(metadata)
        metadata["parse_mode"] = "index"
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
        self, root: str, split: object, streaming: bool, max_rows: int | None, deep: bool
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
            metadata={
                "parse_mode": "deep" if deep else "index",
                "dataset_id": root.removeprefix("hf://"),
                "dependency": "datasets",
                "split": str(split or "unspecified"),
                "streaming": streaming,
                "max_rows": max_rows,
            },
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

    def _remote_index_manifest(
        self, root: str, split: object, streaming: bool, max_rows: int | None
    ) -> DatasetManifest:
        dataset_id = root.removeprefix("hf://")
        split_name = str(split or "unspecified")
        return DatasetManifest(
            dataset_name=dataset_id,
            adapter_name=self.name,
            dataset_root=root,
            sequences=[
                SequenceRecord(
                    sequence_id=split_name,
                    name=split_name,
                    metadata={"streaming": streaming, "max_rows": max_rows},
                )
            ],
            frames=[],
            sensors=[],
            annotations=[],
            calibration=[],
            splits={},
            metadata={
                "parse_mode": "index",
                "dataset_id": dataset_id,
                "split": split_name,
                "streaming": streaming,
                "max_rows": max_rows,
            },
            limitations=[
                "Remote Hugging Face dataset rows were not loaded; use --deep with "
                "datasetlint[hf] for sampled row payload diagnostics."
            ],
            provenance=manifest_provenance(
                root,
                source_format="huggingface",
                adapter_version=self.adapter_version,
                warnings=[],
            ),
        )

    def _load_local_with_datasets(
        self, root: Path, split: object, max_rows: int | None
    ) -> DatasetManifest:
        import datasets  # type: ignore[import-not-found]

        loaded = datasets.load_from_disk(str(root))
        selected = _select_split(loaded, split)
        return self._manifest_from_loaded_dataset(
            dataset_root=str(root),
            dataset_name=root.name,
            source_format="huggingface-cache",
            loaded=selected,
            split=split,
            streaming=False,
            max_rows=max_rows,
        )

    def _load_with_datasets(
        self, root: str, split: object, streaming: bool, max_rows: int | None
    ) -> DatasetManifest:
        import datasets

        dataset_id = root.removeprefix("hf://")
        loaded = datasets.load_dataset(dataset_id, split=split, streaming=streaming)
        return self._manifest_from_loaded_dataset(
            dataset_root=root,
            dataset_name=dataset_id,
            source_format="huggingface",
            loaded=loaded,
            split=split,
            streaming=streaming,
            max_rows=max_rows,
        )

    def _manifest_from_loaded_dataset(
        self,
        *,
        dataset_root: str,
        dataset_name: str,
        source_format: str,
        loaded: Any,
        split: object,
        streaming: bool,
        max_rows: int | None,
    ) -> DatasetManifest:
        features = getattr(loaded, "features", {}) or {}
        frames: list[FrameRecord] = []
        annotations: list[AnnotationRecord] = []
        rows = _sample_rows(loaded, streaming=streaming, max_rows=max_rows)
        for row_index, row in enumerate(rows):
            row_id = _row_id(row)
            frame_id = row_id or str(row_index)
            frames.append(
                FrameRecord(
                    frame_id=frame_id,
                    sequence_id=str(split or "default"),
                    sensor_id=_primary_sensor_from_row(row, features),
                    metadata={
                        "row_index": row_index,
                        "row_id": row_id,
                        "column_types": _row_summary(row),
                    },
                )
            )
            annotations.extend(
                _annotations_from_row(
                    row,
                    frame_id=frame_id,
                    sequence_id=str(split or "default"),
                )
            )
        sensors = _sensors_from_features(features, len(frames))
        if not sensors:
            sensors = _sensors_from_rows(rows, len(frames))
        return DatasetManifest(
            dataset_name=dataset_name,
            adapter_name=self.name,
            dataset_root=dataset_root,
            sequences=[
                SequenceRecord(
                    sequence_id=str(split or "default"),
                    name=str(split or "default"),
                    frame_count=len(frames),
                )
            ],
            frames=frames,
            sensors=sensors,
            annotations=annotations,
            calibration=[],
            splits={str(split): [frame.frame_id for frame in frames]} if split else {},
            metadata={
                "parse_mode": "deep",
                "features": {str(key): str(value) for key, value in dict(features).items()},
                "columns": _columns_from_rows(rows),
                "row_count": len(frames),
                "sampled_rows": len(frames),
                "split": str(split or "default"),
                "streaming": streaming,
                "max_rows": max_rows,
            },
            limitations=[
                "Rows are sampled according to max_rows; large datasets are not fully materialized."
            ],
            provenance=manifest_provenance(
                dataset_root,
                source_format=source_format,
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


def _huggingface_scope(deep: bool, limitations: list[str]) -> dict[str, Any]:
    if not deep:
        return {
            "validation_mode": "index-level",
            "checked": [
                "Hugging Face dataset identifier or local cache metadata",
                "feature metadata when available",
            ],
            "not_checked": [
                "sampled row payloads; use --deep with datasetlint[hf]",
                "full dataset scan",
                "robotics calibration",
                "sensor synchronization",
                "dataset-specific row schemas",
            ],
            "limitations": [
                *limitations,
                "Hugging Face validation is index-level unless --deep samples rows.",
            ],
        }
    return {
        "validation_mode": "deep",
        "checked": [
            "Hugging Face dataset loading",
            "feature schema metadata",
            "sampled row payload summaries",
            "label and bbox-like annotation projection",
        ],
        "not_checked": [
            "full dataset scan",
            "dataset-specific semantic schemas",
            "robotics calibration",
            "sensor synchronization beyond timestamp-like row fields",
        ],
        "limitations": limitations,
    }


def _huggingface_deep_diagnostics(manifest: DatasetManifest) -> dict[str, Any]:
    frame_ids = [frame.frame_id for frame in manifest.frames]
    duplicate_ids = sorted(
        frame_id for frame_id, count in Counter(frame_ids).items() if count > 1
    )
    bbox_annotations = [
        annotation
        for annotation in manifest.annotations
        if annotation.annotation_type == "bbox"
    ]
    invalid_bboxes = [
        annotation
        for annotation in bbox_annotations
        if annotation.values.get("bbox_valid") is False
    ]
    missing_primary_payload = [
        frame for frame in manifest.frames if frame.sensor_id is None
    ]
    errors: list[str] = []
    warnings: list[str] = []
    if not manifest.frames:
        errors.append("Deep Hugging Face sampling decoded no row records.")
    for frame_id in duplicate_ids:
        errors.append(f"Duplicate Hugging Face sample id: {frame_id}.")
    for annotation in invalid_bboxes:
        errors.append(
            f"Hugging Face bbox column {annotation.values.get('column')} on frame "
            f"{annotation.frame_id} is not a numeric [x, y, width, height] payload."
        )
    if missing_primary_payload:
        warnings.append(
            f"{len(missing_primary_payload)} Hugging Face sampled row(s) did not expose a "
            "primary image, video, audio, or text payload column. Location: sampled row "
            "summaries. Fix: configure the dataset features or inspect row column names."
        )
    return {
        "checked": ["Hugging Face deep payload diagnostics"],
        "errors": errors,
        "warnings": warnings,
        "coverage": {
            "row_payloads": bool(manifest.frames),
            "bbox_payloads": bool(bbox_annotations),
            "label_or_bbox_annotations": bool(manifest.annotations),
        },
        "stats": {
            "row_count": len(manifest.frames),
            "bbox_annotation_count": len(bbox_annotations),
            "invalid_bbox_count": len(invalid_bboxes),
            "duplicate_sample_id_count": len(duplicate_ids),
            "rows_without_primary_payload": len(missing_primary_payload),
        },
    }


def _select_split(loaded: Any, split: object) -> Any:
    if split is None:
        return loaded
    try:
        return loaded[str(split)]
    except Exception as exc:
        raise ValueError(f"Could not select Hugging Face split '{split}'.") from exc


def _sample_rows(loaded: Any, *, streaming: bool, max_rows: int | None) -> list[object]:
    if streaming:
        limit = max_rows if max_rows is not None else 1000
        return list(loaded.take(limit))
    try:
        total = len(loaded)
    except TypeError as exc:
        raise ValueError(
            "Hugging Face dataset length is unavailable; use streaming=True for iterable datasets."
        ) from exc
    limit = min(total, max_rows) if max_rows is not None else total
    return list(loaded.select(range(limit)))


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


def _sensors_from_rows(rows: list[object], frame_count: int | None) -> list[SensorStream]:
    columns: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key, value in row.items():
            column = str(key)
            columns.setdefault(column, type(value).__name__)
    return [
        SensorStream(
            sensor_id=name,
            sensor_type=sensor_type,
            name=name,
            modality=sensor_type,
            frame_count=frame_count,
            metadata={"inferred_from": "sampled_rows", "value_type": value_type},
        )
        for name, value_type in sorted(columns.items())
        if (sensor_type := _feature_type(name, value_type.lower())) != "unknown"
    ]


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


def _primary_sensor_from_row(row: object, features: object) -> str | None:
    feature_map = dict(features) if isinstance(features, Mapping) else {}
    if isinstance(row, dict):
        for key in row:
            if _feature_type(str(key), str(feature_map.get(key, "")).lower()) in {
                "camera",
                "video",
                "audio",
                "language",
            }:
                return str(key)
        for key in feature_map:
            if _feature_type(str(key), str(feature_map.get(key, "")).lower()) in {
                "camera",
                "video",
                "audio",
                "language",
            }:
                return str(key)
    return None


def _annotations_from_row(
    row: object, *, frame_id: str, sequence_id: str | None
) -> list[AnnotationRecord]:
    if not isinstance(row, dict):
        return []
    annotations: list[AnnotationRecord] = []
    for key, value in row.items():
        lowered = str(key).lower()
        if "bbox" in lowered or "box" in lowered:
            bbox = _bbox_values(value)
            annotations.append(
                AnnotationRecord(
                    annotation_id=f"{frame_id}:{key}",
                    frame_id=frame_id,
                    sequence_id=sequence_id,
                    annotation_type="bbox",
                    values={
                        "column": str(key),
                        "value_type": type(value).__name__,
                        "bbox": bbox,
                        "bbox_valid": bbox is not None,
                    },
                    metadata={"source": "huggingface_row"},
                )
            )
        elif "label" in lowered or "class" in lowered:
            annotations.append(
                AnnotationRecord(
                    annotation_id=f"{frame_id}:{key}",
                    frame_id=frame_id,
                    sequence_id=sequence_id,
                    category=str(value) if _scalar(value) else None,
                    annotation_type="label",
                    values={
                        "column": str(key),
                        "value_type": type(value).__name__,
                        "scalar": _scalar(value),
                    },
                    metadata={"source": "huggingface_row"},
                )
            )
    return annotations


def _columns_from_rows(rows: list[object]) -> dict[str, str]:
    columns: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key, value in row.items():
            columns.setdefault(str(key), type(value).__name__)
    return columns


def _row_id(row: object) -> str | None:
    if not isinstance(row, dict):
        return None
    for key in ("id", "sample_id", "frame_id", "image_id"):
        value = row.get(key)
        if _scalar(value):
            return str(value)
    return None


def _row_summary(row: object) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {"type": type(row).__name__}
    return {str(key): type(value).__name__ for key, value in row.items()}


def _bbox_values(value: object) -> list[float] | None:
    if not isinstance(value, list | tuple) or len(value) != 4:
        return None
    output: list[float] = []
    for item in value:
        if not isinstance(item, int | float):
            return None
        output.append(float(item))
    return output


def _scalar(value: object) -> bool:
    return isinstance(value, str | int | float | bool) or value is None
