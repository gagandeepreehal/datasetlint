"""Dataset adapter public API."""

from __future__ import annotations

from pathlib import Path

from datasetlint.adapters.base import (
    AdapterDetection,
    AdapterInfo,
    AdapterProvenance,
    AdapterValidationReport,
    AnnotationRecord,
    CalibrationRecord,
    DatasetAdapter,
    DatasetManifest,
    DatasetMetadata,
    FrameRecord,
    SensorInfo,
    SensorStream,
    SequenceRecord,
)
from datasetlint.adapters.coco import CocoAdapter
from datasetlint.adapters.errors import (
    AdapterDependencyError,
    AdapterDetectionError,
    AdapterError,
    AdapterNotFoundError,
    AdapterValidationError,
    UnsupportedDatasetFeature,
)
from datasetlint.adapters.folder import FolderAdapter
from datasetlint.adapters.generic import GenericFolderAdapter
from datasetlint.adapters.huggingface import HuggingFaceAdapter
from datasetlint.adapters.kitti import KittiAdapter
from datasetlint.adapters.mcap import MCAPAdapter
from datasetlint.adapters.nuscenes import NuScenesAdapter
from datasetlint.adapters.registry import (
    available_adapters,
    detect_adapter,
    detect_adapters,
    list_adapter_info,
    list_adapters,
    load_dataset,
    register_adapter,
    select_adapter,
    validate_dataset,
)
from datasetlint.adapters.registry import get_adapter as get_adapter_by_name
from datasetlint.adapters.rosbag import ROSBagAdapter
from datasetlint.adapters.waymo import WaymoAdapter


def get_adapter(path_or_name: str | Path, name: str | None = None) -> DatasetAdapter:
    """Return an adapter by name or use the legacy ``get_adapter(path, name)`` form."""

    candidate = str(path_or_name)
    registered_names = {adapter.name for adapter in list_adapters()}
    if name is None:
        if candidate.lower() in registered_names:
            return get_adapter_by_name(candidate)
        return select_adapter(path_or_name, "auto")
    return select_adapter(path_or_name, name)


__all__ = [
    "AdapterDependencyError",
    "AdapterDetection",
    "AdapterDetectionError",
    "AdapterError",
    "AdapterInfo",
    "AdapterNotFoundError",
    "AdapterProvenance",
    "AdapterValidationError",
    "AdapterValidationReport",
    "AnnotationRecord",
    "CalibrationRecord",
    "CocoAdapter",
    "DatasetAdapter",
    "DatasetManifest",
    "DatasetMetadata",
    "FolderAdapter",
    "FrameRecord",
    "GenericFolderAdapter",
    "HuggingFaceAdapter",
    "KittiAdapter",
    "MCAPAdapter",
    "NuScenesAdapter",
    "ROSBagAdapter",
    "SensorInfo",
    "SensorStream",
    "SequenceRecord",
    "UnsupportedDatasetFeature",
    "WaymoAdapter",
    "available_adapters",
    "detect_adapter",
    "detect_adapters",
    "get_adapter",
    "get_adapter_by_name",
    "list_adapter_info",
    "list_adapters",
    "load_dataset",
    "register_adapter",
    "select_adapter",
    "validate_dataset",
]
