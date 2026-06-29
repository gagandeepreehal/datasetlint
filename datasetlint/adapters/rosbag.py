"""ROS bag adapter with lightweight ROS1/ROS2 bag indexing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from datasetlint.adapters.base import (
    AdapterValidationReport,
    DatasetAdapter,
    DatasetManifest,
    DatasetMetadata,
    SensorInfo,
    SensorStream,
    SequenceRecord,
    manifest_provenance,
    relative_to_root,
    validation_scope,
)


class ROSBagAdapter(DatasetAdapter):
    """Index ROS1 .bag files and ROS2 bag directories without ROS at runtime."""

    name = "rosbag"
    supported_formats = ("ros1-bag", "ros2-bag")
    optional_dependencies = ("rosbags",)
    description = "ROS bag index adapter; optional rosbags support can inspect topics."

    def can_load(self, path: str | Path) -> bool:
        dataset_path = Path(path)
        if dataset_path.is_file():
            return dataset_path.suffix.lower() == ".bag"
        if not dataset_path.is_dir():
            return False
        return (
            any(dataset_path.rglob("*.bag"))
            or (dataset_path / "metadata.yaml").is_file()
            or any(
                file_path.suffix.lower() in {".db3", ".sqlite3"}
                for file_path in dataset_path.rglob("*")
            )
        )

    def load(self, root: str | Path, **kwargs: Any) -> DatasetManifest:
        del kwargs
        dataset_root = Path(root)
        bags = _bag_units(dataset_root)
        warnings = ["ROS bag adapter indexes files without requiring a ROS installation."]
        sequences = [
            SequenceRecord(
                sequence_id=bag.stem if bag.is_file() else bag.name,
                name=bag.name,
                metadata={
                    "file_path": relative_to_root(dataset_root, bag),
                    "kind": "ros1" if bag.suffix.lower() == ".bag" else "ros2",
                    "size_bytes": _size_bytes(bag),
                },
            )
            for bag in bags
        ]
        sensors = _metadata_topics(dataset_root)
        return DatasetManifest(
            dataset_name=dataset_root.name if dataset_root.is_dir() else dataset_root.stem,
            adapter_name=self.name,
            dataset_root=str(dataset_root),
            sequences=sequences,
            frames=[],
            sensors=sensors,
            annotations=[],
            calibration=[],
            splits={},
            metadata={"bag_files": [relative_to_root(dataset_root, bag) for bag in bags]},
            limitations=[
                "Topic and message parsing requires optional ROS bag reader dependencies.",
                "ROS2 metadata.yaml is parsed only for lightweight topic summaries.",
            ],
            provenance=manifest_provenance(
                dataset_root,
                source_format="rosbag",
                adapter_version=self.adapter_version,
                warnings=warnings,
            ),
        )

    def validate(self, root: str | Path, **kwargs: Any) -> AdapterValidationReport:
        manifest = self.load(root, **kwargs)
        dataset_root = Path(root)
        errors: list[str] = []
        warnings = list(manifest.provenance.warnings)
        if not manifest.sequences:
            errors.append("No ROS bag files or ROS2 bag directories found.")
        for rel_path in manifest.metadata.get("bag_files", []):
            path = dataset_root / rel_path
            if path.is_file() and path.stat().st_size == 0:
                warnings.append(f"Empty bag: {rel_path}.")
        ros2_db_files = list(dataset_root.rglob("*.db3")) + list(dataset_root.rglob("*.sqlite3"))
        if ros2_db_files and not (dataset_root / "metadata.yaml").is_file():
            warnings.append("Missing metadata.yaml for ROS2 bag.")
        if not manifest.sensors:
            warnings.append(
                "No topics found; install optional dependencies for deep topic inspection."
            )
        return AdapterValidationReport(
            adapter_name=self.name,
            dataset_root=str(root),
            detected=self.detect(root),
            valid=not errors,
            **validation_scope(self.name, manifest.limitations),
            errors=errors,
            warnings=warnings,
            coverage={"sequences": bool(manifest.sequences), "topics": bool(manifest.sensors)},
            stats={"bag_count": len(manifest.sequences), "topic_count": len(manifest.sensors)},
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
        return [
            SensorInfo(name=sensor.sensor_id, frame_count=sensor.frame_count)
            for sensor in self.load(path).sensors
        ]

    def load_timestamps(self, path: str | Path, sensor_name: str) -> pd.Series:
        del path, sensor_name
        return pd.Series(dtype=float)


def _bag_units(path: Path) -> list[Path]:
    if path.is_file() and path.suffix.lower() == ".bag":
        return [path]
    if not path.is_dir():
        return []
    units = sorted(path.rglob("*.bag"))
    if (path / "metadata.yaml").is_file() or any(
        file_path.suffix.lower() in {".db3", ".sqlite3"} for file_path in path.rglob("*")
    ):
        units.append(path)
    return units


def _metadata_topics(root: Path) -> list[SensorStream]:
    metadata_path = root / "metadata.yaml"
    if not metadata_path.is_file():
        return []
    topics: list[SensorStream] = []
    current_topic: str | None = None
    current_count: int | None = None
    for raw_line in metadata_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("name:"):
            if current_topic:
                topics.append(_topic_sensor(current_topic, current_count))
            current_topic = line.split(":", 1)[1].strip().strip('"')
            current_count = None
        elif line.startswith("message_count:"):
            try:
                current_count = int(line.split(":", 1)[1].strip())
            except ValueError:
                current_count = None
    if current_topic:
        topics.append(_topic_sensor(current_topic, current_count))
    return topics


def _topic_sensor(topic: str, count: int | None) -> SensorStream:
    return SensorStream(
        sensor_id=topic,
        sensor_type=_topic_type(topic),
        name=topic,
        modality="ros_topic",
        frame_count=count,
        metadata={"topic": topic},
    )


def _topic_type(topic: str) -> str:
    lowered = topic.lower()
    if lowered.startswith("/camera") or lowered.startswith("/image") or "/image" in lowered:
        return "camera"
    if lowered.startswith(("/lidar", "/velodyne", "/points")) or "pointcloud" in lowered:
        return "lidar"
    if lowered.startswith("/imu"):
        return "imu"
    if lowered.startswith(("/gps", "/fix")):
        return "gps"
    if lowered in {"/tf", "/tf_static"}:
        return "transform"
    return "unknown"


def _size_bytes(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(file_path.stat().st_size for file_path in path.rglob("*") if file_path.is_file())
