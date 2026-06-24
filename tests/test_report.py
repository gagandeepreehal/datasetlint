from __future__ import annotations

import json
from pathlib import Path

from datasetlint.core import lint_dataset
from datasetlint.report import LintReport
from tests.conftest import write_good_dataset


def test_markdown_formats_nested_stats_as_json_block():
    report = LintReport(
        dataset_path="dataset",
        issues=[],
        stats={"sync": {"sensors": {"camera_front": {"start_time": 0.0}}}},
        passed=True,
    )

    markdown = report.to_markdown()

    assert "'sensors':" not in markdown
    assert "- `sync`:\n\n```json\n" in markdown
    json_block = markdown.split("```json\n", 1)[1].split("\n```", 1)[0]
    assert json.loads(json_block) == {"sensors": {"camera_front": {"start_time": 0.0}}}


def test_report_json_matches_committed_schema_required_fields(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    report = lint_dataset(dataset)
    payload = json.loads(report.to_json())
    schema = json.loads(Path("schemas/report.schema.json").read_text(encoding="utf-8"))

    for field in schema["required"]:
        assert field in payload
    assert payload["findings"] == payload["issues"]
    assert payload["dataset_summary"]["available_modalities"]
    assert payload["dataset_fingerprint"].startswith("sha256:")
