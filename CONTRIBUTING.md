# Contributing

Thanks for helping improve DatasetLint. Keep changes small, typed, and focused on local,
folder-based dataset validation.

## Development Setup

Use Python 3.10 or newer:

```bash
python -m pip install -e ".[dev,docs]"
```

Run the checks before opening a pull request:

```bash
pytest
ruff check .
mypy datasetlint
mkdocs build --strict
```

## Pull Requests

- Include tests for behavior changes and CLI error paths.
- Update README or docs when public commands, fields, config keys, or examples change.
- Keep generated data small enough to live comfortably in the repository.
- Prefer clear user-facing errors over uncaught exceptions for invalid input.
