# DatasetLint Third-Party Adapter Template

This is a minimal installable adapter package that registers through the
`datasetlint.adapters` entry-point group. Use it as a starting point when an
adapter should live outside the DatasetLint repository.

## Try It Locally

Install DatasetLint from this repository first, then install the example package
into the same Python environment:

```bash
python -m pip install -e .
python -m pip install -e examples/third_party_adapter
datasetlint adapters list
datasetlint validate examples/third_party_adapter/sample_dataset --adapter example_telemetry --format json
```

`datasetlint adapters list` should include `example_telemetry` after the package
is installed.

## Package Shape

- `pyproject.toml` declares the `datasetlint.adapters` entry point.
- `src/datasetlint_example_adapter/__init__.py` implements a `DatasetAdapter`.
- `sample_dataset/telemetry.jsonl` is a tiny fixture for local smoke tests.
- `tests/test_example_adapter.py` shows a direct adapter test external teams can
  keep in their own package.

The adapter reads newline-delimited JSON rows with `timestamp`, `camera_path`,
`lidar_path`, and optional `label` fields. It emits normalized manifest records
so DatasetLint can run shared frame, sensor, timestamp, and annotation checks.
