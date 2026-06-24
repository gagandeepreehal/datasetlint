# DatasetLint

DatasetLint validates local robotics and physical AI datasets before they enter training, evaluation, or analysis pipelines.

It is intentionally small:

- Python 3.10+
- local files in, report out
- CLI and importable Python API
- no ROS, simulator, GPU, cloud, or model dependency
- native support for the folder CSV/JSON dataset format

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
- [Stats](stats.md)
- [Diff](diff.md)
- [Adapters](adapters.md)

## Maintainer And Contributor Docs

- [Development](development.md)
- [Roadmap](roadmap.md)
- [Release](release.md)
- [Release Checklist](release-checklist.md)

## Current Status

DatasetLint v0.1 supports deep rule validation for its native folder format and normalized adapter manifests for generic folders, COCO, KITTI, nuScenes, Waymo, ROS bag, MCAP, and Hugging Face datasets. Waymo, ROS bag, and MCAP default to lightweight index-only manifests unless optional parser dependencies are installed.
