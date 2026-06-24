# Release

Before a release:

1. Bump the version in `datasetlint/_version.py` and `pyproject.toml`.
2. Update `CHANGELOG.md`.
3. Run `make release-check`.
4. Run `python -m build`.
5. Run `python -m twine check dist/*`.
6. Draft a GitHub release with the changelog notes.

Publish placeholder:

```bash
python -m twine upload dist/*
```
