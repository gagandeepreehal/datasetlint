from __future__ import annotations

from pathlib import Path

from datasetlint.adapters.rosbag import ROSBagAdapter

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_rosbag_adapter_indexes_ros2_metadata_topics():
    manifest = ROSBagAdapter().load(FIXTURES / "rosbag_index_only")

    assert len(manifest.sequences) == 1
    assert {sensor.sensor_type for sensor in manifest.sensors} == {"camera", "imu"}


def test_rosbag_validation_warns_missing_metadata_yaml(tmp_path):
    (tmp_path / "data.db3").write_text("placeholder", encoding="utf-8")

    report = ROSBagAdapter().validate(tmp_path)

    assert any("Missing metadata.yaml" in warning for warning in report.warnings)
