from __future__ import annotations

from datasetlint import lint_dataset
from tests.conftest import write_good_dataset


def test_unrealistic_speed_returns_warning(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    (dataset / "trajectories" / "ego.csv").write_text(
        "\n".join(
            [
                "timestamp,x,y,yaw,vx,vy",
                "0.0,0.0,0.0,0.0,10.0,0.0",
                "0.1,1.0,0.0,0.0,100.0,0.0",
                "0.2,2.0,0.0,0.0,10.0,0.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = lint_dataset(dataset)

    assert any(
        issue.check_name == "check_unrealistic_speed" and issue.severity == "warning"
        for issue in report.issues
    )

