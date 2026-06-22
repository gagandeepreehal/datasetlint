# Quickstart

## 1. Install From Source

DatasetLint requires Python 3.10 or newer.

```bash
git clone https://github.com/gagandeepreehal/datasetlint.git
cd datasetlint
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev,docs]"
```

Use `python3.10`, `python3.11`, or `python3.12` if that is the interpreter name on your machine.

## 2. Validate The Passing Example

```bash
datasetlint examples/minimal_dataset
```

Expected result:

```text
DatasetLint report for .../examples/minimal_dataset: passed with 0 issue(s) (error=0, warning=0, info=0).
```

## 3. Inspect Other Output Formats

```bash
datasetlint examples/minimal_dataset --format json
datasetlint examples/minimal_dataset --format markdown
```

## 4. Run Focused Checks

```bash
datasetlint examples/minimal_dataset --checks labels
datasetlint examples/minimal_dataset --checks sync
datasetlint examples/minimal_dataset --checks labels,sync
```

## 5. Run The Failure Example

```bash
datasetlint examples/bad_dataset
```

This exits with code `1` because the fixture intentionally contains missing files, invalid calibration, timestamp issues, label problems, and trajectory anomalies.

## 6. Compute Stats And Diffs

```bash
datasetlint stats examples/minimal_dataset
datasetlint diff examples/minimal_dataset examples/bad_dataset
datasetlint adapters examples/minimal_dataset
```

## 7. Use The Python API

```python
from datasetlint import compare_datasets, compute_dataset_stats, lint_dataset

report = lint_dataset("examples/minimal_dataset")
print(report.summary())

stats = compute_dataset_stats("examples/minimal_dataset")
print(stats.frame_counts)

diff = compare_datasets("examples/minimal_dataset", "examples/bad_dataset")
print(diff.summary)
```

## Minimal Dataset Shape

```text
my_dataset/
  metadata.json
  calibration.json
  sensors/
    camera_front.csv
  images/
    000001.jpg
```

```json
{
  "dataset_name": "sample_log",
  "version": "0.1",
  "sensors": ["camera_front"],
  "duration_sec": 0.1
}
```

```csv
timestamp,path,width,height
0.0,images/000001.jpg,1280,720
```
