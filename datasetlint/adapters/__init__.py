"""Dataset adapter registry."""

from __future__ import annotations

from pathlib import Path

from datasetlint.adapters.base import AdapterDetection, DatasetAdapter, DatasetMetadata, SensorInfo
from datasetlint.adapters.folder import FolderAdapter
from datasetlint.adapters.mcap import MCAPAdapter
from datasetlint.adapters.nuscenes import NuScenesAdapter
from datasetlint.adapters.rosbag import ROSBagAdapter
from datasetlint.adapters.waymo import WaymoAdapter

_ADAPTERS: tuple[DatasetAdapter, ...] = (
    FolderAdapter(),
    MCAPAdapter(),
    ROSBagAdapter(),
    NuScenesAdapter(),
    WaymoAdapter(),
)


def available_adapters() -> list[DatasetAdapter]:
    """Return instantiated adapters in auto-detection order."""

    return list(_ADAPTERS)


def detect_adapters(path: str | Path) -> list[AdapterDetection]:
    """Return all adapter detection outcomes for a path."""

    detections: list[AdapterDetection] = []
    for adapter in _ADAPTERS:
        try:
            can_load = adapter.can_load(path)
        except OSError as exc:
            detections.append(
                AdapterDetection(
                    name=adapter.name,
                    can_load=False,
                    message=f"detection failed: {exc}",
                )
            )
            continue
        detections.append(
            AdapterDetection(
                name=adapter.name,
                can_load=can_load,
                message="can load" if can_load else "not detected",
            )
        )
    return detections


def get_adapter(path: str | Path, name: str = "auto") -> DatasetAdapter:
    """Return an adapter by name, or auto-detect one for the path."""

    normalized_name = name.lower()
    if normalized_name != "auto":
        for adapter in _ADAPTERS:
            if adapter.name == normalized_name:
                return adapter
        valid = ", ".join(adapter.name for adapter in _ADAPTERS)
        raise ValueError(f"Unknown adapter '{name}'. Valid adapters: {valid}, auto.")

    for adapter in _ADAPTERS:
        if adapter.can_load(path):
            return adapter
    raise ValueError(f"No DatasetLint adapter could load: {Path(path)}")


__all__ = [
    "AdapterDetection",
    "DatasetAdapter",
    "DatasetMetadata",
    "FolderAdapter",
    "MCAPAdapter",
    "NuScenesAdapter",
    "ROSBagAdapter",
    "SensorInfo",
    "WaymoAdapter",
    "available_adapters",
    "detect_adapters",
    "get_adapter",
]
