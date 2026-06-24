from __future__ import annotations

from datasetlint import lint_dataset
from tests.conftest import write_good_dataset


def test_good_dataset_returns_passed(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")

    report = lint_dataset(dataset)

    assert report.passed is True
    assert report.count_by_severity() == {"info": 0, "warning": 0, "error": 0}


def test_missing_metadata_returns_error(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    (dataset / "metadata.json").unlink()

    report = lint_dataset(dataset)

    assert report.passed is False
    assert any(issue.check_name == "check_required_files" for issue in report.issues)


def test_broken_image_path_returns_error(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    (dataset / "sensors" / "camera_front.csv").write_text(
        "\n".join(
            [
                "timestamp,path,width,height",
                "0.0,images/missing.jpg,1280,720",
                "0.1,images/000002.jpg,1280,720",
                "0.2,images/000003.jpg,1280,720",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = lint_dataset(dataset)

    assert report.passed is False
    assert any(issue.check_name == "check_broken_paths" for issue in report.issues)
