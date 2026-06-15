"""Filesystem helpers."""

from __future__ import annotations

from pathlib import Path


def csv_files(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(path for path in folder.glob("*.csv") if path.is_file())


def stemmed_csv_files(folder: Path) -> dict[str, Path]:
    return {path.stem: path for path in csv_files(folder)}

