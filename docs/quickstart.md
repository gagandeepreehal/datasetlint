# Quickstart

Install the package:

```bash
pip install datasetlint
```

Run the CLI:

```bash
datasetlint examples/minimal_dataset
datasetlint examples/minimal_dataset --format json
datasetlint examples/minimal_dataset --format markdown
datasetlint examples/minimal_dataset --checks labels
datasetlint examples/minimal_dataset --checks sync
datasetlint stats examples/minimal_dataset
datasetlint diff examples/minimal_dataset examples/bad_dataset
datasetlint adapters examples/minimal_dataset
```

Use the Python API:

```python
from datasetlint import compare_datasets, compute_dataset_stats, lint_dataset

report = lint_dataset("examples/minimal_dataset")
print(report.summary())

stats = compute_dataset_stats("examples/minimal_dataset")
diff = compare_datasets("examples/minimal_dataset", "examples/bad_dataset")
```

Configure thresholds with `datasetlint.yaml` in the dataset folder:

```yaml
timestamp_gap_threshold_sec: 0.5
max_timestamp_gap_sec: 0.5
max_pairwise_sync_gap_sec: 0.05
label_max_position_jump_px: 200
label_max_size_change_ratio: 3.0
label_min_track_length: 3
max_speed_mps: 70
max_accel_mps2: 12
expected_sensor_rates:
  camera_front: 10
  imu: 100
  gps: 10
```
