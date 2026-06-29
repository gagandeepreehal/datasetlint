"""Lint report model and serialisation helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from html import escape
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

    def to_html(self) -> str:
        counts = self.count_by_severity()
        status = "passed" if self.passed else "failed"
        checks = ", ".join(self.checks_run)
        adapter_name = _dict_string(self.adapter, "name")
        adapter_mode = _dict_string(self.adapter, "mode")
        return (
            "<!doctype html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '  <meta charset="utf-8">\n'
            '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
            "  <title>DatasetLint Report</title>\n"
            "  <style>\n"
            "    body { font-family: system-ui, -apple-system, Segoe UI, sans-serif; "
            "margin: 2rem; color: #17202a; }\n"
            "    h1, h2 { margin-bottom: 0.4rem; }\n"
            "    table { border-collapse: collapse; width: 100%; margin: 1rem 0; }\n"
            "    th, td { border: 1px solid #d6dde5; padding: 0.5rem; "
            "text-align: left; vertical-align: top; }\n"
            "    th { background: #f3f6f8; }\n"
            "    code, pre { background: #f6f8fa; border-radius: 4px; }\n"
            "    code { padding: 0.1rem 0.25rem; }\n"
            "    pre { padding: 0.75rem; overflow-x: auto; }\n"
            "    .status-passed { color: #0b6b3a; font-weight: 700; }\n"
            "    .status-failed { color: #a11919; font-weight: 700; }\n"
            "  </style>\n"
            "</head>\n"
            "<body>\n"
            "  <h1>DatasetLint Report</h1>\n"
            "  <section>\n"
            "    <h2>Summary</h2>\n"
            "    <table>\n"
            "      <tbody>\n"
            f"        <tr><th>Dataset path</th><td><code>{_html(self.dataset_path)}</code></td></tr>\n"
            "        <tr><th>Status</th><td>"
            f'<span class="status-{status}">{_html(status)}</span></td></tr>\n'
            f"        <tr><th>Total issues</th><td>{len(self.issues)}</td></tr>\n"
            f"        <tr><th>Errors</th><td>{counts['error']}</td></tr>\n"
            f"        <tr><th>Warnings</th><td>{counts['warning']}</td></tr>\n"
            f"        <tr><th>Info</th><td>{counts['info']}</td></tr>\n"
            f"        <tr><th>Checks run</th><td>{_html(checks)}</td></tr>\n"
            f"        <tr><th>Adapter</th><td>{_html(adapter_name)}</td></tr>\n"
            f"        <tr><th>Adapter mode</th><td>{_html(adapter_mode)}</td></tr>\n"
            "        <tr><th>Dataset fingerprint</th><td><code>"
            f"{_html(self.dataset_fingerprint)}</code></td></tr>\n"
            f"        <tr><th>Generated at</th><td><code>{_html(self.generated_at)}</code></td></tr>\n"
            f"        <tr><th>DatasetLint version</th><td><code>{_html(self.datasetlint_version)}</code></td></tr>\n"
            "      </tbody>\n"
            "    </table>\n"
            "  </section>\n"
            "  <section>\n"
            "    <h2>Config Summary</h2>\n"
            f"    <pre>{_json_html(self.config)}</pre>\n"
            "  </section>\n"
            "  <section>\n"
            "    <h2>Dataset Summary</h2>\n"
            f"    <pre>{_json_html(self.dataset_summary)}</pre>\n"
            "  </section>\n"
            "  <section>\n"
            "    <h2>Dataset Stats</h2>\n"
            "    <table>\n"
            "      <thead><tr><th>Metric</th><th>Value</th></tr></thead>\n"
            f"      <tbody>\n{_html_stats_rows(self.stats)}"
            "      </tbody>\n"
            "    </table>\n"
            "  </section>\n"
            "  <section>\n"
            "    <h2>Issues</h2>\n"
            "    <table>\n"
            "      <thead><tr><th>Severity</th><th>Check</th><th>File</th><th>Row</th>"
            "<th>Message</th><th>Metadata</th></tr></thead>\n"
            f"      <tbody>\n{_html_issue_rows(self.issues)}"
            "      </tbody>\n"
            "    </table>\n"
            "  </section>\n"
            "</body>\n"
            "</html>\n"
        )

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


def _html(value: object) -> str:
    if value is None:
        return ""
    return escape(str(value), quote=True)


def _json_html(value: Any) -> str:
    return escape(json.dumps(value, indent=2, sort_keys=True, default=str), quote=False)


def _dict_string(value: Any, key: str) -> str:
    if not isinstance(value, dict):
        return ""
    item = value.get(key)
    return "" if item is None else str(item)


def _html_stats_rows(stats: dict[str, Any]) -> str:
    rows: list[str] = []
    for key, value in sorted(stats.items()):
        rows.append(
            "        <tr>"
            f"<td><code>{_html(key)}</code></td>"
            f"<td><pre>{_json_html(value)}</pre></td>"
            "</tr>\n"
        )
    if not rows:
        rows.append('        <tr><td colspan="2">No dataset stats available.</td></tr>\n')
    return "".join(rows)


def _html_issue_rows(issues: list[Issue]) -> str:
    if not issues:
        return (
            "        <tr><td>info</td><td><code>none</code></td><td></td><td></td>"
            "<td>No issues found.</td><td><code>{}</code></td></tr>\n"
        )
    rows: list[str] = []
    for issue in issues:
        row = "" if issue.row is None else str(issue.row)
        rows.append(
            "        <tr>"
            f"<td>{_html(issue.severity)}</td>"
            f"<td><code>{_html(issue.check_name)}</code></td>"
            f"<td>{_html(issue.file)}</td>"
            f"<td>{_html(row)}</td>"
            f"<td>{_html(issue.message)}</td>"
            f"<td><pre>{_json_html(issue.metadata)}</pre></td>"
            "</tr>\n"
        )
    return "".join(rows)


def should_fail(report: LintReport, fail_on: Severity) -> bool:
    counts = report.count_by_severity()
    if fail_on == "error":
        return counts["error"] > 0
    if fail_on == "warning":
        return counts["error"] > 0 or counts["warning"] > 0
    return len(report.issues) > 0
