# CI Templates

Use DatasetLint in CI to block dataset QA regressions before merge. These snippets assume the repository already contains the dataset paths being checked and that DatasetLint is installed from the current checkout.

## Minimal Dataset Check

```yaml
name: DatasetLint
on:
  pull_request:
  push:
    branches: [main]

jobs:
  datasetlint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: python -m pip install -U pip
      - run: python -m pip install -e .
      - run: datasetlint examples/minimal_dataset
```

## Fail On Warning

```yaml
name: DatasetLint Strict
on:
  pull_request:

jobs:
  datasetlint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: python -m pip install -U pip
      - run: python -m pip install -e .
      - run: datasetlint data/training --fail-on warning
```

## Save Report Artifacts

```yaml
name: DatasetLint Reports
on:
  pull_request:

jobs:
  datasetlint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: python -m pip install -U pip
      - run: python -m pip install -e .
      - run: mkdir -p datasetlint-reports
      - run: datasetlint report examples/bad_dataset --out datasetlint-reports/report.json
        continue-on-error: true
      - run: datasetlint report examples/bad_dataset --out datasetlint-reports/report.md
        continue-on-error: true
      - run: datasetlint report examples/bad_dataset --out datasetlint-reports/report.html
        continue-on-error: true
      - uses: actions/upload-artifact@v4
        with:
          name: datasetlint-reports
          path: datasetlint-reports/
      - run: datasetlint examples/bad_dataset
```

The final validation step preserves the failing exit code after artifacts have been uploaded.

## Diff Old And New Datasets

```yaml
name: DatasetLint Diff
on:
  pull_request:

jobs:
  dataset-diff:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: python -m pip install -U pip
      - run: python -m pip install -e .
      - run: git fetch origin main
      - run: git checkout origin/main -- data/baseline
      - run: datasetlint diff data/baseline data/current --fail-on-regression
```

Adjust `data/baseline` and `data/current` to match the dataset layout in the repository. `--fail-on-regression` exits non-zero when the new dataset has worse issue counts, missing sensors, reduced duration, or other configured regressions.
