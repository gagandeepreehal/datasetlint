# Stats

`datasetlint stats` computes dataset distributions in addition to pass/fail validation.

```bash
datasetlint stats examples/minimal_dataset
datasetlint stats examples/minimal_dataset --format json
datasetlint stats examples/minimal_dataset --format markdown
```

Python:

```python
from datasetlint.stats import compute_dataset_stats

stats = compute_dataset_stats("examples/minimal_dataset")
print(stats.frame_counts)
print(stats.label_class_counts)
```

The returned `DatasetStats` model includes:

- `dataset_path`
- `duration_sec`
- `sensors`
- `frame_counts`
- `inferred_rates_hz`
- `label_class_counts`
- `confidence_summary`
- `track_length_summary`
- `speed_summary`
- `acceleration_summary`
- `missing_frame_counts`
- `issue_summary`
