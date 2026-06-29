from __future__ import annotations

from pathlib import Path

import datasetlint.adapters.waymo as waymo_module
from datasetlint.adapters.waymo import WaymoAdapter

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_waymo_adapter_indexes_tfrecords():
    manifest = WaymoAdapter().load(FIXTURES / "waymo_index_only")

    assert len(manifest.sequences) == 1
    assert manifest.limitations


def test_waymo_validation_catches_duplicate_segment_names(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "segment-1.tfrecord").write_text("a", encoding="utf-8")
    (tmp_path / "b" / "segment-1.tfrecord").write_text("b", encoding="utf-8")

    report = WaymoAdapter().validate(tmp_path)

    assert report.valid is False
    assert any("Duplicate segment names" in error for error in report.errors)


def test_waymo_index_validation_does_not_claim_parsed_frames_or_sensors():
    report = WaymoAdapter().validate(FIXTURES / "waymo_index_only")

    assert report.validation_mode == "index-level"
    assert report.coverage["index_only"] is True
    assert report.coverage["frames"] is False
    assert report.coverage["sensors"] is False
    assert report.coverage["common_rule_inputs"]["frames"] is False
    assert report.coverage["common_rule_inputs"]["sensors"] is False
    assert report.stats["frame_count"] == 0
    assert report.stats["sensor_count"] == 0
    assert report.stats["common_rule_stats"]["frame_count"] == 0
    assert report.stats["common_rule_stats"]["sensor_count"] == 0


def test_waymo_deep_validation_uses_parser_metadata(monkeypatch):
    def fake_parse(dataset_root: Path, files: list[Path], *, max_frames: int):
        assert max_frames == 3
        return waymo_module._ParsedWaymo(
            sequences=[
                waymo_module.SequenceRecord(
                    sequence_id="segment-000001",
                    name="segment-000001",
                    frame_count=1,
                )
            ],
            frames=[
                waymo_module.FrameRecord(
                    frame_id="context:1000",
                    sequence_id="segment-000001",
                    timestamp=0.001,
                    sensor_id="camera_1",
                )
            ],
            sensors=[
                waymo_module.SensorStream(
                    sensor_id="camera_1",
                    sensor_type="camera",
                    frame_count=1,
                )
            ],
            annotations=[
                waymo_module.AnnotationRecord(
                    annotation_id="label-1",
                    frame_id="context:1000",
                    annotation_type="waymo_camera_label",
                )
            ],
            calibration=[
                waymo_module.CalibrationRecord(
                    sensor_id="camera_1",
                    intrinsic=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                )
            ],
            metadata={
                "parse_mode": "deep",
                "tfrecord_files": ["segment-000001.tfrecord"],
                "frame_count": 1,
                "annotation_count": 1,
                "calibration_count": 1,
            },
            limitations=["payloads not decoded"],
        )

    monkeypatch.setattr(waymo_module, "_parse_waymo_files", fake_parse)

    report = WaymoAdapter().validate(FIXTURES / "waymo_index_only", deep=True, max_rows=3)

    assert report.validation_mode == "deep"
    assert report.coverage["index_only"] is False
    assert report.coverage["annotations"] is True
    assert report.coverage["calibration"] is True
    assert report.coverage["common_rule_inputs"]["frames"] is True
    assert "common timestamp consistency" in report.checked
    assert report.stats["frame_count"] == 1
    assert report.stats["common_rule_stats"]["frame_count"] == 1


def test_waymo_deep_parse_failure_is_invalid(monkeypatch):
    def fake_parse(dataset_root: Path, files: list[Path], *, max_frames: int):
        return waymo_module._ParsedWaymo(
            sequences=[
                waymo_module.SequenceRecord(
                    sequence_id="segment-000001",
                    name="segment-000001",
                    frame_count=0,
                )
            ],
            frames=[],
            sensors=[],
            annotations=[],
            calibration=[],
            metadata={
                "parse_mode": "deep",
                "tfrecord_files": ["segment-000001.tfrecord"],
                "frame_count": 0,
                "annotation_count": 0,
                "calibration_count": 0,
            },
            warnings=["Could not parse segment-000001.tfrecord: invalid TFRecord."],
            limitations=["payloads not decoded"],
        )

    monkeypatch.setattr(waymo_module, "_parse_waymo_files", fake_parse)

    report = WaymoAdapter().validate(FIXTURES / "waymo_index_only", deep=True)

    assert report.valid is False
    assert "Could not parse segment-000001.tfrecord" in report.errors[0]
    assert report.warnings == []
