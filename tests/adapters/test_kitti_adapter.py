from __future__ import annotations

from pathlib import Path

from datasetlint.adapters.kitti import KittiAdapter

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_kitti_object_loads_camera_lidar_labels_and_calib():
    manifest = KittiAdapter().load(FIXTURES / "kitti_object")

    assert {sensor.sensor_type for sensor in manifest.sensors} == {"camera", "lidar"}
    assert len({frame.frame_id for frame in manifest.frames}) == len(manifest.frames)
    assert len(manifest.annotations) == 1
    assert manifest.annotations[0].frame_id in {frame.frame_id for frame in manifest.frames}
    assert len(manifest.calibration) == 1


def test_kitti_validation_accepts_complete_fixtures():
    for fixture in ("kitti_object", "kitti_odometry"):
        report = KittiAdapter().validate(FIXTURES / fixture)

        assert report.valid is True
        assert not any("Duplicate frame id" in error for error in report.errors)
        assert not any("Missing calibration" in warning for warning in report.warnings)


def test_kitti_validation_catches_invalid_label_row(tmp_path):
    (tmp_path / "image_2").mkdir()
    (tmp_path / "label_2").mkdir()
    (tmp_path / "image_2" / "000000.png").write_text("placeholder", encoding="utf-8")
    (tmp_path / "label_2" / "000000.txt").write_text("Car 0 0\n", encoding="utf-8")

    report = KittiAdapter().validate(tmp_path)

    assert report.valid is False
    assert any("Invalid KITTI label row length" in error for error in report.errors)
