"""Lint report model and serialisation helpers."""

from __future__ import annotations

import json
from html import escape
from typing import Any

from pydantic import BaseModel, Field

from datasetlint.schemas import Issue, Severity


class LintReport(BaseModel):
    """The result returned by ``lint_dataset``."""

    dataset_path: str
    issues: list[Issue] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)
    passed: bool

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
        adapter = self.stats.get("adapter", {})
        adapter_name = _dict_string(adapter, "name")
        validation_mode = _dict_string(adapter, "validation_mode")
        checks_run = self.stats.get("checks_run", [])
        checks = (
            ", ".join(str(check) for check in checks_run)
            if isinstance(checks_run, list)
            else ""
        )
        fingerprint = self.stats.get("dataset_fingerprint")
        stats_rows = _html_stats_rows(self.stats)
        issue_rows = _html_issue_rows(self.issues)
        config_html = _json_html(self.stats.get("config", {}))
        adapter_html = _json_html(adapter)
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
            "        <tr><th>Dataset path</th><td><code>"
            f"{_html(self.dataset_path)}</code></td></tr>\n"
            "        <tr><th>Status</th><td>"
            f'<span class="status-{status}">{_html(status)}</span></td></tr>\n'
            f"        <tr><th>Errors</th><td>{counts['error']}</td></tr>\n"
            f"        <tr><th>Warnings</th><td>{counts['warning']}</td></tr>\n"
            f"        <tr><th>Info</th><td>{counts['info']}</td></tr>\n"
            f"        <tr><th>Total issues</th><td>{len(self.issues)}</td></tr>\n"
            f"        <tr><th>Checks run</th><td>{_html(checks)}</td></tr>\n"
            f"        <tr><th>Adapter</th><td>{_html(adapter_name)}</td></tr>\n"
            f"        <tr><th>Validation mode</th><td>{_html(validation_mode)}</td></tr>\n"
            "        <tr><th>Dataset fingerprint</th><td><code>"
            f"{_html(fingerprint)}</code></td></tr>\n"
            "      </tbody>\n"
            "    </table>\n"
            "  </section>\n"
            "  <section>\n"
            "    <h2>Adapter Coverage</h2>\n"
            f"    <pre>{adapter_html}</pre>\n"
            "  </section>\n"
            "  <section>\n"
            "    <h2>Config Summary</h2>\n"
            f"    <pre>{config_html}</pre>\n"
            "  </section>\n"
            "  <section>\n"
            "    <h2>Dataset Stats</h2>\n"
            "    <table>\n"
            "      <thead><tr><th>Metric</th><th>Value</th></tr></thead>\n"
            f"      <tbody>\n{stats_rows}"
            "      </tbody>\n"
            "    </table>\n"
            "  </section>\n"
            "  <section>\n"
            "    <h2>Issues</h2>\n"
            "    <table>\n"
            "      <thead><tr><th>Severity</th><th>Check</th><th>File</th><th>Row</th>"
            "<th>Message</th><th>Metadata</th></tr></thead>\n"
            f"      <tbody>\n{issue_rows}"
            "      </tbody>\n"
            "    </table>\n"
            "  </section>\n"
            "</body>\n"
            "</html>\n"
        )

    def _as_dict(self) -> dict[str, Any]:
        if hasattr(self, "model_dump"):
            return self.model_dump()
        return self.dict()


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
    hidden = {
        "adapter",
        "checks_run",
        "config",
        "dataset_fingerprint",
        "issue_count_by_severity",
    }
    rows: list[str] = []
    for key, value in sorted(stats.items()):
        if key in hidden:
            continue
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
