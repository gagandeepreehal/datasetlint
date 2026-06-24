# Adapters

Adapters detect or load dataset formats. The folder adapter is the only adapter that deeply loads data in v0.1.

```bash
datasetlint adapters examples/minimal_dataset
datasetlint examples/minimal_dataset --adapter folder
datasetlint examples/minimal_dataset --adapter auto
```

## Status Table

| Adapter | Status | Detection | Deep validation |
| --- | --- | --- | --- |
| `folder` | supported | folder with `metadata.json`, `sensors/`, `labels/`, or `trajectories/` | yes |
| `mcap` | detection-only | `.mcap` file or folder containing `.mcap` files | no |
| `rosbag` | detection-only | `.bag` file or folder containing `.bag` files | no |
| `nuscenes` | detection-only | likely NuScenes metadata files or `v1.0-*` structure | no |
| `waymo` | detection-only | `.tfrecord` file or folder containing `.tfrecord` files | no |

Detection-only adapters raise `NotImplementedError` for deep parsing. Convert those datasets to the native folder format before linting with v0.1.

## Python API

```python
from datasetlint.adapters import detect_adapters, get_adapter

for detection in detect_adapters("examples/minimal_dataset"):
    print(detection.name, detection.can_load, detection.message)

adapter = get_adapter("examples/minimal_dataset", "auto")
metadata = adapter.load_metadata("examples/minimal_dataset")
```

## Adapter Interface

Custom adapters subclass `DatasetAdapter`:

```python
from datasetlint.adapters.base import DatasetAdapter

class MyAdapter(DatasetAdapter):
    name = "my-format"

    def can_load(self, path):
        ...
```

The interface includes:

- `can_load(path)`
- `load_metadata(path)`
- `list_sensors(path)`
- `load_timestamps(path, sensor_name)`
- `load_labels(path)`
- `load_trajectory(path)`
- `load_calibration(path)`

Register adapters in `datasetlint/adapters/__init__.py` before documenting them as available.

## Current Limitations

- Adapter plugins are not dynamically discovered.
- Non-folder adapters are detection-only.
- Adapter compatibility tests are limited to tiny fixtures.
- There is no automatic conversion pipeline from MCAP, ROS bag, NuScenes, or Waymo to the folder format.
