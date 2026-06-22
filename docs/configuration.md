# Configuration

DatasetLint uses defaults when no config is provided. It looks for `datasetlint.yaml` in the dataset folder, or accepts an explicit path:

```bash
datasetlint examples/minimal_dataset --config examples/minimal_dataset/datasetlint.yaml
```

Python callers can pass a config path, dictionary, or `LintConfig` object.

## Supported File Shape

The config reader supports a simple YAML subset:

- scalar `key: value` entries
- one-level maps such as `expected_sensor_rates`
- comments after `#`

It does not support lists, anchors, multiline strings, or nested maps beyond one level.

Unknown keys are rejected.

## Defaults

```yaml
timestamp_gap_threshold_sec: 0.5
frequency_tolerance_fraction: 0.30
missing_frame_gap_multiplier: 1.5
max_speed_mps: 70.0
max_accel_mps2: 12.0
stationary_distance_threshold_m: 0.05
duration_tolerance_sec: 1.0
label_max_position_jump_px: 200.0
label_max_size_change_ratio: 3.0
label_min_track_length: 3
label_class_switch_threshold: 0
max_pairwise_sync_gap_sec: 0.05
min_overlap_ratio: 0.8
frequency_jitter_ratio: 0.2
frame_count_drop_ratio_warning: 0.1
duration_drop_ratio_warning: 0.1
issue_regression_severity: warning
expected_sensor_rates:
  camera_front: 10.0
  camera_rear: 10.0
  imu: 100.0
  gps: 10.0
```

## Rule Selection

There is no config-file rule enable/disable system in v0.1. Use the CLI `--checks` option or Python `checks=` argument:

```bash
datasetlint examples/minimal_dataset --checks labels,sync
```

```python
from datasetlint import lint_dataset

report = lint_dataset("examples/minimal_dataset", checks=["labels", "sync"])
```

## Severity Overrides

Validation severities are fixed in code in v0.1. The only configurable severity is `issue_regression_severity`, which controls how some diff regressions are classified.

Use CLI failure thresholds to make warnings fail CI:

```bash
datasetlint examples/minimal_dataset --fail-on warning
```
