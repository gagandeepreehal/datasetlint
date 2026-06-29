from __future__ import annotations

import json

from datasetlint.report import LintReport
from datasetlint.schemas import make_issue


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


def test_html_report_escapes_issue_content_and_includes_metadata():
    report = LintReport(
        dataset_path="dataset/<bad>",
        issues=[
            make_issue(
                "check_<name>",
                "error",
                "bad <script>",
                file="labels/detections.csv",
                row=2,
                metadata={"track_id": "car|1"},
            )
        ],
        stats={
            "issue_count": 1,
            "issue_count_by_severity": {"info": 0, "warning": 0, "error": 1},
            "checks_run": ["check_<name>"],
            "adapter": {
                "name": "folder",
                "validation_mode": "deep",
                "checked": ["metadata"],
                "not_checked": ["pixels"],
                "limitations": [],
            },
            "dataset_fingerprint": "sha256:abc",
            "config": {"timestamp_gap_threshold_sec": 0.5},
        },
        passed=False,
    )

    html = report.to_html()

    assert "<!doctype html>" in html
    assert "DatasetLint Report" in html
    assert "dataset/&lt;bad&gt;" in html
    assert "bad &lt;script&gt;" in html
    assert "check_&lt;name&gt;" in html
    assert '"validation_mode": "deep"' in html
    assert "sha256:abc" in html
