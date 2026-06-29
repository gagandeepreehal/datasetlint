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
from datasetlint.adapters import (
    AdapterError,
    AdapterValidationReport,
    DatasetManifest,
    detect_adapter,
    detect_adapters,
    list_adapter_info,
    load_dataset,
    validate_dataset,
)
from datasetlint.core import lint_dataset, validate_checks
from datasetlint.diff import DatasetDiffReport, compare_datasets
from datasetlint.formatters.console import print_report
from datasetlint.report import LintReport, should_fail
from datasetlint.stats import DatasetStats, compute_dataset_stats

app = typer.Typer(add_completion=False, help="Validate robotics and Physical AI datasets.")


class OutputFormat(str, Enum):
    console = "console"
    json = "json"
    markdown = "markdown"
    html = "html"


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
                "diff OLD NEW, adapters list|detect DATASET, inspect DATASET, validate DATASET, "
                "export-manifest DATASET."
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
        typer.Option(
            "--adapter", help="Dataset adapter name, such as folder, generic, coco, or auto."
        ),
    ] = "folder",
    auto_detect: Annotated[
        bool,
        typer.Option("--auto-detect", help="Auto-detect adapter for adapter manifest commands."),
    ] = False,
    split: Annotated[
        str | None,
        typer.Option("--split", help="Optional split for adapters such as Hugging Face."),
    ] = None,
    streaming: Annotated[
        bool,
        typer.Option("--streaming", help="Use streaming mode when supported by the adapter."),
    ] = False,
    deep: Annotated[
        bool,
        typer.Option(
            "--deep",
            help=(
                "Use optional parser-backed validation for MCAP, ROS bag, and Waymo "
                "when dependencies are installed."
            ),
        ),
    ] = False,
    max_rows: Annotated[
        int | None,
        typer.Option("--max-rows", help="Maximum rows to inspect for sampling adapters."),
    ] = 1000,
    output: Annotated[
        Path | None,
        typer.Option("--output", help="Write adapter manifest JSON to this path."),
    ] = None,
    out: Annotated[
        Path | None,
        typer.Option("--out", help="Write report output for report command."),
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
            "diff OLD NEW, adapters list|detect DATASET, inspect DATASET, validate DATASET, "
            "or export-manifest DATASET."
        )

    command = args[0]
    if command == "lint":
        _run_lint(args[1:], config, checks, adapter, format, fail_on)
        return
    if command == "report":
        _run_report(args[1:], config, checks, adapter, out, fail_on)
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
    if command == "inspect":
        _run_inspect(args[1:], adapter, auto_detect, split, streaming, deep, max_rows, format)
        return
    if command == "validate":
        _run_adapter_validate(
            args[1:], adapter, auto_detect, split, streaming, deep, max_rows, format
        )
        return
    if command == "export-manifest":
        _run_export_manifest(
            args[1:], adapter, auto_detect, split, streaming, deep, max_rows, output
        )
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
    _emit_lint_report(report, format)
    if should_fail(report, fail_on.value):
        raise typer.Exit(1)


def _run_report(
    args: list[str],
    config: Path | None,
    checks: str | None,
    adapter: str,
    out: Path | None,
    fail_on: FailLevel,
) -> None:
    if len(args) != 1:
        _usage_error("report expects one dataset path.")
    if out is None:
        _usage_error("report requires --out REPORT.{json,md,html}.")
    try:
        validate_checks(checks)
    except ValueError as exc:
        _usage_error(str(exc))
    try:
        report = lint_dataset(path=Path(args[0]), config=config, checks=checks, adapter=adapter)
    except ValueError as exc:
        _usage_error(str(exc))
    suffix = out.suffix.lower()
    if suffix == ".html":
        content = report.to_html()
    elif suffix == ".json":
        content = report.to_json() + "\n"
    elif suffix in {".md", ".markdown"}:
        content = report.to_markdown()
    else:
        _usage_error("report --out supports .html, .json, .md, and .markdown files.")
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
    except OSError as exc:
        _usage_error(f"Could not write report to {out}: {exc}.")
    typer.echo(f"Wrote report to {out}")
    if should_fail(report, fail_on.value):
        raise typer.Exit(1)


def _emit_lint_report(report: LintReport, format: OutputFormat) -> None:
    if format is OutputFormat.json:
        typer.echo(report.to_json())
    elif format is OutputFormat.markdown:
        typer.echo(report.to_markdown())
    elif format is OutputFormat.html:
        typer.echo(report.to_html())
    else:
        print_report(report)


