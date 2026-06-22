from __future__ import annotations

import json

from datasetlint.report import LintReport


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
