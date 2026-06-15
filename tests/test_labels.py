from __future__ import annotations

from datasetlint import lint_dataset
from tests.conftest import write_good_dataset


def test_invalid_label_confidence_returns_error(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    (dataset / "labels" / "detections.csv").write_text(
        "\n".join(
            [
                "timestamp,track_id,class,x,y,width,height,confidence",
                "0.1,track-1,car,10,20,50,40,1.5",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = lint_dataset(dataset)

    assert report.passed is False
    assert any(issue.check_name == "check_label_confidence_range" for issue in report.issues)


def test_label_class_switching_returns_warning(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    (dataset / "labels" / "detections.csv").write_text(
        "\n".join(
            [
                "timestamp,track_id,class,x,y,width,height,confidence",
                "0.0,track-1,car,10,20,50,40,0.9",
                "0.1,track-1,pedestrian,12,20,50,40,0.9",
                "0.2,track-1,car,14,20,50,40,0.9",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = lint_dataset(dataset, checks="labels")

    assert any(
        issue.check_name == "check_track_id_consistency" and issue.severity == "warning"
        for issue in report.issues
    )


def test_bounding_box_jump_returns_warning(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    (dataset / "labels" / "detections.csv").write_text(
        "\n".join(
            [
                "timestamp,track_id,class,x,y,width,height,confidence",
                "0.0,track-1,car,10,20,50,40,0.9",
                "0.1,track-1,car,400,20,50,40,0.9",
                "0.2,track-1,car,405,20,50,40,0.9",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = lint_dataset(dataset, checks="labels")

    assert any(issue.check_name == "check_label_bbox_jumps" for issue in report.issues)
