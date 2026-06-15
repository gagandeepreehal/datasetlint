"""Command-line interface for DatasetLint."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Annotated

import typer

from datasetlint.core import lint_dataset
from datasetlint.formatters.console import print_report
from datasetlint.report import should_fail

app = typer.Typer(add_completion=False, help="Validate robotics and Physical AI datasets.")


class OutputFormat(str, Enum):
    console = "console"
    json = "json"
    markdown = "markdown"


class FailLevel(str, Enum):
    error = "error"
    warning = "warning"
    info = "info"


@app.command()
def main(
    path: Annotated[Path, typer.Argument(help="Dataset folder to lint.")],
    format: Annotated[OutputFormat, typer.Option("--format", "-f")] = OutputFormat.console,
    fail_on: Annotated[FailLevel, typer.Option("--fail-on")] = FailLevel.error,
    config: Annotated[
        Path | None,
        typer.Option("--config", help="Optional datasetlint.yaml path."),
    ] = None,
) -> None:
    report = lint_dataset(path=path, config=config)
    if format is OutputFormat.json:
        typer.echo(report.to_json())
    elif format is OutputFormat.markdown:
        typer.echo(report.to_markdown())
    else:
        print_report(report)
    if should_fail(report, fail_on.value):
        raise typer.Exit(1)
