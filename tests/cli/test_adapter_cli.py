from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

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
