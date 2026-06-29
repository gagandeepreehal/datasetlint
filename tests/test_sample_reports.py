from __future__ import annotations

import json
from pathlib import Path

from datasetlint import lint_dataset


def test_sample_reports_match_current_api_outputs(monkeypatch):
    repo = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(repo)

    minimal_report = lint_dataset("examples/minimal_dataset")
    bad_report = lint_dataset("examples/bad_dataset")
    reports_dir = repo / "examples" / "reports"

    assert json.loads((reports_dir / "minimal_report.json").read_text(encoding="utf-8")) == (
        json.loads(minimal_report.to_json())
    )
    assert json.loads((reports_dir / "bad_report.json").read_text(encoding="utf-8")) == (
        json.loads(bad_report.to_json())
    )
    assert (reports_dir / "bad_report.md").read_text(encoding="utf-8") == (
        bad_report.to_markdown()
    )
