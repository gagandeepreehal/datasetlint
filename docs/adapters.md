# Adapters

DatasetLint v0 keeps the native folder format as the fully supported adapter and
adds lightweight detection for common robotics dataset containers.

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
calibration.

## Detection-Only Adapters

The following adapters detect likely dataset inputs but do not deeply parse them
in v0:

- `MCAPAdapter` detects `.mcap` files and can list basic file metadata.
- `ROSBagAdapter` detects `.bag` files.
- `NuScenesAdapter` detects `v1.0-*` folder structures or core metadata files.
- `WaymoAdapter` detects `.tfrecord` files.

Deep parsing raises `NotImplementedError` with an actionable message. Convert
these datasets to the folder CSV format before linting with v0.
