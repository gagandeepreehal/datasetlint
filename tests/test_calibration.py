from __future__ import annotations

import json

from datasetlint import lint_dataset
from tests.conftest import write_good_dataset


def test_malformed_calibration_returns_error(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    calibration = json.loads((dataset / "calibration.json").read_text(encoding="utf-8"))
    calibration["camera_front"]["intrinsics"] = [[1000, 0], [0, 1000]]
    (dataset / "calibration.json").write_text(json.dumps(calibration), encoding="utf-8")

    report = lint_dataset(dataset)

    assert report.passed is False
    assert any(issue.check_name == "check_intrinsics_shape" for issue in report.issues)

