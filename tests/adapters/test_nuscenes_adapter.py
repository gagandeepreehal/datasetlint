from __future__ import annotations

from pathlib import Path

from datasetlint.adapters.nuscenes import NuScenesAdapter

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_nuscenes_adapter_loads_metadata_tables():
    manifest = NuScenesAdapter().load(FIXTURES / "nuscenes_mini_like")

    assert manifest.version == "v1.0-mini"
    assert len(manifest.sequences) == 1
    assert len(manifest.frames) == 2
    assert {sensor.sensor_type for sensor in manifest.sensors} == {"camera", "lidar"}


def test_nuscenes_validation_catches_missing_sample_data_file(tmp_path):
    source = FIXTURES / "nuscenes_mini_like" / "v1.0-mini"
    target = tmp_path / "v1.0-mini"
    target.mkdir(parents=True)
    for filename in (
        "scene.json",
        "sample.json",
        "sample_data.json",
        "calibrated_sensor.json",
        "sensor.json",
        "ego_pose.json",
    ):
        (target / filename).write_text(
            (source / filename).read_text(encoding="utf-8"), encoding="utf-8"
        )

    report = NuScenesAdapter().validate(tmp_path)

    assert report.valid is False
    assert any("Missing sample_data file" in error for error in report.errors)
