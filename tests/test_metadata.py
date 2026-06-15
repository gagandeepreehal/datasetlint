from __future__ import annotations

import json

from datasetlint import lint_dataset
from tests.conftest import write_good_dataset


def test_invalid_metadata_schema_returns_error(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    metadata = json.loads((dataset / "metadata.json").read_text(encoding="utf-8"))
    metadata["sensors"] = "camera_front"
    (dataset / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    report = lint_dataset(dataset)

    assert report.passed is False
    assert any(issue.check_name == "check_metadata_schema" for issue in report.issues)


def test_duration_mismatch_returns_warning(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    metadata = json.loads((dataset / "metadata.json").read_text(encoding="utf-8"))
    metadata["duration_sec"] = 10.0
    (dataset / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    report = lint_dataset(dataset)

    assert any(
        issue.check_name == "check_duration_matches_timestamps"
        and issue.severity == "warning"
        for issue in report.issues
    )


def test_missing_dataset_version_returns_warning(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    metadata = json.loads((dataset / "metadata.json").read_text(encoding="utf-8"))
    metadata.pop("version")
    (dataset / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    report = lint_dataset(dataset)

    assert any(
        issue.check_name == "check_dataset_version_present" and issue.severity == "warning"
        for issue in report.issues
    )
