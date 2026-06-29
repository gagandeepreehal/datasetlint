# Release Checklist

Use this before tagging a DatasetLint v0.1 release.

Run the automated release gate first:

```bash
make release-check
```

- Run `pytest`.
- Run `ruff check .`.
- Run `mypy datasetlint`.
- Run `mkdocs build --strict`.
- Build a local package with `python -m build`.
- Run `python -m twine check dist/*`.
- Confirm PyPI project ownership and publishing credentials before upload.
- Confirm the public repository is visible and linked from package metadata.
- Confirm generated sample reports exist under `examples/reports/`.
- Confirm README limitations are near the top and match current adapter coverage.
- Run `datasetlint --version`.
- Run `datasetlint --help`.
- Run `datasetlint examples/minimal_dataset`.
- Run `datasetlint examples/bad_dataset` and confirm it reports errors.
- Run `datasetlint diff examples/minimal_dataset examples/bad_dataset --fail-on-regression`.
- Review `README.md`, `docs/quickstart.md`, and `docs/checks.md` for CLI/API drift.
- Confirm `pyproject.toml` version, Python requirement, dependencies, and console script.
- Confirm `LICENSE` is present and uses MIT terms.
