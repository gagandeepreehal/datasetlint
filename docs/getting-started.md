# Getting Started

DatasetLint runs locally and needs Python 3.10 or newer. The fastest useful
path is to install from this checkout, run one passing fixture, run one failing
fixture, then choose the native-folder, adapter, or CI command that matches your
dataset.

!!! tip "Use a supported Python explicitly"
    On macOS, the ambient `python3` can still be Python 3.9. Use `python3.10`,
    `python3.11`, or `python3.12` when creating the virtual environment.

## 1. Install From This Checkout

```bash
git clone https://github.com/gagandeepreehal/datasetlint.git
cd datasetlint
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev,docs]"
datasetlint --version
```

Use `python3.10`, `python3.11`, or `python3.12` if that is the executable name
on your machine. The macOS system `python3` can be Python 3.9, which is too old
for this project.

## 2. Run The Smoke Loop

```bash
datasetlint lint examples/minimal_dataset
datasetlint examples/minimal_dataset
datasetlint examples/minimal_dataset --format json > minimal-report.json
```

The console output should say the dataset passed with zero issues. The JSON file
is the shape to use in CI or downstream tools.

## 3. Run One Failing Dataset

```bash
datasetlint examples/bad_dataset
datasetlint examples/bad_dataset --format json
datasetlint report examples/bad_dataset --out datasetlint-report.html
```

This fixture intentionally fails. Use it to see the location fields DatasetLint
emits: `file`, `row`, `check_name`, `message`, and `metadata.suggestion`.

| Fixture | Expected Result | Why It Exists |
| --- | --- | --- |
| `examples/minimal_dataset` | pass | Shows the smallest healthy native folder |
| `examples/bad_dataset` | fail | Shows broad issue output across files, metadata, timestamps, labels, calibration, and trajectories |
| `examples/invalid_missing_metadata` | fail | Shows a missing required file |
| `examples/invalid_timestamp_drift` | fail with `--fail-on warning` | Shows timestamp and frequency policy tuning |
| `examples/invalid_label_consistency` | fail | Shows label consistency issues |

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

Adapters are for datasets that are not already in the native folder layout.
Start with detection or inspection before deciding whether validation is strict
enough for your workflow:

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

Start by saving a report artifact, then decide whether warnings should fail the
build. Keep the final validation command as the step that controls CI status.

```bash
datasetlint report DATASET_PATH --out datasetlint-report.json
datasetlint DATASET_PATH --fail-on warning
```

Use [Troubleshooting](troubleshooting.md) when a run fails and [CI Templates](ci.md)
when you want a copy-paste GitHub Actions job.

## 7. Know The Command Boundary

DatasetLint has one Typer entry point. These are positional command words, not a
separate nested CLI tree:

- `lint`
- `report`
- `stats`
- `diff`
- `adapters`
- `inspect`
- `validate`
- `export-manifest`

The shorthand `datasetlint DATASET_PATH` still validates a native folder
dataset. Invalid usage, unknown check groups, bad adapter names, and invalid
config files exit with code `2`.
