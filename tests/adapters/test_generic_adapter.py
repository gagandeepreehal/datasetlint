from __future__ import annotations

from datasetlint.adapters.generic import GenericFolderAdapter


def test_generic_adapter_validation_catches_timestamp_mismatch(tmp_path):
    dataset = tmp_path / "generic"
    (dataset / "images").mkdir(parents=True)
    (dataset / "images" / "a.jpg").write_text("placeholder", encoding="utf-8")
    (dataset / "images" / "b.jpg").write_text("placeholder", encoding="utf-8")
    (dataset / "timestamps.csv").write_text("frame_id,timestamp\na,0.0\n", encoding="utf-8")

    report = GenericFolderAdapter().validate(dataset)

    assert report.valid is True
    assert any("Timestamp count mismatch" in warning for warning in report.warnings)


def test_generic_adapter_validation_catches_broken_annotation_path(tmp_path):
    dataset = tmp_path / "generic"
    dataset.mkdir()
    (dataset / "annotations.json").write_text(
        '{"annotations": [{"id": "a", "path": "missing.jpg"}]}',
        encoding="utf-8",
    )

    report = GenericFolderAdapter().validate(dataset)

    assert any("Broken relative annotation paths" in warning for warning in report.warnings)
