# Checks

The canonical rule reference now lives in [Rules](rules.md).

This page remains as a compatibility entry point for older links. DatasetLint check groups are:

- `files`
- `metadata`
- `timestamps`
- `sensors`
- `sync`
- `calibration`
- `labels`
- `trajectories`
- `all`

Run focused checks with:

```bash
datasetlint examples/minimal_dataset --checks labels
datasetlint examples/minimal_dataset --checks sync
datasetlint examples/minimal_dataset --checks labels,sync
```
