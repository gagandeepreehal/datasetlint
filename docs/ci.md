# CI Templates

Use these snippets inside your own repository. This task only documents
templates; it does not create a separate GitHub Action repository.

## Minimal Dataset Check

```yaml
name: DatasetLint

on:
  pull_request:
  push:

jobs:
  datasetlint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install DatasetLint
        run: python -m pip install datasetlint
      - name: Validate dataset
        run: datasetlint data/robotics_dataset
```

If you are testing DatasetLint from a source checkout instead of a published
package, replace the install step with:

```yaml
      - name: Install DatasetLint from source
        run: python -m pip install -e ".[dev]"
```

## Fail On Warning

```yaml
      - name: Validate dataset with warnings as failures
        run: datasetlint data/robotics_dataset --fail-on warning
```

## Save Report Artifacts

```yaml
      - name: Generate DatasetLint reports
        run: |
          mkdir -p datasetlint-reports
          datasetlint data/robotics_dataset --format json > datasetlint-reports/report.json || true
          datasetlint data/robotics_dataset --format markdown > datasetlint-reports/report.md || true
          datasetlint data/robotics_dataset --format html > datasetlint-reports/report.html || true

      - uses: actions/upload-artifact@v4
        with:
          name: datasetlint-reports
          path: datasetlint-reports/
```

Use a separate gating step if the job should fail after artifacts are saved:

```yaml
      - name: Gate dataset quality
        run: datasetlint data/robotics_dataset --fail-on error
```

## Diff Old And New Datasets

```yaml
      - name: Compare dataset versions
        run: datasetlint diff data/baseline_dataset data/candidate_dataset --fail-on-regression
```

The diff command flags regressions such as removed sensors, frame-count drops,
duration drops, calibration changes, disappeared label classes, and increased
warning or error counts.
