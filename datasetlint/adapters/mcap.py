"""MCAP adapter with lightweight indexing and optional-reader metadata parsing."""

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


class MCAPAdapter(DatasetAdapter):
    """Index MCAP files, with optional channel and message metadata parsing."""

    name = "mcap"
    supported_formats = ("mcap",)
    optional_dependencies = ("mcap",)
    description = "MCAP index adapter; optional mcap package can inspect channels."

    def can_load(self, path: str | Path) -> bool:
        dataset_path = Path(path)
        if dataset_path.is_file():
            return dataset_path.suffix.lower() == ".mcap"
        return dataset_path.is_dir() and any(dataset_path.rglob("*.mcap"))

    def load(self, root: str | Path, **kwargs: Any) -> DatasetManifest:
        dataset_root = Path(root)
        files = _mcap_files(dataset_root)
        deep = bool(kwargs.get("deep", False) or kwargs.get("parse_messages", False))
        max_messages = _positive_int(kwargs.get("max_rows"), default=1000)
        base_metadata = _base_metadata(dataset_root, files)
        if deep:
            parsed = _parse_mcap_files(dataset_root, files, max_messages=max_messages)
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
                metadata={**base_metadata, **parsed.metadata},
                limitations=parsed.limitations,
                provenance=manifest_provenance(
                    dataset_root,
                    source_format="mcap",
                    adapter_version=self.adapter_version,
                    warnings=parsed.warnings,
                ),
            )
        warnings = ["MCAP adapter indexed files without parsing messages."]
        return DatasetManifest(
            dataset_name=dataset_root.name if dataset_root.is_dir() else dataset_root.stem,
            adapter_name=self.name,
            dataset_root=str(dataset_root),
            sequences=_index_sequences(dataset_root, files),
            frames=[],
            sensors=[],
            annotations=[],
            calibration=[],
            splits={},
            metadata=base_metadata,
            limitations=[
                (
                    "Use --deep with the optional mcap package to inspect channels, "
                    "schemas, and message timestamps."
                )
            ],
            provenance=manifest_provenance(
                dataset_root,
                source_format="mcap",
                adapter_version=self.adapter_version,
                warnings=warnings,
            ),
        )

    def validate(self, root: str | Path, **kwargs: Any) -> AdapterValidationReport:
        manifest = self.load(root, **kwargs)
        errors: list[str] = []
        warnings = list(manifest.provenance.warnings)
        files = manifest.metadata.get("files", [])
        if not files:
            errors.append("No MCAP files found.")
        empty = [
            item["path"]
            for item in files
            if isinstance(item, dict) and int(item.get("size_bytes", 0)) == 0
        ]
        if empty:
            warnings.append(f"No messages or empty MCAP files: {', '.join(empty)}.")
        deep = manifest.metadata.get("parse_mode") == "deep"
        if not deep:
            if not manifest.metadata.get("channels"):
                warnings.append("No channels found in index mode.")
            if not manifest.metadata.get("schemas"):
                warnings.append("Missing schemas in index mode.")
        else:
            parse_errors = _parse_errors(warnings)
            errors.extend(parse_errors)
            warnings = [warning for warning in warnings if warning not in parse_errors]
        scope = _mcap_scope(deep, manifest.limitations)
        coverage = {
            "sequences": bool(manifest.sequences),
            "channels": bool(manifest.metadata.get("channels")),
            "schemas": bool(manifest.metadata.get("schemas")),
            "message_timestamps": bool(manifest.frames),
        }
        stats = {
            "mcap_count": len(files),
            "sequence_count": len(manifest.sequences),
            "channel_count": len(manifest.metadata.get("channels", [])),
            "schema_count": len(manifest.metadata.get("schemas", [])),
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
            for sensor in self.load(path, deep=True).sensors
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

    def load_labels(self, path: str | Path) -> pd.DataFrame | None:
        raise _unsupported(path, "labels")

    def load_trajectory(self, path: str | Path) -> pd.DataFrame | None:
        raise _unsupported(path, "trajectory")

    def load_calibration(self, path: str | Path) -> dict[str, Any] | None:
        raise _unsupported(path, "calibration")


@dataclass(slots=True)
class _ParsedMCAP:
    sequences: list[SequenceRecord]
    frames: list[FrameRecord]
    sensors: list[SensorStream]
    metadata: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


def _index_sequences(dataset_root: Path, files: list[Path]) -> list[SequenceRecord]:
    return [
        SequenceRecord(
            sequence_id=file_path.stem,
            name=file_path.name,
            metadata={
                "file_path": relative_to_root(dataset_root, file_path),
                "size_bytes": file_path.stat().st_size,
            },
        )
        for file_path in files
    ]


def _base_metadata(dataset_root: Path, files: list[Path]) -> dict[str, Any]:
    return {
        "files": [
            {
                "path": relative_to_root(dataset_root, file_path),
                "size_bytes": file_path.stat().st_size,
            }
            for file_path in files
        ],
        "schemas": [],
        "channels": [],
    }


def _parse_mcap_files(dataset_root: Path, files: list[Path], *, max_messages: int) -> _ParsedMCAP:
    make_reader = _mcap_make_reader()
    frames: list[FrameRecord] = []
    channel_counts: Counter[str] = Counter()
    channels_by_id: dict[int, dict[str, Any]] = {}
    schemas_by_id: dict[int, dict[str, Any]] = {}
    sequence_counts: Counter[str] = Counter()
    warnings: list[str] = []
    truncated = False

    for file_path in files:
        sequence_id = file_path.stem
        try:
            with file_path.open("rb") as stream:
                reader = make_reader(stream)
                for schema, channel, message in reader.iter_messages():
                    if len(frames) >= max_messages:
                        truncated = True
                        break
                    topic = _object_text(channel, "topic", default=f"channel-{len(channels_by_id)}")
                    channel_id = _object_int(channel, "id")
                    schema_id = _object_int(channel, "schema_id")
                    channels_by_id[channel_id] = {
                        "id": channel_id,
                        "topic": topic,
                        "schema_id": schema_id,
                        "message_encoding": _object_text(channel, "message_encoding"),
                        "metadata": _object_dict(channel, "metadata"),
                    }
                    if schema is not None:
                        schema_key = _object_int(schema, "id")
                        schemas_by_id[schema_key] = {
                            "id": schema_key,
                            "name": _object_text(schema, "name"),
                            "encoding": _object_text(schema, "encoding"),
                        }
                    timestamp = _mcap_timestamp(message)
                    channel_counts[topic] += 1
                    sequence_counts[sequence_id] += 1
                    frames.append(
                        FrameRecord(
                            frame_id=f"{sequence_id}:{len(frames)}",
                            sequence_id=sequence_id,
                            timestamp=timestamp,
                            sensor_id=topic,
                            file_path=relative_to_root(dataset_root, file_path),
                            metadata={
                                "channel_id": channel_id,
                                "schema_id": schema_id,
                                "publish_time_sec": _ns_to_seconds(
                                    _object_int(message, "publish_time")
                                ),
                                "sequence": _object_int(message, "sequence"),
                            },
                        )
                    )
                if truncated:
                    break
        except Exception as exc:
            warnings.append(f"Could not parse {relative_to_root(dataset_root, file_path)}: {exc}.")

    if truncated:
        warnings.append(f"MCAP message parsing stopped at max_rows={max_messages}.")

    sequences = [
        SequenceRecord(
            sequence_id=file_path.stem,
            name=file_path.name,
            frame_count=sequence_counts.get(file_path.stem, 0),
            metadata={
                "file_path": relative_to_root(dataset_root, file_path),
                "size_bytes": file_path.stat().st_size,
            },
        )
        for file_path in files
    ]
    sensors = [
        SensorStream(
            sensor_id=topic,
            sensor_type=_topic_type(topic),
            name=topic,
            modality="mcap_channel",
            frame_count=count,
            metadata={"topic": topic},
        )
        for topic, count in sorted(channel_counts.items())
    ]
    return _ParsedMCAP(
        sequences=sequences,
        frames=frames,
        sensors=sensors,
        metadata={
            "parse_mode": "deep",
            "message_count": len(frames),
            "channels": list(channels_by_id.values()),
            "schemas": list(schemas_by_id.values()),
            "truncated": truncated,
        },
        warnings=warnings,
        limitations=[
            (
                "MCAP channels, schemas, and message timestamps are parsed; message payloads "
                "are not decoded into modality-specific DatasetLint records yet."
            )
        ],
    )


def _mcap_make_reader() -> Any:
    try:
        module = import_module("mcap.reader")
    except ImportError as exc:
        raise AdapterDependencyError(
            "Deep MCAP parsing requires the optional mcap package. "
            "Install with `python -m pip install -e '.[mcap]'`."
        ) from exc
    return cast(Any, module).make_reader


def _mcap_scope(deep: bool, limitations: list[str]) -> dict[str, Any]:
    if not deep:
        return validation_scope("mcap", limitations)
    return {
        "validation_mode": "deep",
        "checked": [
            "MCAP file discovery",
            "channel metadata",
            "schema metadata",
            "message timestamp index",
        ],
        "not_checked": ["message payload decoding", "sensor-specific semantic validation"],
        "limitations": limitations,
    }


def _mcap_files(path: Path) -> list[Path]:
    if path.is_file() and path.suffix.lower() == ".mcap":
        return [path]
    if path.is_dir():
        return sorted(file_path for file_path in path.rglob("*.mcap") if file_path.is_file())
    return []


def _parse_errors(warnings: list[str]) -> list[str]:
    return [warning for warning in warnings if warning.startswith("Could not parse ")]


def _topic_type(topic: str) -> str:
    lowered = topic.lower()
    if "camera" in lowered or "image" in lowered:
        return "camera"
    if "lidar" in lowered or "point" in lowered:
        return "lidar"
    if "imu" in lowered:
        return "imu"
    if "gps" in lowered or "gnss" in lowered or "fix" in lowered:
        return "gps"
    return "unknown"


def _object_int(value: object, name: str) -> int:
    item = getattr(value, name, 0)
    return int(item) if isinstance(item, int) else 0


def _object_text(value: object, name: str, *, default: str = "") -> str:
    item = getattr(value, name, default)
    return item if isinstance(item, str) else default


def _object_dict(value: object, name: str) -> dict[str, Any]:
    item = getattr(value, name, {})
    return cast(dict[str, Any], item) if isinstance(item, dict) else {}


def _mcap_timestamp(message: object) -> float | None:
    log_time = _object_int(message, "log_time")
    if log_time:
        return _ns_to_seconds(log_time)
    publish_time = _object_int(message, "publish_time")
    if publish_time:
        return _ns_to_seconds(publish_time)
    return None


def _ns_to_seconds(value: int) -> float | None:
    if value <= 0:
        return None
    return value / 1_000_000_000.0


def _positive_int(value: object, *, default: int) -> int:
    if isinstance(value, int) and value > 0:
        return value
    return default


def _unsupported(path: str | Path, sensor_name: str) -> NotImplementedError:
    return NotImplementedError(
        "MCAP semantic record loading is not implemented in DatasetLint v0. "
        f"Cannot load {sensor_name} from {path}; use inspect/validate --deep for "
        "channel, schema, and timestamp metadata."
    )
