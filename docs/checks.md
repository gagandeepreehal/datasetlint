# Checks

DatasetLint v0.1 supports simple folder-based datasets with `metadata.json`, `calibration.json`, `sensors/`, `labels/`, and `trajectories/`.

## File Checks

- Required `metadata.json` and `calibration.json`
- Empty CSV files
- Missing sensor CSVs declared by metadata
- Broken paths referenced by CSV rows
- Duplicate filenames across the dataset tree

Issue row numbers follow spreadsheet convention: the header is row 1 and the first data row is
row 2.

## Timestamp Checks

- Non-monotonic timestamps
- Duplicate timestamps
- Large timestamp gaps

## Synchronization Checks

Run only synchronization diagnostics with:

```bash
datasetlint examples/minimal_dataset --checks sync
```

- Sensor time ranges with no overlap or low overlap ratio
- Sensor stream start offsets
- Pairwise median timestamp gaps between sensor streams
- Missing frame bursts based on large timestamp gaps
- Unstable sensor frame intervals
- Per-sensor timing diagnostics in report stats

`max_timestamp_gap_sec` controls missing frame burst diagnostics. The separate
`timestamp_gap_threshold_sec` setting controls the general timestamp gap check across every
loaded CSV; tune both when you want matching thresholds for those related reports.

## Sensor Checks

- Missing required columns
- Invalid camera width or height
- Sensor rates that differ from configured expectations
- Likely missing frames based on timestamp gaps

Camera CSVs require `timestamp`, `path`, `width`, and `height`. `filename` is accepted as a
compatibility alias for `path` when `path` is absent.

## Calibration Checks

- Missing calibration entries for declared sensors
- Invalid camera intrinsics shape or focal lengths
- Malformed extrinsics translation or quaternion
- Quaternion values that are not normalized

## Label Checks

Run only label diagnostics with:

```bash
datasetlint examples/minimal_dataset --checks labels
```

- Missing detection label columns
- Confidence outside `[0, 1]`
- Non-positive label width or height
- Label timestamps outside sensor time ranges
- Track IDs changing class more often than configured
- Duplicate `track_id` at the same timestamp
- Bounding box center jumps above `label_max_position_jump_px`
- Missing timestamps inside a track
- Tracks shorter than `label_min_track_length`
- Bounding box size changes above `label_max_size_change_ratio`

## Trajectory Checks

- Missing trajectory columns
- NaN or infinite values
- Unrealistic speed or acceleration
- Yaw outside `[-pi, pi]`
- Stationary or nearly stationary trajectories

## Check Groups

`--checks` accepts a comma-separated list:

- `files`
- `metadata`
- `timestamps`
- `sensors`
- `sync`
- `calibration`
- `labels`
- `trajectories`
- `all`

Examples:

```bash
datasetlint data/ --checks labels
datasetlint data/ --checks sync
datasetlint data/ --checks labels,sync
```

## Related Configuration

```yaml
label_max_position_jump_px: 200
label_max_size_change_ratio: 3.0
label_min_track_length: 3
label_class_switch_threshold: 0
max_pairwise_sync_gap_sec: 0.05
timestamp_gap_threshold_sec: 0.5
max_timestamp_gap_sec: 0.5
min_overlap_ratio: 0.8
frequency_jitter_ratio: 0.2
```
