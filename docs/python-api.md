# Python API

Recommended public imports:

```python
from datasetlint import compare_datasets, compute_dataset_stats, lint_dataset

report = lint_dataset("examples/minimal_dataset")
print(report.summary())
print(report.to_json())

stats = compute_dataset_stats("examples/minimal_dataset")
diff = compare_datasets("old_dataset", "new_dataset")
```

The stable public models are `Issue`, `LintConfig`, `LintReport`,
`DatasetStats`, and `DatasetDiffReport`.
