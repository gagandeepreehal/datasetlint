"""MCAP adapter with lightweight indexing and optional-reader metadata hooks."""

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
    SequenceRecord,
    manifest_provenance,
    relative_to_root,
)


class MCAPAdapter(DatasetAdapter):
    """Index MCAP files without adding an MCAP runtime dependency."""

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
        del kwargs
        dataset_root = Path(root)
        files = _mcap_files(dataset_root)
        warnings = [
            "MCAP adapter indexes files; install optional mcap package for channel parsing."
        ]
        sequences = [
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
        return DatasetManifest(
            dataset_name=dataset_root.name if dataset_root.is_dir() else dataset_root.stem,
            adapter_name=self.name,
            dataset_root=str(dataset_root),
            sequences=sequences,
            frames=[],
            sensors=[],
            annotations=[],
            calibration=[],
            splits={},
            metadata={
                "files": [
                    {
                        "path": relative_to_root(dataset_root, file_path),
                        "size_bytes": file_path.stat().st_size,
                    }
                    for file_path in files
                ],
                "schemas": [],
                "channels": [],
            },
            limitations=[
                (
                    "Channel, schema, compression, and message inspection require the "
                    "optional mcap package."
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
        if not manifest.metadata.get("channels"):
            warnings.append("No channels found in lightweight mode.")
        if not manifest.metadata.get("schemas"):
            warnings.append("Missing schemas in lightweight mode.")
        return AdapterValidationReport(
            adapter_name=self.name,
            dataset_root=str(root),
            detected=self.detect(root),
            valid=not errors,
            errors=errors,
            warnings=warnings,
            coverage={"sequences": bool(manifest.sequences), "channels": False, "schemas": False},
            stats={"mcap_count": len(files), "sequence_count": len(manifest.sequences)},
        )

    def load_metadata(self, path: str | Path) -> DatasetMetadata:
        manifest = self.load(path)
        return DatasetMetadata(
            dataset_path=manifest.dataset_root,
            name=manifest.dataset_name,
            sensors=[],
            raw=manifest.metadata,
        )

    def list_sensors(self, path: str | Path) -> list[SensorInfo]:
        del path
        return []

    def load_timestamps(self, path: str | Path, sensor_name: str) -> pd.Series:
        raise _unsupported(path, sensor_name)

    def load_labels(self, path: str | Path) -> pd.DataFrame | None:
        raise _unsupported(path, "labels")

    def load_trajectory(self, path: str | Path) -> pd.DataFrame | None:
        raise _unsupported(path, "trajectory")

    def load_calibration(self, path: str | Path) -> dict[str, Any] | None:
        raise _unsupported(path, "calibration")


def _mcap_files(path: Path) -> list[Path]:
    if path.is_file() and path.suffix.lower() == ".mcap":
        return [path]
    if path.is_dir():
        return sorted(file_path for file_path in path.rglob("*.mcap") if file_path.is_file())
    return []


def _unsupported(path: str | Path, sensor_name: str) -> NotImplementedError:
    return NotImplementedError(
        "MCAP deep parsing is not implemented in DatasetLint v0. "
        f"Cannot load {sensor_name} from {path} without an optional MCAP reader."
    )
