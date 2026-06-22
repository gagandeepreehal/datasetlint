from __future__ import annotations

import datasetlint
from datasetlint import lint_dataset
from datasetlint.checks import timestamps


def test_package_exposes_version():
    assert datasetlint.__version__ == "0.1.0"


def test_timestamp_module_does_not_export_duplicate_sync_checks():
    assert not hasattr(timestamps, "check_sensor_time_overlap")
    assert not hasattr(timestamps, "check_sensor_frequency_stability")


def test_lint_dataset_invalid_checks_returns_error_report():
    report = lint_dataset("examples/minimal_dataset", checks="nonexistent")

    assert report.passed is False
    assert report.issues[0].check_name == "select_checks"
    assert report.issues[0].severity == "error"
    assert "Unknown check group 'nonexistent'. Valid groups:" in report.issues[0].message
