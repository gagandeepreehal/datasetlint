"""Command-line interface for DatasetLint."""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Annotated, NoReturn

import typer
from rich.console import Console
from rich.table import Table

from datasetlint._version import __version__
from datasetlint.adapters import detect_adapters
from datasetlint.core import lint_dataset, validate_checks
from datasetlint.diff import DatasetDiffReport, compare_datasets
from datasetlint.formatters.console import print_report
from datasetlint.report import should_fail
from datasetlint.stats import DatasetStats, compute_dataset_stats

app = typer.Typer(add_completion=False, help="Validate robotics and Physical AI datasets.")


class OutputFormat(str, Enum):
    console = "console"
    json = "json"
    markdown = "markdown"


class FailLevel(str, Enum):
    error = "error"
    warning = "warning"
    info = "info"


def _version_callback(value: bool | None) -> None:
    if value:
        typer.echo(f"datasetlint {__version__}")
        raise typer.Exit()


@app.command()
def main(
    args: Annotated[
        list[str],
        typer.Argument(
            help=(
                "Dataset path, or one of: lint DATASET, report DATASET, stats DATASET, "
                "diff OLD NEW, adapters DATASET."
            )
        ),
    ],
    format: Annotated[OutputFormat, typer.Option("--format", "-f")] = OutputFormat.console,
    fail_on: Annotated[FailLevel, typer.Option("--fail-on")] = FailLevel.error,
    config: Annotated[
        Path | None,
        typer.Option("--config", help="Optional datasetlint.yaml path."),
    ] = None,
    checks: Annotated[
        str | None,
        typer.Option("--checks", help="Comma-separated check groups such as labels or sync."),
    ] = None,
    adapter: Annotated[
        str,
        typer.Option("--adapter", help="Dataset adapter name: folder or auto."),
    ] = "folder",
    out: Annotated[
        Path | None,
        typer.Option("--out", help="Write a JSON report to this path for report command."),
    ] = None,
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show DatasetLint version and exit.",
        ),
    ] = None,
    fail_on_regression: Annotated[
        bool,
        typer.Option("--fail-on-regression", help="Exit non-zero when diff regressions exist."),
    ] = False,
) -> None:
    del version
    if not args:
        _usage_error(
            "Provide a dataset path, lint DATASET, report DATASET, stats DATASET, "
            "diff OLD NEW, or adapters DATASET."
        )

    command = args[0]
    if command == "lint":
        _run_lint(args[1:], config, checks, adapter, format, fail_on)
        return
    if command == "report":
        _run_report(args[1:], config, checks, adapter, out)
        return
    if command == "stats":
        _run_stats(args[1:], config, format)
        return
    if command == "diff":
        _run_diff(args[1:], config, format, fail_on_regression)
        return
    if command == "adapters":
        _run_adapters(args[1:], format)
        return

    if len(args) != 1:
        _usage_error("Lint expects one dataset path.")
    _run_lint(args, config, checks, adapter, format, fail_on)


def _run_lint(
    args: list[str],
    config: Path | None,
    checks: str | None,
    adapter: str,
    format: OutputFormat,
    fail_on: FailLevel,
) -> None:
    if len(args) != 1:
        _usage_error("lint expects one dataset path.")
    try:
        validate_checks(checks)
    except ValueError as exc:
        _usage_error(str(exc))
    try:
        report = lint_dataset(path=Path(args[0]), config=config, checks=checks, adapter=adapter)
    except ValueError as exc:
        _usage_error(str(exc))
    if format is OutputFormat.json:
        typer.echo(report.to_json())
    elif format is OutputFormat.markdown:
        typer.echo(report.to_markdown())
    else:
        print_report(report)
    if should_fail(report, fail_on.value):
        raise typer.Exit(1)


def _run_report(
    args: list[str],
    config: Path | None,
    checks: str | None,
    adapter: str,
    out: Path | None,
) -> None:
    if len(args) != 1:
        _usage_error("report expects one dataset path.")
    if out is None:
        _usage_error("report requires --out REPORT.json.")
    try:
        validate_checks(checks)
    except ValueError as exc:
        _usage_error(str(exc))
    try:
        report = lint_dataset(path=Path(args[0]), config=config, checks=checks, adapter=adapter)
    except ValueError as exc:
        _usage_error(str(exc))
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report.to_json() + "\n", encoding="utf-8")
    except OSError as exc:
        _usage_error(f"Could not write report to {out}: {exc}.")
    typer.echo(f"Wrote JSON report to {out}")
    if not report.passed:
        raise typer.Exit(1)


