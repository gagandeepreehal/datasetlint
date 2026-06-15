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
datasetlint examples/minimal_dataset --checks labels
datasetlint examples/minimal_dataset --checks sync
datasetlint examples/minimal_dataset --adapter auto
datasetlint examples/minimal_dataset --format json
datasetlint examples/minimal_dataset --format markdown
datasetlint examples/bad_dataset --fail-on error
datasetlint stats examples/minimal_dataset --format console
datasetlint stats examples/minimal_dataset --format json
datasetlint diff examples/minimal_dataset examples/bad_dataset
datasetlint diff old_dataset new_dataset --fail-on-regression
datasetlint adapters examples/minimal_dataset
```

## Python Usage

```python
from datasetlint import compare_datasets, compute_dataset_stats, lint_dataset
from datasetlint.adapters import get_adapter

report = lint_dataset(path="examples/minimal_dataset", config=None)
print(report.summary())
print(report.to_markdown())

label_report = lint_dataset("examples/minimal_dataset", checks="labels")
sync_report = lint_dataset("examples/minimal_dataset", checks="sync")
stats = compute_dataset_stats("examples/minimal_dataset")
diff = compare_datasets("old_dataset", "new_dataset")
adapter = get_adapter("examples/minimal_dataset", "auto")
```

Lower-level integrations that already have a `DatasetContext` can also import
`check_label_consistency` from `datasetlint.checks.labels` and
`check_sensor_synchronization` from `datasetlint.checks.sync`.

## Configuration

DatasetLint uses defaults when no config is provided. A dataset can include `datasetlint.yaml`:

```yaml
timestamp_gap_threshold_sec: 0.5
max_timestamp_gap_sec: 0.5
max_pairwise_sync_gap_sec: 0.05
min_overlap_ratio: 0.8
frequency_jitter_ratio: 0.2
label_max_position_jump_px: 200
label_max_size_change_ratio: 3.0
label_min_track_length: 3
label_class_switch_threshold: 0
max_speed_mps: 70
max_accel_mps2: 12
frame_count_drop_ratio_warning: 0.1
duration_drop_ratio_warning: 0.1
issue_regression_severity: warning
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

## Feature Overview

- Label consistency checks validate `labels/detections.csv` for required columns, confidence range, positive boxes, duplicate `(timestamp, track_id)` rows, class switches, short tracks, missing in-track timestamps, large box jumps, and abrupt size changes.
- Sensor synchronization checks report per-sensor timing, inferred rates, overlap duration, pairwise timestamp gaps, missing frame bursts, and frequency jitter.
- `datasetlint stats` computes dataset distributions for sensors, labels, tracks, trajectories, missing frames, and issue severity counts.
- `datasetlint diff` compares two datasets and classifies regressions such as removed sensors, frame-count drops, duration drops, calibration changes, disappeared label classes, and increased issue counts.
- `datasetlint adapters` reports adapter detection. The folder adapter is fully supported; MCAP, ROS bag, NuScenes, and Waymo adapters are detection-only in v0 and raise clear `NotImplementedError` messages for deep parsing.

## Contributing

Keep v0.1 focused on pure Python, typed APIs, local files, and useful error messages. Run:

```bash
pytest
ruff check .
mypy datasetlint
```

DatasetLint is MIT licensed.
