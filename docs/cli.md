# CLI Reference

DatasetLint installs one console script:

```bash
datasetlint --help
datasetlint --version
```

The implementation uses one Typer entry point. `stats`, `diff`, and `adapters` are positional command words.

## Validate

```bash
datasetlint DATASET_PATH
```

Purpose: validate a native folder dataset.

Common options:

| Option | Values | Purpose |
| --- | --- | --- |
| `--format`, `-f` | `console`, `json`, `markdown` | Select output format |
| `--fail-on` | `error`, `warning`, `info` | Choose which severity makes the command exit non-zero |
| `--config` | path | Load config from a specific file |
| `--checks` | comma-separated groups | Run only selected check groups |
| `--adapter` | `folder`, `auto`, or adapter name | Select adapter |

Examples:

```bash
datasetlint examples/minimal_dataset
datasetlint examples/minimal_dataset --checks labels,sync
datasetlint examples/minimal_dataset --format json
datasetlint examples/minimal_dataset --fail-on warning
```

## Stats

```bash
datasetlint stats DATASET_PATH
datasetlint stats DATASET_PATH --format json
datasetlint stats DATASET_PATH --format markdown
```

Purpose: compute dataset distributions without changing validation semantics.

Stats include sensors, frame counts, inferred rates, label class counts, confidence summary, track length summary, speed summary, acceleration summary, missing frame counts, and issue summary.

## Diff

```bash
datasetlint diff OLD_DATASET NEW_DATASET
datasetlint diff OLD_DATASET NEW_DATASET --format json
datasetlint diff OLD_DATASET NEW_DATASET --fail-on-regression
```

Purpose: compare two folder datasets and classify changes, regressions, and improvements.

`--fail-on-regression` exits with code `1` when regressions are present.

## Adapters

```bash
datasetlint adapters DATASET_PATH
datasetlint adapters DATASET_PATH --format json
datasetlint adapters DATASET_PATH --format markdown
```

Purpose: report which adapters detect a dataset path.

## Check Groups

`--checks` accepts:

- `files`
- `metadata`
- `timestamps`
- `sensors`
- `sync`
- `calibration`
- `labels`
- `trajectories`
- `all`

Multiple groups can be combined:

```bash
datasetlint examples/minimal_dataset --checks labels,sync
```

## Exit Codes

| Code | Meaning |
| ---: | --- |
| `0` | Command completed and did not meet the configured failure threshold |
| `1` | Validation failed the `--fail-on` threshold, or diff regressions were found with `--fail-on-regression` |
| `2` | Invalid usage, unknown check group, bad adapter, or invalid config |

## Output Location

DatasetLint prints reports to stdout. It does not currently write report files by itself. Redirect output when you want an artifact:

```bash
datasetlint examples/minimal_dataset --format json > datasetlint-report.json
datasetlint examples/minimal_dataset --format markdown > datasetlint-report.md
```
