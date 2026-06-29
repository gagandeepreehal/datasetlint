from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from datasetlint.adapters.huggingface import HuggingFaceAdapter, _annotations_from_row

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_huggingface_adapter_indexes_cache_like_dataset():
    manifest = HuggingFaceAdapter().load(FIXTURES / "hf_cache_like")

    assert manifest.dataset_name == "hf_cache_like"
    assert {sensor.sensor_id for sensor in manifest.sensors} >= {"image", "label", "caption"}


def test_huggingface_validation_runs_common_manifest_rules():
    report = HuggingFaceAdapter().validate(FIXTURES / "hf_cache_like")

    assert report.valid is True
    assert report.coverage["common_rule_inputs"]["sensors"] is True
    assert "common sensor links" in report.checked
    assert report.stats["common_rule_stats"]["sensor_count"] >= 3


def test_huggingface_row_labels_decode_to_common_annotations():
    annotations = _annotations_from_row(
        {"image": object(), "label": 3, "bbox": [0, 0, 10, 10]},
        frame_id="0",
        sequence_id="train",
    )

    assert {annotation.annotation_type for annotation in annotations} == {"bbox", "label"}
    assert {annotation.frame_id for annotation in annotations} == {"0"}


def test_huggingface_validation_reports_missing_dependency_for_remote():
    if importlib.util.find_spec("datasets") is not None:
        pytest.skip("datasets is installed; missing-dependency path is environment-specific")
    report = HuggingFaceAdapter().validate("hf://namespace/dataset", split="train")

    assert report.valid is False
    assert any("datasets dependency missing" in error for error in report.errors)
