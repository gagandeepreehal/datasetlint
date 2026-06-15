from __future__ import annotations

from datasetlint import lint_dataset
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

