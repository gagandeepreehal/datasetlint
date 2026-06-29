# Quickstart

DatasetLint is a lightweight local-first dataset validation, dataset QA, and
robotics data quality toolkit for robotics and Physical AI datasets.

## Install

DatasetLint requires Python 3.10 or newer. On macOS, the system `python3` may be
Python 3.9; install a newer interpreter first:

```bash
brew install python@3.11
```

Use the source checkout path until a public PyPI release is published and
verified:

```bash
python3.11 -m pip install -e ".[dev]"
```

## Try In 60 Seconds

```bash
datasetlint examples/minimal_dataset
datasetlint report examples/bad_dataset --out report.md
datasetlint report examples/bad_dataset --out report.html
```

`examples/minimal_dataset` should pass. `examples/bad_dataset` should fail with
concrete issues such as missing references, duplicate timestamps, invalid
calibration, invalid label geometry, and unrealistic trajectory speed.

## CLI Basics

The `examples/...` paths below assume a source checkout. If you installed only
the wheel, replace them with paths to datasets on your machine.

```bash
datasetlint examples/minimal_dataset
datasetlint lint examples/minimal_dataset
datasetlint examples/minimal_dataset --format json
datasetlint examples/minimal_dataset --format markdown
datasetlint examples/minimal_dataset --format html
datasetlint examples/minimal_dataset --checks labels
datasetlint examples/minimal_dataset --checks sync
datasetlint stats examples/minimal_dataset
datasetlint diff examples/minimal_dataset examples/bad_dataset
datasetlint adapters examples/minimal_dataset
```

Use the Python API:

```python
from datasetlint import compare_datasets, compute_dataset_stats, lint_dataset

report = lint_dataset("examples/minimal_dataset")
print(report.summary())

stats = compute_dataset_stats("examples/minimal_dataset")
diff = compare_datasets("examples/minimal_dataset", "examples/bad_dataset")
```

Configure thresholds with `datasetlint.yaml` in the dataset folder:

```yaml
timestamp_gap_threshold_sec: 0.5
max_pairwise_sync_gap_sec: 0.05
max_timestamp_gap_sec: 0.5
label_max_position_jump_px: 200
label_max_size_change_ratio: 3.0
label_min_track_length: 3
max_speed_mps: 70
max_accel_mps2: 12
expected_sensor_rates:
  camera_front: 10
  imu: 100
  gps: 10
```

`timestamp_gap_threshold_sec` is the general timestamp gap threshold. `max_timestamp_gap_sec`
is used by synchronization diagnostics and stats for sensor-stream burst gaps.

A minimal `metadata.json` uses `dataset_name`:

```json
{
  "dataset_name": "sample_log",
  "version": "0.1",
  "sensors": ["camera_front"],
  "duration_sec": 0.2
}
```

Camera sensor CSVs require `timestamp,path,width,height`. `filename` is also accepted as an
alias for `path` if `path` is not present:

```csv
timestamp,path,width,height
0.0,images/000001.jpg,1280,720
```

## Adapter Expectations

Deep validation works best on the native DatasetLint folder format. MCAP, ROS
bag, Waymo, NuScenes, KITTI, COCO, and Hugging Face inputs are currently
index-level or manifest-level unless optional parsers are implemented later.
