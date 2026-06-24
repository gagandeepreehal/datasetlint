# Getting Started

DatasetLint runs locally against a folder dataset. It needs Python 3.10 or newer.

```bash
python -m pip install -e ".[dev]"
datasetlint lint examples/minimal_dataset
datasetlint report examples/minimal_dataset --out report.json
```

Use `examples/broken_dataset` to inspect failure output without downloading data.
