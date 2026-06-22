# Concepts

## Dataset

A dataset is a local folder containing metadata, calibration, sensor CSVs, labels, trajectories, and referenced files such as images.

## Sample

A sample is one row or event in a dataset file, such as one camera frame row, one IMU row, one label row, or one trajectory row.

## Sensor Stream

A sensor stream is a CSV under `sensors/`. DatasetLint has specialized column expectations for camera, IMU, and GPS streams, and a generic timestamp-only expectation for other sensor names.

## Metadata

`metadata.json` describes the dataset name, version, declared sensors, and duration. The `sensors` list is used to check whether declared sensor CSVs and calibration entries exist.

## Schema

A schema is the expected shape of files and columns. DatasetLint currently validates a practical folder CSV/JSON schema rather than a separate schema language.

## Rule

A rule is a check function that returns zero or more `Issue` objects. Rules are grouped as files, metadata, timestamps, sensors, sync, calibration, labels, and trajectories.

## Severity

Issue severities are `error`, `warning`, and `info`. Validation passes when there are no `error` issues. The CLI `--fail-on` option can make warnings or any issue fail the command.

## Adapter

An adapter detects or loads a dataset format. The folder adapter is supported. MCAP, ROS bag, NuScenes, and Waymo adapters are detection-only in v0.1.

## Report

A report is the output from validation. It includes pass/fail state, issues, and stats. Reports can be printed to the console or serialized as JSON or Markdown.

## Baseline

A baseline is a known-good dataset or previous dataset revision that you compare against a new dataset. DatasetLint does not store baselines; it compares two local folders.

## Diff

A diff compares an old dataset folder and a new dataset folder. It reports metadata changes, sensor changes, frame count changes, duration changes, calibration changes, label class changes, issue count changes, and selected trajectory stat changes.
