"""Module entrypoint for ``python -m datasetlint``."""

from __future__ import annotations

from datasetlint.cli import app


def main() -> None:
    """Run the DatasetLint CLI."""

    app()


if __name__ == "__main__":
    main()
