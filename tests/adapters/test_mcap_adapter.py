from __future__ import annotations

from pathlib import Path

import datasetlint.adapters.mcap as mcap_module
from datasetlint.adapters.mcap import MCAPAdapter

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_mcap_adapter_indexes_files():
    manifest = MCAPAdapter().load(FIXTURES / "mcap_index_only")

    assert len(manifest.sequences) == 1
    assert manifest.metadata["files"][0]["path"] == "log.mcap"


def test_mcap_validation_warns_for_empty_file(tmp_path):
    (tmp_path / "empty.mcap").write_text("", encoding="utf-8")

    report = MCAPAdapter().validate(tmp_path)

    assert any("empty MCAP" in warning for warning in report.warnings)


def test_mcap_deep_validation_uses_parser_metadata(monkeypatch):
    def fake_parse(dataset_root: Path, files: list[Path], *, max_messages: int):
        assert max_messages == 5
        return mcap_module._ParsedMCAP(
            sequences=[
                mcap_module.SequenceRecord(
                    sequence_id="log",
                    name="log.mcap",
                    frame_count=1,
                )
            ],
            frames=[
                mcap_module.FrameRecord(
                    frame_id="log:0",
                    sequence_id="log",
                    timestamp=1.0,
                    sensor_id="/camera/image",
                )
            ],
            sensors=[
                mcap_module.SensorStream(
                    sensor_id="/camera/image",
                    sensor_type="camera",
                    frame_count=1,
                )
            ],
            metadata={
                "parse_mode": "deep",
                "message_count": 1,
                "channels": [{"id": 1, "topic": "/camera/image"}],
                "schemas": [{"id": 1, "name": "sensor_msgs/Image"}],
            },
            limitations=["payloads not decoded"],
        )

    monkeypatch.setattr(mcap_module, "_parse_mcap_files", fake_parse)

    report = MCAPAdapter().validate(FIXTURES / "mcap_index_only", deep=True, max_rows=5)

    assert report.validation_mode == "deep"
    assert report.coverage["channels"] is True
    assert report.coverage["message_timestamps"] is True
    assert report.coverage["common_rule_inputs"]["frames"] is True
    assert "common timestamp consistency" in report.checked
    assert report.stats["message_count"] == 1
    assert report.stats["common_rule_stats"]["frame_count"] == 1


def test_mcap_deep_parse_failure_is_invalid(monkeypatch):
    def fake_parse(dataset_root: Path, files: list[Path], *, max_messages: int):
        return mcap_module._ParsedMCAP(
            sequences=[
                mcap_module.SequenceRecord(
                    sequence_id="log",
                    name="log.mcap",
                    frame_count=0,
                )
            ],
            frames=[],
            sensors=[],
            metadata={
                "parse_mode": "deep",
                "message_count": 0,
                "channels": [],
                "schemas": [],
            },
            warnings=["Could not parse log.mcap: not a valid MCAP file."],
            limitations=["payloads not decoded"],
        )

    monkeypatch.setattr(mcap_module, "_parse_mcap_files", fake_parse)

    report = MCAPAdapter().validate(FIXTURES / "mcap_index_only", deep=True)

    assert report.valid is False
    assert "Could not parse log.mcap" in report.errors[0]


def test_mcap_deep_validation_reports_topic_desync(monkeypatch):
    def fake_parse(dataset_root: Path, files: list[Path], *, max_messages: int):
        return mcap_module._ParsedMCAP(
            sequences=[
                mcap_module.SequenceRecord(
                    sequence_id="log",
                    name="log.mcap",
                    frame_count=4,
                )
            ],
            frames=[
                mcap_module.FrameRecord(
                    frame_id="log:0",
                    sequence_id="log",
                    timestamp=1.0,
                    sensor_id="/camera/image",
                ),
                mcap_module.FrameRecord(
                    frame_id="log:1",
                    sequence_id="log",
                    timestamp=2.0,
                    sensor_id="/camera/image",
                ),
                mcap_module.FrameRecord(
                    frame_id="log:2",
                    sequence_id="log",
                    timestamp=1.2,
                    sensor_id="/imu",
                ),
                mcap_module.FrameRecord(
                    frame_id="log:3",
                    sequence_id="log",
                    timestamp=2.2,
                    sensor_id="/imu",
                ),
            ],
            sensors=[
                mcap_module.SensorStream(
                    sensor_id="/camera/image",
                    sensor_type="camera",
                    frame_count=2,
                ),
                mcap_module.SensorStream(
                    sensor_id="/imu",
                    sensor_type="imu",
                    frame_count=2,
                ),
            ],
            metadata={
                "parse_mode": "deep",
                "message_count": 4,
                "channels": [{"id": 1, "topic": "/camera/image"}, {"id": 2, "topic": "/imu"}],
                "schemas": [{"id": 1, "name": "sensor_msgs/Image"}],
            },
            limitations=["payloads not decoded"],
        )

    monkeypatch.setattr(mcap_module, "_parse_mcap_files", fake_parse)

    report = MCAPAdapter().validate(FIXTURES / "mcap_index_only", deep=True)

    assert any(
        "/camera/image and /imu median sync gap" in warning and "Fix:" in warning
        for warning in report.warnings
    )
