# Adapters

Adapters let DatasetLint inspect common robotics, autonomous-driving, vision, and physical-AI dataset formats without requiring users to convert everything into the native CSV/JSON folder layout first.

The existing lint rules still run against the native `folder` adapter. The newer adapters produce a normalized `DatasetManifest` for discovery, inspection, validation, and export.

## Which Command Should I Use?

| Need | Command |
| --- | --- |
| See installed and discoverable adapters | `datasetlint adapters list` |
| Ask DatasetLint what matches a path | `datasetlint adapters detect DATASET_PATH` |
| Print a summarized manifest | `datasetlint inspect DATASET_PATH --adapter NAME` |
| Validate an adapter manifest for CI | `datasetlint validate DATASET_PATH --adapter NAME --format json` |
| Save the normalized manifest | `datasetlint export-manifest DATASET_PATH --adapter NAME --output manifest.json` |
| Parse MCAP, ROS bag, or Waymo metadata instead of file-only indexing | `datasetlint validate DATASET_PATH --adapter NAME --deep` |

Use `inspect` when you are exploring a new dataset. Use `validate` when the
result should pass or fail a job.

## Commands

```bash
datasetlint adapters list
datasetlint adapters detect DATASET_PATH
datasetlint adapters DATASET_PATH
datasetlint inspect DATASET_PATH --adapter coco
datasetlint inspect DATASET_PATH --auto-detect
datasetlint validate DATASET_PATH --adapter kitti
datasetlint validate DATASET_PATH --adapter mcap --deep
datasetlint inspect DATASET_PATH --adapter waymo --deep --max-rows 1000
datasetlint validate hf://namespace/dataset --adapter huggingface --split train --max-rows 1000
datasetlint export-manifest DATASET_PATH --adapter nuscenes --output manifest.json
```

All adapter commands support `--format console`, `--format json`, and `--format markdown` except `export-manifest`, which writes JSON to `--output`. `inspect`, `validate`, and `export-manifest` also accept `--deep` for parser-backed MCAP, ROS bag, and Waymo metadata when the matching optional extra is installed. If `validate --deep` cannot run because an optional parser is missing or cannot parse the file, adapter validation reports `valid: false` in the requested output format and exits non-zero through the CLI.

## Common Workflows

### Validate A Local COCO Or KITTI Dataset

```bash
datasetlint adapters detect /data/coco/train2017
datasetlint validate /data/coco/train2017 --adapter coco --format json

datasetlint validate /data/kitti/object --adapter kitti
```

### Inspect Argoverse 2 Or LeRobot

```bash
datasetlint inspect /data/av2/sensor --adapter argoverse2
datasetlint validate /data/av2/sensor --adapter argoverse2 --format json

datasetlint inspect /data/lerobot/push_cube --adapter lerobot
datasetlint validate /data/lerobot/push_cube --adapter lerobot --format json
```

These adapters index the common local files without requiring heavy devkits.
They do not decode parquet, feather, video, image, or lidar payload contents.

### Deep-Validate MCAP And ROS Bag Metadata

```bash
python -m pip install -e ".[mcap]"
datasetlint validate logs/run.mcap --adapter mcap --deep --format json

python -m pip install -e ".[ros]"
datasetlint validate logs/run.bag --adapter rosbag --deep --format json
```

Default mode only indexes files. Deep mode reads topic/channel/schema/timestamp
metadata where the optional parser supports it. It still does not decode every
camera frame, point cloud, or ROS message into semantic native records.

### Use A Third-Party Adapter

Install the package into the same environment as `datasetlint`, then confirm it
is discoverable:

```bash
python -m pip install datasetlint-myformat
datasetlint adapters list
datasetlint validate /data/internal-log --adapter myformat --format json
```

## Supported Datasets

| Dataset / Format | Adapter | Status | Optional Dependency | Notes |
| --- | --- | --- | --- | --- |
| Native DatasetLint folders | `folder` | supported | none | CSV/JSON format used by existing lint checks |
| Generic folders | `generic` | supported | none | Recursive inferred schema for images, point clouds, videos, labels, and timestamps |
| COCO | `coco` | supported | none | Direct JSON parser for images, categories, bbox, and segmentation references |
| KITTI | `kitti` | supported | none | Object and odometry layouts with camera, lidar, labels, calibration, and timestamps |
| Argoverse 2 | `argoverse2` | supported | none | Sensor/scenario file indexing for AV2 logs, annotations, calibration, and timestamped filenames |
| LeRobot | `lerobot` | supported | none | Local LeRobot metadata, episode parquet/jsonl, task metadata, and videos |
| nuScenes | `nuscenes` | supported | optional `nuscenes-devkit` | Direct metadata-table parser available without the devkit |
| Waymo | `waymo` | index + optional deep metadata | optional Waymo/TensorFlow package | TFRecord indexing by default; `--deep` parses frame, label, sensor, and calibration metadata, not image/lidar payload bytes |
| ROS bag | `rosbag` | index + optional deep metadata | optional `rosbags` | ROS1/ROS2 file indexing by default; `--deep` parses topics, message types, counts, and timestamps |
| MCAP | `mcap` | index + optional deep metadata | optional `mcap` | File indexing by default; `--deep` parses channels, schemas, and message timestamps |
| Hugging Face | `huggingface` | supported | `datasets` | Cache/local metadata works without the extra; guarded remote sampling needs `datasets` |

## Validation Coverage

