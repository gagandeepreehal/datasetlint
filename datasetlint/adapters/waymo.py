"""Lightweight Waymo adapter detection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from datasetlint.adapters.base import DatasetAdapter, DatasetMetadata, SensorInfo


class WaymoAdapter(DatasetAdapter):
    """Detect Waymo Open Dataset TFRecord files without TensorFlow."""

    name = "waymo"

    def can_load(self, path: str | Path) -> bool:
        dataset_path = Path(path)
        if dataset_path.is_file():
            return dataset_path.suffix.lower() == ".tfrecord"
        return dataset_path.is_dir() and any(dataset_path.glob("*.tfrecord"))

    def load_metadata(self, path: str | Path) -> DatasetMetadata:
        raise _unsupported(path)

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
        "Waymo TFRecord parsing is not implemented in DatasetLint v0 and TensorFlow is not a "
        f"runtime dependency. Convert {path} to the folder CSV format before linting."
    )
