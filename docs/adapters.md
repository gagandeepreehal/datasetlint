# Adapters

DatasetLint v0 keeps the native folder format as the fully supported adapter and
adds lightweight detection for common robotics dataset containers.

Commands using `examples/...` assume a source checkout. For wheel-only installs,
replace them with paths to local datasets.

```bash
datasetlint adapters examples/minimal_dataset
datasetlint examples/minimal_dataset --adapter folder
datasetlint examples/minimal_dataset --adapter auto
```

Python:

```python
from datasetlint.adapters import get_adapter

adapter = get_adapter("examples/minimal_dataset", "auto")
metadata = adapter.load_metadata("examples/minimal_dataset")
```

## Folder Adapter

`FolderAdapter` fully supports the current DatasetLint layout:

```text
metadata.json
calibration.json
sensors/*.csv
labels/detections.csv
trajectories/*.csv
```

It can load metadata, sensor listings, timestamps, labels, trajectories, and
calibration. Reports mark this as `deep` validation.

## Coverage Modes

Validation reports include adapter coverage:

- `deep`: native DatasetLint folder validation with checks over loaded JSON and
  CSV tables.
- `manifest-level`: manifest files can be parsed or inspected, but common deep
  robotics rules do not yet run over that format.
- `index-level`: DatasetLint detects likely files or directories and records
  what was present, but it does not parse the format deeply.

## Non-Native Adapters

The following adapters detect likely dataset inputs but do not deeply parse them
in v0:

| Adapter | Mode | Checked | Not Checked |
| --- | --- | --- | --- |
| `MCAPAdapter` | index-level | `.mcap` file presence and size metadata | channels, schemas, message timestamps, sync, calibration, labels, trajectories |
| `ROSBagAdapter` | index-level | `.bag` file presence | ROS connections, message timestamps, sync, calibration topics, labels, trajectories |
| `WaymoAdapter` | index-level | `.tfrecord` file presence | TFRecord parsing, Waymo frame protos, timestamps, calibration, labels, trajectories |
| `NuScenesAdapter` | index-level | version directory markers and core metadata filename presence | relational schema, sample data references, ego poses, calibration, annotations, sync |
| `KITTIAdapter` | index-level | common KITTI directory markers | calibration contents, image/lidar matching, timestamps, label geometry, trajectories |
| `COCOAdapter` | manifest-level | COCO JSON parseability and top-level `images`/`annotations` keys | image existence, taxonomy semantics, robotics timestamps, sync, calibration, trajectories |
| `HuggingFaceAdapter` | manifest-level | metadata files and Arrow or Parquet shard presence | feature semantics, media references, robotics timestamps, sync, calibration, labels, trajectories |

Deep parsing raises `NotImplementedError` with an actionable message. Convert
these datasets to the folder CSV format before linting with v0, or add an
optional parser-backed adapter in a future release.
