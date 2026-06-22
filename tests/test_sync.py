from __future__ import annotations

from datasetlint import lint_dataset
from tests.conftest import write_good_dataset


def test_pairwise_sync_gap_returns_warning(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    (dataset / "sensors" / "lidar.csv").write_text(
        "\n".join(
            [
                "timestamp",
                "0.03",
                "0.13",
                "0.23",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = lint_dataset(
        dataset,
        checks="sync",
        config={"max_pairwise_sync_gap_sec": 0.01},
    )

    assert any(issue.check_name == "check_pairwise_sync_gap" for issue in report.issues)


def test_missing_frame_burst_returns_warning(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    (dataset / "sensors" / "camera_front.csv").write_text(
        "\n".join(
            [
                "timestamp,path,width,height",
                "0.0,images/000001.jpg,1280,720",
                "0.1,images/000002.jpg,1280,720",
                "1.0,images/000003.jpg,1280,720",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = lint_dataset(dataset, checks="sync")

    assert any(issue.check_name == "check_missing_frame_bursts" for issue in report.issues)


def test_missing_frame_burst_uses_timestamp_gap_threshold(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    (dataset / "sensors" / "camera_front.csv").write_text(
        "\n".join(
            [
                "timestamp,path,width,height",
                "0.0,images/000001.jpg,1280,720",
                "0.1,images/000002.jpg,1280,720",
                "0.9,images/000003.jpg,1280,720",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = lint_dataset(
        dataset,
        checks="sync",
        config={"timestamp_gap_threshold_sec": 1.0},
    )

    assert not any(issue.check_name == "check_missing_frame_bursts" for issue in report.issues)


def test_default_checks_do_not_double_report_sensor_timestamp_gap(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    (dataset / "sensors" / "camera_front.csv").write_text(
        "\n".join(
            [
                "timestamp,path,width,height",
                "0.0,images/000001.jpg,1280,720",
                "0.1,images/000002.jpg,1280,720",
                "1.0,images/000003.jpg,1280,720",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    reports = [
        lint_dataset(dataset),
        lint_dataset(dataset, checks="timestamps,sync"),
    ]

    for report in reports:
        assert any(issue.check_name == "check_large_timestamp_gaps" for issue in report.issues)
        assert not any(
            issue.check_name == "check_missing_frame_bursts" for issue in report.issues
        )
