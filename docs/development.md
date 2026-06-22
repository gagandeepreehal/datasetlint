# Development

## Package Structure

```text
datasetlint/
  adapters/      adapter interfaces and implementations
  checks/        validation rules
  formatters/    console report formatting
  io/            CSV, JSON, and filesystem helpers
  cli.py         command-line entry point
  core.py        lint orchestration and config loading
  diff.py        dataset comparison
  report.py      report models and serialization
  schemas.py     shared config, issue, and context models
  stats.py       dataset statistics
```

## Local Commands

```bash
python -m pip install -e ".[dev,docs]"
pytest
ruff check .
mypy datasetlint
mkdocs build --strict
```

Use `ruff format path/to/file.py` for touched Python files when formatting is part of the change.

## Test Strategy

Tests should cover:

- rule-level pass/fail behavior
- CLI success, failure, and usage errors
- public API imports and report serialization
- config parsing and unknown-key failures
- adapter detection and detection-only messages
- stats and diff summaries
- tiny example datasets where useful

## Adding Rules

Add rule functions under `datasetlint/checks/`, register them in `datasetlint/core.py`, and document them in [Rules](rules.md). Rules should return `Issue` objects and avoid external services.

## Adding Adapters

Add adapter classes under `datasetlint/adapters/`, register them in `datasetlint/adapters/__init__.py`, and update [Adapters](adapters.md). Do not document deep support until the adapter can load the data needed by validation.

## Adding Config

Add fields to `LintConfig` in `datasetlint/schemas.py`, tests for defaults and parsing, and docs in [Configuration](configuration.md). Unknown config keys are intentionally rejected.

## Release Checks

Before tagging a release:

```bash
make release-check
mkdocs build --strict
```

Then follow [Release Checklist](release-checklist.md) and `PUBLISHING.md`.
