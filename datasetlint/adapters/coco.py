"""COCO dataset adapter using standard JSON parsing."""

from __future__ import annotations

import json
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
    relative_to_root,
)


class CocoAdapter(DatasetAdapter):
    """Load COCO images, categories, and annotations without pycocotools."""

    name = "coco"
    supported_formats = ("coco", "coco-instances")
    description = "COCO JSON adapter for images, boxes, segmentations, and categories."

    def can_load(self, path: str | Path) -> bool:
        root = Path(path)
        if not root.exists():
            return False
        return bool(_annotation_files(root))

    def load(self, root: str | Path, **kwargs: Any) -> DatasetManifest:
        del kwargs
        dataset_root = Path(root)
        annotation_files = _annotation_files(dataset_root)
        warnings: list[str] = []
        frames_by_id: dict[str, FrameRecord] = {}
        annotations: list[AnnotationRecord] = []
        splits: dict[str, list[str]] = {}
        categories_by_id: dict[int, str] = {}
        duplicate_image_ids: list[str] = []
        duplicate_annotation_ids: list[str] = []

        for annotation_path in annotation_files:
            payload = _read_coco(annotation_path)
            split = _split_from_annotation_file(annotation_path)
            categories_by_id.update(_categories(payload))
            image_ids = [
                str(item.get("id")) for item in payload.get("images", []) if isinstance(item, dict)
            ]
            duplicate_image_ids.extend(_duplicates(image_ids))
            for image in payload.get("images", []):
                if not isinstance(image, dict):
                    continue
                image_id = str(image.get("id"))
                file_name = str(image.get("file_name", ""))
                file_path = _resolve_image_path(dataset_root, file_name)
                frame = FrameRecord(
                    frame_id=image_id,
                    sequence_id=split,
                    timestamp=None,
                    sensor_id="camera",
                    file_path=relative_to_root(dataset_root, file_path) if file_path else file_name,
                    width=_optional_int(image.get("width")),
                    height=_optional_int(image.get("height")),
                    metadata={key: value for key, value in image.items() if key not in {"id"}},
                )
                frames_by_id[image_id] = frame
                if split:
                    splits.setdefault(split, []).append(image_id)

            annotation_ids = [
                str(item.get("id"))
                for item in payload.get("annotations", [])
                if isinstance(item, dict) and item.get("id") is not None
            ]
            duplicate_annotation_ids.extend(_duplicates(annotation_ids))
            for index, annotation in enumerate(payload.get("annotations", [])):
                if not isinstance(annotation, dict):
                    continue
                annotation_id = str(annotation.get("id", f"{annotation_path.stem}-{index}"))
                annotation_image_id = (
                    str(annotation.get("image_id"))
                    if annotation.get("image_id") is not None
                    else None
                )
                category_id = _optional_int(annotation.get("category_id"))
                category = categories_by_id.get(category_id) if category_id is not None else None
                annotation_type = "bbox_2d" if "bbox" in annotation else "segmentation"
                if "segmentation" in annotation and "bbox" not in annotation:
                    annotation_type = "segmentation"
                annotations.append(
                    AnnotationRecord(
                        annotation_id=annotation_id,
                        frame_id=annotation_image_id,
                        sequence_id=split,
                        category=category,
                        annotation_type=annotation_type,
                        values=dict(annotation),
                        metadata={
                            "category_id": category_id,
                            "source": relative_to_root(dataset_root, annotation_path),
                        },
                    )
                )

            if not payload.get("categories"):
                warnings.append(
                    f"{relative_to_root(dataset_root, annotation_path)} has empty categories."
                )

        sequence_ids = sorted({frame.sequence_id or "coco" for frame in frames_by_id.values()})
        sequences = [
            SequenceRecord(
                sequence_id=sequence_id,
                name=sequence_id,
                split=sequence_id,
                frame_count=sum(
                    1
                    for frame in frames_by_id.values()
                    if (frame.sequence_id or "coco") == sequence_id
                ),
            )
            for sequence_id in sequence_ids
        ]
        sensors = [
            SensorStream(
                sensor_id="camera",
                sensor_type="camera",
                name="camera",
                modality="image",
                frame_count=len(frames_by_id),
            )
        ]
        if duplicate_image_ids:
            warnings.append(f"Duplicate image ids: {', '.join(sorted(set(duplicate_image_ids)))}.")
        if duplicate_annotation_ids:
            warnings.append(
                f"Duplicate annotation ids: {', '.join(sorted(set(duplicate_annotation_ids)))}."
            )
        return DatasetManifest(
            dataset_name=dataset_root.name,
            adapter_name=self.name,
            dataset_root=str(dataset_root),
            sequences=sequences,
            frames=sorted(frames_by_id.values(), key=lambda frame: frame.frame_id),
            sensors=sensors,
            annotations=annotations,
            calibration=[],
            splits=splits,
            metadata={"categories": categories_by_id},
            limitations=["COCO adapter parses JSON directly and does not require pycocotools."],
            provenance=manifest_provenance(
                dataset_root,
                source_format="coco",
                adapter_version=self.adapter_version,
                warnings=warnings,
            ),
        )

    def validate(self, root: str | Path, **kwargs: Any) -> AdapterValidationReport:
        manifest = self.load(root, **kwargs)
        dataset_root = Path(root)
        errors: list[str] = []
        warnings = list(manifest.provenance.warnings)
        image_ids = {frame.frame_id for frame in manifest.frames}
        category_ids = {
            int(category_id)
            for category_id in manifest.metadata.get("categories", {}).keys()
            if isinstance(category_id, int)
        }
        for frame in manifest.frames:
            if frame.file_path and not (dataset_root / frame.file_path).is_file():
                errors.append(f"Missing image file: {frame.file_path}.")
        for annotation in manifest.annotations:
            image_id = annotation.frame_id
            if image_id is not None and image_id not in image_ids:
                errors.append(f"Annotation image_id not found: {image_id}.")
            category_id = annotation.metadata.get("category_id")
            if isinstance(category_id, int) and category_id not in category_ids:
                errors.append(f"Category id not found: {category_id}.")
            bbox = annotation.values.get("bbox")
            if isinstance(bbox, list) and len(bbox) >= 4 and (bbox[2] <= 0 or bbox[3] <= 0):
                errors.append(f"Invalid bbox dimensions for annotation {annotation.annotation_id}.")
        if not manifest.metadata.get("categories"):
            errors.append("Empty categories.")
        return AdapterValidationReport(
            adapter_name=self.name,
            dataset_root=str(root),
            detected=self.detect(root),
            valid=not errors,
            errors=errors,
            warnings=warnings,
            coverage={
                "frames": bool(manifest.frames),
                "annotations": bool(manifest.annotations),
                "categories": bool(manifest.metadata.get("categories")),
                "splits": bool(manifest.splits),
            },
            stats={
                "frame_count": len(manifest.frames),
                "annotation_count": len(manifest.annotations),
                "category_count": len(manifest.metadata.get("categories", {})),
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
        return [SensorInfo(name="camera", frame_count=len(self.load(path).frames))]


def _annotation_files(root: Path) -> list[Path]:
    if root.is_file() and root.suffix.lower() == ".json" and _looks_like_coco(root):
        return [root]
    if not root.is_dir():
        return []
    candidates = (
        sorted((root / "annotations").glob("instances_*.json"))
        if (root / "annotations").is_dir()
        else []
    )
    candidates.extend(sorted(path for path in root.glob("*.json") if _looks_like_coco(path)))
    return [path for path in candidates if _looks_like_coco(path)]


def _looks_like_coco(path: Path) -> bool:
    try:
        payload = _read_coco(path)
    except (OSError, json.JSONDecodeError, ValueError):
        return False
    return all(
        isinstance(payload.get(key), list) for key in ("images", "annotations", "categories")
    )


def _read_coco(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _categories(payload: dict[str, Any]) -> dict[int, str]:
    categories: dict[int, str] = {}
    for category in payload.get("categories", []):
        if isinstance(category, dict):
            category_id = _optional_int(category.get("id"))
            name = category.get("name")
            if category_id is not None and isinstance(name, str):
                categories[category_id] = name
    return categories


def _resolve_image_path(root: Path, file_name: str) -> Path | None:
    if not file_name:
        return None
    direct = root / file_name
    if direct.exists():
        return direct
    for prefix in ("images", "train2017", "val2017", "test2017"):
        candidate = root / prefix / file_name
        if candidate.exists():
            return candidate
    return root / file_name


def _split_from_annotation_file(path: Path) -> str | None:
    name = path.stem
    for split in ("train", "val", "test"):
        if split in name:
            return split
    return None


def _optional_int(value: object) -> int | None:
    if not isinstance(value, str | bytes | bytearray | int | float):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _duplicates(values: list[str]) -> list[str]:
    counts = Counter(values)
    return [value for value, count in counts.items() if count > 1]
