# DatasetLint

DatasetLint is a lightweight, local-first dataset validation, dataset QA, and robotics data quality toolkit for robotics and Physical AI datasets.

It catches timestamp drift, missing frames, broken calibration, invalid labels, and trajectory anomalies before they poison training, evaluation, or replay pipelines. It runs without robots, simulators, GPUs, ROS, cloud services, or large models.

## Current Limitations

DatasetLint v0 is intentionally small and honest about coverage:

- Deep validation works best on the native DatasetLint folder format: `metadata.json`, `calibration.json`, `sensors/*.csv`, `labels/*.csv`, and `trajectories/*.csv`.
- Adapters provide format detection plus manifest, index, or export inspection where practical; they do not all provide deep validation.
- MCAP, ROS bag, Waymo, NuScenes, KITTI, COCO, and Hugging Face dataset inputs are currently index-level or manifest-level unless optional parsers are implemented later.
- DatasetLint validates structure, timing, calibration shape, labels, and trajectory consistency. It does not decode image pixels, point clouds, ROS messages, or model-ready tensors.
- Public package installation should be verified during release. Until a published PyPI release is confirmed, use the source checkout install path below.

## Try In 60 Seconds

From a source checkout:

```bash
python3.11 -m venv .venv311
.venv311/bin/python -m pip install -e ".[dev]"
.venv311/bin/datasetlint examples/minimal_dataset
.venv311/bin/datasetlint report examples/bad_dataset --out report.md
.venv311/bin/datasetlint report examples/bad_dataset --out report.html
```

Expected shape:

- `examples/minimal_dataset` should pass.
- `examples/bad_dataset` should fail with concrete robotics data quality issues.
- `report.html` is a static, local HTML report.

## What DatasetLint Catches

Concrete checks include:

- Missing metadata such as `metadata.json` or required fields
- Broken file references from camera CSV rows to image files
- Duplicate timestamps
- Timestamp gaps
- Sensor sync gaps across streams
- Missing calibration for declared sensors
- Invalid camera intrinsics
- Non-normalized quaternion values
- Invalid label geometry such as non-positive boxes
- Duplicate track ID at the same timestamp
- Unrealistic trajectory speed
- Dataset diff regression, such as removed sensors or increased warning/error counts

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

DatasetLint requires Python 3.10 or newer. On macOS, the system `python3` may be
Python 3.9; install a newer interpreter first, for example:

```bash
brew install python@3.11
```

Source install:

```bash
python3.11 -m pip install -e ".[dev]"
```

After a public PyPI release is published and ownership is verified:

```bash
python3.11 -m pip install datasetlint
```

## CLI Usage

The `examples/...` paths below assume a source checkout. If you installed the
wheel only, replace them with paths to datasets on your machine.

```bash
datasetlint examples/minimal_dataset
datasetlint lint examples/minimal_dataset
datasetlint examples/minimal_dataset --checks labels
datasetlint examples/minimal_dataset --checks sync
datasetlint examples/minimal_dataset --adapter auto
datasetlint examples/minimal_dataset --format json
datasetlint examples/minimal_dataset --format markdown
datasetlint report examples/bad_dataset --out report.md
datasetlint report examples/bad_dataset --out report.html
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
html = report.to_html()

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
max_pairwise_sync_gap_sec: 0.05
max_timestamp_gap_sec: 0.5
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

`timestamp_gap_threshold_sec` controls the general timestamp check across all loaded CSV files.
`max_timestamp_gap_sec` controls sync diagnostics and stats for burst-sized gaps in sensor streams.

## Folder Dataset Contract

At minimum, a folder dataset includes `metadata.json`, `calibration.json`, and CSV files under
`sensors/`, `labels/`, or `trajectories/`.

```json
{
  "dataset_name": "sample_log",
  "version": "0.1",
  "sensors": ["camera_front", "imu", "gps"],
  "duration_sec": 0.2
}
```

Camera sensor CSVs require these columns:

```csv
timestamp,path,width,height
0.0,images/000001.jpg,1280,720
```

`filename` is accepted as an alias for `path` when a camera CSV does not already include `path`.
IMU CSVs require `timestamp,ax,ay,az,gx,gy,gz`; GPS CSVs require `timestamp,lat,lon,alt`.

## Example Output

```text
DatasetLint report for /path/to/dataset: failed with 3 issue(s) (error=2, warning=1, info=0).
```

JSON, Markdown, and static HTML outputs are available through `--format`.
Generated sample reports live under `examples/reports/`.

Issue row numbers use spreadsheet-style 1-based rows: the CSV header is row 1 and the first
data row is row 2.

## Feature Overview

- Label consistency checks validate `labels/detections.csv` for required columns, confidence range, positive boxes, duplicate `(timestamp, track_id)` rows, class switches, short tracks, missing in-track timestamps, large box jumps, and abrupt size changes.
- Sensor synchronization checks report per-sensor timing, inferred rates, overlap duration, pairwise timestamp gaps, missing frame bursts, and frequency jitter.
- `datasetlint stats` computes dataset distributions for sensors, labels, tracks, trajectories, missing frames, and issue severity counts.
- `datasetlint diff` compares two datasets and classifies regressions such as removed sensors, frame-count drops, duration drops, calibration changes, disappeared label classes, and increased issue counts.
- `datasetlint adapters` reports adapter detection, validation mode, checked surface, unchecked surface, and limitations. The folder adapter is fully supported; MCAP, ROS bag, Waymo, NuScenes, KITTI, COCO, and Hugging Face adapters are index-level or manifest-level in v0 and raise clear `NotImplementedError` messages for deep parsing.

## Contributing

Keep v0.1 focused on pure Python, typed APIs, local files, and useful error messages. Run:

```bash
pytest
ruff check .
mypy datasetlint
```

DatasetLint is MIT licensed.
