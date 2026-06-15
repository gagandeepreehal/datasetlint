"""Lightweight MCAP adapter detection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from datasetlint.adapters.base import DatasetAdapter, DatasetMetadata, SensorInfo


class MCAPAdapter(DatasetAdapter):
    """Detect MCAP files without adding an MCAP runtime dependency."""

    name = "mcap"

    def can_load(self, path: str | Path) -> bool:
        dataset_path = Path(path)
        if dataset_path.is_file():
            return dataset_path.suffix.lower() == ".mcap"
        return dataset_path.is_dir() and any(dataset_path.glob("*.mcap"))

    def load_metadata(self, path: str | Path) -> DatasetMetadata:
        files = _mcap_files(Path(path))
        return DatasetMetadata(
            dataset_path=str(path),
            name="mcap",
            raw={
                "file_count": len(files),
                "files": [
                    {"path": str(file_path), "size_bytes": file_path.stat().st_size}
                    for file_path in files
                ],
            },
        )

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


def _mcap_files(path: Path) -> list[Path]:
    if path.is_file() and path.suffix.lower() == ".mcap":
        return [path]
    if path.is_dir():
        return sorted(file_path for file_path in path.glob("*.mcap") if file_path.is_file())
    return []


def _unsupported(path: str | Path) -> NotImplementedError:
    return NotImplementedError(
        "MCAP deep parsing is not implemented in DatasetLint v0. "
        f"Install a future MCAP adapter or convert {path} to the folder CSV format."
    )
