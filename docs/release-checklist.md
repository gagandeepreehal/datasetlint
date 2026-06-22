# Release Checklist

Use this before tagging a DatasetLint v0.1 release.

Run the automated release gate first:

```bash
make release-check
```

Use `PYTHON=/path/to/python` when the dev dependencies are installed in a specific
environment, and `WHEEL_DIR=/tmp/datasetlint-wheel` when you want wheel artifacts outside
the worktree.

- Run `pytest`.
- Run `ruff check .`.
- Run `mypy datasetlint`.
- Build a local wheel with `python -m pip wheel . --no-deps --no-build-isolation`.
- Lint `examples/minimal_dataset` and confirm it passes.
- Lint `examples/bad_dataset` and confirm it reports errors.
- Review `README.md`, `docs/quickstart.md`, and `docs/checks.md` for CLI/API drift.
- Confirm `pyproject.toml` version, Python requirement, dependencies, and console script.
- Confirm `LICENSE` is present and uses MIT terms.
