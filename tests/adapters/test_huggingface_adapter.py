from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

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
    assert report.validation_mode == "index-level"
    assert report.coverage["index_only"] is True
    assert report.coverage["common_rule_inputs"]["sensors"] is True
    assert "common sensor links" in report.checked
    assert report.stats["common_rule_stats"]["sensor_count"] >= 3


def test_huggingface_deep_validation_reports_sample_payload_diagnostics(monkeypatch):
    rows = [
        {"id": "same", "image": object(), "label": 1, "bbox": [0, 0, 10, 10]},
        {"id": "same", "image": object(), "label": "free", "bbox": [1, 2, 3]},
    ]

    class FakeDataset:
        features = {
            "image": {"_type": "Image"},
            "label": {"_type": "ClassLabel"},
            "bbox": {"feature": "Sequence"},
        }

        def __len__(self) -> int:
            return len(rows)

        def select(self, indexes):
            return [rows[index] for index in indexes]

    def fake_load_dataset(dataset_id: str, *, split: str, streaming: bool):
        assert dataset_id == "namespace/dataset"
        assert split == "train"
        assert streaming is False
        return FakeDataset()

    monkeypatch.setattr(importlib.util, "find_spec", lambda name: object())
    monkeypatch.setitem(
        sys.modules,
        "datasets",
        SimpleNamespace(load_dataset=fake_load_dataset),
    )

    report = HuggingFaceAdapter().validate(
        "hf://namespace/dataset", split="train", deep=True, max_rows=2
    )

    assert report.validation_mode == "deep"
    assert report.valid is False
    assert report.coverage["row_payloads"] is True
    assert report.coverage["bbox_payloads"] is True
    assert report.coverage["common_rule_inputs"]["frames"] is True
    assert "Hugging Face deep payload diagnostics" in report.checked
    assert report.stats["duplicate_sample_id_count"] == 1
    assert report.stats["invalid_bbox_count"] == 1
    assert any("Duplicate Hugging Face sample id" in error for error in report.errors)
    assert any("not a numeric [x, y, width, height]" in error for error in report.errors)


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


def test_huggingface_deep_validation_requires_datasets_dependency(monkeypatch):
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)

    report = HuggingFaceAdapter().validate("hf://namespace/dataset", split="train", deep=True)

    assert report.valid is False
    assert report.validation_mode == "deep"
    assert any("run deep Hugging Face row diagnostics" in error for error in report.errors)
