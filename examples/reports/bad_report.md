# DatasetLint Report

- Dataset: `examples/bad_dataset`
- Status: `failed`
- Errors: `16`
- Warnings: `15`
- Info: `0`

## Stats

- `adapter`:

```json
{
  "checked": [
    "native DatasetLint folder layout",
    "metadata schema",
    "required files",
    "CSV parseability",
    "broken file references",
    "timestamps and timestamp gaps",
    "sensor synchronization",
    "calibration and camera intrinsics",
    "labels and track consistency",
    "trajectories"
  ],
  "limitations": [
    "Deep validation is designed for the native DatasetLint folder format."
  ],
  "name": "folder",
  "not_checked": [
    "image pixel decoding",
    "point cloud payload decoding",
    "semantic correctness of labels"
  ],
  "validation_mode": "deep"
}
```
- `checks_run`:

```json
[
  "check_required_files",
  "check_empty_files",
  "check_missing_sensor_files",
  "check_broken_paths",
  "check_duplicate_filenames",
  "check_metadata_schema",
  "check_declared_sensors_exist",
  "check_duration_matches_timestamps",
  "check_dataset_version_present",
  "check_monotonic_timestamps",
  "check_duplicate_timestamps",
  "check_large_timestamp_gaps",
  "check_sensor_columns",
  "check_sensor_dimensions",
  "check_sensor_frequency",
  "check_missing_frames",
  "check_sensor_time_overlap",
  "check_timestamp_offset",
  "check_pairwise_sync_gap",
  "check_missing_frame_bursts",
  "check_frequency_stability",
  "check_calibration_exists",
  "check_intrinsics_shape",
  "check_intrinsics_values",
  "check_extrinsics_shape",
  "check_quaternion_norm",
  "check_label_columns",
  "check_label_confidence_range",
  "check_label_geometry",
  "check_label_timestamps_match_sensor_range",
  "check_track_id_consistency",
  "check_label_bbox_jumps",
  "check_label_missing_timestamps",
  "check_duplicate_track_id_timestamp",
  "check_short_tracks",
  "check_label_size_changes",
  "check_trajectory_columns",
  "check_trajectory_finite_values",
  "check_unrealistic_speed",
  "check_unrealistic_acceleration",
  "check_yaw_range",
  "check_stationary_dataset"
]
```
- `config`:

```json
{
  "duration_drop_ratio_warning": 0.1,
  "duration_tolerance_sec": 1.0,
  "expected_sensor_rates": {
    "camera_front": 10.0,
    "camera_rear": 10.0,
    "gps": 10.0,
    "imu": 100.0
  },
  "frame_count_drop_ratio_warning": 0.1,
  "frequency_jitter_ratio": 0.2,
  "frequency_tolerance_fraction": 0.3,
  "issue_regression_severity": "warning",
  "label_class_switch_threshold": 0,
  "label_max_position_jump_px": 200.0,
  "label_max_size_change_ratio": 3.0,
  "label_min_track_length": 3,
  "max_accel_mps2": 12.0,
  "max_pairwise_sync_gap_sec": 0.05,
  "max_speed_mps": 70.0,
  "max_timestamp_gap_sec": 0.5,
  "min_overlap_ratio": 0.8,
  "missing_frame_gap_multiplier": 1.5,
  "stationary_distance_threshold_m": 0.05,
  "timestamp_gap_threshold_sec": 0.5
}
```
- `dataset_fingerprint`: `"sha256:8880b5deefbb54dd5bb2c4004e94138becb08fc4c953476c82b13f28568158b8"`
- `declared_sensor_count`: `3`
- `issue_count`: `31`
- `issue_count_by_severity`:

```json
{
  "error": 16,
  "info": 0,
  "warning": 15
}
```
- `label_file_count`: `1`
- `sensor_count`: `2`
- `sync`:

```json
{
  "overlap_duration_sec": 0.0,
  "pairwise_gaps": {
    "camera_front:imu": {
      "max_gap_sec": 18.01,
      "median_gap_sec": 18.005000000000003
    }
  },
  "sensors": {
    "camera_front": {
      "duration_sec": 2.0,
      "end_time": 2.0,
      "frame_count": 3.0,
      "inferred_frequency_hz": 0.5,
      "max_dt_sec": 2.0,
      "median_dt_sec": 2.0,
      "start_time": 0.0
    },
    "imu": {
      "duration_sec": 0.010000000000001563,
      "end_time": 20.01,
      "frame_count": 2.0,
      "inferred_frequency_hz": 99.99999999998437,
      "max_dt_sec": 0.010000000000001563,
      "median_dt_sec": 0.010000000000001563,
      "start_time": 20.0
    }
  }
}
```
- `trajectory_file_count`: `1`

