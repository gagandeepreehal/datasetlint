# Publishing

DatasetLint releases are published from tagged commits after the release gate
passes.

## Preconditions

- The GitHub repository is public.
- The PyPI project name `datasetlint` is owned by the maintainer.
- The TestPyPI project name `datasetlint` is owned by the maintainer.
- PyPI trusted publishing is configured for this repository, the
  `.github/workflows/publish.yml` workflow, and the `pypi` environment.
- TestPyPI trusted publishing is configured for this repository, the
  `.github/workflows/publish.yml` workflow, and the `testpypi` environment.
- `CHANGELOG.md`, `CITATION.cff`, and `pyproject.toml` all contain the release
  version.

Confirm the `datasetlint` PyPI project is owned by the maintainer before
announcing `pip install datasetlint`. If the name is not owned yet, claim it by
performing the first trusted-publishing release from this repository.

## Workflow Targets

The `Publish` workflow has three publishing paths:

- Manual dispatch with `target: testpypi` builds, checks, and publishes to
  TestPyPI using the `testpypi` environment. This is the default manual target.
- Publishing a GitHub release builds, checks, and publishes to PyPI using the
  `pypi` environment.
- Manual dispatch with `target: pypi` is allowed only when the workflow is run
  from a tag ref. Use this only to recover or replay a release after confirming
  the tag and artifacts.

Do not add PyPI or TestPyPI API tokens to GitHub secrets for the normal release
path. The workflow uses OpenID Connect trusted publishing through GitHub
environments.

## Release Gate

Run:

```bash
python -m pip install -e ".[dev,docs]"
make release-check
mkdocs build --strict
```

## TestPyPI Dry Run

Before tagging the release, run the `Publish` workflow manually with
`target: testpypi` from the release commit. After it succeeds, verify a fresh
install from TestPyPI:

```bash
python -m venv /tmp/datasetlint-testpypi
/tmp/datasetlint-testpypi/bin/python -m pip install --upgrade pip
/tmp/datasetlint-testpypi/bin/python -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  "datasetlint==0.0.1"
/tmp/datasetlint-testpypi/bin/datasetlint --version
```

Use the release version instead of `0.0.1`.

## Tag And Publish To PyPI

Create and push an annotated tag:

```bash
git tag -a v0.0.1 -m "DatasetLint v0.0.1"
git push origin v0.0.1
```

Then draft and publish a GitHub release for that tag. The `Publish` workflow
builds source and wheel distributions, checks metadata, and publishes to PyPI
through trusted publishing.

If the GitHub release event needs to be replayed, run the `Publish` workflow
manually from the tag ref with `target: pypi`.

## Manual Fallback

Use this only if trusted publishing is unavailable:

```bash
python -m pip install build twine
python -m build
python -m twine check dist/*
python -m twine upload dist/*
```

Do not upload artifacts built from a dirty worktree.
