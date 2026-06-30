# DatasetLint End-User Test Prompt

Copy the text below into Claude Code to run a comprehensive end-user test of DatasetLint from scratch.

---

## Prompt

You are testing DatasetLint as a first-time end user. The repo is already cloned and installed in a virtual environment at `.venv`. Work from the project root. Follow the steps below in order, observe the actual output after each command, and report any unexpected result.

### 0. Verify the install

```bash
source .venv/bin/activate
datasetlint --version
datasetlint --help
```

Confirm the version prints and `--help` lists the subcommands: `lint`, `report`, `stats`, `diff`, `adapters`, `inspect`, `validate`, `export-manifest`.

---

### 1. Validate the passing example

```bash
datasetlint examples/minimal_dataset
datasetlint lint examples/minimal_dataset
```

Both forms should exit 0 and print something like:
`DatasetLint report for .../examples/minimal_dataset: passed with 0 issue(s) (error=0, warning=0, info=0).`

Run focused check groups and confirm each also exits 0:

```bash
datasetlint examples/minimal_dataset --checks labels
datasetlint examples/minimal_dataset --checks sync
datasetlint examples/minimal_dataset --checks labels,sync
datasetlint examples/minimal_dataset --checks files,metadata,timestamps,sensors,calibration,trajectories
```

Verify that an unknown check group exits 2:

```bash
datasetlint examples/minimal_dataset --checks nonexistent_group
echo "Exit code: $?"
```

---

### 2. Output formats on the passing dataset

```bash
datasetlint examples/minimal_dataset --format json
datasetlint examples/minimal_dataset --format markdown
datasetlint examples/minimal_dataset --format html > /tmp/minimal_report.html
```

For JSON: confirm the output is valid JSON with a `"passed"` key set to `true` and `"issues"` as an empty list.  
For Markdown: confirm a heading and a pass summary are present.  
For HTML: confirm `/tmp/minimal_report.html` exists and contains `<html`.

Write report files:

```bash
datasetlint report examples/minimal_dataset --out /tmp/minimal_report.json
datasetlint report examples/minimal_dataset --out /tmp/minimal_report.md
datasetlint report examples/minimal_dataset --out /tmp/minimal_report2.html
```

Confirm all three files exist and contain content.

---

### 3. Validate the failing example

```bash
datasetlint examples/bad_dataset
echo "Exit code: $?"
```

Exit code must be 1. Confirm the output lists at least one `error`-severity issue covering missing files, calibration, timestamps, labels, or trajectory anomalies.

Try different output formats on the failing dataset:

```bash
datasetlint examples/bad_dataset --format json | python3 -c "import sys,json; d=json.load(sys.stdin); print('passed:', d['passed'], '| issues:', len(d['issues']))"
datasetlint examples/bad_dataset --format markdown
```

Test `--fail-on` thresholds:

```bash
datasetlint examples/minimal_dataset --fail-on warning
echo "Exit code: $?"   # expect 0 — no warnings in minimal

datasetlint examples/invalid_timestamp_drift --fail-on warning
echo "Exit code: $?"   # expect 1 — has timestamp warnings
```

---

### 4. Other named example datasets

```bash
datasetlint examples/invalid_missing_metadata
echo "Exit code: $?"   # expect 1

datasetlint examples/invalid_label_consistency
echo "Exit code: $?"   # expect 1
```

---

### 5. Config file

```bash
datasetlint examples/minimal_dataset --config examples/minimal_dataset/datasetlint.yaml
```

If the file exists, confirm it passes. Then test that an unknown config key is rejected (exit 2):

```bash
echo "bad_key: 999" > /tmp/bad_config.yaml
datasetlint examples/minimal_dataset --config /tmp/bad_config.yaml
echo "Exit code: $?"   # expect 2
```

---

### 6. Stats

```bash
datasetlint stats examples/minimal_dataset
datasetlint stats examples/minimal_dataset --format json
datasetlint stats examples/minimal_dataset --format markdown
```

Confirm the console output lists sensor names and frame counts, the JSON output is valid, and the Markdown output has headings.

---

### 7. Diff

```bash
datasetlint diff examples/minimal_dataset examples/bad_dataset
echo "Exit code (no flag): $?"   # typically 0 unless threshold met

datasetlint diff examples/minimal_dataset examples/bad_dataset --fail-on-regression
echo "Exit code (--fail-on-regression): $?"   # expect 1

datasetlint diff examples/minimal_dataset examples/bad_dataset --format json
datasetlint diff examples/minimal_dataset examples/bad_dataset --format markdown
```

Confirm diff output describes regressions and improvements between the two datasets.

