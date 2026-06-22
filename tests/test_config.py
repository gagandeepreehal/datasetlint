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
