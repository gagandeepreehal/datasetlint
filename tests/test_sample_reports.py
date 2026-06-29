from __future__ import annotations

import json
import re
from pathlib import Path

from datasetlint.core import lint_dataset
from datasetlint.report import LintReport

REPORTS_DIR = Path("examples/reports")


def test_minimal_sample_report_matches_generated_report():
    committed = json.loads((REPORTS_DIR / "minimal_report.json").read_text(encoding="utf-8"))
    generated = json.loads(_sample_report("examples/minimal_dataset").to_json())

    assert _without_generated_at(committed) == _without_generated_at(generated)


def test_bad_sample_report_json_matches_generated_report():
    committed = json.loads((REPORTS_DIR / "bad_report.json").read_text(encoding="utf-8"))
    generated = json.loads(_sample_report("examples/bad_dataset").to_json())

    assert _without_generated_at(committed) == _without_generated_at(generated)


def test_bad_sample_report_markdown_matches_generated_report():
    committed = (REPORTS_DIR / "bad_report.md").read_text(encoding="utf-8")
    generated = _sample_report("examples/bad_dataset").to_markdown()

    assert _normalize_generated_at(committed) == _normalize_generated_at(generated)


def _sample_report(path: str) -> LintReport:
    report = lint_dataset(path)
    return report.model_copy(update={"dataset_path": path})


def _without_generated_at(payload: dict[str, object]) -> dict[str, object]:
    normalized = dict(payload)
    normalized.pop("generated_at", None)
    return normalized


def _normalize_generated_at(markdown: str) -> str:
    return re.sub(r"- Generated at: `[^`]+`", "- Generated at: `<generated-at>`", markdown)
