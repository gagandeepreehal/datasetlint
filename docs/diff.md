# Diff

`datasetlint diff` compares two datasets and classifies changes, regressions, and
improvements.

```bash
datasetlint diff old_dataset new_dataset
datasetlint diff old_dataset new_dataset --format json
datasetlint diff old_dataset new_dataset --fail-on-regression
```

Python:

```python
from datasetlint.diff import compare_datasets

report = compare_datasets("old_dataset", "new_dataset")
print(report.summary)
```

The diff covers:

- Metadata changes
- Sensors added or removed
- Duration changes
- Frame count changes
- Frequency changes
- Calibration changes
- Label class distribution changes
- Issue count changes
- Trajectory speed and acceleration summary changes

Regressions include removed sensors, significant frame-count or duration drops,
calibration changes, disappeared label classes, and increased warning/error issue
counts. Use `--fail-on-regression` in CI to exit non-zero when regressions are
found.

Relevant thresholds:

```yaml
frame_count_drop_ratio_warning: 0.1
duration_drop_ratio_warning: 0.1
issue_regression_severity: warning
```
