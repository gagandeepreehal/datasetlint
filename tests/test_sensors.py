from __future__ import annotations

from datasetlint import lint_dataset
from tests.conftest import write_good_dataset


def test_invalid_camera_dimensions_return_error(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    (dataset / "sensors" / "camera_front.csv").write_text(
        "\n".join(
            [
                "timestamp,path,width,height",
                "0.0,images/000001.jpg,0,720",
                "0.1,images/000002.jpg,1280,720",
                "0.2,images/000003.jpg,1280,720",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = lint_dataset(dataset)

    assert report.passed is False
    assert any(issue.check_name == "check_sensor_dimensions" for issue in report.issues)

