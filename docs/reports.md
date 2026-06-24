# Reports

DatasetLint reports are available as console output, JSON, or Markdown.

```bash
datasetlint examples/minimal_dataset --format console
datasetlint examples/minimal_dataset --format json
datasetlint examples/minimal_dataset --format markdown
```

Use the dedicated report command when you want a JSON artifact:

```bash
datasetlint report examples/minimal_dataset --out datasetlint-report.json
```

Formatted validation output still prints to stdout. Redirect output when you
want those representations as files:

```bash
datasetlint examples/minimal_dataset --format json > datasetlint-report.json
datasetlint examples/minimal_dataset --format markdown > datasetlint-report.md
```

HTML output is not implemented in v0.1.

## Validation Report Fields

Python validation returns `LintReport`:

- `dataset_path`
- `generated_at`
- `datasetlint_version`
- `dataset_fingerprint`
- `dataset_summary`
- `checks_run`
- `adapter`
- `config`
- `issues`
- `findings`
- `stats`
- `passed`

Each issue includes:

- `check_name`
- `severity`
- `message`
- `file`
- `row`
- `metadata`

Rows are 1-based CSV rows. The header is row 1 and the first data row is row 2.

The committed JSON schema is `schemas/report.schema.json`.

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
| `1` | Validation failed the `--fail-on` threshold, or diff regressions were found with `--fail-on-regression` |
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
