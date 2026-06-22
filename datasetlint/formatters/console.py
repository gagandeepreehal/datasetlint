"""Rich console report formatter."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from datasetlint.report import LintReport


def print_report(report: LintReport, console: Console | None = None) -> None:
    output = console or Console()
    counts = report.count_by_severity()
    output.print(report.summary())
    table = Table(title="Issues")
    table.add_column("Severity")
    table.add_column("Check", no_wrap=True, min_width=28)
    table.add_column("File")
    table.add_column("Row", justify="right")
    table.add_column("Message")
    if not report.issues:
        table.add_row("info", "none", "", "", "No issues found.")
    else:
        for issue in report.issues:
            style = {"error": "red", "warning": "yellow", "info": "cyan"}[issue.severity]
            table.add_row(
                f"[{style}]{issue.severity}[/{style}]",
                issue.check_name,
                issue.file or "",
                "" if issue.row is None else str(issue.row),
                issue.message,
            )
    output.print(table)
    output.print(
        f"errors={counts['error']} warnings={counts['warning']} info={counts['info']}"
    )
