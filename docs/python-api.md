# Python API

Public imports from `datasetlint`:

```python
from datasetlint import (
    DatasetDiffReport,
    DatasetStats,
    Issue,
    LintConfig,
    LintReport,
    compare_datasets,
    compute_dataset_stats,
    lint_dataset,
)
```

## Validate A Dataset

```python
from datasetlint import lint_dataset

report = lint_dataset("examples/minimal_dataset")
print(report.summary())
print(report.passed)
print(report.count_by_severity())
```

## Read A Report

```python
print(report.to_json())
print(report.to_markdown())

for issue in report.issues:
    print(issue.severity, issue.check_name, issue.file, issue.row, issue.message)
```

## Configure Rules

Pass a config dictionary, `LintConfig`, config file path, or `None`:

```python
from datasetlint import LintConfig, lint_dataset

config = LintConfig(timestamp_gap_threshold_sec=0.25)
report = lint_dataset("examples/minimal_dataset", config=config)

report = lint_dataset(
    "examples/minimal_dataset",
    config={"max_pairwise_sync_gap_sec": 0.1},
    checks="sync",
)
```

`checks` accepts a comma-separated string or a list of group names:

```python
lint_dataset("examples/minimal_dataset", checks="labels,sync")
lint_dataset("examples/minimal_dataset", checks=["labels", "sync"])
```

## Stats

```python
from datasetlint import compute_dataset_stats

stats = compute_dataset_stats("examples/minimal_dataset")
print(stats.frame_counts)
print(stats.inferred_rates_hz)
print(stats.to_markdown())
```

## Diff

```python
from datasetlint import compare_datasets

diff = compare_datasets("examples/minimal_dataset", "examples/bad_dataset")
print(diff.summary)
print(diff.to_json())
```

## Adapters

```python
from datasetlint.adapters import detect_adapters, get_adapter

detections = detect_adapters("examples/minimal_dataset")
adapter = get_adapter("examples/minimal_dataset", "auto")
metadata = adapter.load_metadata("examples/minimal_dataset")
```

Only the folder adapter deeply loads data in v0.1. MCAP, ROS bag, NuScenes, and Waymo adapters are detection-only.
