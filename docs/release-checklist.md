# Release Checklist

Use this before tagging a DatasetLint release.

Run the automated release gate first:

```bash
make release-check
mkdocs build --strict
```

Use `PYTHON=/path/to/python` when the dev dependencies are installed in a specific
environment, and `WHEEL_DIR=/tmp/datasetlint-wheel` when you want wheel artifacts outside
the worktree.

- Run `pytest`.
- Run `ruff check .`.
- Run `mypy datasetlint`.
- Run `mkdocs build --strict`.
- Build distributions with `python -m build`.
- Check distributions with `python -m twine check dist/*`.
- Confirm `datasetlint --version`.
- Confirm `datasetlint --help`.
- Confirm `datasetlint examples/minimal_dataset`.
- Confirm `datasetlint examples/bad_dataset`.
- Confirm `datasetlint diff examples/minimal_dataset examples/bad_dataset --fail-on-regression`.
- Confirm generated sample reports are current:
  - `examples/reports/minimal_report.json`
  - `examples/reports/bad_report.json`
  - `examples/reports/bad_report.md`
- Confirm README limitations are near the top and still match adapter coverage.
- Lint `examples/minimal_dataset` and confirm it passes.
- Lint `examples/bad_dataset` and confirm it reports errors.
- Review `README.md`, `docs/quickstart.md`, and `docs/checks.md` for CLI/API drift.
- Confirm `pyproject.toml` version, Python requirement, dependencies, and console script.
- Confirm `LICENSE` is present and uses MIT terms.
- Confirm `SECURITY.md`, `CITATION.cff`, and `PUBLISHING.md` are current.
- Confirm the public GitHub repository is reachable and matches the release commit.
- Confirm the `testpypi` GitHub environment and TestPyPI trusted publisher are configured
  for `.github/workflows/publish.yml`.
- Run the `Publish` workflow manually with `target: testpypi` from the release commit.
- Install the release version from TestPyPI in a fresh virtual environment.
- Confirm the `pypi` GitHub environment and PyPI trusted publisher are configured for
  `.github/workflows/publish.yml`.
- Confirm the `datasetlint` PyPI project is owned by the maintainer before announcing
  `pip install datasetlint` as the default install path.
- Confirm GitHub Pages is enabled for the docs workflow.