def _run_stats(args: list[str], config: Path | None, format: OutputFormat) -> None:
    if len(args) != 1:
        _usage_error("stats expects one dataset path.")
    if format is OutputFormat.html:
        _usage_error("stats does not support --format html.")
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
    if format is OutputFormat.html:
        _usage_error("diff does not support --format html.")
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
    if format is OutputFormat.html:
        _usage_error("adapters does not support --format html.")
    if len(args) == 1 and args[0] == "list":
        _print_adapter_list(format)
        return
    if len(args) == 2 and args[0] == "detect":
        _print_adapter_detection(args[1], format)
        return
    if len(args) != 1:
        _usage_error("adapters expects list, detect DATASET, or one dataset path.")
    _print_adapter_detection(args[0], format)


def _print_adapter_list(format: OutputFormat) -> None:
    adapters = list_adapter_info()
    if format is OutputFormat.json:
        typer.echo(json.dumps([adapter.to_dict() for adapter in adapters], indent=2))
        return
    if format is OutputFormat.markdown:
        lines = [
            "# DatasetLint Adapters",
            "",
            "| Adapter | Formats | Availability | Optional dependencies | Description |",
            "| --- | --- | --- | --- | --- |",
        ]
        for adapter in adapters:
            deps = ", ".join(
                f"{name}={'yes' if available else 'no'}"
                for name, available in adapter.optional_dependencies.items()
            )
            lines.append(
                f"| {adapter.name} | {', '.join(adapter.supported_formats)} | "
                f"{adapter.availability} | {deps or 'none'} | {adapter.description} |"
            )
        typer.echo("\n".join(lines) + "\n")
        return
    console = Console()
    table = Table(title="DatasetLint Adapters")
    table.add_column("Adapter")
    table.add_column("Formats")
    table.add_column("Availability")
    table.add_column("Optional deps")
    table.add_column("Description")
    for adapter in adapters:
        deps = ", ".join(
            f"{name}:{'yes' if available else 'no'}"
            for name, available in adapter.optional_dependencies.items()
        )
        table.add_row(
            adapter.name,
            ", ".join(adapter.supported_formats),
            adapter.availability,
            deps or "none",
            adapter.description,
        )
    console.print(table)


def _print_adapter_detection(dataset: str, format: OutputFormat) -> None:
    detections = detect_adapters(Path(dataset) if not dataset.startswith("hf://") else dataset)
    selected_name: str | None = None
    ambiguity: str | None = None
    try:
        selected_name = detect_adapter(
            Path(dataset) if not dataset.startswith("hf://") else dataset
        ).name
    except AdapterError as exc:
        ambiguity = str(exc)
    if format is OutputFormat.json:
        typer.echo(
            json.dumps(
                {
                    "detections": [detection.to_dict() for detection in detections],
                    "selected": selected_name,
                    "warning": ambiguity,
                },
                indent=2,
            )
        )
    elif format is OutputFormat.markdown:
        lines = [
            "# DatasetLint Adapters",
            "",
            "| Adapter | Detected | Message |",
            "| --- | --- | --- |",
        ]
        for detection in detections:
            lines.append(f"| {detection.name} | `{detection.can_load}` | {detection.message} |")
        if selected_name:
            lines.extend(["", f"Selected adapter: `{selected_name}`"])
        if ambiguity:
            lines.extend(["", f"Warning: {ambiguity}"])
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
        if selected_name:
            console.print(f"Selected adapter: {selected_name}")
        if ambiguity:
            console.print(f"Warning: {ambiguity}")


def _run_inspect(
    args: list[str],
    adapter: str,
    auto_detect: bool,
    split: str | None,
    streaming: bool,
    deep: bool,
    max_rows: int | None,
    format: OutputFormat,
) -> None:
    if len(args) != 1:
        _usage_error("inspect expects one dataset path.")
    if format is OutputFormat.html:
        _usage_error("inspect does not support --format html.")
    adapter_name = None if auto_detect or adapter == "auto" else adapter
    try:
        manifest = load_dataset(
            _adapter_root(args[0]),
            adapter=adapter_name,
            split=split,
            streaming=streaming,
            deep=deep,
            max_rows=max_rows,
        )
    except AdapterError as exc:
        _usage_error(str(exc))
    if format is OutputFormat.json:
        typer.echo(manifest.to_json())
        return
    if format is OutputFormat.markdown:
        typer.echo(_manifest_markdown(manifest))
        return
    console = Console()
    console.print(
        f"Dataset: {manifest.dataset_name} adapter={manifest.adapter_name} "
        f"sequences={len(manifest.sequences)} frames={len(manifest.frames)} "
        f"sensors={len(manifest.sensors)} annotations={len(manifest.annotations)}"
    )
    console.print(f"splits={manifest.splits}")
    if manifest.limitations:
        console.print("limitations=" + "; ".join(manifest.limitations))
    if manifest.provenance.warnings:
        console.print("warnings=" + "; ".join(manifest.provenance.warnings))


