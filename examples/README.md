# DatasetLint Examples

These fixtures are intentionally tiny. They are meant for smoke tests, docs, and learning the failure messages, not for benchmarking performance.

Run all commands from the repository root after installing DatasetLint:

```bash
python -m pip install -e ".[dev,docs]"
```

## Example Matrix

| Example | Command | Expected | What To Learn |
| --- | --- | --- | --- |
| `minimal_dataset` | `datasetlint examples/minimal_dataset` | pass | Valid native folder layout |
| `bad_dataset` | `datasetlint examples/bad_dataset` | fail | Broad failure surface across files, metadata, sync, calibration, labels, and trajectories |
| `invalid_missing_metadata` | `datasetlint examples/invalid_missing_metadata` | fail | Required `metadata.json` behavior |
| `invalid_timestamp_drift` | `datasetlint examples/invalid_timestamp_drift --checks timestamps,sensors,sync --fail-on warning` | fail | Timestamp gaps, missing-frame warnings, and frequency drift |
| `invalid_label_consistency` | `datasetlint examples/invalid_label_consistency --checks labels` | fail | Duplicate track timestamps and class-switch warnings |

## Passing Dataset

```bash
datasetlint examples/minimal_dataset
```

Expected summary:

```text
passed with 0 issue(s) (error=0, warning=0, info=0)
```

## Broad Invalid Dataset

```bash
datasetlint examples/bad_dataset
```

Expected summary in the current codebase:

```text
failed with 30 issue(s) (error=16, warning=14, info=0)
```

This fixture intentionally combines many unrelated problems. Use the targeted invalid examples below when documenting or testing one category at a time.

## Missing Metadata

```bash
datasetlint examples/invalid_missing_metadata
```

Expected: fails because `metadata.json` is missing.

## Timestamp Drift

```bash
datasetlint examples/invalid_timestamp_drift --checks timestamps,sensors,sync --fail-on warning
```

Expected: fails at the command level because `--fail-on warning` treats warning findings as a non-zero result. The report shows timestamp gaps, likely missing frames, and frequency/sync warnings.

Use JSON output when asserting exact check names:

```bash
datasetlint examples/invalid_timestamp_drift --checks timestamps,sensors,sync --format json
```

## Label Consistency

```bash
datasetlint examples/invalid_label_consistency --checks labels
```

Expected: fails because the fixture includes a duplicate `(timestamp, track_id)` row and warnings for track consistency.

## Stats And Diff Examples

```bash
datasetlint stats examples/minimal_dataset
datasetlint diff examples/minimal_dataset examples/bad_dataset
datasetlint adapters examples/minimal_dataset
```

Redirect JSON or Markdown output when you want artifacts:

```bash
datasetlint examples/minimal_dataset --format json > datasetlint-report.json
datasetlint diff examples/minimal_dataset examples/bad_dataset --format markdown > datasetlint-diff.md
```
