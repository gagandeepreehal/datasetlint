# Publishing

DatasetLint releases are published from tagged commits after the release gate
passes.

## Preconditions

- The GitHub repository is public.
- The PyPI project name `datasetlint` is owned by the maintainer.
- PyPI trusted publishing is configured for this repository and the `pypi`
  environment.
- `CHANGELOG.md`, `CITATION.cff`, and `pyproject.toml` all contain the release
  version.

Confirm the `datasetlint` PyPI project is owned by the maintainer before
announcing `pip install datasetlint`. If the name is not owned yet, claim it by
performing the first trusted-publishing release from this repository.

## Release Gate

Run:

```bash
python -m pip install -e ".[dev,docs]"
make release-check
mkdocs build --strict
```

## Tag And Publish

Create and push an annotated tag:

```bash
git tag -a v0.1.0 -m "DatasetLint v0.1.0"
git push origin v0.1.0
```

Then run the `Publish` GitHub Actions workflow for that tag. The workflow builds
source and wheel distributions, checks metadata, and publishes to PyPI through
trusted publishing.

## Manual Fallback

Use this only if trusted publishing is unavailable:

```bash
python -m pip install build twine
python -m build
python -m twine check dist/*
python -m twine upload dist/*
```

Do not upload artifacts built from a dirty worktree.
