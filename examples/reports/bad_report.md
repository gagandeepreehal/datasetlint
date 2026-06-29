# DatasetLint Report

- Dataset: `examples/bad_dataset`
- Status: `failed`
- Generated at: `2026-06-29T14:09:59+00:00`
- DatasetLint version: `0.1.0`
- Dataset fingerprint: `sha256:7b22ecb438212ec4ee2ec30052d58d5e0b4fbe1e577c7848f2b378b2591a7811`
- Errors: `16`
- Warnings: `14`
- Info: `0`

## Stats

- `declared_sensor_count`: `3`
- `issue_count`: `30`
- `issue_count_by_severity`:

```json
{
  "error": 16,
  "info": 0,
  "warning": 14
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
