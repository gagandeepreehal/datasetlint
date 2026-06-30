from __future__ import annotations

from pathlib import Path

from datasetlint.adapters.argoverse2 import Argoverse2Adapter

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_argoverse2_adapter_indexes_sensor_log():
    manifest = Argoverse2Adapter().load(FIXTURES / "argoverse2_sensor")

    assert manifest.adapter_name == "argoverse2"
    assert len(manifest.sequences) == 1
    assert {sensor.sensor_type for sensor in manifest.sensors} == {"camera", "lidar"}
    assert {frame.timestamp for frame in manifest.frames} == {0.0, 0.1}
    assert manifest.annotations
    assert manifest.calibration


def test_argoverse2_validation_reports_manifest_scope():
    report = Argoverse2Adapter().validate(FIXTURES / "argoverse2_sensor")

    assert report.valid is True
    assert report.coverage["frames"] is True
    assert "common timestamp consistency" in report.checked
    assert not any("median sync gap" in warning for warning in report.warnings)
    assert report.stats["frame_count"] == 3
