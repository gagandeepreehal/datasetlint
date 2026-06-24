# Rules

Rules are deterministic check functions grouped by validation area. Each rule returns `Issue` objects with severity, check name, message, optional file, optional row, and metadata.

## Files

| Rule | Severity | Purpose |
| --- | --- | --- |
| `check_required_files` | error | Require `metadata.json` and `calibration.json` |
| `check_empty_files` | error | Report empty CSV files |
| `check_missing_sensor_files` | error | Ensure declared sensors have matching `sensors/<name>.csv` files |
| `check_broken_paths` | error | Ensure CSV `path` references exist |
| `check_duplicate_filenames` | warning | Report duplicate filenames in the dataset tree |

## Metadata

| Rule | Severity | Purpose |
| --- | --- | --- |
| `check_metadata_schema` | error | Validate `metadata.json` shape |
| `check_declared_sensors_exist` | error | Ensure declared sensors are loaded |
| `check_duration_matches_timestamps` | warning | Compare metadata duration to observed sensor timestamp span |
| `check_dataset_version_present` | warning | Require a non-empty version string |

## Timestamps

| Rule | Severity | Purpose |
| --- | --- | --- |
| `check_monotonic_timestamps` | error | Require monotonically increasing timestamps |
| `check_duplicate_timestamps` | warning | Report duplicate timestamps |
| `check_large_timestamp_gaps` | warning | Report gaps above `timestamp_gap_threshold_sec` |

When timestamp checks and sync checks run together, DatasetLint deduplicates overlapping burst-gap findings.

## Sensors

| Rule | Severity | Purpose |
| --- | --- | --- |
| `check_sensor_columns` | error | Require sensor-specific columns |
| `check_sensor_dimensions` | error | Validate camera width and height |
| `check_sensor_frequency` | warning | Compare observed rate to `expected_sensor_rates` |
| `check_missing_frames` | warning | Detect likely missing frames from timestamp gaps |

Column expectations:

- camera: `timestamp`, `path`, `width`, `height`
- IMU: `timestamp`, `ax`, `ay`, `az`, `gx`, `gy`, `gz`
- GPS: `timestamp`, `lat`, `lon`, `alt`
- other sensors: `timestamp`

Camera CSVs may use `filename` as a compatibility alias when `path` is absent.

## Synchronization

| Rule | Severity | Purpose |
| --- | --- | --- |
| `check_sensor_time_overlap` | error or warning | Require overlapping sensor timestamp ranges and warn on low overlap ratio |
| `check_timestamp_offset` | warning | Report stream start offsets above `max_pairwise_sync_gap_sec` |
| `check_pairwise_sync_gap` | warning | Report pairwise median sync gaps above threshold |
| `check_missing_frame_bursts` | warning | Report burst-sized timestamp gaps |
| `check_frequency_stability` | warning | Report frame interval jitter above `frequency_jitter_ratio` |

## Calibration

| Rule | Severity | Purpose |
| --- | --- | --- |
| `check_calibration_exists` | error | Require calibration entries for declared sensors |
| `check_intrinsics_shape` | error | Require camera intrinsics to be 3x3 |
| `check_intrinsics_values` | error | Require finite positive focal lengths |
| `check_extrinsics_shape` | error | Require translation[3] and rotation_quat[4] |
| `check_quaternion_norm` | error | Require normalized quaternions |

## Labels

| Rule | Severity | Purpose |
| --- | --- | --- |
| `check_label_columns` | error | Require detection label columns |
| `check_label_confidence_range` | error | Require confidence in `[0, 1]` |
| `check_label_geometry` | error | Require positive width and height |
| `check_label_timestamps_match_sensor_range` | error | Require labels inside observed sensor time range |
| `check_track_id_consistency` | warning | Report track class switches above threshold |
| `check_label_bbox_jumps` | warning | Report large bounding box center jumps |
| `check_label_missing_timestamps` | warning | Report likely missing labels inside a track |
| `check_duplicate_track_id_timestamp` | error | Report duplicate `track_id` at the same timestamp |
| `check_short_tracks` | warning | Report tracks shorter than `label_min_track_length` |
| `check_label_size_changes` | warning | Report abrupt bounding box size changes |

Detection labels require:

```text
timestamp, track_id, class, x, y, width, height, confidence
```

## Trajectories

| Rule | Severity | Purpose |
| --- | --- | --- |
| `check_trajectory_columns` | error | Require trajectory columns |
| `check_trajectory_finite_values` | error | Require finite numeric values |
| `check_unrealistic_speed` | warning | Report speeds above `max_speed_mps` |
| `check_unrealistic_acceleration` | warning | Report acceleration above `max_accel_mps2` |
| `check_yaw_range` | warning | Require yaw in `[-pi, pi]` |
| `check_stationary_dataset` | warning | Report nearly stationary trajectories |

Trajectory CSVs require:

```text
timestamp, x, y, yaw, vx, vy
```

## Configuration

Thresholds are documented in [Configuration](configuration.md). Validation issue severities are fixed in code except `issue_regression_severity`, which applies to diff regression classification.
