# DatasetLint

DatasetLint validates local robotics and physical AI datasets before they enter training, evaluation, or analysis pipelines.

It is intentionally small: local files in, deterministic report out. Use it when
you want to catch schema drift, broken references, timestamp problems, label
issues, calibration mistakes, or adapter ingestion failures before a dataset
reaches training or CI.

## Start With The Workflow You Need

| Goal | Read This | First Command |
| --- | --- | --- |
| Install and run the examples | [Getting Started](getting-started.md) | `datasetlint examples/minimal_dataset` |
| Validate the native CSV/JSON folder format | [Dataset Format](dataset-format.md) | `datasetlint lint DATASET_PATH` |
| Run only selected checks or change severities | [Configuration](configuration.md) | `datasetlint DATASET_PATH --config DATASET_PATH/datasetlint.yaml` |
| Inspect MCAP, ROS bag, Argoverse 2, LeRobot, COCO, KITTI, or other formats | [Adapters](adapters.md) | `datasetlint validate DATASET_PATH --adapter auto` |
| Save JSON, Markdown, or HTML artifacts | [Reports](reports.md) | `datasetlint report DATASET_PATH --out report.json` |
| Fix a failing run | [Troubleshooting](troubleshooting.md) | `datasetlint DATASET_PATH --format json` |
| Add a CI gate | [CI Templates](ci.md) | `datasetlint DATASET_PATH --fail-on warning` |

## What You Get

- Python 3.10+
- local files in, report out
- CLI and importable Python API
- no ROS, simulator, GPU, cloud, or model dependency
- native support for the folder CSV/JSON dataset format
- adapter manifests for common robotics and vision dataset formats
- JSON output and stable exit codes for CI

## Start Here

- [Installation](installation.md)
- [Getting Started](getting-started.md)
- [Quickstart](quickstart.md)
- [Dataset Format](dataset-format.md)
- [CLI Reference](cli.md)
- [Python API](python-api.md)

## Core References

- [Concepts](concepts.md)
- [Rules](rules.md)
- [Checks](checks.md)
- [Configuration](configuration.md)
- [Reports](reports.md)
- [Troubleshooting](troubleshooting.md)
- [CI Templates](ci.md)
- [Stats](stats.md)
- [Diff](diff.md)
- [Adapters](adapters.md)
- [Architecture](architecture.md)

## Maintainer And Contributor Docs

- [Development](development.md)
- [Roadmap](roadmap.md)
- [Release](release.md)
- [Release Checklist](release-checklist.md)

## Current Status

DatasetLint v0.1 supports deep rule validation for its native folder format and normalized adapter manifests for generic folders, COCO, KITTI, Argoverse 2, LeRobot, nuScenes, Waymo, ROS bag, MCAP, Hugging Face, and plugin-provided datasets. Waymo, ROS bag, and MCAP default to lightweight index manifests; install the matching extra and use `--deep` for parser-backed metadata.
