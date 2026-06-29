# CLI Reference

DatasetLint installs one console script:

```bash
datasetlint --help
datasetlint --version
```

The implementation uses one Typer entry point. `lint`, `report`, `stats`, `diff`,
`adapters`, `inspect`, `validate`, and `export-manifest` are positional command
words. The shorthand `datasetlint DATASET_PATH` still validates a native folder
dataset.

## Validate

```bash
datasetlint lint DATASET_PATH
datasetlint DATASET_PATH
```

Purpose: validate a native folder dataset.

Common options:

| Option | Values | Purpose |
| --- | --- | --- |
| `--format`, `-f` | `console`, `json`, `markdown`, `html` | Select output format |
| `--fail-on` | `error`, `warning`, `info` | Choose which severity makes the command exit non-zero |
| `--config` | path | Load config from a specific file |
| `--checks` | comma-separated groups | Run only selected check groups |
| `--adapter` | `folder`, `auto`, or adapter name | Select adapter |

Examples:

```bash
datasetlint lint examples/minimal_dataset
datasetlint examples/minimal_dataset
datasetlint examples/minimal_dataset --checks labels,sync
datasetlint examples/minimal_dataset --format json
datasetlint examples/minimal_dataset --format html > report.html
datasetlint examples/minimal_dataset --fail-on warning
```

## Report File

```bash
datasetlint report DATASET_PATH --out datasetlint-report.json
datasetlint report DATASET_PATH --out datasetlint-report.md
datasetlint report DATASET_PATH --out datasetlint-report.html
```

Purpose: write JSON, Markdown, or static HTML validation reports to files for CI
artifacts, release evidence, or downstream tooling.

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
datasetlint adapters list
datasetlint adapters detect DATASET_PATH
datasetlint adapters DATASET_PATH
datasetlint adapters DATASET_PATH --format json
datasetlint adapters DATASET_PATH --format markdown
```

Purpose: list adapter availability or report which adapters detect a dataset path.

## Inspect Adapter Manifest

```bash
datasetlint inspect DATASET_PATH --adapter coco
datasetlint inspect DATASET_PATH --auto-detect
datasetlint inspect hf://namespace/dataset --adapter huggingface --split train --max-rows 1000
datasetlint inspect DATASET_PATH --adapter waymo --deep --max-rows 1000
datasetlint inspect DATASET_PATH --format json
```

Purpose: load a normalized `DatasetManifest` and print dataset name, adapter,
sequence count, frame count, sensor streams, annotation count, splits,
limitations, and warnings.

## Validate Adapter Manifest

```bash
datasetlint validate DATASET_PATH --adapter kitti
datasetlint validate DATASET_PATH --auto-detect
datasetlint validate DATASET_PATH --adapter mcap --deep
datasetlint validate hf://namespace/dataset --adapter huggingface --split train --max-rows 1000
datasetlint validate DATASET_PATH --format json
```

Purpose: run adapter-specific validation and return errors, warnings, coverage,
validation mode, checked scope, unchecked scope, limitations, and stats. This is
separate from `datasetlint lint`, which runs the native folder rule engine.
Validation output includes `coverage.common_rule_inputs` and
`stats.common_rule_stats` when decoded adapter records can feed shared manifest
checks.
Use `--deep` with MCAP, ROS bag, or Waymo after installing the matching extra
when you want parser-backed channel/topic/frame metadata instead of only file
indexing.

## Export Manifest

```bash
datasetlint export-manifest DATASET_PATH --adapter nuscenes --output manifest.json
datasetlint export-manifest DATASET_PATH --auto-detect --output manifest.json
datasetlint export-manifest DATASET_PATH --adapter rosbag --deep --output manifest.json
```

Purpose: write the normalized `DatasetManifest` JSON to a file.

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
| `1` | Validation failed the `--fail-on` threshold, adapter validation failed, or diff regressions were found with `--fail-on-regression` |
| `2` | Invalid usage, unknown check group, bad adapter, or invalid config |

## Output Location

Validation output prints to stdout by default. Use `datasetlint report --out`
when you want a JSON artifact, or redirect formatted output when you want a
captured console or Markdown file:

```bash
datasetlint report examples/minimal_dataset --out datasetlint-report.json
datasetlint report examples/minimal_dataset --out datasetlint-report.html
datasetlint examples/minimal_dataset --format json > datasetlint-report.json
datasetlint examples/minimal_dataset --format markdown > datasetlint-report.md
datasetlint examples/minimal_dataset --format html > datasetlint-report.html
```
