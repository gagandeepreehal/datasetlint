from __future__ import annotations

import json
from pathlib import Path

import pytest

from datasetlint.adapters import (
    AdapterDetectionError,
    DatasetManifest,
    detect_adapter,
    list_adapters,
    load_dataset,
    select_adapter,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_list_adapters_returns_expected_defaults():
    names = {adapter.name for adapter in list_adapters()}

    assert {
        "generic",
        "coco",
        "kitti",
        "nuscenes",
        "waymo",
        "rosbag",
        "mcap",
        "huggingface",
    }.issubset(names)


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [
        ("generic_dataset", "generic"),
        ("coco_dataset", "coco"),
        ("kitti_object", "kitti"),
        ("kitti_odometry", "kitti"),
        ("nuscenes_mini_like", "nuscenes"),
        ("waymo_index_only", "waymo"),
        ("rosbag_index_only", "rosbag"),
        ("mcap_index_only", "mcap"),
        ("hf_cache_like", "huggingface"),
    ],
)
def test_detect_adapter_for_fixtures(fixture: str, expected: str):
    assert detect_adapter(FIXTURES / fixture).name == expected


def test_ambiguous_detection_raises_clear_error(tmp_path):
    (tmp_path / "log.mcap").write_text("placeholder", encoding="utf-8")
    (tmp_path / "log.bag").write_text("placeholder", encoding="utf-8")

    with pytest.raises(AdapterDetectionError, match="Ambiguous dataset adapter detection"):
        detect_adapter(tmp_path)


def test_explicit_adapter_overrides_detection():
    adapter = select_adapter(FIXTURES / "coco_dataset", "generic")

    assert adapter.name == "generic"


@pytest.mark.parametrize(
    ("fixture", "adapter"),
    [
        ("generic_dataset", "generic"),
        ("coco_dataset", "coco"),
        ("kitti_object", "kitti"),
        ("kitti_odometry", "kitti"),
        ("nuscenes_mini_like", "nuscenes"),
        ("waymo_index_only", "waymo"),
        ("rosbag_index_only", "rosbag"),
        ("mcap_index_only", "mcap"),
        ("hf_cache_like", "huggingface"),
    ],
)
def test_each_adapter_loads_json_serializable_manifest(fixture: str, adapter: str):
    manifest = load_dataset(FIXTURES / fixture, adapter=adapter)

    assert isinstance(manifest, DatasetManifest)
    assert manifest.adapter_name == adapter
    assert json.loads(manifest.to_json())["adapter_name"] == adapter
