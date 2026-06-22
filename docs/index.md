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
- [Release Checklist](release-checklist.md)

## Current Status

DatasetLint v0.1 supports deep validation for its native folder format. MCAP, ROS bag, NuScenes, and Waymo adapters are detection-only in the current codebase.
