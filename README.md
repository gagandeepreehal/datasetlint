# DatasetLint

[![CI](https://github.com/gagandeepreehal/datasetlint/actions/workflows/ci.yml/badge.svg)](https://github.com/gagandeepreehal/datasetlint/actions/workflows/ci.yml)
[![Docs](https://github.com/gagandeepreehal/datasetlint/actions/workflows/docs.yml/badge.svg)](https://github.com/gagandeepreehal/datasetlint/actions/workflows/docs.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

DatasetLint catches timestamp drift, missing frames, broken calibration, invalid labels, and trajectory anomalies before they poison Physical AI training and evaluation pipelines.

DatasetLint is a lightweight, standalone Python library for validating folder-based robotics datasets. It runs without robots, simulators, GPUs, ROS, cloud services, or large models.

Documentation: https://gagandeepreehal.github.io/datasetlint/

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
python3.11 -m pip install -e ".[dev]"
```

```bash
python -m pip install -e ".[dev]"
```

The project is prepared for a future PyPI release, but this README does not assume one has been
published. After publication, the intended install command is `python -m pip install datasetlint`.

For local development:

```bash
python -m pip install -e ".[dev,docs]"
```

## CLI Usage

```bash
datasetlint lint examples/minimal_dataset
datasetlint report examples/minimal_dataset --out report.json
datasetlint examples/minimal_dataset
datasetlint examples/minimal_dataset --checks labels
datasetlint examples/minimal_dataset --checks sync
datasetlint examples/minimal_dataset --adapter auto
datasetlint examples/minimal_dataset --format json
datasetlint examples/minimal_dataset --format markdown
datasetlint lint examples/broken_dataset --fail-on error
datasetlint stats examples/minimal_dataset --format console
datasetlint stats examples/minimal_dataset --format json
datasetlint diff examples/minimal_dataset examples/broken_dataset
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

`timestamp_gap_threshold_sec` controls both the general timestamp gap check and sensor-stream
burst-gap diagnostics.
Unknown or removed config keys fail validation so stale `datasetlint.yaml` files are not silently
ignored.

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

JSON and Markdown outputs are available through `--format`.

Issue row numbers use spreadsheet-style 1-based rows: the CSV header is row 1 and the first
data row is row 2.

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

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, style, tests, and extension guidance.

## Roadmap

- Keep the folder adapter stable and documented.
- Add deeper robotics-format adapters only when they can be tested with small local fixtures.
- Expand report schemas without breaking existing JSON consumers.
- Keep checks deterministic and offline.

## Limitations

- DatasetLint validates local file structure and consistency; it does not certify dataset safety,
  model readiness, policy compliance, or sensor physical correctness.
- MCAP, ROS bag, NuScenes, and Waymo adapters are detection-only in v0.
- The YAML config reader intentionally supports a small key-value subset.

## Citation

If DatasetLint helps your work, cite the repository metadata in [CITATION.cff](CITATION.cff).

DatasetLint is MIT licensed.
