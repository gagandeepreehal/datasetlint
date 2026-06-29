from __future__ import annotations

from pathlib import Path

import datasetlint.adapters.rosbag as rosbag_module
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


def test_rosbag_deep_validation_uses_parser_metadata(monkeypatch):
    def fake_parse(dataset_root: Path, bags: list[Path], *, max_messages: int):
        assert max_messages == 7
        return rosbag_module._ParsedROSBag(
            sequences=[
                rosbag_module.SequenceRecord(
                    sequence_id="rosbag_index_only",
                    name="rosbag_index_only",
                    frame_count=1,
                )
            ],
            frames=[
                rosbag_module.FrameRecord(
                    frame_id="rosbag_index_only:0",
                    sequence_id="rosbag_index_only",
                    timestamp=1.0,
                    sensor_id="/camera/image",
                )
            ],
            sensors=[
                rosbag_module.SensorStream(
                    sensor_id="/camera/image",
                    sensor_type="camera",
                    frame_count=1,
                )
            ],
            metadata={
                "parse_mode": "deep",
                "bag_files": ["rosbag_index_only"],
                "message_count": 1,
                "topics": [
                    {
                        "name": "/camera/image",
                        "msgtype": "sensor_msgs/msg/Image",
                        "message_count": 1,
                    }
                ],
            },
            limitations=["payloads not decoded"],
        )

    monkeypatch.setattr(rosbag_module, "_parse_rosbag_units", fake_parse)

    report = ROSBagAdapter().validate(FIXTURES / "rosbag_index_only", deep=True, max_rows=7)

    assert report.validation_mode == "deep"
    assert report.coverage["topics"] is True
    assert report.coverage["message_timestamps"] is True
    assert report.coverage["common_rule_inputs"]["frames"] is True
    assert "common timestamp consistency" in report.checked
    assert report.stats["message_count"] == 1
    assert report.stats["common_rule_stats"]["frame_count"] == 1


def test_rosbag_deep_parse_failure_is_invalid(monkeypatch):
    def fake_parse(dataset_root: Path, bags: list[Path], *, max_messages: int):
        return rosbag_module._ParsedROSBag(
            sequences=[
                rosbag_module.SequenceRecord(
                    sequence_id="rosbag_index_only",
                    name="rosbag_index_only",
                    frame_count=0,
                )
            ],
            frames=[],
            sensors=[],
            metadata={
                "parse_mode": "deep",
                "bag_files": ["."],
                "message_count": 0,
                "topics": [],
            },
            warnings=["Could not parse .: metadata is invalid."],
            limitations=["payloads not decoded"],
        )

    monkeypatch.setattr(rosbag_module, "_parse_rosbag_units", fake_parse)

    report = ROSBagAdapter().validate(FIXTURES / "rosbag_index_only", deep=True)

    assert report.valid is False
    assert "Could not parse ." in report.errors[0]
