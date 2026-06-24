from __future__ import annotations

from pathlib import Path

from datasetlint.adapters.waymo import WaymoAdapter

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_waymo_adapter_indexes_tfrecords():
    manifest = WaymoAdapter().load(FIXTURES / "waymo_index_only")

    assert len(manifest.sequences) == 1
    assert manifest.limitations


def test_waymo_validation_catches_duplicate_segment_names(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "segment-1.tfrecord").write_text("a", encoding="utf-8")
    (tmp_path / "b" / "segment-1.tfrecord").write_text("b", encoding="utf-8")

    report = WaymoAdapter().validate(tmp_path)

    assert report.valid is False
    assert any("Duplicate segment names" in error for error in report.errors)
