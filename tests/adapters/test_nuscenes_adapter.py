from __future__ import annotations

import json
import shutil
import struct
from pathlib import Path

from datasetlint.adapters.nuscenes import NuScenesAdapter

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_nuscenes_adapter_loads_metadata_tables():
    manifest = NuScenesAdapter().load(FIXTURES / "nuscenes_mini_like")

    assert manifest.version == "v1.0-mini"
    assert len(manifest.sequences) == 1
    assert len(manifest.frames) == 2
    assert {sensor.sensor_type for sensor in manifest.sensors} == {"camera", "lidar"}


def test_nuscenes_validation_runs_common_manifest_rules():
    report = NuScenesAdapter().validate(FIXTURES / "nuscenes_mini_like")

    assert report.valid is True
    assert report.coverage["common_rule_inputs"]["frames"] is True
    assert report.coverage["common_rule_inputs"]["calibration"] is True
    assert "common sensor sync summary" in report.checked
    assert report.stats["common_rule_stats"]["frame_count"] == 2


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


def test_nuscenes_deep_validation_reports_payload_diagnostics(tmp_path):
    dataset = _copy_nuscenes_fixture(tmp_path)
    (dataset / "v1.0-mini" / "samples" / "CAM_FRONT" / "000001.jpg").write_bytes(
        _jpeg_header(width=640, height=480)
    )
    (dataset / "v1.0-mini" / "samples" / "LIDAR_TOP" / "000001.bin").write_bytes(
        struct.pack("<5f", 1.0, 2.0, 3.0, 4.0, 5.0)
    )

    report = NuScenesAdapter().validate(dataset, deep=True, max_rows=10)

    assert report.valid is True
    assert report.validation_mode == "deep"
    assert report.coverage["payload_metadata"] is True
    assert report.coverage["camera_payload_headers"] is True
    assert report.coverage["lidar_payload_points"] is True
    assert report.coverage["common_rule_inputs"]["frames"] is True
    assert "nuScenes deep payload diagnostics" in report.checked
    assert "common timestamp consistency" in report.checked
    assert report.stats["payload_sample_count"] == 2
    assert report.stats["camera_image_payload_count"] == 1
    assert report.stats["lidar_payload_count"] == 1
    assert report.stats["invalid_payload_count"] == 0


def test_nuscenes_deep_validation_catches_malformed_payloads(tmp_path):
    dataset = _copy_nuscenes_fixture(tmp_path)
    (dataset / "v1.0-mini" / "samples" / "CAM_FRONT" / "000001.jpg").write_bytes(
        b"not an image"
    )
    (dataset / "v1.0-mini" / "samples" / "LIDAR_TOP" / "000001.bin").write_bytes(b"bad")

    report = NuScenesAdapter().validate(dataset, deep=True)

    assert report.valid is False
    assert report.validation_mode == "deep"
    assert report.coverage["payload_metadata"] is True
    assert report.coverage["camera_payload_headers"] is False
    assert report.coverage["lidar_payload_points"] is False
    assert report.stats["invalid_payload_count"] == 2
    assert any(
        "camera file does not expose a recognized image header" in error
        for error in report.errors
    )
    assert any("lidar payload size 3 is not divisible" in error for error in report.errors)


def test_nuscenes_validation_checks_sample_and_ego_pose_links(tmp_path):
    dataset = _copy_nuscenes_fixture(tmp_path)
    sample_data_path = dataset / "v1.0-mini" / "sample_data.json"
    sample_data = json.loads(sample_data_path.read_text(encoding="utf-8"))
    sample_data[0]["ego_pose_token"] = "missing-ego-pose"
    sample_data[1]["sample_token"] = "missing-sample"
    sample_data_path.write_text(json.dumps(sample_data), encoding="utf-8")

    report = NuScenesAdapter().validate(dataset)

    assert report.valid is False
    assert any(
        "references missing ego_pose missing-ego-pose" in error
        for error in report.errors
    )
    assert any("references missing sample missing-sample" in error for error in report.errors)


def _copy_nuscenes_fixture(tmp_path: Path) -> Path:
    target = tmp_path / "nuscenes_mini_like"
    shutil.copytree(FIXTURES / "nuscenes_mini_like", target)
    return target


def _jpeg_header(*, width: int, height: int) -> bytes:
    return (
        b"\xff\xd8"
        b"\xff\xc0"
        b"\x00\x11"
        b"\x08"
        + height.to_bytes(2, "big")
        + width.to_bytes(2, "big")
        + b"\x03\x01\x11\x00\x02\x11\x00\x03\x11\x00"
        b"\xff\xd9"
    )
