# Adapters

Adapters let DatasetLint inspect common robotics, autonomous-driving, vision, and physical-AI dataset formats without requiring users to convert everything into the native CSV/JSON folder layout first.

The existing lint rules still run against the native `folder` adapter. The newer adapters produce a normalized `DatasetManifest` for discovery, inspection, validation, and export.

## Commands

```bash
datasetlint adapters list
datasetlint adapters detect DATASET_PATH
datasetlint adapters DATASET_PATH
datasetlint inspect DATASET_PATH --adapter coco
datasetlint inspect DATASET_PATH --auto-detect
datasetlint validate DATASET_PATH --adapter kitti
datasetlint validate hf://namespace/dataset --adapter huggingface --split train --max-rows 1000
datasetlint export-manifest DATASET_PATH --adapter nuscenes --output manifest.json
```

All adapter commands support `--format console`, `--format json`, and `--format markdown` except `export-manifest`, which writes JSON to `--output`.

## Supported Datasets

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

## Installation Extras

The base package does not install heavy dataset runtimes. Install extras only when needed:

```bash
python -m pip install -e ".[adapters]"
python -m pip install -e ".[hf]"
python -m pip install -e ".[mcap]"
python -m pip install -e ".[ros]"
python -m pip install -e ".[nuscenes]"
python -m pip install -e ".[waymo]"
python -m pip install -e ".[all-adapters]"
```

## Python API

```python
from datasetlint.adapters import (
    detect_adapter,
    detect_adapters,
    list_adapters,
    load_dataset,
    validate_dataset,
)

detections = detect_adapters("tests/fixtures/coco_dataset")
adapter = detect_adapter("tests/fixtures/coco_dataset")
manifest = load_dataset("tests/fixtures/coco_dataset", adapter="coco")
report = validate_dataset("tests/fixtures/kitti_object", adapter="kitti")
```

## Normalized Manifest

Every manifest uses the same internal schema:

- `DatasetManifest`
- `SequenceRecord`
- `FrameRecord`
- `SensorStream`
- `AnnotationRecord`
- `CalibrationRecord`
- `AdapterProvenance`
- `AdapterValidationReport`

Unsupported or unavailable semantics are explicit. Adapters should populate `limitations`, `metadata`, and `provenance.warnings` instead of silently dropping fields.

## Detection Rules

Auto-detection works like this:

- Explicit `--adapter NAME` always selects that adapter.
- `--auto-detect` runs detection across registered adapters.
- If exactly one specialized adapter matches, it is used.
- If multiple specialized adapters match, DatasetLint reports ambiguity and does not choose silently.
- If no specialized adapter matches, `folder` or `generic` can be used as a fallback when they can load the path.

## Adding An Adapter

Create a subclass of `DatasetAdapter` and implement:

- `name`
- `supported_formats`
- `detect(root)` or `can_load(path)`
- `load(root, **kwargs) -> DatasetManifest`
- `validate(root, **kwargs) -> AdapterValidationReport`

Optional methods can expose sequences, frames, annotations, sensors, calibration, and metadata. Register the adapter in `datasetlint/adapters/registry.py`.

## Testing New Adapters

Use tiny synthetic fixtures. Do not commit real large datasets.

Cover:

- adapter registration and list output
- detection for representative layouts
- ambiguous detection
- explicit adapter override
- JSON-serializable manifests
- validation failures for broken references or invalid rows
- CLI `adapters`, `inspect`, `validate`, and `export-manifest`
- optional dependency paths, skipped when dependencies are unavailable

## Current Limitations

- The core rule engine still validates native folder CSV/JSON datasets.
- `waymo`, `rosbag`, and `mcap` default to index-only manifests.
- Hugging Face remote loading requires the `datasets` extra and sampling safeguards.
- Adapter plugins are registered in code, not discovered dynamically from entry points yet.