---

### 8. Adapter discovery

```bash
datasetlint adapters list
datasetlint adapters list --format json
datasetlint adapters detect examples/minimal_dataset
datasetlint adapters examples/minimal_dataset
datasetlint adapters examples/minimal_dataset --format json
datasetlint adapters examples/minimal_dataset --format markdown
```

Confirm `adapters list` shows at least: `folder`, `generic`, `coco`, `kitti`, `nuscenes`, `waymo`, `rosbag`, `mcap`, `huggingface`.

---

### 9. Adapter inspect and validate (COCO fixture)

```bash
datasetlint inspect tests/fixtures/coco_dataset --adapter coco
datasetlint inspect tests/fixtures/coco_dataset --adapter coco --format json
datasetlint validate tests/fixtures/coco_dataset --adapter coco
datasetlint validate tests/fixtures/coco_dataset --adapter coco --format json
```

Confirm `inspect` prints dataset name, adapter, frame count, and annotation count.  
Confirm `validate` prints `valid: true` (or lists specific known issues) and exposes `checked` and `not_checked` scopes.

---

### 10. Adapter inspect and validate (KITTI fixture)

```bash
datasetlint inspect tests/fixtures/kitti_object --adapter kitti
datasetlint validate tests/fixtures/kitti_object --adapter kitti
datasetlint validate tests/fixtures/kitti_object --adapter kitti --format json
```

Confirm `validate` exits 0 for a valid KITTI fixture and shows validation coverage metadata.

---

### 11. Export manifest

```bash
datasetlint export-manifest tests/fixtures/coco_dataset --adapter coco --output /tmp/coco_manifest.json
cat /tmp/coco_manifest.json | python3 -c "import sys,json; d=json.load(sys.stdin); print('adapter:', d.get('adapter'), '| frames:', len(d.get('frames', [])))"
```

Confirm the manifest is valid JSON with `adapter`, `frames`, and `sequences` keys.

---

### 12. Auto-detect

```bash
datasetlint inspect tests/fixtures/coco_dataset --auto-detect
datasetlint validate tests/fixtures/coco_dataset --auto-detect
```

Confirm auto-detect identifies the COCO adapter without an explicit `--adapter` flag.

---

### 13. Python API smoke test

Run the following script inline and confirm each line prints without exceptions:

```bash
python3 - <<'EOF'
from datasetlint import lint_dataset, compute_dataset_stats, compare_datasets, LintReport, DatasetStats, DatasetDiffReport
from datasetlint.adapters import detect_adapters, load_dataset, validate_dataset

# Native lint
report = lint_dataset("examples/minimal_dataset")
assert report.passed, f"Expected pass, got: {report.summary()}"
print("lint_dataset passed:", report.summary())

# Focused checks
label_report = lint_dataset("examples/minimal_dataset", checks="labels")
sync_report  = lint_dataset("examples/minimal_dataset", checks=["sync"])
print("focused checks passed:", label_report.passed, sync_report.passed)

# Stats
stats = compute_dataset_stats("examples/minimal_dataset")
print("stats frame_counts:", stats.frame_counts)

# Diff
diff = compare_datasets("examples/minimal_dataset", "examples/bad_dataset")
print("diff summary:", diff.summary)

# Adapter detection
detections = detect_adapters("tests/fixtures/coco_dataset")
print("detected adapters:", [d.adapter for d in detections])

# Adapter load
manifest = load_dataset("tests/fixtures/coco_dataset", adapter="coco")
print("manifest adapter:", manifest.adapter, "| frames:", len(manifest.frames))

# Adapter validate
validation = validate_dataset("tests/fixtures/kitti_object", adapter="kitti")
print("kitti validation valid:", validation.valid)

print("\nAll Python API checks passed.")
EOF
```

---

### 14. Exit code contract summary

Verify the following exit codes are correct (run a few to confirm):

| Command | Expected exit code |
|---|---|
| `datasetlint examples/minimal_dataset` | 0 |
| `datasetlint examples/bad_dataset` | 1 |
| `datasetlint examples/minimal_dataset --checks nonexistent` | 2 |
| `datasetlint examples/minimal_dataset --config /tmp/bad_config.yaml` | 2 |
| `datasetlint diff examples/minimal_dataset examples/bad_dataset --fail-on-regression` | 1 |

---

### 15. Report findings

After running all steps, summarize:
- Which commands passed as documented
- Which commands produced unexpected output or wrong exit codes
- Any error messages or stack traces
- Any feature that worked differently from the docs

Flag any discrepancy as a potential bug and include the exact command and actual output.
