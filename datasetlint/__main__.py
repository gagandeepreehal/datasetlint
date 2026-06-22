"""Module entry point for ``python -m datasetlint``."""

from datasetlint.cli import app


def main() -> None:
    app()


if __name__ == "__main__":
    main()
