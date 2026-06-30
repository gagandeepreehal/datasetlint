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


def test_argoverse2_adapter_detects_logs_under_split_directories(tmp_path: Path):
    log_dir = tmp_path / "train" / "log_001"
    lidar_dir = log_dir / "sensors" / "lidar"
    lidar_dir.mkdir(parents=True)
    (lidar_dir / "1000000000000000000.feather").touch()

    adapter = Argoverse2Adapter()
    manifest = adapter.load(tmp_path)

    assert adapter.can_load(tmp_path) is True
    assert [sequence.sequence_id for sequence in manifest.sequences] == ["train/log_001"]
    assert manifest.frames[0].file_path == (
        "train/log_001/sensors/lidar/1000000000000000000.feather"
    )
