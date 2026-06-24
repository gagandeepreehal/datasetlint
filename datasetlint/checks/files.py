"""File-level checks."""

from __future__ import annotations

from collections import defaultdict

from datasetlint.schemas import DatasetContext, Issue, make_issue, relative_path


def check_required_files(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    for filename in ("metadata.json", "calibration.json"):
        if not (ctx.path / filename).is_file():
            issues.append(
                make_issue(
                    "check_required_files",
                    "error",
                    f"Missing required file: {filename}.",
                    file=filename,
                )
            )
    return issues


def check_empty_files(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    for csv_path in sorted(ctx.path.rglob("*.csv")):
        if csv_path.is_file() and csv_path.stat().st_size == 0:
            issues.append(
                make_issue(
                    "check_empty_files",
                    "error",
                    "CSV file is empty.",
                    file=relative_path(ctx.path, csv_path),
                )
            )
    return issues


def check_missing_sensor_files(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    for sensor in ctx.declared_sensors():
        sensor_file = ctx.path / "sensors" / f"{sensor}.csv"
        if not sensor_file.is_file():
            issues.append(
                make_issue(
                    "check_missing_sensor_files",
                    "error",
                    f"Metadata declares sensor '{sensor}', but sensors/{sensor}.csv is missing.",
                    file=relative_path(ctx.path, sensor_file),
                    metadata={"sensor": sensor},
                )
            )
    return issues


def check_broken_paths(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    for _name, csv_path, frame in ctx.iter_frames():
        if "path" not in frame.columns:
            continue
        for index, value in frame["path"].items():
            if not isinstance(value, str) or not value:
                continue
            referenced = ctx.path / value
            if not referenced.exists():
                issues.append(
                    make_issue(
                        "check_broken_paths",
                        "error",
                        f"Referenced file does not exist: {value}.",
                        file=relative_path(ctx.path, csv_path),
                        row=int(index) + 2,
                        metadata={"path": value},
                    )
                )
    return issues


def check_duplicate_filenames(ctx: DatasetContext) -> list[Issue]:
    files_by_name: dict[str, list[str]] = defaultdict(list)
    for path in ctx.path.rglob("*"):
        if path.is_file() and not any(part.startswith(".") for part in path.parts):
            files_by_name[path.name].append(relative_path(ctx.path, path))
    issues: list[Issue] = []
    for filename, paths in sorted(files_by_name.items()):
        if len(paths) > 1:
            issues.append(
                make_issue(
                    "check_duplicate_filenames",
                    "warning",
                    f"Duplicate filename '{filename}' appears in multiple folders.",
                    metadata={"paths": paths},
                )
            )
    return issues
