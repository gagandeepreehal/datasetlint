# Troubleshooting

DatasetLint issue messages are meant to tell you where to look and what to try
next. JSON, Markdown, HTML, and console reports include:

- `check_name`
- `severity`
- `file`
- `row` when a CSV row is known
- `message` with location and fix guidance
- `metadata.suggestion` for native lint issues

CSV rows are 1-based. Row 1 is the header and the first data row is row 2.

## Native Folder Checks

For native folder datasets, start with the issue location:

```text
Timestamp gap exceeds 0.500s. Location: sensors/camera_front.csv:42. Fix: inspect dropped frames, logging stalls, or the configured timestamp threshold.
```

Open the reported file and row first. If the rule is intentionally noisy for a
team-specific dataset, configure it instead of ignoring the entire check group:

```yaml
rules:
  disabled:
    - check_sensor_frequency
  severity:
    check_large_timestamp_gaps: info
```

To run only a narrow policy in CI:

```yaml
rules:
  enabled:
    - calibration
    - labels
```

## MCAP And ROS Bag Logs

Use deep validation when you need topic/channel timestamps rather than file-only
indexing:

```bash
datasetlint validate DATASET_PATH --adapter mcap --deep
datasetlint validate DATASET_PATH --adapter rosbag --deep
```

Deep validation reports parser failures as errors, dropped topics as warnings,
and cross-topic desync with the topic names and timing gap:

```text
Sensors/topics /camera/image and /imu median sync gap 0.2s exceeds 0.05s (max 0.2s). Fix: verify timestamp units, hardware clock sync, or topic alignment inside the bag/log.
```

If parsing fails, install the matching extra and retry:

```bash
python -m pip install -e ".[mcap]"
python -m pip install -e ".[ros]"
```

## Adapter Plugins

If a third-party adapter does not appear in `datasetlint adapters list`, check
that the package exposes the `datasetlint.adapters` entry point:

```toml
[project.entry-points."datasetlint.adapters"]
myformat = "datasetlint_myformat:MyFormatAdapter"
```

Then confirm the package is installed in the same Python environment as the
`datasetlint` command.
