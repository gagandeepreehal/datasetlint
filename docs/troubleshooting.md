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

## First Triage

1. Re-run with JSON so every field is visible:

   ```bash
   datasetlint DATASET_PATH --format json
   ```

2. Open the reported `file` and `row` first. Most native lint failures point at
   the exact CSV row or JSON file involved.
3. Read `metadata.suggestion` when present. It is intended to be the first fix
   to try.
4. If the rule is correct but too strict for this dataset, change the config
   rather than ignoring the whole report.

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

## Common Native-Folder Symptoms

| Symptom | Likely Cause | First Fix |
| --- | --- | --- |
| `metadata.json` is missing | Dataset is not in the native folder layout | Add the file or validate through an adapter |
| Broken path under `sensors/*.csv` | A CSV row references a missing image or file | Fix the relative path from the dataset root |
| Timestamp gap warning | Dropped frames, logging pause, or wrong time unit | Inspect the reported row and tune `timestamp_gap_threshold_sec` only if expected |
| Sensor frequency warning | Expected rate does not match this collection setup | Update `expected_sensor_rates` or disable `check_sensor_frequency` |
| Sync gap warning | Streams are offset or clocks are not aligned | Compare sensor start times and hardware clock configuration |
| Label timestamp error | Labels refer to times outside observed sensor data | Fix label timestamps or include the matching sensor rows |

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

If you requested JSON, missing deep dependencies are still reported as JSON:

```bash
datasetlint validate logs/run.mcap --adapter mcap --deep --format json
```

The report will have `valid: false`, `validation_mode: deep`, and an `errors`
entry explaining which optional package is missing.

## Adapter Validation

Use `inspect` before `validate` when a dataset format is new to you:

```bash
datasetlint adapters detect DATASET_PATH
datasetlint inspect DATASET_PATH --adapter auto
datasetlint validate DATASET_PATH --adapter auto --format json
```

If `--adapter auto` is ambiguous, pass the adapter explicitly. DatasetLint does
not silently choose between multiple specialized adapters.

## Adapter Plugins

If a third-party adapter does not appear in `datasetlint adapters list`, check
that the package exposes the `datasetlint.adapters` entry point:

```toml
[project.entry-points."datasetlint.adapters"]
myformat = "datasetlint_myformat:MyFormatAdapter"
```

Then confirm the package is installed in the same Python environment as the
`datasetlint` command.

## Config Errors

Unknown config keys are usage errors and exit with code `2`. This is deliberate:
old config names should fail loudly instead of silently changing CI behavior.

Check:

- key spelling against [Configuration](configuration.md)
- indentation under `rules.enabled`, `rules.disabled`, and `rules.severity`
- whether a value that should be a list is written as a scalar

## Exit Codes

| Code | Meaning | What To Do |
| ---: | --- | --- |
| `0` | No issue met the configured failure threshold | Save the report if needed |
| `1` | Validation failed, adapter validation failed, or diff regressions were found | Read issue fields or adapter `errors` |
| `2` | Invalid usage, unknown check or adapter, or invalid config | Fix the command or config before rerunning |
