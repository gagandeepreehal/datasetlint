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
```

Use the Python API:

```python
from datasetlint import lint_dataset

report = lint_dataset("examples/minimal_dataset")
print(report.summary())
```

Configure thresholds with `datasetlint.yaml` in the dataset folder:

```yaml
timestamp_gap_threshold_sec: 0.5
max_speed_mps: 70
max_accel_mps2: 12
expected_sensor_rates:
  camera_front: 10
  imu: 100
  gps: 10
```