## Issues

| Severity | Check | File | Row | Message |
| --- | --- | --- | --- | --- |
| error | `check_missing_sensor_files` | sensors/gps.csv |  | Metadata declares sensor 'gps', but sensors/gps.csv is missing. |
| error | `check_broken_paths` | sensors/camera_front.csv | 2 | Referenced file does not exist: images/missing.jpg. |
| error | `check_broken_paths` | sensors/camera_front.csv | 3 | Referenced file does not exist: images/also_missing.jpg. |
| error | `check_broken_paths` | sensors/camera_front.csv | 4 | Referenced file does not exist: images/000003.jpg. |
| error | `check_declared_sensors_exist` | metadata.json |  | Declared sensor 'gps' has no matching CSV in sensors/. |
| warning | `check_duration_matches_timestamps` | metadata.json |  | metadata duration_sec does not match observed timestamp span. |
| warning | `check_dataset_version_present` | metadata.json |  | metadata.json should include a non-empty version string. |
| warning | `check_duplicate_timestamps` | sensors/camera_front.csv | 3 | Duplicate timestamp. |
| warning | `check_large_timestamp_gaps` | sensors/camera_front.csv | 4 | Timestamp gap exceeds 0.500s. |
| error | `check_sensor_dimensions` | sensors/camera_front.csv | 3 | Camera width and height must be positive numbers. |
| warning | `check_sensor_frequency` | sensors/camera_front.csv |  | Observed sensor rate differs from expected rate. |
| warning | `check_missing_frames` | sensors/camera_front.csv | 4 | Likely missing frame based on timestamp gap. |
| error | `check_sensor_time_overlap` |  |  | Sensor timestamp ranges do not overlap; align sensor streams before training. |
| warning | `check_timestamp_offset` |  |  | Sensor stream start times differ more than configured. |
| warning | `check_pairwise_sync_gap` |  |  | Pairwise sensor timestamp gap exceeds configured median threshold. |
| warning | `check_missing_frame_bursts` | sensors/camera_front.csv | 4 | Sensor has a burst-sized timestamp gap; inspect dropped frames or logging stalls. |
| error | `check_calibration_exists` | calibration.json |  | Missing calibration entry for sensor 'imu'. |
| error | `check_calibration_exists` | calibration.json |  | Missing calibration entry for sensor 'gps'. |
| error | `check_intrinsics_shape` | calibration.json |  | Calibration intrinsics for 'camera_front' must be a 3x3 matrix. |
| error | `check_extrinsics_shape` | calibration.json |  | Calibration extrinsics for 'camera_front' must include translation[3] and rotation_quat[4]. |
| error | `check_quaternion_norm` | calibration.json |  | Quaternion for 'camera_front' is not normalized. |
| error | `check_label_confidence_range` | labels/detections.csv | 2 | Label confidence must be in [0, 1]. |
| error | `check_label_geometry` | labels/detections.csv | 2 | Label width and height must be positive. |
| error | `check_label_timestamps_match_sensor_range` | labels/detections.csv | 2 | Label timestamp is outside the observed sensor timestamp range. |
| error | `check_label_timestamps_match_sensor_range` | labels/detections.csv | 3 | Label timestamp is outside the observed sensor timestamp range. |
| warning | `check_track_id_consistency` | labels/detections.csv |  | Track ID changes class more often than configured. |
| warning | `check_short_tracks` | labels/detections.csv |  | Track is shorter than configured minimum length. |
| warning | `check_unrealistic_speed` | trajectories/ego.csv | 3 | Trajectory speed exceeds configured maximum. |
| warning | `check_unrealistic_acceleration` | trajectories/ego.csv | 3 | Trajectory acceleration exceeds configured maximum. |
| warning | `check_unrealistic_acceleration` | trajectories/ego.csv | 4 | Trajectory acceleration exceeds configured maximum. |
| warning | `check_yaw_range` | trajectories/ego.csv | 3 | Yaw should be in [-pi, pi]. |