def _run_stats(args: list[str], config: Path | None, format: OutputFormat) -> None:
    if len(args) != 1:
        _usage_error("stats expects one dataset path.")
    try:
        stats = compute_dataset_stats(Path(args[0]), config=config)
    except ValueError as exc:
        _usage_error(str(exc))
    if format is OutputFormat.json:
        typer.echo(stats.to_json())
    elif format is OutputFormat.markdown:
        typer.echo(stats.to_markdown())
    else:
        _print_stats(stats)


def _run_diff(
    args: list[str],
    config: Path | None,
    format: OutputFormat,
    fail_on_regression: bool,
) -> None:
    if len(args) != 2:
        _usage_error("diff expects OLD_DATASET and NEW_DATASET paths.")
    try:
        report = compare_datasets(Path(args[0]), Path(args[1]), config=config)
    except ValueError as exc:
        _usage_error(str(exc))
    if format is OutputFormat.json:
        typer.echo(report.to_json())
    elif format is OutputFormat.markdown:
        typer.echo(report.to_markdown())
    else:
        _print_diff(report)
    if fail_on_regression and report.regressions:
        raise typer.Exit(1)


def _run_adapters(args: list[str], format: OutputFormat) -> None:
    if len(args) != 1:
        _usage_error("adapters expects one dataset path.")
    detections = detect_adapters(Path(args[0]))
    if format is OutputFormat.json:
        typer.echo(json.dumps([detection.model_dump() for detection in detections], indent=2))
    elif format is OutputFormat.markdown:
        lines = [
            "# DatasetLint Adapters",
            "",
            "| Adapter | Detected | Message |",
            "| --- | --- | --- |",
        ]
        for detection in detections:
            lines.append(f"| {detection.name} | `{detection.can_load}` | {detection.message} |")
        typer.echo("\n".join(lines) + "\n")
    else:
        console = Console()
        table = Table(title="Dataset Adapters")
        table.add_column("Adapter")
        table.add_column("Detected")
        table.add_column("Message")
        for detection in detections:
            table.add_row(detection.name, str(detection.can_load), detection.message)
        console.print(table)


def _print_stats(stats: DatasetStats) -> None:
    console = Console()
    console.print(f"DatasetLint stats for {stats.dataset_path}")
    console.print(f"duration_sec={stats.duration_sec} sensors={len(stats.sensors)}")
    table = Table(title="Sensors")
    table.add_column("Sensor")
    table.add_column("Frames", justify="right")
    table.add_column("Rate Hz", justify="right")
    table.add_column("Missing Frames", justify="right")
    for sensor in stats.sensors:
        rate = stats.inferred_rates_hz.get(sensor)
        table.add_row(
            sensor,
            str(stats.frame_counts.get(sensor, 0)),
            "" if rate is None else f"{rate:.3f}",
            str(stats.missing_frame_counts.get(sensor, 0)),
        )
    console.print(table)
    console.print(f"label_class_counts={stats.label_class_counts}")
    console.print(f"issue_summary={stats.issue_summary}")


def _print_diff(report: DatasetDiffReport) -> None:
    console = Console()
    console.print(
        "DatasetLint diff: "
        f"changes={len(report.changes)} regressions={len(report.regressions)} "
        f"improvements={len(report.improvements)}"
    )
    table = Table(title="Changes")
    table.add_column("Severity")
    table.add_column("Category")
    table.add_column("Name")
    table.add_column("Delta")
    table.add_column("Message")
    if not report.changes:
        table.add_row("info", "none", "none", "", "No differences found.")
    else:
        for change in report.changes:
            table.add_row(
                change.severity,
                change.category,
                change.name,
                str(change.delta),
                change.message,
            )
    console.print(table)


def _usage_error(message: str) -> NoReturn:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(2)
