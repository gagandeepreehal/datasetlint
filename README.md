# DatasetLint

[![CI](https://github.com/gagandeepreehal/datasetlint/actions/workflows/ci.yml/badge.svg)](https://github.com/gagandeepreehal/datasetlint/actions/workflows/ci.yml)
[![Docs](https://github.com/gagandeepreehal/datasetlint/actions/workflows/docs.yml/badge.svg)](https://github.com/gagandeepreehal/datasetlint/actions/workflows/docs.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

DatasetLint is a lightweight, local-first linting toolkit for robotics and physical AI datasets. It checks dataset structure, metadata, timestamps, labels, calibration, trajectories, simple distribution stats, dataset diffs, and adapter compatibility before bad data reaches training or evaluation.

It runs locally on folder-based datasets with Python, CSV, and JSON. It does not require robots, simulators, GPUs, ROS, cloud services, or model runtimes.

Documentation: [DatasetLint docs](https://gagandeepreehal.github.io/datasetlint/)

## Why This Exists

Robotics datasets often fail in quiet ways:

- dataset schema drift between collection, labeling, and training
- broken or duplicated timestamps
- missing metadata, calibration, sensor files, or referenced frames
- inconsistent labels and track IDs
- silent frame drops or distribution shifts
- adapter-specific ingestion problems discovered too late

DatasetLint catches those issues at the dataset folder boundary so teams can fail fast in local development and CI.

## Who It Is For

- robotics ML engineers validating training and evaluation data
- physical AI teams maintaining local dataset collections
- dataset maintainers reviewing schema and metadata quality
- researchers sharing small reproducible datasets
- CI users blocking bad dataset changes before merge

## Current Capabilities

DatasetLint v0.1 supports deep rule validation for the native folder dataset format and normalized manifest workflows for common external dataset formats. Current capabilities include:

- required `metadata.json` and `calibration.json`
- empty CSV files, broken referenced paths, and duplicate filenames
- metadata schema, declared sensors, duration consistency, and version presence
- monotonic, duplicate, and large-gap timestamps
- camera, IMU, GPS, and generic sensor columns
- camera dimensions, expected sensor rates, and likely missing frames
- sensor time overlap, start offsets, pairwise sync gaps, burst gaps, and jitter
- calibration intrinsics, extrinsics, and quaternion normalization
- label columns, confidence, geometry, timestamp range, class switches, duplicate tracks, short tracks, missing labels, box jumps, and size changes
- trajectory columns, finite values, speed, acceleration, yaw range, and stationary motion
- dataset statistics and folder-to-folder diffs
- normalized adapter manifests for generic folders, COCO, KITTI, nuScenes, Waymo, ROS bag, MCAP, and Hugging Face datasets
- adapter validation, inspection, discovery, and manifest export commands

## Installation

DatasetLint requires Python 3.10 or newer. Install from source:

```bash
git clone https://github.com/gagandeepreehal/datasetlint.git
cd datasetlint
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev,docs]"
```

Use `python3.10`, `python3.11`, or `python3.12` if that is the executable name on your machine. The macOS system `python3` may be Python 3.9, which is too old for this project.

This repository has publishing metadata and a publish workflow, but this checkout has no release tags. Until the first PyPI release is published, use the source install above instead of `pip install datasetlint`.

Adapter extras are opt-in so the base install stays lightweight:

```bash
python -m pip install -e ".[adapters]"
python -m pip install -e ".[hf]"
python -m pip install -e ".[mcap]"
python -m pip install -e ".[ros]"
python -m pip install -e ".[nuscenes]"
python -m pip install -e ".[waymo]"
python -m pip install -e ".[all-adapters]"
```

## Quickstart

Validate the passing example dataset:

```bash
datasetlint lint examples/minimal_dataset
datasetlint examples/minimal_dataset
```

Expected result:

```text
DatasetLint report for .../examples/minimal_dataset: passed with 0 issue(s) (error=0, warning=0, info=0).
```

Run a focused check group:

```bash
datasetlint examples/minimal_dataset --checks labels
datasetlint examples/minimal_dataset --checks sync
```

Render machine-readable output:

```bash
datasetlint report examples/minimal_dataset --out report.json
datasetlint examples/minimal_dataset --format json
datasetlint examples/minimal_dataset --format markdown
```

Inspect the intentionally failing dataset:

```bash
datasetlint examples/bad_dataset
```

`examples/bad_dataset` exits non-zero because it contains missing files, invalid calibration, timestamp issues, label problems, and trajectory anomalies.

## CLI Usage

DatasetLint exposes one console script:

```bash
datasetlint --help
datasetlint --version
```

Validate a dataset:

```bash
datasetlint lint DATASET_PATH
datasetlint DATASET_PATH
datasetlint DATASET_PATH --checks labels,sync
datasetlint DATASET_PATH --config DATASET_PATH/datasetlint.yaml
datasetlint DATASET_PATH --adapter folder
datasetlint DATASET_PATH --adapter auto
datasetlint DATASET_PATH --format console
datasetlint DATASET_PATH --format json
datasetlint DATASET_PATH --format markdown
datasetlint DATASET_PATH --fail-on warning
```

Write a JSON validation report:

```bash
datasetlint report DATASET_PATH --out report.json
```

Compute statistics:

```bash
datasetlint stats DATASET_PATH
datasetlint stats DATASET_PATH --format json
datasetlint stats DATASET_PATH --format markdown
```

Compare two datasets:

```bash
datasetlint diff OLD_DATASET NEW_DATASET
datasetlint diff OLD_DATASET NEW_DATASET --format json
datasetlint diff OLD_DATASET NEW_DATASET --fail-on-regression
```

Inspect adapter detection:

```bash
datasetlint adapters DATASET_PATH
datasetlint adapters list
datasetlint adapters detect DATASET_PATH
datasetlint adapters DATASET_PATH --format json
```

Inspect, validate, or export normalized manifests for common formats:

```bash
datasetlint inspect DATASET_PATH --adapter coco
datasetlint inspect DATASET_PATH --auto-detect
datasetlint validate DATASET_PATH --adapter kitti
datasetlint validate hf://namespace/dataset --adapter huggingface --split train --max-rows 1000
datasetlint export-manifest DATASET_PATH --adapter nuscenes --output manifest.json
```

Exit codes:

- `0`: command completed and did not meet the configured failure threshold
- `1`: validation failed the `--fail-on` threshold, or diff regressions were found with `--fail-on-regression`
- `2`: invalid usage, unknown check group, bad adapter, or invalid config

## Python API Usage

```python
from datasetlint import compare_datasets, compute_dataset_stats, lint_dataset
from datasetlint.adapters import detect_adapters, get_adapter, load_dataset, validate_dataset

report = lint_dataset("examples/minimal_dataset")
print(report.summary())
print(report.count_by_severity())
print(report.to_markdown())

label_report = lint_dataset("examples/minimal_dataset", checks="labels")
sync_report = lint_dataset("examples/minimal_dataset", checks=["sync"])

stats = compute_dataset_stats("examples/minimal_dataset")
print(stats.frame_counts)

diff = compare_datasets("examples/minimal_dataset", "examples/bad_dataset")
print(diff.summary)

detections = detect_adapters("examples/minimal_dataset")
adapter = get_adapter("examples/minimal_dataset", "auto")

manifest = load_dataset("tests/fixtures/coco_dataset", adapter="coco")
validation = validate_dataset("tests/fixtures/kitti_object", adapter="kitti")
```

Public imports from `datasetlint` are `lint_dataset`, `compare_datasets`, `compute_dataset_stats`, `Issue`, `LintConfig`, `LintReport`, `DatasetStats`, and `DatasetDiffReport`.

## Examples

| Path | Expected result | Demonstrates |
| --- | --- | --- |
| `examples/minimal_dataset` | pass | valid folder dataset with camera, IMU, GPS, labels, calibration, and trajectory |
| `examples/bad_dataset` | fail | broad failure surface used for validation and diff examples |
| `examples/invalid_missing_metadata` | fail | missing `metadata.json` |
| `examples/invalid_timestamp_drift` | fail with `--fail-on warning` | timestamp gaps and frequency drift |
| `examples/invalid_label_consistency` | fail | track class switch and duplicate track timestamp |

See [examples/README.md](examples/README.md) for commands and expected outcomes.

## Configuration

DatasetLint uses defaults when no config is provided. A dataset can include `datasetlint.yaml`, or the CLI can receive `--config path/to/datasetlint.yaml`.

Supported keys:

```yaml
timestamp_gap_threshold_sec: 0.5
frequency_tolerance_fraction: 0.30
missing_frame_gap_multiplier: 1.5
max_speed_mps: 70
max_accel_mps2: 12
stationary_distance_threshold_m: 0.05
duration_tolerance_sec: 1.0
label_max_position_jump_px: 200
label_max_size_change_ratio: 3.0
label_min_track_length: 3
label_class_switch_threshold: 0
max_pairwise_sync_gap_sec: 0.05
min_overlap_ratio: 0.8
frequency_jitter_ratio: 0.2
frame_count_drop_ratio_warning: 0.1
duration_drop_ratio_warning: 0.1
issue_regression_severity: warning
expected_sensor_rates:
  camera_front: 10
  camera_rear: 10
  imu: 100
  gps: 10
```

The config reader intentionally supports a simple YAML subset: scalar `key: value` pairs and one-level maps such as `expected_sensor_rates`. Unknown keys fail validation so stale configs do not silently pass.

## Reports

Validation reports include:

- summary pass/fail state
- issue severity: `error`, `warning`, or `info`
- check name
- file path and 1-based CSV row when available
- message and structured metadata
- stats such as issue counts, sensor counts, and sync diagnostics

Output formats are console, JSON, and Markdown:

```bash
datasetlint examples/minimal_dataset --format console
datasetlint examples/minimal_dataset --format json
datasetlint examples/minimal_dataset --format markdown
```

Issue row numbers use spreadsheet-style rows: the CSV header is row 1 and the first data row is row 2.

## CI Usage

Minimal GitHub Actions example:

```yaml
name: Dataset Lint
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
      - run: python -m pip install -e ".[dev]"
      - run: datasetlint examples/minimal_dataset
```

Use `--fail-on warning` for stricter validation, or `datasetlint diff OLD_DATASET NEW_DATASET --fail-on-regression` when comparing dataset revisions.

## Supported Formats And Adapters

| Dataset / Format | Adapter | Status | Optional Dependency | Notes |
| --- | --- | --- | --- | --- |
| Native DatasetLint folders | `folder` | supported | none | CSV/JSON format used by existing lint checks |
| Generic folders | `generic` | supported | none/`pyyaml` | Recursive inferred schema for images, point clouds, videos, labels, and timestamps |
| COCO | `coco` | supported | none | Direct JSON parser for images, categories, bbox, and segmentation references |
| KITTI | `kitti` | supported | none | Object and odometry layouts with camera, lidar, labels, calibration, and timestamps |
| nuScenes | `nuscenes` | supported | optional `nuscenes-devkit` | Direct metadata-table parser available without the devkit |
| Waymo | `waymo` | index-supported | optional Waymo package | TFRecord indexing by default; full parse remains optional |
| ROS bag | `rosbag` | index-supported | optional `rosbags` | ROS1/ROS2 file indexing and lightweight ROS2 metadata topic summaries |
| MCAP | `mcap` | index-supported | optional `mcap` | File indexing by default; channel/schema parsing is optional |
| Hugging Face | `huggingface` | supported | `datasets` | Cache metadata indexing plus guarded remote sampling |
| Custom adapters | subclass `DatasetAdapter` | experimental | adapter-specific | Implement `detect`, `load`, and `validate`, then register the adapter |

## Limitations

- DatasetLint is not a dataset management platform.
- DatasetLint is not a model evaluation framework.
- DatasetLint is not a simulator or replay tool.
- Current validation is local-first and file-based.
- Existing rule checks still validate the native folder CSV/JSON format; non-folder adapters produce normalized manifests and adapter validation reports.
- Waymo, ROS bag, and MCAP default to safe index-only manifests unless optional parsers are available.
- Hugging Face remote datasets require the `datasets` extra and explicit sampling controls.
- Large-dataset performance has not been benchmarked yet.
- The config reader supports a small YAML subset, not full YAML syntax.
- Report output is file/terminal oriented; there is no report UI yet.

## Roadmap

Near term:

- stronger dataset diff coverage
- more targeted example datasets
- CI templates for common repository layouts
- clearer rule plugin examples

Medium term:

- deeper MCAP, ROS bag, and Waymo optional parser integrations
- conversion helpers from normalized manifests to the native lintable folder format
- richer sensor synchronization checks
- report UI or static HTML output

Long term:

- rule plugin system
- benchmark sample datasets
- performance profiling on larger logs
- adapter compatibility test suite

Non-goals:

- replacing dataset version control systems
- storing or hosting datasets
- running model evaluation
- simulating robotics environments

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) for local setup, tests, linting, type checks, docs, and guidance for adding rules or adapters.

## License

DatasetLint is released under the [MIT License](LICENSE).
