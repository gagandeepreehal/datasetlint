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

Recommended layout:

```text
my_dataset/
  datasetlint.yaml
  metadata.json
  calibration.json
  sensors/
```

Then run:

```bash
datasetlint my_dataset
```

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

## Common Recipes

### Run Only Calibration And Labels

This is useful for a new dataset where sensor-frequency policy is not stable
yet, but calibration and labels must be enforced from day one:

```yaml
rules:
  enabled:
    - calibration
    - labels
  disabled:
    - check_sensor_frequency
```

### Keep Timestamp Gaps Visible But Non-Blocking

```yaml
rules:
  severity:
    check_large_timestamp_gaps: info
```

The issue still appears in reports, and the original severity is preserved in
`issue.metadata.original_severity`.

### Make CI Fail On Warnings

Use config for the policy and `--fail-on warning` for the CI threshold:

```bash
datasetlint DATASET_PATH --config DATASET_PATH/datasetlint.yaml --fail-on warning
```

### Tune Expected Sensor Rates

```yaml
frequency_tolerance_fraction: 0.25
expected_sensor_rates:
  camera_front: 30.0
  camera_rear: 30.0
  imu: 200.0
  lidar_top: 10.0
```

If a stream is intentionally bursty, disable only the noisy rule instead of the
whole `sensors` group:

```yaml
rules:
  disabled:
    - check_sensor_frequency
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

## Finding Rule Names

Use [Rules](rules.md) as the reference list. The stable rule names are the
function names in the left column, such as:

- `check_sensor_frequency`
- `check_large_timestamp_gaps`
- `check_pairwise_sync_gap`
- `check_label_geometry`
- `check_quaternion_norm`

Group names are broader shortcuts: `files`, `metadata`, `timestamps`, `sensors`,
`sync`, `calibration`, `labels`, `trajectories`, and `all`.

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

## Invalid Configs

DatasetLint rejects unknown keys with exit code `2`. This prevents old config
names from silently changing validation behavior. If a config fails to load:

1. Check the spelling against the defaults above.
2. Check nested YAML indentation under `rules`.
3. Re-run with `--format json` only after the config parses; usage errors are
   intentionally reported as concise CLI errors.
