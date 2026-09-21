"""Adapter for DatasetLint's simple folder format."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from datasetlint.adapters.base import (
    AnnotationRecord,
    CalibrationRecord,
    DatasetAdapter,
    DatasetManifest,
    DatasetMetadata,
    FrameRecord,
    SensorInfo,
    SensorStream,
    SequenceRecord,
    manifest_provenance,
)
from datasetlint.io.csv import read_csv
from datasetlint.io.filesystem import stemmed_csv_files
from datasetlint.io.json import read_json


class FolderAdapter(DatasetAdapter):
    """Load the native folder-based DatasetLint layout."""

    name = "folder"
    supported_formats = ("datasetlint-folder",)
    description = "Native DatasetLint folder format used by the existing lint checks."

    def can_load(self, path: str | Path) -> bool:
        dataset_path = Path(path)
        return dataset_path.is_dir() and (
            (dataset_path / "metadata.json").is_file()
            or (dataset_path / "sensors").is_dir()
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

    def load(self, root: str | Path, **kwargs: Any) -> DatasetManifest:
        del kwargs
        dataset_path = Path(root)
        metadata = self.load_metadata(dataset_path)
        sensors = [
            SensorStream(
                sensor_id=sensor.name,
                sensor_type=_sensor_type(sensor.name),
                name=sensor.name,
                modality=_sensor_type(sensor.name),
                frequency_hz=sensor.inferred_frequency_hz,
                frame_count=sensor.frame_count,
                metadata={"path": sensor.path},
            )
            for sensor in self.list_sensors(dataset_path)
        ]
        frames: list[FrameRecord] = []
        for sensor in sensors:
            sensor_path = sensor.metadata.get("path")
            if not isinstance(sensor_path, str):
                continue
            frame = read_csv(Path(sensor_path))
            for index, row in frame.iterrows():
                frame_id = str(row.get("frame_id", row.get("path", f"{sensor.sensor_id}-{index}")))
                frames.append(
                    FrameRecord(
                        frame_id=frame_id,
                        sequence_id="root",
                        timestamp=_optional_float(row.get("timestamp")),
                        sensor_id=sensor.sensor_id,
                        file_path=str(row.get("path")) if row.get("path") is not None else None,
                        width=_optional_int(row.get("width")),
                        height=_optional_int(row.get("height")),
                        metadata={"row_index": int(index)},
                    )
                )
        annotations: list[AnnotationRecord] = []
        labels = self.load_labels(dataset_path)
        if labels is not None:
            for index, row in labels.iterrows():
                track_id = row.get("track_id")
                annotation_id = (
                    f"{track_id}-{int(index)}" if track_id is not None else f"label-{int(index)}"
                )
                annotations.append(
                    AnnotationRecord(
                        annotation_id=str(annotation_id),
                        frame_id=str(row.get("frame_id"))
                        if row.get("frame_id") is not None
                        else None,
                        sequence_id="root",
                        category=str(row.get("class")) if row.get("class") is not None else None,
                        annotation_type="bbox_2d",
                        values={str(key): value for key, value in row.items()},
                    )
                )
        calibration_records: list[CalibrationRecord] = []
        calibration = self.load_calibration(dataset_path)
        if calibration:
            for sensor_id, value in calibration.items():
                if isinstance(value, dict):
                    calibration_records.append(
                        CalibrationRecord(
                            sensor_id=str(sensor_id),
                            intrinsic=value.get("intrinsics")
                            if isinstance(value.get("intrinsics"), list)
                            else None,
                            metadata=value,
                        )
                    )
        return DatasetManifest(
            dataset_name=metadata.name or dataset_path.name,
            adapter_name=self.name,
            dataset_root=str(dataset_path),
            version=metadata.version,
            sequences=[
                SequenceRecord(
                    sequence_id="root",
                    name=metadata.name,
                    frame_count=len(frames) or None,
                )
            ],
            frames=frames,
            sensors=sensors,
            annotations=annotations,
            calibration=calibration_records,
            splits={},
            metadata=metadata.raw,
            limitations=[
                "Native folder manifest is derived from CSV rows used by existing lint checks."
            ],
            provenance=manifest_provenance(
                dataset_path,
                source_format="datasetlint-folder",
                adapter_version=self.adapter_version,
            ),
        )


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


def _sensor_type(sensor_name: str) -> str:
    lowered = sensor_name.lower()
    if "camera" in lowered:
        return "camera"
    if "lidar" in lowered or "velodyne" in lowered:
        return "lidar"
    if "imu" in lowered:
        return "imu"
    if "gps" in lowered:
        return "gps"
    return "unknown"


def _optional_float(value: object) -> float | None:
    if not isinstance(value, str | bytes | bytearray | int | float):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: object) -> int | None:
    if not isinstance(value, str | bytes | bytearray | int | float):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
