from __future__ import annotations

import json
from pathlib import Path

from datasetlint.core import lint_dataset
from datasetlint.report import LintReport
from datasetlint.schemas import make_issue
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


def test_dataset_fingerprint_does_not_read_referenced_payloads(tmp_path, monkeypatch):
    dataset = write_good_dataset(tmp_path / "dataset")
    original_open = Path.open

    def guarded_open(self: Path, *args, **kwargs):
        if self.suffix == ".jpg":
            raise AssertionError("fingerprint should not read image payloads")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)

    report = lint_dataset(dataset)

    assert report.passed is True
    assert report.dataset_fingerprint is not None
    assert report.dataset_fingerprint.startswith("sha256:")


def test_html_report_includes_summary_issue_metadata_and_escapes_values():
    report = LintReport(
        dataset_path="dataset/<unsafe>",
        issues=[
            make_issue(
                "check_<name>",
                "error",
                "bad <script>alert(1)</script>",
                file="labels/<bad>.csv",
                row=3,
                metadata={"key": "<value>"},
            )
        ],
        stats={"issue_count": 1, "sensor_count": 2},
        passed=False,
        dataset_summary={"available_modalities": ["labels"]},
        checks_run=["check_<name>"],
        adapter={"name": "folder", "mode": "folder"},
        config={"timestamp_gap_threshold_sec": 0.5},
        dataset_fingerprint="sha256:abc",
    )

    html = report.to_html()

    assert "<title>DatasetLint Report</title>" in html
    assert "Dataset path" in html
    assert "Adapter mode" in html
    assert "Dataset fingerprint" in html
    assert "Config Summary" in html
    assert "Dataset Summary" in html
    assert "Dataset Stats" in html
    assert "Issues" in html
    assert "&lt;unsafe&gt;" in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "&lt;value&gt;" in html
    assert "<script>alert(1)</script>" not in html


def test_html_report_is_stable_across_generated_at_changes():
    report = LintReport(
        dataset_path="dataset",
        issues=[],
        stats={"issue_count": 0},
        passed=True,
        generated_at="2026-01-01T00:00:00+00:00",
        dataset_summary={"sensor_count": 1},
        checks_run=["check_required_files"],
        adapter={"name": "folder", "mode": "folder"},
        config={"timestamp_gap_threshold_sec": 0.5},
        dataset_fingerprint="sha256:abc",
    )
    later = report.model_copy(update={"generated_at": "2026-01-01T00:00:30+00:00"})

    html = report.to_html()

    assert html == later.to_html()
    assert "Generated at" not in html
