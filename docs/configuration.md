# Configuration

DatasetLint uses defaults when no config is provided. It looks for `datasetlint.yaml` in the dataset folder, or accepts an explicit path:

```bash
datasetlint examples/minimal_dataset --config examples/minimal_dataset/datasetlint.yaml
```

Python callers can pass a config path, dictionary, or `LintConfig` object.

## Supported File Shape

Config files are parsed as YAML with PyYAML. Lists, nested maps, quoted strings,
comments, anchors, and normal YAML scalar types are supported. Unknown keys are
rejected so stale configs do not silently pass.

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
rules:
  enabled: null
  disabled: []
  severity: {}
expected_sensor_rates:
  camera_front: 10.0
  camera_rear: 10.0
  imu: 100.0
  gps: 10.0
```

## Rule Selection

Use `rules.enabled` to run only named groups or individual check functions. Use
`rules.disabled` to remove noisy checks from whichever set would otherwise run.
Names can be group names such as `calibration`, `labels`, and `sync`, or concrete
check function names such as `check_sensor_frequency`.

```yaml
rules:
  enabled:
    - calibration
    - labels
  disabled:
    - check_sensor_frequency
```

The CLI `--checks` option and Python `checks=` argument still work. When they are
provided, they choose the base rule set and `rules.disabled` still removes checks
from that base set.

```bash
datasetlint examples/minimal_dataset --checks labels,sync
```

## Severity Overrides

Use `rules.severity` to override native lint issue severity by check name. This
is useful when CI should record a known issue without failing on it.

```yaml
rules:
  severity:
    check_large_timestamp_gaps: info
    check_pairwise_sync_gap: warning
```

Overrides preserve the original severity in `issue.metadata.original_severity`.
`issue_regression_severity` remains the separate setting for dataset diff
regression classification.

Use CLI failure thresholds to make warnings fail CI:

```bash
datasetlint examples/minimal_dataset --fail-on warning
```
