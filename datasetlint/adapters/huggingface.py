"""Lightweight Hugging Face dataset export detection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from datasetlint.adapters.base import AdapterCoverage, DatasetAdapter, DatasetMetadata, SensorInfo
from datasetlint.io.json import read_json


class HuggingFaceAdapter(DatasetAdapter):
    """Detect local Hugging Face dataset exports without depending on datasets."""

    name = "huggingface"

    def coverage(self) -> AdapterCoverage:
        return AdapterCoverage(
            validation_mode="manifest-level",
            checked=[
                "Hugging Face dataset metadata files",
                "local Arrow or Parquet shard presence",
            ],
            not_checked=[
                "feature schema semantics",
                "media file references",
                "robotics timestamps",
                "sensor synchronization",
                "calibration",
                "labels",
                "trajectories",
            ],
            limitations=[
                "The optional Hugging Face datasets parser is not implemented in DatasetLint v0."
            ],
        )

    def can_load(self, path: str | Path) -> bool:
        dataset_path = Path(path)
        if not dataset_path.is_dir():
            return False
        metadata_files = ("dataset_info.json", "dataset_infos.json", "state.json")
        if any((dataset_path / name).is_file() for name in metadata_files):
            return True
        return any(dataset_path.rglob("*.arrow")) or any(dataset_path.rglob("*.parquet"))

    def load_metadata(self, path: str | Path) -> DatasetMetadata:
        dataset_path = Path(path)
        raw: dict[str, Any] = {}
        for name in ("dataset_info.json", "dataset_infos.json", "state.json"):
            metadata_path = dataset_path / name
            if metadata_path.is_file():
                value = read_json(metadata_path)
                raw[name] = value
        raw["arrow_file_count"] = sum(1 for _path in dataset_path.rglob("*.arrow"))
        raw["parquet_file_count"] = sum(1 for _path in dataset_path.rglob("*.parquet"))
        return DatasetMetadata(dataset_path=str(dataset_path), name="huggingface", raw=raw)

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


def _unsupported(path: str | Path) -> NotImplementedError:
    return NotImplementedError(
        "Hugging Face dataset deep validation is not implemented in DatasetLint v0. "
        f"Export {path} to the native folder CSV format before linting."
    )
