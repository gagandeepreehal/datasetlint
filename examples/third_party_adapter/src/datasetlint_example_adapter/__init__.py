"""Minimal third-party DatasetLint adapter template."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from datasetlint.adapters import (
    AnnotationRecord,
    DatasetAdapter,
    DatasetManifest,
    FrameRecord,
    SensorStream,
    SequenceRecord,
)
from datasetlint.adapters.base import manifest_provenance, relative_to_root


class ExampleTelemetryAdapter(DatasetAdapter):
    """Read a tiny JSONL telemetry layout as normalized manifest records."""

    name = "example_telemetry"
    supported_formats = ("example-telemetry-jsonl",)
    description = "Example third-party adapter registered by entry point."

    def can_load(self, path: str | Path) -> bool:
        root = Path(path)
        return root.is_dir() and (root / "telemetry.jsonl").is_file()

    def load(self, root: str | Path, **kwargs: Any) -> DatasetManifest:
        del kwargs
        dataset_root = Path(root)
        rows = _read_rows(dataset_root / "telemetry.jsonl")
        frames: list[FrameRecord] = []
        annotations: list[AnnotationRecord] = []
        sensor_counts = {"camera": 0, "lidar": 0}

        for index, row in enumerate(rows):
            frame_id = str(row.get("frame_id") or index)
            timestamp = _optional_float(row.get("timestamp"))
            camera_path = _optional_text(row.get("camera_path"))
            lidar_path = _optional_text(row.get("lidar_path"))
            if camera_path:
                sensor_counts["camera"] += 1
                frames.append(
                    FrameRecord(
                        frame_id=f"{frame_id}:camera",
                        sequence_id="default",
                        timestamp=timestamp,
                        sensor_id="camera",
                        file_path=camera_path,
                    )
                )
            if lidar_path:
                sensor_counts["lidar"] += 1
                frames.append(
                    FrameRecord(
                        frame_id=f"{frame_id}:lidar",
                        sequence_id="default",
                        timestamp=timestamp,
                        sensor_id="lidar",
                        file_path=lidar_path,
                    )
                )
            label = _optional_text(row.get("label"))
            if label:
                annotations.append(
                    AnnotationRecord(
                        annotation_id=f"{frame_id}:label",
                        frame_id=f"{frame_id}:camera" if camera_path else None,
                        sequence_id="default",
                        category=label,
                        annotation_type="label",
                    )
                )

        sensors = [
            SensorStream(
                sensor_id="camera",
                sensor_type="camera",
                name="camera",
                modality="camera",
                frame_count=sensor_counts["camera"],
            ),
            SensorStream(
                sensor_id="lidar",
                sensor_type="lidar",
                name="lidar",
                modality="lidar",
                frame_count=sensor_counts["lidar"],
            ),
        ]
        return DatasetManifest(
            dataset_name=dataset_root.name,
            adapter_name=self.name,
            dataset_root=str(dataset_root),
            sequences=[
                SequenceRecord(
                    sequence_id="default",
                    name=dataset_root.name,
                    frame_count=len(frames),
                )
            ],
            frames=frames,
            sensors=sensors,
            annotations=annotations,
            calibration=[],
            splits={},
            metadata={
                "telemetry_file": relative_to_root(dataset_root, dataset_root / "telemetry.jsonl"),
                "row_count": len(rows),
            },
            limitations=[
                "Example adapter validates JSONL references and timestamps only; "
                "it does not decode payload files."
            ],
            provenance=manifest_provenance(
                dataset_root,
                source_format="example-telemetry-jsonl",
                adapter_version=self.adapter_version,
                warnings=[],
            ),
        )


def _read_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"telemetry.jsonl line {line_number} must be a JSON object.")
            rows.append(payload)
    return rows


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _optional_float(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


__all__ = ["ExampleTelemetryAdapter"]
