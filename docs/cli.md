# CLI

```bash
datasetlint --help
datasetlint --version
datasetlint lint examples/minimal_dataset
datasetlint report examples/minimal_dataset --out report.json
datasetlint stats examples/minimal_dataset --format json
datasetlint diff examples/minimal_dataset examples/broken_dataset
datasetlint adapters examples/minimal_dataset
```

The shorthand `datasetlint examples/minimal_dataset` remains supported for linting.

Normal user mistakes return concise errors without Python tracebacks. Use tests or
Python debugging for development-time traces.
