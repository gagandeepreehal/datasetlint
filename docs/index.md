# DatasetLint

DatasetLint validates local robotics and physical AI datasets before they enter
training, evaluation, or analysis pipelines.

It is intentionally small: local files in, deterministic report out. Use it to
catch schema drift, broken references, timestamp problems, label issues,
calibration mistakes, and adapter ingestion failures while the dataset is still
cheap to fix.

!!! note "Install status"
    DatasetLint currently documents source installs from this repository. Do not
    use `pip install datasetlint` as the default path until a public package
    release exists.

## First Five Minutes

```bash
git clone https://github.com/gagandeepreehal/datasetlint.git
cd datasetlint
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev,docs]"

datasetlint --version
datasetlint examples/minimal_dataset
datasetlint examples/bad_dataset --format json
```

`examples/minimal_dataset` should pass. `examples/bad_dataset` should fail and
show the issue fields you will see in real projects.

## Choose Your Path

| Goal | Read This | First Command |
| --- | --- | --- |
| Install and run the examples | [Getting Started](getting-started.md) | `datasetlint examples/minimal_dataset` |
| Validate the native CSV/JSON folder format | [Dataset Format](dataset-format.md) | `datasetlint lint DATASET_PATH` |
| Tune checks or severities | [Configuration](configuration.md) | `datasetlint DATASET_PATH --config DATASET_PATH/datasetlint.yaml` |
| Inspect MCAP, ROS bag, Argoverse 2, LeRobot, COCO, KITTI, or other formats | [Adapters](adapters.md) | `datasetlint inspect DATASET_PATH --adapter auto` |
| Save JSON, Markdown, or HTML artifacts | [Reports](reports.md) | `datasetlint report DATASET_PATH --out datasetlint-report.json` |
| Fix a failing run | [Troubleshooting](troubleshooting.md) | `datasetlint DATASET_PATH --format json` |
| Add a CI gate | [CI Templates](ci.md) | `datasetlint DATASET_PATH --fail-on warning` |
| Call DatasetLint from Python | [Python API](python-api.md) | `from datasetlint import lint_dataset` |
| Work on DatasetLint itself | [Development](development.md) | `make check` |

## What You Get

- Python 3.10+
- local files in, report out
- CLI and importable Python API
- no ROS, simulator, GPU, cloud, or model dependency
- native support for the folder CSV/JSON dataset format
- adapter manifests for common robotics and vision dataset formats
- JSON output and stable exit codes for CI

## Documentation Map

| Section | Best For |
| --- | --- |
| [Start](installation.md) | New users installing from source and running the examples |
| [Use DatasetLint](concepts.md) | Dataset owners configuring checks, reports, stats, and diffs |
| [Integrate](cli.md) | CLI users, Python callers, CI maintainers, and adapter users |
| [Maintain](development.md) | Contributors changing rules, adapters, docs, or release process |

## Common Outputs

| Need | Command |
| --- | --- |
| Human-readable terminal report | `datasetlint DATASET_PATH` |
| JSON for automation | `datasetlint DATASET_PATH --format json` |
| Markdown report | `datasetlint DATASET_PATH --format markdown` |
| Static HTML report | `datasetlint DATASET_PATH --format html > report.html` |
| File artifact with inferred format | `datasetlint report DATASET_PATH --out report.json` |
| Dataset distribution summary | `datasetlint stats DATASET_PATH` |
| Regression check between folders | `datasetlint diff OLD_DATASET NEW_DATASET --fail-on-regression` |

## Exit Codes

| Code | Meaning |
| ---: | --- |
| `0` | Command completed and did not meet the configured failure threshold |
| `1` | Validation failed, adapter validation failed, or diff regressions were found |
| `2` | Invalid command, unknown check or adapter, or invalid config |

## Current Status

DatasetLint v0.1 supports deep rule validation for its native folder format and
normalized adapter manifests for generic folders, COCO, KITTI, Argoverse 2,
LeRobot, nuScenes, Waymo, ROS bag, MCAP, Hugging Face, and plugin-provided
datasets.

Waymo, ROS bag, MCAP, and Hugging Face default to lightweight index/cache
manifests. Install the matching extra and use `--deep` when you need
parser-backed metadata or sampled Hugging Face row diagnostics.
