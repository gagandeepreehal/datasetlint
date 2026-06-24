from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from datasetlint.adapters.huggingface import HuggingFaceAdapter

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_huggingface_adapter_indexes_cache_like_dataset():
    manifest = HuggingFaceAdapter().load(FIXTURES / "hf_cache_like")

    assert manifest.dataset_name == "hf_cache_like"
    assert {sensor.sensor_id for sensor in manifest.sensors} >= {"image", "label", "caption"}


def test_huggingface_validation_reports_missing_dependency_for_remote():
    if importlib.util.find_spec("datasets") is not None:
        pytest.skip("datasets is installed; missing-dependency path is environment-specific")
    report = HuggingFaceAdapter().validate("hf://namespace/dataset", split="train")

    assert report.valid is False
    assert any("datasets dependency missing" in error for error in report.errors)
