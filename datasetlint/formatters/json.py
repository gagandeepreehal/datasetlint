"""JSON report formatter."""

from datasetlint.report import LintReport


def format_report(report: LintReport) -> str:
    return report.to_json()

