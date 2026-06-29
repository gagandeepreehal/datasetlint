"""Lightweight COCO annotation manifest detection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from datasetlint.adapters.base import AdapterCoverage, DatasetAdapter, DatasetMetadata, SensorInfo
from datasetlint.io.json import read_json


class COCOAdapter(DatasetAdapter):
    """Detect COCO-style annotation JSON without validating image payloads."""

    name = "coco"

    def coverage(self) -> AdapterCoverage:
        return AdapterCoverage(
            validation_mode="manifest-level",
            checked=[
                "COCO annotation JSON parseability",
                "top-level images and annotations keys",
            ],
            not_checked=[
                "referenced image existence",
                "category taxonomy semantics",
                "robotics timestamps",
                "sensor synchronization",
                "calibration",
                "trajectory data",
            ],
            limitations=[
                "COCO validation is limited to manifest detection in DatasetLint v0."
            ],
        )

    def can_load(self, path: str | Path) -> bool:
        annotation_path = _annotation_path(Path(path))
        if annotation_path is None:
            return False
        try:
            value = read_json(annotation_path)
        except ValueError:
            return False
        return isinstance(value, dict) and isinstance(value.get("images"), list) and isinstance(
            value.get("annotations"), list
        )

    def load_metadata(self, path: str | Path) -> DatasetMetadata:
        annotation_path = _annotation_path(Path(path))
        raw: dict[str, Any] = {}
        if annotation_path is not None:
            value = read_json(annotation_path)
            if isinstance(value, dict):
                raw = {
                    "annotation_path": str(annotation_path),
                    "image_count": len(value.get("images", []))
                    if isinstance(value.get("images"), list)
                    else None,
                    "annotation_count": len(value.get("annotations", []))
                    if isinstance(value.get("annotations"), list)
                    else None,
                    "category_count": len(value.get("categories", []))
                    if isinstance(value.get("categories"), list)
                    else None,
                }
        return DatasetMetadata(dataset_path=str(path), name="coco", raw=raw)

    def list_sensors(self, path: str | Path) -> list[SensorInfo]:
        raise _unsupported(path)

    def load_timestamps(self, path: str | Path, sensor_name: str) -> pd.Series:
        raise _unsupported(path)

    def load_labels(self, path: str | Path) -> pd.DataFrame | None:
        raise _unsupported(path)

    def load_trajectory(self, path: str | Path) -> pd.DataFrame | None:
        raise _unsupported(path)

    def load_calibration(self, path: str | Path) -> dict[str, Any] | None:
        raise _unsupported(path)


def _annotation_path(path: Path) -> Path | None:
    if path.is_file() and path.suffix.lower() == ".json":
        return path
    if not path.is_dir():
        return None
    annotation_dir = path / "annotations"
    candidates = sorted(annotation_dir.glob("*.json")) if annotation_dir.is_dir() else []
    if not candidates:
        candidates = sorted(path.glob("*.json"))
    return candidates[0] if candidates else None


def _unsupported(path: str | Path) -> NotImplementedError:
    return NotImplementedError(
        "COCO deep validation is not implemented in DatasetLint v0. "
        f"Export {path} to the native folder CSV format before linting."
    )
