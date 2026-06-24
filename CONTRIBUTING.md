# Contributing

DatasetLint is a small, typed, local-first project. Keep contributions focused on making robotics and physical AI dataset validation more accurate, easier to run, and easier to trust.

## Project Philosophy

- Prefer concrete validation errors over broad claims.
- Keep examples tiny enough for the repository.
- Treat CLI output, report fields, config keys, and docs as public contracts.
- Do not add adapter or rule claims until the implementation exists.
- Keep the default path local: files in, report out.

## Local Setup

Use Python 3.10 or newer. On macOS, `python3` may be Python 3.9, so use an explicit modern interpreter if needed.

```bash
git clone https://github.com/gagandeepreehal/datasetlint.git
cd datasetlint
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev,docs]"
```

## Test And Quality Commands

Run these before opening a pull request:

```bash
pytest
ruff check .
mypy datasetlint
mkdocs build --strict
```

`ruff format` is available through the dev dependencies. Use it intentionally on touched Python files and avoid formatting unrelated files in mixed-purpose pull requests:

```bash
ruff format path/to/file.py
```

The release gate runs the main checks plus a wheel build and example smoke tests:

```bash
make release-check
```

## Adding A Rule

1. Add the check function under `datasetlint/checks/`.
2. Return `Issue` objects with stable `check_name`, `severity`, `message`, `file`, `row`, and metadata.
3. Register the function in the appropriate group in `datasetlint/core.py`.
4. Add focused tests under `tests/`.
5. Update `docs/rules.md`, `docs/configuration.md` if a config key is added, and README feature summaries if the behavior is user-facing.

Rules should be deterministic and should not require network access, GPU runtimes, ROS, simulators, or model services.

## Adding An Adapter

1. Implement `DatasetAdapter` from `datasetlint/adapters/base.py`.
2. Make `can_load()` cheap and conservative.
3. Return clear `NotImplementedError` messages for detection-only adapters.
4. Register the adapter in `datasetlint/adapters/__init__.py`.
5. Add tests for detection, error messages, and any implemented loading behavior.
6. Update `docs/adapters.md` and the supported format table in README.

Only mark an adapter as supported when it deeply loads the data used by validation. Detection alone should be documented as detection-only.

## Adding A Fixture Dataset

- Keep fixtures small and text-based where possible.
- Put user-facing fixtures under `examples/`.
- Put test-only fixtures under `tests/fixtures/` if they become necessary.
- Include the exact command and expected pass/fail result in `examples/README.md`.
- Avoid committing private paths, real customer data, secrets, or sensitive map/location details.

## Writing Docs

- Document actual commands and public imports only.
- Use `datasetlint --help` and tests as the source of truth.
- Mark planned work in `docs/roadmap.md`, not as current features.
- Run `mkdocs build --strict` after changing docs navigation or links.

## Pull Requests

Pull requests should include:

- tests for behavior changes
- docs updates for user-facing CLI, API, config, adapter, report, or example changes
- small fixtures when needed
- compatibility notes when public fields or commands change
- a clear explanation of any limitation or follow-up

## Issue Reporting

Use the issue templates in `.github/ISSUE_TEMPLATE/`. For bugs, include the DatasetLint version or commit, Python version, OS, install method, command run, expected behavior, actual behavior, logs, and a minimal dataset structure or repro.

## Style Expectations

- Python code should be typed.
- Keep runtime dependencies modest.
- Prefer clear helper functions over broad abstractions.
- Keep user-facing messages actionable.
- Do not hide invalid config keys or stale dataset schema fields.
