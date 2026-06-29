"""Lightweight NuScenes adapter detection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from datasetlint.adapters.base import AdapterCoverage, DatasetAdapter, DatasetMetadata, SensorInfo


class NuScenesAdapter(DatasetAdapter):
    """Detect NuScenes-like folder structures without parsing the full schema."""

    name = "nuscenes"

    def coverage(self) -> AdapterCoverage:
        return AdapterCoverage(
            validation_mode="index-level",
            checked=[
                "NuScenes version directory markers",
                "core metadata filename presence",
            ],
            not_checked=[
                "NuScenes relational schema",
                "sample data references",
                "ego poses",
                "calibration",
                "annotations",
                "sensor synchronization",
            ],
            limitations=["NuScenes deep parsing is not implemented in DatasetLint v0."],
        )

    def can_load(self, path: str | Path) -> bool:
        dataset_path = Path(path)
        if not dataset_path.is_dir():
            return False
        if any(
            child.is_dir() and child.name.startswith("v1.0-")
            for child in dataset_path.iterdir()
        ):
            return True
        return any((dataset_path / name).is_file() for name in ("scene.json", "sample.json"))

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
        "NuScenes parsing is not implemented in DatasetLint v0. "
        f"Convert {path} to the folder CSV format or add a dedicated adapter."
    )
