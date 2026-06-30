from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

import datasetlint.adapters.mcap as mcap_module
from datasetlint.cli import app

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_cli_adapters_list_works():
    result = CliRunner().invoke(app, ["adapters", "list", "--format", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert {item["name"] for item in payload} >= {"generic", "coco", "kitti"}


def test_cli_adapters_detect_works():
    result = CliRunner().invoke(
        app, ["adapters", "detect", str(FIXTURES / "coco_dataset"), "--format", "json"]
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["selected"] == "coco"


def test_cli_inspect_works():
    result = CliRunner().invoke(
        app,
        ["inspect", str(FIXTURES / "kitti_object"), "--adapter", "kitti", "--format", "json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["adapter_name"] == "kitti"
    assert payload["sensors"]


def test_cli_validate_works():
    result = CliRunner().invoke(
        app,
        [
            "validate",
            str(FIXTURES / "nuscenes_mini_like"),
            "--adapter",
            "nuscenes",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["valid"] is True
    assert payload["validation_mode"] == "manifest-level"
    assert payload["checked"]
    assert payload["not_checked"]
    assert payload["limitations"]
    assert payload["coverage"]["common_rule_inputs"]["frames"] is True


def test_cli_validate_deep_adapter_mode(monkeypatch):
    def fake_parse(dataset_root: Path, files: list[Path], *, max_messages: int):
        assert max_messages == 2
        return mcap_module._ParsedMCAP(
            sequences=[mcap_module.SequenceRecord(sequence_id="log", name="log.mcap")],
            frames=[
                mcap_module.FrameRecord(
                    frame_id="log:0",
                    sequence_id="log",
                    timestamp=1.0,
                    sensor_id="/imu",
                )
            ],
            sensors=[
                mcap_module.SensorStream(
                    sensor_id="/imu",
                    sensor_type="imu",
                    frame_count=1,
                )
            ],
            metadata={
                "parse_mode": "deep",
                "message_count": 1,
                "channels": [{"topic": "/imu"}],
                "schemas": [{"name": "sensor_msgs/Imu"}],
            },
            limitations=["payloads not decoded"],
        )

    monkeypatch.setattr(mcap_module, "_parse_mcap_files", fake_parse)

    result = CliRunner().invoke(
        app,
        [
            "validate",
            str(FIXTURES / "mcap_index_only"),
            "--adapter",
            "mcap",
            "--deep",
            "--max-rows",
            "2",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["validation_mode"] == "deep"
    assert payload["coverage"]["message_timestamps"] is True
    assert payload["coverage"]["common_rule_inputs"]["frames"] is True
    assert "common timestamp consistency" in payload["checked"]


def test_cli_validate_json_exits_nonzero_when_invalid(tmp_path):
    annotations = tmp_path / "annotations"
    annotations.mkdir()
    (annotations / "instances_train2017.json").write_text(
        '{"images": [{"id": 1, "file_name": "missing.jpg"}], '
        '"annotations": [{"id": 2, "image_id": 1, "category_id": 3, '
        '"bbox": [0, 0, 1, 1]}], '
        '"categories": [{"id": 3, "name": "car"}]}',
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        ["validate", str(tmp_path), "--adapter", "coco", "--format", "json"],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["valid"] is False
    assert any("Missing image file" in error for error in payload["errors"])


def test_cli_validate_json_reports_missing_deep_dependency(monkeypatch):
    def fake_reader():
        raise mcap_module.AdapterDependencyError(
            "Deep MCAP parsing requires the optional mcap package."
        )

    monkeypatch.setattr(mcap_module, "_mcap_make_reader", fake_reader)

    result = CliRunner().invoke(
        app,
        [
            "validate",
            str(FIXTURES / "mcap_index_only"),
            "--adapter",
            "mcap",
            "--deep",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["adapter_name"] == "mcap"
    assert payload["detected"] is True
    assert payload["valid"] is False
    assert payload["validation_mode"] == "deep"
    assert "Deep MCAP parsing requires" in payload["errors"][0]


def test_cli_validate_markdown_exits_nonzero_when_invalid(tmp_path):
    annotations = tmp_path / "annotations"
    annotations.mkdir()
    (annotations / "instances_train2017.json").write_text(
        '{"images": [{"id": 1, "file_name": "missing.jpg"}], '
        '"annotations": [{"id": 2, "image_id": 1, "category_id": 3, '
        '"bbox": [0, 0, 1, 1]}], '
        '"categories": [{"id": 3, "name": "car"}]}',
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        ["validate", str(tmp_path), "--adapter", "coco", "--format", "markdown"],
    )

    assert result.exit_code == 1
    assert "- valid: `False`" in result.stdout
    assert "- validation_mode: `manifest-level`" in result.stdout
    assert "- checked:" in result.stdout
    assert "- not_checked:" in result.stdout
    assert "- limitations:" in result.stdout
    assert "Missing image file" in result.stdout


def test_cli_export_manifest_writes_json(tmp_path):
    output = tmp_path / "manifest.json"

    result = CliRunner().invoke(
        app,
        [
            "export-manifest",
            str(FIXTURES / "coco_dataset"),
            "--adapter",
            "coco",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["adapter_name"] == "coco"
