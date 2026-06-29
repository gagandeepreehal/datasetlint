# Reports

DatasetLint reports are available as console output, JSON, Markdown, or static HTML.

```bash
datasetlint examples/minimal_dataset --format console
datasetlint examples/minimal_dataset --format json
datasetlint examples/minimal_dataset --format markdown
datasetlint examples/minimal_dataset --format html
```

Use the dedicated report command when you want a report artifact:

```bash
datasetlint report examples/minimal_dataset --out datasetlint-report.json
datasetlint report examples/minimal_dataset --out datasetlint-report.md
datasetlint report examples/minimal_dataset --out datasetlint-report.html
```

Formatted validation output still prints to stdout. Redirect output when you
want those representations as files:

```bash
datasetlint examples/minimal_dataset --format json > datasetlint-report.json
datasetlint examples/minimal_dataset --format markdown > datasetlint-report.md
datasetlint examples/bad_dataset --format html > report.html
datasetlint report examples/bad_dataset --out report.html
```

The HTML report is plain static HTML with no frontend build step. It includes the dataset path, pass/fail state, issue counts by severity, checks run, adapter name and mode, dataset fingerprint, config summary, dataset summary, stats when available, and an issue table with severity, check, file, row, message, and metadata. HTML output intentionally omits `generated_at` so repeated runs over the same inputs produce stable HTML. JSON and Markdown reports still include `generated_at`.

Committed sample reports:

- `examples/reports/minimal_report.json`
- `examples/reports/bad_report.json`
- `examples/reports/bad_report.md`

## Validation Report Fields

Python validation returns `LintReport`:

- `dataset_path`
- `generated_at`
- `datasetlint_version`
- `dataset_fingerprint` from a lightweight file-manifest hash
- `dataset_summary`
- `checks_run`
- `adapter`
- `config`
- `issues`
- `findings`
- `stats`
- `passed`

Static HTML renders the same report data except for `generated_at`, which is omitted for deterministic output.

Each issue includes:

- `check_name`
- `severity`
- `message`
- `file`
- `row`
- `metadata`

Rows are 1-based CSV rows. The header is row 1 and the first data row is row 2.

The committed JSON schema is `schemas/report.schema.json`.

## Adapter Manifest And Validation Fields

Adapter inspection returns `DatasetManifest`:

- `dataset_name`
- `adapter_name`
- `dataset_root`
- `version`
- `sequences`
- `frames`
- `sensors`
- `annotations`
- `calibration`
- `splits`
- `metadata`
- `limitations`
- `provenance`

Adapter validation returns `AdapterValidationReport`:

- `adapter_name`
- `dataset_root`
- `detected`
- `valid`
- `validation_mode`
- `checked`
- `not_checked`
- `limitations`
- `errors`
- `warnings`
- `coverage`
- `stats`

Use `datasetlint export-manifest DATASET --adapter NAME --output manifest.json` when you need a JSON artifact for adapter output.

## Severity Levels

| Severity | Meaning |
| --- | --- |
| `error` | Dataset is invalid for the current rule |
| `warning` | Dataset has suspicious or risky data |
| `info` | Informational finding |

Validation `passed` is true when there are no `error` issues.

## Exit Codes

| Code | Meaning |
| ---: | --- |
| `0` | Command completed and did not meet the configured failure threshold |
| `1` | Validation failed the `--fail-on` threshold, adapter validation failed, or diff regressions were found with `--fail-on-regression` |
| `2` | Invalid usage, unknown check group, bad adapter, or invalid config |

## CI Behavior

Default validation fails only on errors:

```bash
datasetlint examples/minimal_dataset
```

Fail on warnings too:

```bash
datasetlint examples/minimal_dataset --fail-on warning
```

Fail on any finding:

```bash
datasetlint examples/minimal_dataset --fail-on info
```
