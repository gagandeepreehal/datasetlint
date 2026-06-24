# Configuration

DatasetLint uses defaults unless a `datasetlint.yaml` file is present or a
config path is passed with `--config`.

```yaml
timestamp_gap_threshold_sec: 0.5
max_pairwise_sync_gap_sec: 0.05
expected_sensor_rates:
  camera_front: 10
  imu: 100
```

Unknown keys fail validation so stale configs do not silently change behavior.
The parser intentionally supports simple key-value YAML and nested maps only.
