"""Lightweight ROS bag adapter detection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from datasetlint.adapters.base import AdapterCoverage, DatasetAdapter, DatasetMetadata, SensorInfo


class ROSBagAdapter(DatasetAdapter):
    """Detect ROS bag files without depending on ROS."""

    name = "rosbag"

    def coverage(self) -> AdapterCoverage:
        return AdapterCoverage(
            validation_mode="index-level",
            checked=["ROS bag file extension", "file presence"],
            not_checked=[
                "ROS connection metadata",
                "message timestamps",
                "sensor synchronization",
                "calibration topics",
                "labels",
                "trajectories",
            ],
            limitations=[
                "ROS bag parsing is not implemented and ROS is not a runtime dependency."
            ],
        )

    def can_load(self, path: str | Path) -> bool:
        dataset_path = Path(path)
        if dataset_path.is_file():
            return dataset_path.suffix.lower() == ".bag"
        return dataset_path.is_dir() and any(dataset_path.glob("*.bag"))

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
        "ROS bag parsing is not implemented in DatasetLint v0 and ROS is not a runtime "
        f"dependency. Convert {path} to the folder CSV format before linting."
    )
