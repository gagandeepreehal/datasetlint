# Getting Started

DatasetLint runs locally and needs Python 3.10 or newer. The fastest path is:
install from this checkout, run the passing fixture, run the failing fixture,
then add the config or adapter command that matches your dataset.

## 1. Install From This Checkout

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev,docs]"
datasetlint --version
```

Use `python3.10`, `python3.11`, or `python3.12` if that is the executable name
on your machine. The macOS system `python3` can be Python 3.9, which is too old
for this project.

## 2. Run One Passing Dataset

```bash
datasetlint lint examples/minimal_dataset
datasetlint examples/minimal_dataset --format json
```

The console output should say the dataset passed with zero issues. The JSON
output is the shape to use in CI or downstream tools.

## 3. Run One Failing Dataset

```bash
datasetlint examples/bad_dataset
datasetlint examples/bad_dataset --format json
datasetlint report examples/bad_dataset --out datasetlint-report.html
```

This fixture intentionally fails. Use it to see the location fields DatasetLint
emits: `file`, `row`, `check_name`, `message`, and `metadata.suggestion`.

## 4. Choose Checks For Your Team

Use `--checks` for a quick one-off run:

```bash
datasetlint DATASET_PATH --checks calibration,labels
```

Use `datasetlint.yaml` when the policy should live with the dataset:

```yaml
rules:
  enabled:
    - calibration
    - labels
  disabled:
    - check_sensor_frequency
  severity:
    check_large_timestamp_gaps: info
```

Then run:

```bash
datasetlint DATASET_PATH --config DATASET_PATH/datasetlint.yaml
```

See [Configuration](configuration.md) for more recipes.

## 5. Inspect External Formats

Adapters are for datasets that are not already in the native folder layout:

```bash
datasetlint adapters list
datasetlint adapters detect tests/fixtures/coco_dataset
datasetlint inspect tests/fixtures/coco_dataset --adapter coco
datasetlint validate tests/fixtures/kitti_object --adapter kitti
```

For MCAP and ROS bag logs, install the matching extra before deep validation:

```bash
python -m pip install -e ".[mcap]"
datasetlint validate logs/run.mcap --adapter mcap --deep --format json

python -m pip install -e ".[ros]"
datasetlint validate logs/run.bag --adapter rosbag --deep --format json
```

Deep adapter validation reports missing optional dependencies and parser
failures in the requested output format, so JSON consumers do not need to parse
plain-text error strings.

## 6. Add A CI Gate

Start with JSON or HTML artifacts, then decide whether warnings should fail the
build:

```bash
datasetlint report DATASET_PATH --out datasetlint-report.json
datasetlint DATASET_PATH --fail-on warning
```

Use [Troubleshooting](troubleshooting.md) when a run fails and [CI Templates](ci.md)
when you want a copy-paste GitHub Actions job.
