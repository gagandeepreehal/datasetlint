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

