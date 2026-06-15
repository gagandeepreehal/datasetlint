# DatasetLint

DatasetLint catches timestamp drift, missing frames, broken calibration, invalid labels, and trajectory anomalies before they poison Physical AI training and evaluation pipelines.

DatasetLint is a lightweight, standalone Python library for validating folder-based robotics datasets. It runs on a MacBook without robots, simulators, GPUs, ROS, cloud services, or large models.

## Why Robotics Datasets Fail

Robotics logs mix sensor streams, metadata, labels, calibration, and trajectories. Small inconsistencies often surface much later as bad training data, misleading evaluations, or broken replay tooling. DatasetLint checks those issues at the dataset folder boundary.

Common failures include:

- Missing metadata, calibration, sensor CSVs, or referenced image files
- Duplicate, non-monotonic, or non-overlapping timestamps
- Missing sensor columns, invalid camera dimensions, and unstable rates
- Malformed intrinsics, extrinsics, and quaternion values
- Invalid label confidence, label geometry, and track class drift
- Unrealistic speed, acceleration, yaw, or stationary trajectories

## Installation

```bash
pip install datasetlint
```

For local development:

```bash
python -m pip install -e ".[dev]"
```

## CLI Usage

```bash
datasetlint examples/minimal_dataset
datasetlint examples/minimal_dataset --format json
datasetlint examples/minimal_dataset --format markdown
datasetlint examples/bad_dataset --fail-on error
```

## Python Usage

```python
from datasetlint import lint_dataset

report = lint_dataset(path="examples/minimal_dataset", config=None)
print(report.summary())
print(report.to_markdown())
```

## Configuration

DatasetLint uses defaults when no config is provided. A dataset can include `datasetlint.yaml`:

```yaml
timestamp_gap_threshold_sec: 0.5
max_speed_mps: 70
max_accel_mps2: 12
expected_sensor_rates:
  camera_front: 10
  imu: 100
  gps: 10
```

The YAML reader intentionally supports this simple shape without adding a runtime YAML dependency.

## Example Output

```text
DatasetLint report for /path/to/dataset: failed with 3 issue(s) (error=2, warning=1, info=0).
```

JSON and Markdown outputs are available through `--format`.

## Contributing

Keep v0.1 focused on pure Python, typed APIs, local files, and useful error messages. Run:

```bash
pytest
ruff check .
mypy datasetlint
```

DatasetLint is MIT licensed.

