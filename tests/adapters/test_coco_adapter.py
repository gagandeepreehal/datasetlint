from __future__ import annotations

from datasetlint.adapters.coco import CocoAdapter


def test_coco_adapter_validation_catches_missing_image(tmp_path):
    annotations = tmp_path / "annotations"
    annotations.mkdir()
    (annotations / "instances_train2017.json").write_text(
        '{"images": [{"id": 1, "file_name": "missing.jpg"}], '
        '"annotations": [{"id": 2, "image_id": 1, "category_id": 3, "bbox": [0, 0, 1, 1]}], '
        '"categories": [{"id": 3, "name": "car"}]}',
        encoding="utf-8",
    )

    report = CocoAdapter().validate(tmp_path)

    assert report.valid is False
    assert any("Missing image file" in error for error in report.errors)


def test_coco_adapter_validation_catches_invalid_bbox(tmp_path):
    annotations = tmp_path / "annotations"
    annotations.mkdir()
    (tmp_path / "image.jpg").write_text("placeholder", encoding="utf-8")
    (annotations / "instances_train2017.json").write_text(
        '{"images": [{"id": 1, "file_name": "image.jpg"}], '
        '"annotations": [{"id": 2, "image_id": 1, "category_id": 3, "bbox": [0, 0, 0, 1]}], '
        '"categories": [{"id": 3, "name": "car"}]}',
        encoding="utf-8",
    )

    report = CocoAdapter().validate(tmp_path)

    assert report.valid is False
    assert any("Invalid bbox dimensions" in error for error in report.errors)
