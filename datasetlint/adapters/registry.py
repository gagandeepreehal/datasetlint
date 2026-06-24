"""Adapter registration, discovery, loading, and validation."""

from __future__ import annotations

from pathlib import Path

from datasetlint.adapters.base import (
    AdapterDetection,
    AdapterInfo,
    AdapterValidationReport,
    DatasetAdapter,
    DatasetManifest,
)
from datasetlint.adapters.coco import CocoAdapter
from datasetlint.adapters.errors import AdapterDetectionError, AdapterNotFoundError
from datasetlint.adapters.folder import FolderAdapter
from datasetlint.adapters.generic import GenericFolderAdapter
from datasetlint.adapters.huggingface import HuggingFaceAdapter
from datasetlint.adapters.kitti import KittiAdapter
from datasetlint.adapters.mcap import MCAPAdapter
from datasetlint.adapters.nuscenes import NuScenesAdapter
from datasetlint.adapters.rosbag import ROSBagAdapter
from datasetlint.adapters.waymo import WaymoAdapter

_REGISTRY: dict[str, DatasetAdapter] = {}
_AUTO_FALLBACKS = {"generic", "folder"}


def register_adapter(adapter_cls: type[DatasetAdapter] | DatasetAdapter) -> DatasetAdapter:
    """Register an adapter class or instance and return the instance."""

    adapter = adapter_cls() if isinstance(adapter_cls, type) else adapter_cls
    _REGISTRY[adapter.name] = adapter
    return adapter


def get_adapter(name: str) -> DatasetAdapter:
    """Return a registered adapter by name."""

    normalized = name.lower()
    adapter = _REGISTRY.get(normalized)
    if adapter is None:
        valid = ", ".join([*sorted(_REGISTRY), "auto"])
        raise AdapterNotFoundError(f"Unknown adapter '{name}'. Valid adapters: {valid}.")
    return adapter


def list_adapters() -> list[DatasetAdapter]:
    """Return registered adapters in deterministic order."""

    return [adapter for _, adapter in sorted(_REGISTRY.items())]


def list_adapter_info() -> list[AdapterInfo]:
    """Return adapter metadata for CLI output."""

    return [adapter.availability() for adapter in list_adapters()]


def available_adapters() -> list[DatasetAdapter]:
    """Backward-compatible alias for adapter instances."""

    return list_adapters()


def detect_adapters(path: str | Path) -> list[AdapterDetection]:
    """Return all adapter detection outcomes for a path."""

    detections: list[AdapterDetection] = []
    for adapter in list_adapters():
        try:
            can_load = adapter.detect(path)
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


def detect_adapter(root: str | Path) -> DatasetAdapter:
    """Detect exactly one adapter, falling back to generic/folder only if needed."""

    detections = detect_adapters(root)
    matches = [detection.name for detection in detections if detection.can_load]
    specialized = [name for name in matches if name not in _AUTO_FALLBACKS]
    if len(specialized) == 1:
        return get_adapter(specialized[0])
    if len(specialized) > 1:
        raise AdapterDetectionError(
            "Ambiguous dataset adapter detection: " + ", ".join(sorted(specialized)) + "."
        )
    for fallback in ("folder", "generic"):
        if fallback in matches:
            return get_adapter(fallback)
    raise AdapterDetectionError(f"No DatasetLint adapter could load: {Path(root)}")


def select_adapter(root: str | Path, adapter: str | None = None) -> DatasetAdapter:
    """Return explicit adapter or auto-detected adapter."""

    if adapter is None or adapter == "auto":
        return detect_adapter(root)
    return get_adapter(adapter)


def load_dataset(root: str | Path, adapter: str | None = None, **kwargs: object) -> DatasetManifest:
    """Load a normalized manifest with an explicit or detected adapter."""

    selected = select_adapter(root, adapter)
    return selected.load(root, **kwargs)


def validate_dataset(
    root: str | Path, adapter: str | None = None, **kwargs: object
) -> AdapterValidationReport:
    """Validate a dataset using an explicit or detected adapter."""

    selected = select_adapter(root, adapter)
    return selected.validate(root, **kwargs)


def _register_defaults() -> None:
    for adapter_cls in (
        FolderAdapter,
        GenericFolderAdapter,
        CocoAdapter,
        KittiAdapter,
        NuScenesAdapter,
        WaymoAdapter,
        ROSBagAdapter,
        MCAPAdapter,
        HuggingFaceAdapter,
    ):
        register_adapter(adapter_cls)


_register_defaults()
