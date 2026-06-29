# Reports

DatasetLint can print reports to the console, JSON, Markdown, or static HTML.

```bash
datasetlint examples/minimal_dataset
datasetlint examples/minimal_dataset --format json
datasetlint examples/minimal_dataset --format markdown
datasetlint report examples/bad_dataset --out report.html
```

The `examples/...` paths assume a source checkout. If you installed only the
wheel, replace them with paths to datasets on your machine.

Commands that print a failing dataset report to stdout exit non-zero by default.
Use `datasetlint report ... --out ...` for failing datasets when you want to
generate a file without stopping a copy-paste shell session.

The `report` command writes a file and does not add a frontend dependency. The
output suffix selects the format:

```bash
datasetlint report examples/bad_dataset --out report.html
datasetlint report examples/bad_dataset --out report.json
datasetlint report examples/bad_dataset --out report.md
```

## HTML Contents

The HTML report is a plain static file with escaped content and deterministic
ordering. It includes:

- Title
- Dataset path
- Pass or fail status
- Issue count by severity
- Checks run
- Adapter name and validation mode
- Dataset fingerprint
- Config summary
- Adapter coverage and limitations
- Dataset stats when available
- Issue table with severity, check, file, row, message, and metadata

## Generated Examples

Generated sample reports are stored in `examples/reports/`:

- `minimal_report.json`
- `bad_report.json`
- `bad_report.md`

Regenerate them from the real CLI paths with:

```bash
mkdir -p examples/reports
datasetlint report examples/minimal_dataset --out examples/reports/minimal_report.json
datasetlint report examples/bad_dataset --out examples/reports/bad_report.json
datasetlint report examples/bad_dataset --out examples/reports/bad_report.md
```
