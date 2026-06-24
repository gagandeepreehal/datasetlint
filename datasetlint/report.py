"""Lint report model and serialisation helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from datasetlint._version import __version__
from datasetlint.schemas import Issue, Severity


class LintReport(BaseModel):
    """The result returned by ``lint_dataset``."""

    dataset_path: str
    issues: list[Issue] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)
    passed: bool
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    )
    dataset_summary: dict[str, Any] = Field(default_factory=dict)
    checks_run: list[str] = Field(default_factory=list)
    adapter: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)
    dataset_fingerprint: str | None = None
    datasetlint_version: str = __version__

    def count_by_severity(self) -> dict[str, int]:
        counts = {"info": 0, "warning": 0, "error": 0}
        for issue in self.issues:
            counts[issue.severity] += 1
        return counts

    def summary(self) -> str:
        counts = self.count_by_severity()
        status = "passed" if self.passed else "failed"
        total = len(self.issues)
        return (
            f"DatasetLint report for {self.dataset_path}: {status} with {total} issue(s) "
            f"(error={counts['error']}, warning={counts['warning']}, info={counts['info']})."
        )

    def to_json(self) -> str:
        return json.dumps(self._as_dict(), indent=2, sort_keys=True)

    def to_markdown(self) -> str:
        counts = self.count_by_severity()
        lines = [
            "# DatasetLint Report",
            "",
            f"- Dataset: `{self.dataset_path}`",
            f"- Status: `{'passed' if self.passed else 'failed'}`",
            f"- Generated at: `{self.generated_at}`",
            f"- DatasetLint version: `{self.datasetlint_version}`",
            f"- Dataset fingerprint: `{self.dataset_fingerprint or ''}`",
            f"- Errors: `{counts['error']}`",
            f"- Warnings: `{counts['warning']}`",
            f"- Info: `{counts['info']}`",
            "",
        ]
        if self.stats:
            lines.extend(["## Stats", ""])
            for key, value in sorted(self.stats.items()):
                lines.extend(_format_markdown_stat(key, value))
            lines.append("")
        lines.extend(
            [
                "## Issues",
                "",
                "| Severity | Check | File | Row | Message |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        if not self.issues:
            lines.append("| info | none |  |  | No issues found. |")
        else:
            for issue in self.issues:
                lines.append(
                    "| {severity} | `{check}` | {file} | {row} | {message} |".format(
                        severity=issue.severity,
                        check=_escape_markdown(issue.check_name),
                        file=_escape_markdown(issue.file or ""),
                        row="" if issue.row is None else issue.row,
                        message=_escape_markdown(issue.message),
                    )
                )
        return "\n".join(lines) + "\n"

    def _as_dict(self) -> dict[str, Any]:
        if hasattr(self, "model_dump"):
            data = self.model_dump()
        else:
            data = self.dict()
        data["findings"] = data["issues"]
        return data


def _escape_markdown(value: str) -> str:
    return value.replace("|", "\\|")


def _format_markdown_stat(key: str, value: Any) -> list[str]:
    if isinstance(value, dict | list):
        return [
            f"- `{_escape_markdown(key)}`:",
            "",
            "```json",
            json.dumps(value, indent=2, sort_keys=True, default=str),
            "```",
        ]
    return [f"- `{_escape_markdown(key)}`: `{json.dumps(value, sort_keys=True, default=str)}`"]


def should_fail(report: LintReport, fail_on: Severity) -> bool:
    counts = report.count_by_severity()
    if fail_on == "error":
        return counts["error"] > 0
    if fail_on == "warning":
        return counts["error"] > 0 or counts["warning"] > 0
    return len(report.issues) > 0
