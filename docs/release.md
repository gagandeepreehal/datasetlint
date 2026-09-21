# Release

Before a release:

1. Bump the version in `datasetlint/_version.py` and `pyproject.toml`.
2. Update `CHANGELOG.md`.
3. Run `make release-check`.
4. Run `mkdocs build --strict`.
5. Run the `Publish` workflow manually with `target: testpypi`.
6. Install the release version from TestPyPI in a fresh virtual environment.
7. Create and push an annotated `vX.Y.Z` tag.
8. Draft and publish a GitHub release with the changelog notes.

The GitHub release publish event uploads the checked distributions to PyPI
through trusted publishing. Manual `target: pypi` dispatch is only for replaying
a release from a tag ref.

```bash
git tag -a 0.0.2 -m "DatasetLint 0.0.2"
git push origin 0.0.2
```

See `PUBLISHING.md` for trusted publisher setup and the exact TestPyPI install
smoke command.
