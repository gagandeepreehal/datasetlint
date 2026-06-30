"""ROS bag adapter with lightweight indexing and optional message metadata parsing."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from typing import Any, cast

import pandas as pd

from datasetlint.adapters.base import (
    AdapterValidationReport,
    DatasetAdapter,
    DatasetManifest,
    DatasetMetadata,
    FrameRecord,
    SensorInfo,
    SensorStream,
    SequenceRecord,
    manifest_provenance,
    relative_to_root,
    validation_scope,
)
from datasetlint.adapters.errors import AdapterDependencyError
from datasetlint.adapters.manifest_rules import merge_common_rule_result, run_manifest_rules


class ROSBagAdapter(DatasetAdapter):
    """Index ROS bags, with optional topic and message timestamp parsing."""

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
        dataset_root = Path(root)
        bags = _bag_units(dataset_root)
        deep = bool(kwargs.get("deep", False) or kwargs.get("parse_messages", False))
        max_messages = _positive_int(kwargs.get("max_rows"), default=1000)
        if deep:
            parsed = _parse_rosbag_units(dataset_root, bags, max_messages=max_messages)
            return DatasetManifest(
                dataset_name=dataset_root.name if dataset_root.is_dir() else dataset_root.stem,
                adapter_name=self.name,
                dataset_root=str(dataset_root),
                sequences=parsed.sequences,
                frames=parsed.frames,
                sensors=parsed.sensors,
                annotations=[],
                calibration=[],
                splits={},
                metadata=parsed.metadata,
                limitations=parsed.limitations,
                provenance=manifest_provenance(
                    dataset_root,
                    source_format="rosbag",
                    adapter_version=self.adapter_version,
                    warnings=parsed.warnings,
                ),
            )
        warnings = ["ROS bag adapter indexed files without parsing message payloads."]
        sensors = _metadata_topics(dataset_root)
        return DatasetManifest(
            dataset_name=dataset_root.name if dataset_root.is_dir() else dataset_root.stem,
            adapter_name=self.name,
            dataset_root=str(dataset_root),
            sequences=_index_sequences(dataset_root, bags),
            frames=[],
            sensors=sensors,
            annotations=[],
            calibration=[],
            splits={},
            metadata={
                "parse_mode": "index",
                "bag_files": [relative_to_root(dataset_root, bag) for bag in bags],
            },
            limitations=[
                (
                    "Use --deep with the optional rosbags package to inspect topics, "
                    "message types, counts, and timestamps."
                ),
                "Index mode parses ROS2 metadata.yaml only for lightweight topic summaries.",
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
                "No topics found; use --deep with optional dependencies for topic inspection."
        )
        deep = manifest.metadata.get("parse_mode") == "deep"
        if deep:
            parse_errors = _parse_errors(warnings)
            errors.extend(parse_errors)
            warnings = [warning for warning in warnings if warning not in parse_errors]
        scope = _rosbag_scope(deep, manifest.limitations)
        coverage = {
            "sequences": bool(manifest.sequences),
            "topics": bool(manifest.sensors),
            "message_timestamps": bool(manifest.frames),
        }
        stats = {
            "bag_count": len(manifest.sequences),
            "topic_count": len(manifest.sensors),
            "message_count": manifest.metadata.get("message_count", 0),
        }
        scope, errors, warnings, coverage, stats = merge_common_rule_result(
            scope=scope,
            errors=errors,
            warnings=warnings,
            coverage=coverage,
            stats=stats,
            result=run_manifest_rules(manifest, root),
        )
        return AdapterValidationReport(
            adapter_name=self.name,
            dataset_root=str(root),
            detected=self.detect(root),
            valid=not errors,
            **scope,
            errors=errors,
            warnings=warnings,
            coverage=coverage,
            stats=stats,
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
        manifest = self.load(path, deep=True)
        return pd.Series(
            [
                frame.timestamp
                for frame in manifest.frames
                if frame.sensor_id == sensor_name and frame.timestamp is not None
            ],
            dtype=float,
        )


@dataclass(slots=True)
class _ParsedROSBag:
    sequences: list[SequenceRecord]
    frames: list[FrameRecord]
    sensors: list[SensorStream]
    metadata: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


def _index_sequences(dataset_root: Path, bags: list[Path]) -> list[SequenceRecord]:
    return [
        SequenceRecord(
            sequence_id=_bag_sequence_id(bag),
            name=bag.name,
            metadata={
                "file_path": relative_to_root(dataset_root, bag),
                "kind": "ros1" if bag.suffix.lower() == ".bag" else "ros2",
                "size_bytes": _size_bytes(bag),
            },
        )
        for bag in bags
    ]


def _parse_errors(warnings: list[str]) -> list[str]:
    return [warning for warning in warnings if warning.startswith("Could not parse ")]


def _parse_rosbag_units(
    dataset_root: Path, bags: list[Path], *, max_messages: int
) -> _ParsedROSBag:
    any_reader = _rosbags_any_reader()
    frames: list[FrameRecord] = []
    topic_counts: Counter[str] = Counter()
    topic_types: dict[str, str] = {}
    sequence_counts: Counter[str] = Counter()
    warnings: list[str] = []
    truncated = False

    for bag in bags:
        sequence_id = _bag_sequence_id(bag)
        try:
            with any_reader([bag]) as reader:
                for connection in getattr(reader, "connections", []):
                    topic = _object_text(connection, "topic", default="unknown")
                    topic_types[topic] = _object_text(connection, "msgtype")
                for connection, timestamp_ns, _rawdata in reader.messages():
                    if len(frames) >= max_messages:
                        truncated = True
                        break
                    topic = _object_text(connection, "topic", default="unknown")
                    msgtype = _object_text(connection, "msgtype")
                    topic_types[topic] = msgtype
                    topic_counts[topic] += 1
                    sequence_counts[sequence_id] += 1
                    frames.append(
                        FrameRecord(
                            frame_id=f"{sequence_id}:{len(frames)}",
                            sequence_id=sequence_id,
                            timestamp=_ns_to_seconds(timestamp_ns),
                            sensor_id=topic,
                            file_path=relative_to_root(dataset_root, bag),
                            metadata={"topic": topic, "msgtype": msgtype},
                        )
                    )
                if truncated:
                    break
        except Exception as exc:
            warnings.append(f"Could not parse {relative_to_root(dataset_root, bag)}: {exc}.")

    if truncated:
        warnings.append(f"ROS bag message parsing stopped at max_rows={max_messages}.")

    all_topics = sorted(set(topic_types) | set(topic_counts))
    sensors = [
        SensorStream(
            sensor_id=topic,
            sensor_type=_topic_type(topic),
            name=topic,
            modality="ros_topic",
            frame_count=topic_counts.get(topic, 0),
            metadata={"topic": topic, "msgtype": topic_types.get(topic, "")},
        )
        for topic in all_topics
    ]
    sequences = [
        SequenceRecord(
            sequence_id=_bag_sequence_id(bag),
            name=bag.name,
            frame_count=sequence_counts.get(_bag_sequence_id(bag), 0),
            metadata={
                "file_path": relative_to_root(dataset_root, bag),
                "kind": "ros1" if bag.suffix.lower() == ".bag" else "ros2",
                "size_bytes": _size_bytes(bag),
            },
        )
        for bag in bags
    ]
    return _ParsedROSBag(
        sequences=sequences,
        frames=frames,
        sensors=sensors,
        metadata={
            "parse_mode": "deep",
            "bag_files": [relative_to_root(dataset_root, bag) for bag in bags],
            "message_count": len(frames),
            "topics": [
                {
                    "name": topic,
                    "msgtype": topic_types.get(topic, ""),
                    "message_count": topic_counts.get(topic, 0),
                }
                for topic in all_topics
            ],
            "truncated": truncated,
        },
        warnings=warnings,
        limitations=[
            (
                "ROS bag topics, message types, counts, and timestamps are parsed; message "
                "payloads are not decoded into modality-specific DatasetLint records yet."
            )
        ],
    )


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


def _rosbags_any_reader() -> Any:
    try:
        module = import_module("rosbags.highlevel")
    except ImportError as exc:
        raise AdapterDependencyError(
            "Deep ROS bag parsing requires the optional rosbags package. "
            "Install with `python -m pip install -e '.[ros]'`."
        ) from exc
    return cast(Any, module).AnyReader


def _rosbag_scope(deep: bool, limitations: list[str]) -> dict[str, Any]:
    if not deep:
        return validation_scope("rosbag", limitations)
    return {
        "validation_mode": "deep",
        "checked": [
            "ROS bag file discovery",
            "topic metadata",
            "message types",
            "message timestamp index",
        ],
        "not_checked": ["message payload decoding", "sensor-specific semantic validation"],
        "limitations": limitations,
    }


def _bag_sequence_id(path: Path) -> str:
    return path.stem if path.is_file() else path.name


def _object_text(value: object, name: str, *, default: str = "") -> str:
    item = getattr(value, name, default)
    return item if isinstance(item, str) else default


def _ns_to_seconds(value: object) -> float | None:
    if not isinstance(value, int) or value <= 0:
        return None
    return value / 1_000_000_000.0


def _positive_int(value: object, *, default: int) -> int:
    if isinstance(value, int) and value > 0:
        return value
    return default
