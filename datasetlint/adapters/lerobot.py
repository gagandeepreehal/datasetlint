"""LeRobot dataset adapter for local episode data and video layouts."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pandas as pd

from datasetlint.adapters.base import (
    AdapterValidationReport,
    AnnotationRecord,
    DatasetAdapter,
    DatasetManifest,
    DatasetMetadata,
    FrameRecord,
    SensorInfo,
    SensorStream,
    SequenceRecord,
    manifest_provenance,
    read_json_object,
    relative_to_root,
    validation_scope,
)
from datasetlint.adapters.manifest_rules import merge_common_rule_result, run_manifest_rules

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}
EPISODE_TABLE_EXTENSIONS = {".parquet", ".jsonl"}


class LeRobotAdapter(DatasetAdapter):
    """Index local LeRobot datasets without importing the lerobot package."""

    name = "lerobot"
    supported_formats = ("lerobot",)
    description = "LeRobot local dataset adapter for meta files, episode tables, and videos."

    def can_load(self, path: str | Path) -> bool:
        root = Path(path)
        if not root.is_dir():
            return False
        meta = root / "meta"
        if (meta / "info.json").is_file() or (meta / "episodes.jsonl").is_file():
            return True
        return (root / "data").is_dir() and any(root.glob("data/**/*.parquet"))

    def load(self, root: str | Path, **kwargs: Any) -> DatasetManifest:
        del kwargs
        dataset_root = Path(root)
        info = _read_info(dataset_root)
        episodes = _read_jsonl(dataset_root / "meta" / "episodes.jsonl")
        tasks = _read_jsonl(dataset_root / "meta" / "tasks.jsonl")
        frames: list[FrameRecord] = []
        sensors_by_id: dict[str, SensorStream] = {}
        warnings: list[str] = []

        episode_metadata = _episode_metadata_by_id(episodes)
        for file_path in _episode_tables(dataset_root):
            episode_id = _episode_id_from_name(file_path)
            sensor_id = "episode_data"
            frames.append(
                FrameRecord(
                    frame_id=f"{episode_id}/data",
                    sequence_id=episode_id,
                    sensor_id=sensor_id,
                    file_path=relative_to_root(dataset_root, file_path),
                    metadata={
                        "extension": file_path.suffix.lower(),
                        "episode_metadata": episode_metadata.get(episode_id, {}),
                    },
                )
            )
            _upsert_sensor(sensors_by_id, sensor_id, "tabular", "episode_table")

        for file_path in _video_files(dataset_root):
            episode_id = _episode_id_from_name(file_path)
            sensor_id = _video_sensor_id(dataset_root, file_path)
            frames.append(
                FrameRecord(
                    frame_id=f"{episode_id}/{sensor_id}",
                    sequence_id=episode_id,
                    sensor_id=sensor_id,
                    file_path=relative_to_root(dataset_root, file_path),
                    metadata={
                        "extension": file_path.suffix.lower(),
                        "episode_metadata": episode_metadata.get(episode_id, {}),
                    },
                )
            )
            _upsert_sensor(sensors_by_id, sensor_id, "camera", "video")

        for sensor_id, sensor in list(sensors_by_id.items()):
            count = sum(1 for frame in frames if frame.sensor_id == sensor_id)
            sensors_by_id[sensor_id] = sensor.model_copy(update={"frame_count": count})

        sequences = _sequences(dataset_root, episodes, frames)
        annotations = _task_annotations(tasks)
        splits = _splits_from_info(info, frames)
        if not frames:
            warnings.append(
                "No LeRobot episode tables or videos were indexed. Location: data/ and videos/. "
                "Fix: validate a local LeRobot dataset root containing episode_*.parquet "
                "or episode_*.mp4 files."
            )

        return DatasetManifest(
            dataset_name=str(info.get("repo_id") or dataset_root.name),
            adapter_name=self.name,
            dataset_root=str(dataset_root),
            version=str(info.get("codebase_version"))
            if info.get("codebase_version") is not None
            else None,
            sequences=sequences,
            frames=frames,
            sensors=sorted(sensors_by_id.values(), key=lambda item: item.sensor_id),
            annotations=annotations,
            calibration=[],
            splits=splits,
            metadata={
                "info": info,
                "episode_count": len(sequences),
                "task_count": len(tasks),
            },
            limitations=[
                "LeRobot parquet rows are indexed without requiring pyarrow or lerobot.",
                "Video payloads and per-step observation/action tensors are not decoded.",
            ],
            provenance=manifest_provenance(
                dataset_root,
                source_format="lerobot",
                adapter_version=self.adapter_version,
                warnings=warnings,
            ),
        )

    def validate(self, root: str | Path, **kwargs: Any) -> AdapterValidationReport:
        manifest = self.load(root, **kwargs)
        dataset_root = Path(root)
        errors: list[str] = []
        warnings = list(manifest.provenance.warnings)
        if not (dataset_root / "meta" / "info.json").is_file():
            warnings.append(
                "Missing LeRobot meta/info.json. Location: meta/info.json. "
                "Fix: export or download the complete LeRobot dataset metadata."
            )
        if not manifest.frames:
            errors.append(
                "No LeRobot episode payloads found. Location: data/ or videos/. "
                "Fix: include episode parquet files or camera videos before validation."
            )
        data_episode_ids = {
            frame.sequence_id
            for frame in manifest.frames
            if frame.sensor_id == "episode_data" and frame.sequence_id is not None
        }
        video_episode_ids = {
            frame.sequence_id
            for frame in manifest.frames
            if frame.sensor_id != "episode_data" and frame.sequence_id is not None
        }
        missing_video = sorted(data_episode_ids - video_episode_ids)
        if missing_video:
            warnings.append(
                "LeRobot episodes with data but no indexed videos: "
                f"{', '.join(missing_video)}. Location: videos/. Fix: include camera videos "
                "or confirm this dataset is intentionally state-only."
            )
        scope = validation_scope(self.name, manifest.limitations)
        coverage = {
            "sequences": bool(manifest.sequences),
            "frames": bool(manifest.frames),
            "sensors": bool(manifest.sensors),
            "annotations": bool(manifest.annotations),
            "splits": bool(manifest.splits),
        }
        stats = {
            "sequence_count": len(manifest.sequences),
            "frame_count": len(manifest.frames),
            "sensor_count": len(manifest.sensors),
            "task_count": len(manifest.annotations),
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
            version=manifest.version,
            sensors=[sensor.sensor_id for sensor in manifest.sensors],
            raw=manifest.metadata,
        )

    def list_sensors(self, path: str | Path) -> list[SensorInfo]:
        manifest = self.load(path)
        return [
            SensorInfo(name=sensor.sensor_id, frame_count=sensor.frame_count)
            for sensor in manifest.sensors
        ]

    def load_timestamps(self, path: str | Path, sensor_name: str) -> pd.Series:
        del path, sensor_name
        return pd.Series([], dtype=float)


def _read_info(root: Path) -> dict[str, Any]:
    path = root / "meta" / "info.json"
    if not path.is_file():
        return {}
    try:
        return read_json_object(path)
    except ValueError:
        return {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(raw, dict):
            rows.append(raw)
    return rows


def _episode_tables(root: Path) -> list[Path]:
    data_dir = root / "data"
    if not data_dir.is_dir():
        return []
    return sorted(
        file_path
        for file_path in data_dir.rglob("*")
        if file_path.is_file() and file_path.suffix.lower() in EPISODE_TABLE_EXTENSIONS
    )


def _video_files(root: Path) -> list[Path]:
    video_dir = root / "videos"
    if not video_dir.is_dir():
        return []
    return sorted(
        file_path
        for file_path in video_dir.rglob("*")
        if file_path.is_file() and file_path.suffix.lower() in VIDEO_EXTENSIONS
    )


def _episode_id_from_name(path: Path) -> str:
    stem = path.stem
    if stem.startswith("episode_"):
        return stem.removeprefix("episode_")
    return stem


def _video_sensor_id(root: Path, path: Path) -> str:
    parts = path.relative_to(root).parts
    for part in reversed(parts[:-1]):
        if not part.startswith("chunk-") and part != "videos":
            return part
    return "video"


def _upsert_sensor(
    sensors: dict[str, SensorStream], sensor_id: str, sensor_type: str, modality: str
) -> None:
    sensors.setdefault(
        sensor_id,
        SensorStream(
            sensor_id=sensor_id,
            sensor_type=sensor_type,
            name=sensor_id,
            modality=modality,
        ),
    )


def _episode_metadata_by_id(episodes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in episodes:
        episode_id = item.get("episode_index", item.get("episode_id", item.get("index")))
        if episode_id is None:
            continue
        result[str(episode_id).zfill(6)] = item
        result[str(episode_id)] = item
    return result


def _sequences(
    root: Path, episodes: list[dict[str, Any]], frames: list[FrameRecord]
) -> list[SequenceRecord]:
    if episodes:
        return [
            SequenceRecord(
                sequence_id=str(
                    item.get("episode_index", item.get("episode_id", item.get("index", index)))
                ).zfill(6),
                name=str(item.get("episode_index", index)),
                frame_count=_optional_int(item.get("length", item.get("num_frames"))),
                metadata=item,
            )
            for index, item in enumerate(episodes)
        ]
    sequence_ids = sorted({frame.sequence_id for frame in frames if frame.sequence_id is not None})
    return [
        SequenceRecord(
            sequence_id=sequence_id,
            name=sequence_id,
            frame_count=sum(1 for frame in frames if frame.sequence_id == sequence_id),
            metadata={"source": relative_to_root(root, root)},
        )
        for sequence_id in sequence_ids
    ]


def _task_annotations(tasks: list[dict[str, Any]]) -> list[AnnotationRecord]:
    annotations: list[AnnotationRecord] = []
    for index, task in enumerate(tasks):
        task_id = str(task.get("task_index", task.get("id", index)))
        annotations.append(
            AnnotationRecord(
                annotation_id=f"task-{task_id}",
                category="task",
                annotation_type="lerobot_task",
                values=task,
                metadata={"source": "meta/tasks.jsonl"},
            )
        )
    return annotations


def _splits_from_info(info: dict[str, Any], frames: list[FrameRecord]) -> dict[str, list[str]]:
    raw_splits = info.get("splits")
    if not isinstance(raw_splits, dict):
        return {}
    splits: dict[str, list[str]] = {}
    for split_name, values in raw_splits.items():
        episode_ids = _episode_ids_from_split_values(values)
        if episode_ids:
            splits[str(split_name)] = [
                frame.frame_id
                for frame in frames
                if frame.sequence_id is not None and frame.sequence_id in episode_ids
            ]
    return splits


def _episode_ids_from_split_values(values: object) -> set[str]:
    if isinstance(values, str):
        return _episode_ids_from_split_string(values)
    if isinstance(values, int):
        return _normalized_episode_ids([values])
    if isinstance(values, list):
        return _normalized_episode_ids(values)
    return set()


def _episode_ids_from_split_string(value: str) -> set[str]:
    stripped = value.strip()
    if not stripped:
        return set()
    if ":" not in stripped:
        return _normalized_episode_ids([stripped])
    parts = stripped.split(":")
    if len(parts) != 2:
        return set()
    try:
        start = int(parts[0] or 0)
        end = int(parts[1])
    except ValueError:
        return set()
    if end < start:
        return set()
    return _normalized_episode_ids(range(start, end))


def _normalized_episode_ids(values: Iterable[object]) -> set[str]:
    episode_ids: set[str] = set()
    for value in values:
        episode_id = str(value)
        episode_ids.add(episode_id)
        episode_ids.add(episode_id.zfill(6))
    return episode_ids


def _optional_int(value: object) -> int | None:
    if not isinstance(value, str | bytes | bytearray | int | float):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