Adapter validation reports expose `validation_mode`, `checked`, `not_checked`, and `limitations` so CI output does not overclaim coverage. They also include `coverage.common_rule_inputs` and `stats.common_rule_stats` when decoded manifest records are available for shared checks such as frame references, timestamp consistency, sensor links, calibration shape, annotation links, and split references.

| Adapter | Validation mode | Checked | Not checked |
| --- | --- | --- | --- |
| `folder` | manifest-level through `datasetlint validate`; deep rules through `datasetlint lint` | native folder manifest extraction and file discovery | deep lint rules in adapter validation output |
| `coco` | manifest-level | JSON structure, image references, category references, basic bbox dimensions | image payload decoding, robotics calibration, sensor synchronization |
| `kitti` | manifest-level | KITTI layout, image/lidar pairing, label row shape, calibration file presence, odometry timestamp monotonicity | binary point cloud contents, camera image decoding, 3D geometry realism |
| `argoverse2` | manifest-level | AV2 log/scenario discovery, camera/lidar/scenario file indexing, annotation/calibration file presence, timestamp consistency when encoded in filenames | feather/parquet payload decoding, map semantics, AV2 metric checks |
| `lerobot` | manifest-level | LeRobot metadata discovery, episode table/video indexing, task metadata indexing, split references | parquet row decoding, video frame decoding, observation/action tensor semantics |
| `nuscenes` | manifest-level | metadata tables, sample/sample_data references, annotation references, calibrated sensor references, common frame/sensor/calibration references when tables are present | sensor payload decoding, map layers, full devkit checks |
| `huggingface` | manifest-level | cache metadata or remote metadata, split/sample availability, sampled image/label/bbox-like rows when rows are loaded | full dataset scan, robotics calibration, sensor synchronization, dataset-specific row schemas |
| `waymo` default | index-level | TFRecord file discovery, file sizes, duplicate segment names | frame parsing, labels, calibration, sensor synchronization |
| `waymo --deep` | deep metadata | TFRecord frame parsing, camera/lidar sensor metadata, label metadata, calibration metadata | camera image bytes, lidar range images, Waymo metric evaluation |
| `rosbag` default | index-level | bag file discovery, ROS2 `metadata.yaml`, empty bag files, lightweight topic summaries when available | message payloads, topic schemas, timestamp synchronization |
| `rosbag --deep` | deep metadata | bag file discovery, topic metadata, message types, message timestamp index | message payload decoding, sensor-specific semantic validation |
| `mcap` default | index-level | MCAP file discovery, file sizes, empty file detection | messages, channels, schemas, timestamp synchronization |
| `mcap --deep` | deep metadata | MCAP file discovery, channel metadata, schema metadata, message timestamp index | message payload decoding, sensor-specific semantic validation |

Common manifest rules only run on records the adapter actually decoded. Waymo index-mode TFRecord placeholders are not counted as common frame or sensor inputs. MCAP and ROS bag `--deep` modes contribute channel/topic timestamp records to common timestamp, dropped-topic, and cross-topic sync checks, but message payloads are still not decoded into camera images, point clouds, poses, or labels. Single-file roots such as one `.bag`, `.mcap`, or `.tfrecord` resolve relative manifest file paths from the file's containing directory.

Adapter availability is about optional dependencies, not validation depth for every code path. For example, `datasetlint adapters list --format json` may report `huggingface` as `available-index-only` when the `datasets` package is missing, while local cache-like Hugging Face metadata can still validate at manifest level. nuScenes is `available` because DatasetLint can parse metadata JSON tables directly; the optional devkit is not required for the current manifest-level checks.

Deep native rule validation currently means the DatasetLint folder rule engine. Adapter `--deep` mode parses external-format metadata into manifests and runs the shared manifest-rule layer where possible; it does not yet run every native rule over those manifests.

## Output And Exit Codes

Adapter validation exits with:

- `0` when the adapter validation report is valid
- `1` when validation produces errors, including missing required parser
  dependencies for a requested deep validation
- `2` for usage errors such as an unknown adapter name or invalid command

When `--format json` or `--format markdown` is requested, validation failures
are emitted in that format. This includes missing optional deep dependencies,
so CI consumers can parse the report instead of scraping plain text.

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

Optional methods can expose sequences, frames, annotations, sensors, calibration, and metadata.

Built-in adapters are registered in `datasetlint/adapters/registry.py`. Third-party packages can register adapters without forking DatasetLint by exposing a `datasetlint.adapters` entry point:

```toml
[project.entry-points."datasetlint.adapters"]
myformat = "datasetlint_myformat:MyFormatAdapter"
```

The entry point may load a `DatasetAdapter` subclass, an adapter instance, or a factory returning one or more adapters. Once installed, `datasetlint adapters list`, `datasetlint inspect --adapter myformat`, and `datasetlint validate --adapter myformat` discover it lazily.

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
- `waymo`, `rosbag`, and `mcap` default to index-only validation unless `--deep` is requested and the matching optional dependency is installed.
- `argoverse2` and `lerobot` index common local files without heavy devkit dependencies, but do not decode parquet, feather, video, image, or lidar payload contents.
- `waymo`, `rosbag`, and `mcap` `--deep` modes decode external-format metadata into common rule inputs where possible, but they do not decode full camera, lidar, or ROS/MCAP message payload semantics yet.
- Hugging Face remote loading requires the `datasets` extra and sampling safeguards; it does not scan entire remote datasets by default. Sampled label/bbox-like columns are exposed as common annotation inputs, but full dataset-specific row schemas remain best-effort.
