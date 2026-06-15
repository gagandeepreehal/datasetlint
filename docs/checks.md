# Checks

DatasetLint v0.1 supports simple folder-based datasets with `metadata.json`, `calibration.json`, `sensors/`, `labels/`, and `trajectories/`.

## File Checks

- Required `metadata.json` and `calibration.json`
- Empty CSV files
- Missing sensor CSVs declared by metadata
- Broken paths referenced by CSV rows
- Duplicate filenames across the dataset tree

## Timestamp Checks

- Non-monotonic timestamps
- Duplicate timestamps
- Large timestamp gaps
- Sensor time ranges with no overlap
- Unstable sensor frame intervals

## Sensor Checks

- Missing required columns
- Invalid camera width or height
- Sensor rates that differ from configured expectations
- Likely missing frames based on timestamp gaps

## Calibration Checks

- Missing calibration entries for declared sensors
- Invalid camera intrinsics shape or focal lengths
- Malformed extrinsics translation or quaternion
- Quaternion values that are not normalized

## Label Checks

- Missing detection label columns
- Confidence outside `[0, 1]`
- Non-positive label width or height
- Label timestamps outside sensor time ranges
- Track IDs assigned multiple class names

## Trajectory Checks

- Missing trajectory columns
- NaN or infinite values
- Unrealistic speed or acceleration
- Yaw outside `[-pi, pi]`
- Stationary or nearly stationary trajectories

