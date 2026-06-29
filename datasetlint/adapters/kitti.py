"""Lightweight KITTI-style folder detection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from datasetlint.adapters.base import AdapterCoverage, DatasetAdapter, DatasetMetadata, SensorInfo


class KITTIAdapter(DatasetAdapter):
    """Detect KITTI-style folders without parsing calibration or labels deeply."""

    name = "kitti"

    def coverage(self) -> AdapterCoverage:
        return AdapterCoverage(
            validation_mode="index-level",
            checked=[
                "KITTI directory markers",
                "presence of common image, lidar, calibration, or label folders",
            ],
            not_checked=[
                "calibration file contents",
                "image and lidar frame matching",
                "timestamps",
                "label geometry",
                "track consistency",
                "trajectories",
            ],
            limitations=["KITTI deep parsing is not implemented in DatasetLint v0."],
        )

    def can_load(self, path: str | Path) -> bool:
        dataset_path = Path(path)
        if not dataset_path.is_dir():
            return False
        markers = ("image_2", "image_3", "velodyne", "calib", "label_2", "oxts", "sequences")
        marker_count = sum(1 for name in markers if (dataset_path / name).exists())
        return marker_count >= 2

    def load_metadata(self, path: str | Path) -> DatasetMetadata:
        dataset_path = Path(path)
        markers = ("image_2", "image_3", "velodyne", "calib", "label_2", "oxts", "sequences")
        raw: dict[str, Any] = {
            "present_markers": [name for name in markers if (dataset_path / name).exists()]
        }
        return DatasetMetadata(dataset_path=str(dataset_path), name="kitti", raw=raw)

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
        "KITTI deep validation is not implemented in DatasetLint v0. "
        f"Export {path} to the native folder CSV format before linting."
    )
