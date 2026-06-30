from __future__ import annotations

import pytest

from datasetlint import lint_dataset
from datasetlint.schemas import LintConfig
from tests.conftest import write_good_dataset


def test_dataset_yaml_config_overrides_thresholds(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    (dataset / "datasetlint.yaml").write_text("max_speed_mps: 150\n", encoding="utf-8")
    (dataset / "trajectories" / "ego.csv").write_text(
        "\n".join(
            [
                "timestamp,x,y,yaw,vx,vy",
                "0.0,0.0,0.0,0.0,100.0,0.0",
                "0.1,10.0,0.0,0.0,100.0,0.0",
                "0.2,20.0,0.0,0.0,100.0,0.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = lint_dataset(dataset)

    assert not any(issue.check_name == "check_unrealistic_speed" for issue in report.issues)


def test_config_rejects_removed_timestamp_gap_key(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    (dataset / "datasetlint.yaml").write_text("max_timestamp_gap_sec: 1.0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="max_timestamp_gap_sec"):
        lint_dataset(dataset, checks="sync")


def test_config_dict_rejects_removed_timestamp_gap_key():
    with pytest.raises(ValueError, match="max_timestamp_gap_sec"):
        LintConfig(max_timestamp_gap_sec=1.0)


def test_yaml_config_can_enable_specific_groups(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    (dataset / "datasetlint.yaml").write_text(
        "\n".join(
            [
                "rules:",
                "  enabled:",
                "    - calibration",
                "    - labels",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = lint_dataset(dataset)

    assert report.checks_run
    assert set(report.checks_run).issubset(
        {
            "check_calibration_exists",
            "check_intrinsics_shape",
            "check_intrinsics_values",
            "check_extrinsics_shape",
            "check_quaternion_norm",
            "check_label_columns",
            "check_label_confidence_range",
            "check_label_geometry",
            "check_label_timestamps_match_sensor_range",
            "check_track_id_consistency",
            "check_label_bbox_jumps",
            "check_label_missing_timestamps",
            "check_duplicate_track_id_timestamp",
            "check_short_tracks",
            "check_label_size_changes",
        }
    )
    assert "check_sensor_frequency" not in report.checks_run


def test_yaml_config_can_disable_single_rule(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    (dataset / "datasetlint.yaml").write_text(
        "\n".join(
            [
                "expected_sensor_rates:",
                "  camera_front: 1000.0",
                "rules:",
                "  disabled:",
                "    - check_sensor_frequency",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = lint_dataset(dataset, checks="sensors")

    assert "check_sensor_frequency" not in report.checks_run
    assert not any(issue.check_name == "check_sensor_frequency" for issue in report.issues)


def test_yaml_config_can_override_rule_severity(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    (dataset / "sensors" / "camera_front.csv").write_text(
        "\n".join(
            [
                "timestamp,path,width,height",
                "0.0,images/000001.jpg,640,480",
                "2.0,images/000002.jpg,640,480",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (dataset / "datasetlint.yaml").write_text(
        "\n".join(
            [
                "rules:",
                "  severity:",
                "    check_large_timestamp_gaps: info",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = lint_dataset(dataset, checks="timestamps")
    issue = next(
        issue for issue in report.issues if issue.check_name == "check_large_timestamp_gaps"
    )

    assert issue.severity == "info"
    assert issue.metadata["original_severity"] == "warning"
    assert report.count_by_severity()["info"] == 1
