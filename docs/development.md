# Development

DatasetLint development favors small, verified changes. Keep public contracts
stable: CLI command words, exit codes, JSON fields, report formats, adapter
names, and documented examples should stay aligned with the implementation.

## Environment

Use Python 3.10 or newer. The repo `Makefile` prefers `python3.12`,
`python3.11`, then `python3.10` when available.

```bash
git clone https://github.com/gagandeepreehal/datasetlint.git
cd datasetlint
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev,docs]"
```

If you only need runtime behavior, `python -m pip install -e .` is enough.
Install adapter extras only for the formats you are actively testing.

## Package Structure

```text
datasetlint/
  adapters/      adapter interfaces, registry, normalized models, and implementations
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

## Daily Commands

```bash
make check
python -m pytest tests/test_cli.py
python -m pytest tests/adapters/test_coco_adapter.py
python -m ruff check .
python -m ruff format --check .
python -m mypy datasetlint
python -m mkdocs build --strict
```

Use `python -m ruff format path/to/file.py` for touched Python files when
formatting is part of the change. Use `make release-check` before release
branches or packaging changes.

## Test Strategy

Tests should cover:

- rule-level pass/fail behavior
- CLI success, failure, and usage errors
- public API imports and report serialization
- config parsing and unknown-key failures
- adapter registration, detection, manifests, validation, and optional-dependency paths
- stats and diff summaries
- tiny example datasets where useful

For docs-only changes, run at least:

```bash
python -m mkdocs build --strict
python -m datasetlint examples/minimal_dataset --format json
git diff --check
```

The CLI smoke keeps examples, command names, and import/install behavior honest.

## Adding Rules

Add rule functions under `datasetlint/checks/`, register them in
`datasetlint/core.py`, and document them in [Rules](rules.md). Rules should
return `Issue` objects and avoid external services.

## Adding Adapters

Add built-in adapter classes under `datasetlint/adapters/`, register them in
`datasetlint/adapters/registry.py`, export public classes or helpers from
`datasetlint/adapters/__init__.py`, and update [Adapters](adapters.md).
Third-party packages can use the `datasetlint.adapters` entry-point group
instead of forking the repo. `examples/third_party_adapter` is a minimal
installable template with a `pyproject.toml` entry point, adapter class, sample
dataset, and test.

An adapter should implement:

- `name`
- `supported_formats`
- `detect(root)` or `can_load(path)`
- `load(root, **kwargs)`
- `validate(root, **kwargs)`

Use `DatasetManifest` and `AdapterValidationReport` from
`datasetlint.adapters.base`. Keep optional dependencies out of the base install,
and use tiny synthetic fixtures for tests.

When an adapter can decode semantic records, populate the normalized `frames`,
`sensors`, `annotations`, `calibration`, and `splits` fields rather than only
adapter-specific metadata. `datasetlint.adapters.manifest_rules` runs shared
checks over those records and merges the results into
`coverage.common_rule_inputs`, `stats.common_rule_stats`, and `checked`.

## Adding Config

Add fields to `LintConfig` in `datasetlint/schemas.py`, tests for defaults and
parsing, and docs in [Configuration](configuration.md). Unknown config keys are
intentionally rejected.

## Updating Docs

Docs are part of the product contract. Update the page that a user would
actually read:

| Change | Docs To Check |
| --- | --- |
| CLI command, option, or exit code | [CLI Reference](cli.md), [Getting Started](getting-started.md), [Troubleshooting](troubleshooting.md) |
| Report field or output format | [Reports](reports.md), [CI Templates](ci.md), generated examples under `examples/reports/` |
| Native folder rule | [Rules](rules.md), [Checks](checks.md), [Configuration](configuration.md) |
| Adapter behavior | [Adapters](adapters.md), [CLI Reference](cli.md), adapter tests |
| Packaging or release process | [Installation](installation.md), [Release](release.md), [Release Checklist](release-checklist.md) |

MkDocs uses the built-in Read the Docs theme plus `docs/assets/stylesheets/extra.css`.
Keep the docs dependency-light unless there is a strong reason to add another
package.

## Release Checks

Before tagging a release:

```bash
make release-check
mkdocs build --strict
```

Then follow [Release Checklist](release-checklist.md) and `PUBLISHING.md`.
