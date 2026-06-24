# Getting Started

DatasetLint runs locally and needs Python 3.10 or newer. The main lint rule engine validates the native folder dataset format, and adapter commands inspect normalized manifests for common external formats.

```bash
python -m pip install -e ".[dev]"
datasetlint lint examples/minimal_dataset
datasetlint report examples/minimal_dataset --out report.json
datasetlint adapters list
datasetlint inspect tests/fixtures/coco_dataset --adapter coco
```

Use `examples/broken_dataset` to inspect failure output without downloading data.
