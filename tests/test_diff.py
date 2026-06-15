from __future__ import annotations

from datasetlint.diff import compare_datasets
from tests.conftest import write_good_dataset


def test_diff_report_generation(tmp_path):
    old_dataset = write_good_dataset(tmp_path / "old")
    new_dataset = write_good_dataset(tmp_path / "new")
    (new_dataset / "sensors" / "lidar.csv").write_text(
        "timestamp\n0.0\n0.1\n0.2\n",
        encoding="utf-8",
    )

    report = compare_datasets(old_dataset, new_dataset)

    assert any(change.category == "sensors" and change.name == "lidar" for change in report.changes)
    assert any(change.name == "lidar" for change in report.improvements)


def test_diff_regression_detection(tmp_path):
    old_dataset = write_good_dataset(tmp_path / "old")
    new_dataset = write_good_dataset(tmp_path / "new")
    (new_dataset / "sensors" / "camera_front.csv").write_text(
        "\n".join(
            [
                "timestamp,path,width,height",
                "0.0,images/000001.jpg,1280,720",
                "0.1,images/000002.jpg,1280,720",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = compare_datasets(old_dataset, new_dataset)

    assert any(
        change.category == "frame_counts" and change.name == "camera_front"
        for change in report.regressions
    )
