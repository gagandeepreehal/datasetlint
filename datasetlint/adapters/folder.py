"""Adapter for DatasetLint's simple folder format."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from datasetlint.adapters.base import AdapterCoverage, DatasetAdapter, DatasetMetadata, SensorInfo
from datasetlint.io.csv import read_csv
from datasetlint.io.filesystem import stemmed_csv_files
from datasetlint.io.json import read_json


class FolderAdapter(DatasetAdapter):
    """Load the native folder-based DatasetLint layout."""

    name = "folder"

    def coverage(self) -> AdapterCoverage:
        return AdapterCoverage(
            validation_mode="deep",
            checked=[
                "native DatasetLint folder layout",
                "metadata schema",
                "required files",
                "CSV parseability",
                "broken file references",
                "timestamps and timestamp gaps",
                "sensor synchronization",
                "calibration and camera intrinsics",
                "labels and track consistency",
                "trajectories",
            ],
            not_checked=[
                "image pixel decoding",
                "point cloud payload decoding",
                "semantic correctness of labels",
            ],
            limitations=[
                "Deep validation is designed for the native DatasetLint folder format."
            ],
        )

    def can_load(self, path: str | Path) -> bool:
        dataset_path = Path(path)
        return dataset_path.is_dir() and (
            (dataset_path / "metadata.json").is_file()
            or (dataset_path / "sensors").is_dir()
            or (dataset_path / "labels").is_dir()
            or (dataset_path / "trajectories").is_dir()
        )

    def load_metadata(self, path: str | Path) -> DatasetMetadata:
        dataset_path = Path(path)
        raw = _read_optional_json(dataset_path / "metadata.json")
        sensors = raw.get("sensors", [])
        return DatasetMetadata(
            dataset_path=str(dataset_path),
            name=_optional_string(raw.get("dataset_name")),
            version=_optional_string(raw.get("version")),
            sensors=[sensor for sensor in sensors if isinstance(sensor, str)]
            if isinstance(sensors, list)
            else [],
            raw=raw,
        )

    def list_sensors(self, path: str | Path) -> list[SensorInfo]:
        dataset_path = Path(path)
        sensors: list[SensorInfo] = []
        for sensor, csv_path in stemmed_csv_files(dataset_path / "sensors").items():
            frame = read_csv(csv_path)
            timestamps = _numeric_timestamps(frame)
            start_time: float | None = None
            end_time: float | None = None
            inferred_frequency: float | None = None
            if not timestamps.empty:
                start_time = float(timestamps.min())
                end_time = float(timestamps.max())
                gaps = timestamps.sort_values().diff().dropna()
                gaps = gaps[gaps > 0]
                if not gaps.empty:
                    inferred_frequency = float(1.0 / gaps.median())
            sensors.append(
                SensorInfo(
                    name=sensor,
                    path=str(csv_path),
                    frame_count=len(frame),
                    start_time=start_time,
                    end_time=end_time,
                    inferred_frequency_hz=inferred_frequency,
                )
            )
        return sensors

    def load_timestamps(self, path: str | Path, sensor_name: str) -> pd.Series:
        csv_path = Path(path) / "sensors" / f"{sensor_name}.csv"
        if not csv_path.is_file():
            raise FileNotFoundError(f"Sensor CSV not found: {csv_path}")
        frame = read_csv(csv_path)
        if "timestamp" not in frame.columns:
            raise ValueError(f"Sensor CSV is missing timestamp column: {csv_path}")
        return pd.to_numeric(frame["timestamp"], errors="coerce")

    def load_labels(self, path: str | Path) -> pd.DataFrame | None:
        label_path = Path(path) / "labels" / "detections.csv"
        if not label_path.is_file():
            return None
        return read_csv(label_path)

    def load_trajectory(self, path: str | Path) -> pd.DataFrame | None:
        trajectory_path = Path(path) / "trajectories" / "ego.csv"
        if trajectory_path.is_file():
            return read_csv(trajectory_path)
        candidates = stemmed_csv_files(Path(path) / "trajectories")
        if not candidates:
            return None
        first_path = next(iter(candidates.values()))
        return read_csv(first_path)

    def load_calibration(self, path: str | Path) -> dict[str, Any] | None:
        calibration_path = Path(path) / "calibration.json"
        if not calibration_path.is_file():
            return None
        raw = read_json(calibration_path)
        if not isinstance(raw, dict):
            raise ValueError("calibration.json must contain a JSON object.")
        return raw


def _read_optional_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    raw = read_json(path)
    if not isinstance(raw, dict):
        raise ValueError(f"{path.name} must contain a JSON object.")
    return raw


def _optional_string(value: object) -> str | None:
    if isinstance(value, str):
        return value
    return None


def _numeric_timestamps(frame: pd.DataFrame) -> pd.Series:
    if "timestamp" not in frame.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(frame["timestamp"], errors="coerce").dropna()