def _run_adapter_validate(
    args: list[str],
    adapter: str,
    auto_detect: bool,
    split: str | None,
    streaming: bool,
    deep: bool,
    max_rows: int | None,
    format: OutputFormat,
) -> None:
    if len(args) != 1:
        _usage_error("validate expects one dataset path.")
    if format is OutputFormat.html:
        _usage_error("validate does not support --format html.")
    adapter_name = None if auto_detect or adapter == "auto" else adapter
    try:
        report = validate_dataset(
            _adapter_root(args[0]),
            adapter=adapter_name,
            split=split,
            streaming=streaming,
            deep=deep,
            max_rows=max_rows,
        )
    except AdapterError as exc:
        _usage_error(str(exc))
    if format is OutputFormat.json:
        typer.echo(report.to_json())
        if not report.valid:
            raise typer.Exit(1)
        return
    if format is OutputFormat.markdown:
        typer.echo(_adapter_validation_markdown(report))
        if not report.valid:
            raise typer.Exit(1)
        return
    console = Console()
    console.print(
        f"Adapter validation: adapter={report.adapter_name} valid={report.valid} "
        f"errors={len(report.errors)} warnings={len(report.warnings)}"
    )
    for error in report.errors:
        console.print(f"Error: {error}")
    for warning in report.warnings:
        console.print(f"Warning: {warning}")
    console.print(f"validation_mode={report.validation_mode}")
    console.print(f"checked={report.checked}")
    console.print(f"not_checked={report.not_checked}")
    console.print(f"limitations={report.limitations}")
    console.print(f"coverage={report.coverage}")
    console.print(f"stats={report.stats}")
    if not report.valid:
        raise typer.Exit(1)


def _run_export_manifest(
    args: list[str],
    adapter: str,
    auto_detect: bool,
    split: str | None,
    streaming: bool,
    deep: bool,
    max_rows: int | None,
    output: Path | None,
) -> None:
    if len(args) != 1:
        _usage_error("export-manifest expects one dataset path.")
    if output is None:
        _usage_error("export-manifest requires --output manifest.json.")
    adapter_name = None if auto_detect or adapter == "auto" else adapter
    try:
        manifest = load_dataset(
            _adapter_root(args[0]),
            adapter=adapter_name,
            split=split,
            streaming=streaming,
            deep=deep,
            max_rows=max_rows,
        )
    except AdapterError as exc:
        _usage_error(str(exc))
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(manifest.to_json() + "\n", encoding="utf-8")
    except OSError as exc:
        _usage_error(f"Could not write manifest to {output}: {exc}.")
    typer.echo(f"Wrote JSON manifest to {output}")


def _adapter_root(value: str) -> str | Path:
    if value.startswith("hf://"):
        return value
    return Path(value)


def _manifest_markdown(manifest: DatasetManifest) -> str:
    manifest_dict = manifest.to_dict()
    return (
        "# DatasetLint Manifest\n\n"
        f"- dataset: `{manifest_dict['dataset_name']}`\n"
        f"- adapter: `{manifest_dict['adapter_name']}`\n"
        f"- sequences: `{len(manifest_dict['sequences'])}`\n"
        f"- frames: `{len(manifest_dict['frames'])}`\n"
        f"- sensors: `{len(manifest_dict['sensors'])}`\n"
        f"- annotations: `{len(manifest_dict['annotations'])}`\n"
        f"- splits: `{manifest_dict['splits']}`\n"
        f"- limitations: `{manifest_dict['limitations']}`\n"
    )


def _adapter_validation_markdown(report: AdapterValidationReport) -> str:
    report_dict = report.to_dict()
    lines = [
        "# DatasetLint Adapter Validation",
        "",
        f"- adapter: `{report_dict['adapter_name']}`",
        f"- valid: `{report_dict['valid']}`",
        f"- detected: `{report_dict['detected']}`",
        f"- validation_mode: `{report_dict['validation_mode']}`",
        f"- checked: `{report_dict['checked']}`",
        f"- not_checked: `{report_dict['not_checked']}`",
        f"- limitations: `{report_dict['limitations']}`",
        f"- stats: `{report_dict['stats']}`",
        f"- coverage: `{report_dict['coverage']}`",
    ]
    if report_dict["errors"]:
        lines.append(f"- errors: {', '.join(report_dict['errors'])}")
    if report_dict["warnings"]:
        lines.append(f"- warnings: {', '.join(report_dict['warnings'])}")
    return "\n".join(lines) + "\n"


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
