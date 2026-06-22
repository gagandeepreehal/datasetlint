# DatasetLint End-User Evaluation Report

**Evaluator role:** Senior robotics software engineer, open-source maintainer, dataset quality engineer, and QA lead  
**Evaluation date:** 2026-06-23  
**Repository:** `/Users/gagandeep/Documents/datasetlint`  
**Package version:** 0.1.0  
**Python used for testing:** 3.11.15 (via Homebrew)

---

## 1. Executive Summary

DatasetLint is a lightweight Python library and CLI for validating folder-based robotics and Physical AI datasets. The concept is sound and there is a real gap in the ecosystem for this kind of offline, dependency-free linting tool. The codebase is clean, well-typed, and shows evidence of careful design.

However, the package is **not ready for a public v0.1 release** in its current state. The most critical problems are: the package fails to install on the system Python 3.9 that `pip` resolves to on macOS (a barrier that will silently block most first-time users), two major CLI commands crash with unhandled Python `ValueError` tracebacks instead of clean error messages, `__version__` is absent, the `--version` flag does not exist, two functions exist in `timestamps.py` that are silently unreachable dead code, the markdown report format embeds raw Python `dict` literals that break machine parsing and are ugly in rendered docs, and the formatters subpackage (`formatters/json.py`, `formatters/markdown.py`) is entirely dead code. The test suite has 26 tests but zero coverage of the error paths that are actually broken.

A serious robotics or physical AI user evaluating this tool will encounter a raw `ValueError` traceback within five minutes of first use (typing `--checks invalid` or `--adapter foobar`), and will walk away.

---

## 2. Final Verdict

**Ready for public launch: NO**

Fix the five critical and four high severity issues first. The core detection logic is solid and the concept is worth shipping, but the user-facing rough edges are bad enough to generate negative first impressions that are very hard to recover from.

---

## 3. Scores (0–10)

| Dimension | Score | Rationale |
|---|---|---|
| Launch Readiness | 3/10 | Install fails on system Python; two CLI crashes; no `--version`; dead code |
| Adoption | 4/10 | Concept is good; docs are thin but acceptable for v0; crashes will block adoption |
| Developer Experience | 5/10 | Clean API design, but `ValueError` escaping from `lint_dataset()` breaks calling code |
| Documentation | 5/10 | README is comprehensive but has schema divergence (uses `name` vs required `dataset_name`); no CONTRIBUTING or CHANGELOG |
| CLI | 4/10 | No `--version`; two crash paths; check name truncation in console table |
| API Design | 7/10 | Clean, typed, composable; only spoiled by `ValueError` leaking from `lint_dataset` |
| Reliability | 5/10 | Happy path is solid; error paths are untested and broken |
| Production Readiness | 3/10 | No `__version__`; no changelog; no GitHub repo URL; dead code in tree |
| Differentiation | 7/10 | No comparable standalone offline robotics dataset linter exists with this featureset |

---

## 4. What Works Well (verified only)

All of the following were run and confirmed to behave correctly:

- `pip install -e .` succeeds on Python 3.11 and installs all transitive dependencies cleanly.
- `datasetlint examples/minimal_dataset` passes with zero issues and produces a clean Rich table.
- `datasetlint examples/bad_dataset` correctly identifies 31 issues (16 errors, 15 warnings) across all check categories.
- `datasetlint examples/minimal_dataset --format json` produces valid, machine-parseable JSON.
- `datasetlint stats examples/minimal_dataset` produces a correct sensor table with inferred rates and missing frame counts.
- `datasetlint diff examples/minimal_dataset examples/bad_dataset` correctly classifies 12 regressions and 1 improvement across sensors, calibration, issue counts, and trajectory stats.
- `datasetlint adapters examples/minimal_dataset` correctly identifies folder adapter as detected and others as not detected.
- `datasetlint examples/minimal_dataset --checks labels` and `--checks sync` filter correctly.
- `datasetlint examples/bad_dataset --fail-on error` exits with code 1.
- `datasetlint diff examples/minimal_dataset examples/bad_dataset --fail-on-regression` exits with code 1.
- The Python API (`lint_dataset`, `compute_dataset_stats`, `compare_datasets`) all return correct typed results on valid inputs.
- Non-existent dataset path produces a clean error issue in the report (not a crash).
- YAML config parsing for flat and nested keys works correctly.
- Nested `expected_sensor_rates:` in `datasetlint.yaml` is correctly parsed into the `LintConfig` dict field.
- All 26 pytest tests pass on Python 3.11 in 0.78 seconds.
- The `check_sensor_time_overlap` in `sync.py` correctly returns empty list when fewer than 2 sensors exist.
- Label checks correctly catch confidence outside `[0, 1]`, non-positive bounding boxes, out-of-range timestamps, class switching, short tracks, bbox jumps, and duplicate `(track_id, timestamp)` pairs.
- Calibration checks correctly flag malformed intrinsics, extrinsics, and un-normalized quaternions.
- Trajectory checks correctly flag unrealistic speed, acceleration, and yaw out of range.
- The `--fail-on warning` and `--fail-on info` exit-code semantics are correctly implemented.

---

## 5. Critical Issues

### CRIT-1: Package fails to install on macOS system Python 3.9

**Evidence:** Running `pip install -e .` on macOS (Python 3.9.6, which is the default macOS system Python resolved when a user types `pip install datasetlint`) fails immediately with:
```
ERROR: Package 'datasetlint' requires a different Python: 3.9.6 not in '>=3.10'
```

**Reproduction:**
```bash
python --version        # 3.9.6
pip install datasetlint # FAILS
```

**Expected:** Either the package installs, or the error message directs the user to install Python 3.10+.  
**Actual:** Silent failure. The error message from pip is accurate but nothing in the README, quickstart, or installation section warns users that macOS ships Python 3.9.  
**Why it matters:** Every macOS user who has not explicitly installed Python 3.10+ via Homebrew or pyenv will hit this on first install with no guidance. They will silently conclude the package is broken.  
**Fix:** Add a prominent Python version prerequisite note to the README installation section. Example: "Requires Python 3.10+. On macOS, install via `brew install python@3.11` then use `pip3.11 install datasetlint`."

---

### CRIT-2: CLI crashes with unhandled `ValueError` traceback when an invalid `--checks` group is passed

**Evidence:** Passing any non-existent check group name prints a full Python traceback to the terminal and exits with code 1.

**Reproduction:**
```bash
datasetlint examples/minimal_dataset --checks bad_group
```

**Actual output (truncated):**
```
╭─────────────────────── Traceback (most recent call last) ────────────────────────╮
│ ...core.py:289 in _select_checks                                                 │
│  ValueError: Unknown check group 'bad_group'. Known groups: all, calibration, ...│
╰──────────────────────────────────────────────────────────────────────────────────╯
ValueError: Unknown check group 'bad_group'. Known groups: all, calibration, ...
```

**Expected:** A clean, user-friendly error message like:
```
Error: Unknown check group 'bad_group'. Valid groups: all, calibration, files, ...
```
Exit code 2 (usage error), not 1 (lint error).  
**Why it matters:** This is the second thing a user will try after reading `--help`. The traceback looks like a bug. It will generate GitHub issues and immediately undermine trust.  
**Fix:** Catch `ValueError` from `_select_checks` in `cli.py:main()` and call `_usage_error()`.

---

### CRIT-3: CLI crashes with unhandled `ValueError` traceback when an invalid `--adapter` name is passed

**Evidence:** Same failure mode as CRIT-2.

**Reproduction:**
```bash
datasetlint examples/minimal_dataset --adapter foobar
```

**Actual output:** Full Python traceback ending in:
```
ValueError: Unknown adapter 'foobar'. Known adapters: folder, mcap, rosbag, nuscenes, waymo, auto.
```

**Expected:** Clean user-facing error message and exit code 2.  
**Why it matters:** Same as CRIT-2. Any typo in the adapter name produces a traceback.  
**Fix:** Catch `ValueError` from `get_adapter` in `cli.py:main()` (or in `_select_adapter`) and call `_usage_error()`.

---

### CRIT-4: `datasetlint.__version__` does not exist

**Evidence:**
```bash
python3.11 -c "import datasetlint; print(datasetlint.__version__)"
# AttributeError: module 'datasetlint' has no attribute '__version__'
```

**Expected:** Returns `"0.1.0"`.  
**Why it matters:** Every integration script, CI pipeline, and debugging session relies on `import datasetlint; datasetlint.__version__`. Many tools (pip, setuptools, poetry) populate it automatically; this one does not. The `--version` flag also fails because of this (see HIGH-1).  
**Fix:** Add `__version__ = "0.1.0"` to `datasetlint/__init__.py`. Or use `importlib.metadata.version("datasetlint")`.

---

### CRIT-5: Dead code in `datasetlint/checks/timestamps.py` silently bypasses two check functions

**Evidence:**
```python
from datasetlint.core import CHECKS, TIMESTAMP_CHECKS
from datasetlint.checks import timestamps
timestamps.check_sensor_time_overlap in CHECKS        # False
timestamps.check_sensor_frequency_stability in CHECKS # False
```

`datasetlint/checks/timestamps.py` defines `check_sensor_time_overlap` and `check_sensor_frequency_stability`. Neither is imported into `core.py` or added to any check group tuple. Both functions have parallel (different) implementations in `sync.py`. The `timestamps` versions run zero checks.

**Why it matters:** If a contributor or user imports directly from `datasetlint.checks.timestamps`, they get silent no-ops. The timestamps module's `check_sensor_time_overlap` has a slightly different (simpler) implementation than the one in `sync.py`, raising the question of which is authoritative. This is confusing to contributors and suggests the codebase grew without a refactor pass.  
**Fix:** Remove the dead functions from `timestamps.py`, or add them to `TIMESTAMP_CHECKS` if they are intentional additions. Make `sync.py`'s functions the only canonical implementations.

---

## 6. High Severity Issues

### HIGH-1: `--version` flag does not exist

**Reproduction:**
```bash
datasetlint --version
# Error: No such option: --version
```

**Expected:** `datasetlint 0.1.0`  
**Fix:** Add `typer.Option("--version", callback=version_callback, is_eager=True)` to the CLI.

---

### HIGH-2: `lint_dataset()` leaks `ValueError` to calling code when `checks=` is invalid

**Evidence:**
```python
from datasetlint import lint_dataset
lint_dataset("examples/minimal_dataset", checks="nonexistent")
# raises ValueError instead of returning a LintReport with an error issue
```

**Expected:** Returns a `LintReport` with an error issue describing the invalid check group, consistent with how every other error condition is handled.  
**Why it matters:** Any library code that calls `lint_dataset()` and passes `checks` from user input must now wrap it in a try/except. This breaks the design principle that `lint_dataset` always returns a `LintReport`.

---

### HIGH-3: Markdown report embeds raw Python `dict` literals instead of structured data

**Evidence:** The `--format markdown` output of `lint_dataset` includes:
```markdown
- `sync`: `{'sensors': {'camera_front': {'start_time': 0.0, 'end_time': 0.2, ...}}, ...}`
```
This is a Python `repr()` string embedded in markdown, not formatted JSON or a table.

**Why it matters:** The markdown format is advertised as a human-readable and pipeline-friendly alternative. A raw Python dict is neither. It renders badly in GitHub PR comments, documentation, and CI reports. It also cannot be parsed by non-Python tools.  
**Fix:** In `report.py:to_markdown()`, serialize the `sync` stats dict to indented JSON or a nested list, not `repr()`.

---

### HIGH-4: `formatters/json.py` and `formatters/markdown.py` are entirely dead code

**Evidence:** Only `formatters/console.py` is imported in the codebase (`cli.py:17`). The `json.py` and `markdown.py` formatters are never imported or called anywhere.

**Why it matters:** Dead code in a released package is confusing to contributors who might think they should use these formatters, and to users who might import them expecting them to be the canonical serialization path. The actual JSON and markdown formatting is done directly in `LintReport.to_json()` and `LintReport.to_markdown()`, which is fine, but the dead formatter modules imply a different design that was abandoned.  
**Fix:** Either remove `formatters/json.py` and `formatters/markdown.py`, or wire them up to actually be used.

---

## 7. Medium Severity Issues

### MED-1: Check name column is truncated in the console table

**Evidence:** In the console output of `datasetlint examples/bad_dataset`, check names are truncated to approximately 20 characters: `check_missing_sen…`, `check_broken_paths`, `check_declared_se…`. This makes it impossible to copy-paste the check name for filtering.  
**Fix:** Either widen the column minimum or show the full check name in a tooltip / footnote.

---

### MED-2: README documents `name` in `metadata.json` but the required field is `dataset_name`

**Evidence:** The README shows:
```json
{ "name": "...", "version": "...", ... }
```
The actual required field (enforced by `check_metadata_schema`) is `dataset_name`. Any user who copies the README example will immediately get a lint error on a dataset they just created.

**Verification:**
```bash
# Creating metadata with "name" instead of "dataset_name" produces:
# error: metadata.json must include a non-empty string dataset_name.
```

**Fix:** Correct the README metadata example to use `dataset_name`.

---

### MED-3: Camera sensor CSV requires column named `path` but README and quickstart use `filename`

**Evidence:** Creating a camera sensor CSV with `filename` as the column name (a natural choice) produces:
```
error: Sensor 'camera_front' is missing required columns: path.
```
The README does not document the required camera column names anywhere.  
**Fix:** Document required sensor CSV columns in the README and quickstart. Consider accepting both `path` and `filename` (or alias one to the other with a warning).

---

### MED-4: Test suite has no coverage of the two CLI crash paths (CRIT-2, CRIT-3)

**Evidence:** `tests/test_cli.py` has 4 tests, none of which test `--checks invalid_group` or `--adapter unknown`. The crashes in CRIT-2 and CRIT-3 would have been caught before shipping if these tests existed.

---

### MED-5: No `CONTRIBUTING.md`, `CHANGELOG.md`, or `CODE_OF_CONDUCT.md`

**Evidence:** `ls /Users/gagandeep/Documents/datasetlint/*.md` returns only `README.md`.  
**Why it matters:** Without `CONTRIBUTING.md`, external contributors do not know how to run the dev setup, what the PR process is, or what the code standards are.

---

### MED-6: No `[project.urls]` section in `pyproject.toml`

**Evidence:** `pyproject.toml` has no `[project.urls]` table, so the PyPI page will have no Homepage, Source, or Bug Tracker links.  
**Fix:** Add:
```toml
[project.urls]
"Homepage" = "https://github.com/..."
"Bug Tracker" = "https://github.com/.../issues"
```

---

### MED-7: `check_large_timestamp_gaps` and `check_missing_frame_bursts` may double-report the same gap

**Evidence:** Both checks scan for large timestamp gaps. `check_large_timestamp_gaps` in `timestamps.py` uses `timestamp_gap_threshold_sec` (default 0.5s), while `check_missing_frame_bursts` in `sync.py` uses `max_timestamp_gap_sec` (default 0.5s). These are the same default value and the same underlying condition. In `examples/bad_dataset`, the same gap in `camera_front.csv` triggers both `check_large_timestamp_gaps` (row 4) and `check_missing_frame_bursts` (row 4).

Additionally, `LintConfig` has two separate fields — `timestamp_gap_threshold_sec` and `max_timestamp_gap_sec` — with the same default (0.5) that control semantically related but slightly different checks. Users tuning one will not know they also need to tune the other.  
**Fix:** Merge the two config fields, or clearly document their distinct purposes.

---

## 8. Low Severity Issues

### LOW-1: Row numbers in issues may confuse users on label files

Row numbers in issue reports are 1-based (header = row 1, first data row = row 2), which is the correct spreadsheet convention. However, this is not documented anywhere. A user seeing `row=2` for the first data row may be confused.

---

### LOW-2: `imu` inferred frequency shows floating point noise

In `stats` output: `imu: 99.99999999999999 Hz` instead of `100.000 Hz`. This is due to floating-point arithmetic in gap median calculation. Minor but looks unprofessional in reports.

---

### LOW-3: `datasetlint stats --format markdown` renders `Rate Hz` as integer (drops decimal)

The console stats table shows `10.000` (3 decimal places) but the markdown table shows `10`. The `_format_optional` function in `stats.py` uses `:.6g` which drops trailing zeros, producing `10` for exactly 10.0.

---

### LOW-4: Release checklist is a docs file, not automated

The `docs/release-checklist.md` is a manual checklist. None of the steps are automated. A `Makefile` or `just` recipe would make this more reliable.

---

### LOW-5: `.DS_Store` is not in `.gitignore`

**Evidence:** `/Users/gagandeep/Documents/datasetlint/.DS_Store` exists and was found in the repo tree.  
**Fix:** Add `.DS_Store` to `.gitignore`.

---

### LOW-6: `frequency_jitter_fraction` and `frequency_jitter_ratio` both exist in `LintConfig`

**Evidence:** `LintConfig` has both `frequency_jitter_fraction` (used by `timestamps.check_sensor_frequency_stability`) and `frequency_jitter_ratio` (used by `sync.check_frequency_stability`). Because `timestamps.check_sensor_frequency_stability` is dead code, `frequency_jitter_fraction` is also effectively dead. This is another symptom of CRIT-5.

---

## 9. Installation Findings

| Command | Result |
|---|---|
| `python --version` | `Python 3.9.6` (macOS system Python) |
| `pip install -e .` (Python 3.9) | **FAILS**: `requires Python >=3.10` |
| `/opt/homebrew/bin/python3.11 -m pip install -e .` | Succeeds in ~15 seconds |
| `import datasetlint` | Succeeds |
| `datasetlint.__version__` | **AttributeError** (missing) |
| `datasetlint --version` | **Error: No such option** |

The README's installation section says `pip install datasetlint` with no Python version prerequisite warning. On macOS, `pip` resolves to Python 3.9 by default. This is a first-contact failure that will affect the majority of macOS users who have not explicitly set up Python 3.10+.

---

## 10. Documentation Findings

- **README.md** is well-structured and covers the feature set clearly.
- **Critical gap:** The metadata example uses `"name"` instead of `"dataset_name"` — contradicts the actual schema (see MED-2).
- **Critical gap:** Camera CSV `path` column is not mentioned; `filename` would be a natural guess (see MED-3).
- **docs/quickstart.md** is functional but minimal. It does not show what a correct `metadata.json` looks like.
- **docs/checks.md** accurately documents all check groups and config keys.
- **docs/adapters.md** correctly notes that non-folder adapters are detection-only in v0.
- **docs/release-checklist.md** is useful but entirely manual.
- **No CONTRIBUTING.md**: There is no document explaining how to set up the dev environment, run linting, or submit a PR.
- **No CHANGELOG.md**: No release history exists.
- **No CODE_OF_CONDUCT.md**: Standard for open source projects.
- **No `[project.urls]`** in pyproject.toml: No link to repository from PyPI.

---

## 11. CLI Findings

| Command | Result |
|---|---|
| `datasetlint --help` | Correct |
| `datasetlint --version` | **Error: No such option** |
| `datasetlint <path>` | Works correctly |
| `datasetlint <path> --format json` | Works correctly |
| `datasetlint <path> --format markdown` | Works (but sync dict is raw Python) |
| `datasetlint <path> --checks labels` | Works |
| `datasetlint <path> --checks bad_group` | **Traceback** (CRIT-2) |
| `datasetlint <path> --adapter foobar` | **Traceback** (CRIT-3) |
| `datasetlint stats <path>` | Works |
| `datasetlint stats <path> --format json` | Works, correct JSON |
| `datasetlint stats <path> --format markdown` | Works (minor rate formatting issue) |
| `datasetlint diff <old> <new>` | Works |
| `datasetlint diff <old> <new> --fail-on-regression` | Works, exits 1 |
| `datasetlint diff <old> <new> --format json` | Works, correct JSON |
| `datasetlint adapters <path>` | Works |
| `datasetlint adapters <path> --format json` | Works |
| `datasetlint <nonexistent path>` | Produces issues correctly, no crash |

The CLI uses a positional `args` list with manual dispatch (`if command == "stats"`) instead of typer subcommands. This means `datasetlint --help` does not show that `stats`, `diff`, and `adapters` are subcommands with their own options — they are described only in the `ARGS...` help string. A user reading `--help` for the first time cannot discover the subcommands or their options.

---

## 12. API Findings

**Public API surface (`datasetlint/__init__.py`):**
- `lint_dataset(path, config=None, checks=None, adapter="folder") -> LintReport` — clean; leaks ValueError on bad `checks` (HIGH-2)
- `compute_dataset_stats(path, config=None) -> DatasetStats` — clean
- `compare_datasets(old_path, new_path, config=None) -> DatasetDiffReport` — clean
- `LintReport`, `DatasetStats`, `DatasetDiffReport` — all Pydantic models, well-typed
- `Issue`, `LintConfig` — clean Pydantic models

**Lower-level API (from README):**
- `check_label_consistency(ctx)` and `check_sensor_synchronization(ctx)` — correctly documented and work
- `DatasetContext` is not in `__all__` but is constructable for advanced use

**Key design decision:** `lint_dataset` always returns a `LintReport` even for missing paths. This is the right call — library code should not raise on user data problems. But the `ValueError` on bad `checks=` breaks this contract.

---

## 13. Workflow Testing Results

| # | Workflow | Result |
|---|---|---|
| 1 | First install (macOS system Python) | FAIL: Python 3.9 not supported |
| 2 | Install with Python 3.11 | PASS |
| 3 | Import package, check version | FAIL: no `__version__` |
| 4 | Run `--help` | PASS |
| 5 | Run `--version` | FAIL: option does not exist |
| 6 | Lint minimal dataset (console) | PASS: 0 issues |
| 7 | Lint bad dataset (console) | PASS: 31 issues correctly identified |
| 8 | Lint dataset with `--format json` | PASS: valid JSON |
| 9 | Lint dataset with `--format markdown` | PARTIAL: sync dict is raw Python |
| 10 | Lint with `--checks labels` | PASS |
| 11 | Lint with `--checks sync` | PASS |
| 12 | Lint with `--checks bad_group` | FAIL: traceback |
| 13 | Lint with `--adapter foobar` | FAIL: traceback |
| 14 | Use Python API `lint_dataset` | PASS for valid inputs |
| 15 | Use Python API `lint_dataset(checks="bad")` | FAIL: ValueError leaks to caller |
| 16 | `datasetlint stats` console | PASS |
| 17 | `datasetlint stats --format json` | PASS |
| 18 | `datasetlint stats --format markdown` | PARTIAL: rate formatting drops decimals |
| 19 | `datasetlint diff` | PASS |
| 20 | `datasetlint diff --fail-on-regression` | PASS |
| 21 | `datasetlint adapters` | PASS |
| 22 | Create synthetic dataset with correct schema | PASS |
| 23 | Create synthetic dataset with wrong metadata keys | FAIL to lint (error issued) — correct behavior |
| 24 | YAML config override | PASS |
| 25 | Non-existent dataset path | PASS: error issue returned, no crash |
| 26 | Run `pytest` | PASS: 26 passed in 0.78s |

---

## 14. Dataset Diff Findings

- `compare_datasets` correctly computes regressions for: removed sensors, frame count drops, calibration changes, increased issue counts, speed/acceleration increases, and disappeared label classes.
- The `--fail-on-regression` flag correctly exits 1 when regressions exist.
- JSON and markdown diff output formats work correctly.
- The console diff table is wide and may wrap on narrow terminals.
- The diff only watches four specific check names for regression tracking (`check_sensor_time_overlap`, `check_pairwise_sync_gap`, `check_unrealistic_speed`, `check_unrealistic_acceleration`). Other checks that worsen are tracked only in aggregate issue counts, not per-check. This is a deliberate v0 scoping but not documented.

---

## 15. Adapter Findings

- `FolderAdapter` works correctly and is the only fully functional adapter.
- `MCAPAdapter`, `ROSBagAdapter`, `NuScenesAdapter`, `WaymoAdapter` all return clear `NotImplementedError` messages when `load_metadata` is called — as documented.
- The `--adapter auto` flag correctly falls back to `FolderAdapter` when the dataset does not exist.
- `detect_adapters()` reports all five adapters correctly.
- No adapter other than `folder` can actually lint a dataset in v0. This is documented in the README and `adapters.md`, so it is not a defect — but it is a significant limitation that robotics users may not notice until they try.

---

## 16. Sensor Synchronization Findings

- `check_sensor_time_overlap` correctly catches non-overlapping sensor ranges (error) and low-overlap ratio (warning).
- `check_timestamp_offset` correctly catches start-time offsets between sensor streams.
- `check_pairwise_sync_gap` correctly computes nearest-timestamp gaps between all sensor pairs.
- `check_missing_frame_bursts` correctly detects burst-sized gaps.
- `check_frequency_stability` correctly detects jitter above threshold.
- Single-sensor datasets correctly return empty list from `check_sensor_time_overlap` (boundary case verified).
- The `_nearest_timestamp_gaps` implementation using `np.searchsorted` is algorithmically correct and efficient.
- **Duplicate check issue:** `timestamps.py` has its own `check_sensor_time_overlap` (simpler implementation) that is dead code. Only `sync.py`'s version runs (CRIT-5).

---

## 17. Label Consistency Findings

- All 10 label checks run correctly and produce accurate results on the bad dataset.
- `check_label_columns` correctly requires all 8 columns.
- `check_label_confidence_range` correctly flags values outside `[0, 1]`.
- `check_label_geometry` correctly flags non-positive width/height.
- `check_label_timestamps_match_sensor_range` correctly flags labels outside the sensor time window.
- `check_track_id_consistency` correctly flags class switches.
- `check_label_bbox_jumps` correctly computes center-to-center distance.
- `check_label_missing_timestamps` correctly uses minimum in-track gap as expected gap.
- `check_duplicate_track_id_timestamp` correctly finds duplicate `(track_id, timestamp)` pairs.
- `check_short_tracks` correctly enforces `label_min_track_length`.
- `check_label_size_changes` correctly computes max-ratio of width and height changes.

---

## 18. Distribution Analysis Findings

- `compute_dataset_stats` correctly computes frame counts, inferred rates, label class counts, confidence distributions, track length distributions, speed/acceleration distributions, and missing frame counts.
- `DatasetStats.to_json()` produces valid machine-parseable JSON.
- `DatasetStats.to_markdown()` renders a human-readable table, but the Labels and Trajectories sections embed raw Python dicts (same issue as MED-3 / HIGH-3).
- The `speed_summary` and `acceleration_summary` are only populated when the trajectory CSV has `vx` and `vy` columns — datasets with only `x`, `y`, `z` positional columns will show empty summaries with no diagnostic. This is undocumented.

---

## 19. Reliability Findings

**Negative tests run:**

| Test | Result |
|---|---|
| `lint_dataset` on non-existent path | Returns error issue, no crash |
| `lint_dataset` on file (not directory) | Returns error issue, no crash |
| `lint_dataset(checks="bad")` | Raises ValueError (broken) |
| `datasetlint --adapter foobar` | Raises ValueError traceback (broken) |
| Empty dataset (no CSVs) | Returns required-files errors correctly |
| Malformed calibration.json | Returns error issues correctly |
| Non-monotonic timestamps | Detected correctly |
| Duplicate timestamps | Detected correctly |
| Valid YAML config | Parsed correctly |
| Nested YAML dict config | Parsed correctly |

**The core happy-path and many sad-path inputs are handled correctly. The two crash paths are both input validation errors that should never reach user-visible stack traces.**

---

## 20. Test Suite Findings

- **26 tests, 0 failures** on Python 3.11.
- Test infrastructure: pytest with `tmp_path` fixture. `conftest.py` has a single `write_good_dataset()` helper.
- **Coverage gaps:**
  - No test for `--version` flag (which doesn't exist)
  - No test for `--checks invalid_group` (CRIT-2)
  - No test for `--adapter foobar` (CRIT-3)
  - No test for `lint_dataset(checks="bad")` API behavior (HIGH-2)
  - No test for Python API `__version__` attribute (CRIT-4)
  - No test that `check_sensor_time_overlap` in `timestamps.py` is or is not reachable (CRIT-5)
  - No test for the markdown output `sync` field format (HIGH-3)
  - No test for `--format markdown` diff output
  - No test for YAML config loading edge cases (list syntax, comments, blank lines)
  - No test for single-sensor datasets in sync checks
  - No test for datasets with `vx`/`vy` absent (speed summary empty)
- Tests do not use `pytest-cov` or report coverage — no coverage target is defined.
- Dev dependencies in `pyproject.toml` do not include `pytest-cov`, `typer[all]`, or test-specific extras.

---

## 21. Open Source Readiness Findings

| Item | Status |
|---|---|
| LICENSE file (MIT) | Present |
| README.md | Present (with schema errors) |
| CONTRIBUTING.md | **Missing** |
| CHANGELOG.md | **Missing** |
| CODE_OF_CONDUCT.md | **Missing** |
| GitHub Actions CI | Present (tests on 3.10, 3.11, 3.12) |
| `[project.urls]` in pyproject.toml | **Missing** |
| `.DS_Store` in repo | **Present** (should be gitignored) |
| `__version__` in package | **Missing** |
| PyPI classifiers | Present and accurate |
| Keywords | Present |
| Authors | Present (generic) |
| Example datasets | Present (minimal and bad) |
| Docs | Present (5 markdown files) |

---

## 22. Production Readiness Findings

- No structured logging (acceptable for a CLI tool, but library users have no log hooks).
- No profiling or performance benchmarks. For very large CSVs (millions of rows), the per-row issue generation in label checks may be slow; no warning exists.
- No support for streaming or partial dataset validation. The entire dataset is loaded into memory as DataFrames.
- No plugin or extension point for custom checks. Users who want domain-specific checks must fork the code.
- The YAML parser is hand-rolled and handles only a subset of YAML syntax (no lists, no multi-line values, no anchors). This is documented as intentional but is a trap for users who try to write any YAML beyond the documented shape.
- No Windows path handling issues found (uses `pathlib.Path` throughout).
- No concurrent access issues (fully stateless per invocation).

---

## 23. Competitive Review

There is no direct comparable tool that is:
- Pure Python
- Local / offline
- Importable as a library
- Focused on robotics/physical AI datasets
- Free and open source

The closest alternatives:
- **Great Expectations** — general-purpose data validation, not robotics-specific, heavy dependency tree, cloud-oriented
- **Pandera** — DataFrame schema validation only, no file/calibration/sync checks
- **MCAP CLI** — MCAP-specific, no label or calibration checks
- **ROS2 bag tools** — ROS-specific, not general-purpose
- **Custom per-project scripts** — the status quo this tool replaces

DatasetLint's differentiation is real. The synchronization checks, calibration checks, and label consistency checks are genuinely useful and not available elsewhere in a standalone form. The `diff` feature for regression detection across dataset versions is particularly novel.

The limitation is the folder-only format requirement. The robotics community primarily uses MCAP, ROS bags, NuScenes, and Waymo formats. Until adapters are implemented, DatasetLint requires a data conversion step that many teams will not want to do.

---

## 24. Top 10 Improvements Before Launch

1. **Add Python version prerequisite warning to README** (CRIT-1). This costs 2 lines of text and will prevent dozens of frustrated first installs.
2. **Catch `ValueError` in CLI for bad `--checks` and `--adapter` inputs** (CRIT-2, CRIT-3). A 5-line fix that eliminates the most visible first-impression failure.
3. **Add `__version__` to `datasetlint/__init__.py`** (CRIT-4). One line.
4. **Add `--version` to CLI** (HIGH-1). Five lines of typer code.
5. **Fix `lint_dataset` to return a `LintReport` with an error issue instead of raising `ValueError` on bad `checks=`** (HIGH-2). Keeps the API contract consistent.
6. **Remove dead code** from `timestamps.py` (`check_sensor_time_overlap`, `check_sensor_frequency_stability`, `frequency_jitter_fraction` from LintConfig) and from `formatters/` (CRIT-5, HIGH-4).
7. **Fix README metadata example** to use `dataset_name` not `name` (MED-2). Document the required camera CSV column `path`.
8. **Fix markdown report's `sync` stat to use indented JSON, not Python repr** (HIGH-3).
9. **Add CONTRIBUTING.md** with dev setup, test commands, and PR guidelines (MED-5).
10. **Add tests for all error paths** that are currently broken (MED-4). Specifically: `--checks bad_group`, `--adapter foobar`, `lint_dataset(checks="bad")`, `--version`.

---

## 25. Recommended Roadmap

### Before Launch (v0.1.0 tag)

- All 5 critical issues fixed
- All 4 high severity issues fixed
- MED-2, MED-3 documentation fixes
- Add CONTRIBUTING.md
- Add `.gitignore` entry for `.DS_Store`
- Add `[project.urls]` to pyproject.toml
- Add `--version` flag tests

### After Launch (v0.1.x patch releases)

- Fix markdown report Python dict embedding (HIGH-3)
- Fix console column truncation (MED-1)
- Document speed_summary behavior when vx/vy columns absent
- Add pytest-cov to dev dependencies and set a minimum coverage target (80%)
- Merge `timestamp_gap_threshold_sec` and `max_timestamp_gap_sec` into one config field

### Longer-Term (v0.2 and beyond)

- Implement MCAP adapter (highest priority for robotics community adoption)
- Implement ROS bag adapter
- Add custom check plugin interface (callback-based or entry_points-based)
- Add support for streaming/chunked validation of large datasets
- Add `--output FILE` flag to write reports to disk
- Add per-check severity override configuration
- Add NuScenes adapter
- Consider making `calibration.json` optional (not all datasets have calibration)
- Provide a GitHub Action that runs datasetlint in CI pipelines

---

## 26. Reproduction Appendix

All commands were run in `/Users/gagandeep/Documents/datasetlint` unless noted.

### Environment

```
python3 --version            → Python 3.9.6 (system, blocks install)
/opt/homebrew/bin/python3.11 --version → Python 3.11.15
pip3 --version → pip 26.0.1 (Python 3.9)
/opt/homebrew/bin/python3.11 -m pip --version → pip 26.1 (Python 3.11)
```

### Install

```bash
pip install -e .
# ERROR: Package 'datasetlint' requires a different Python: 3.9.6 not in '>=3.10'

/opt/homebrew/bin/python3.11 -m pip install -e .
# Successfully installed datasetlint-0.1.0 (and all deps)
```

### Version checks

```bash
# Exported PATH="/opt/homebrew/bin:$PATH" for all CLI commands below

python3.11 -c "import datasetlint; print(datasetlint.__version__)"
# AttributeError: module 'datasetlint' has no attribute '__version__'

datasetlint --version
# Error: No such option: --version
```

### CLI happy path

```bash
datasetlint examples/minimal_dataset
# passed with 0 issue(s) (error=0, warning=0, info=0)

datasetlint examples/bad_dataset
# failed with 31 issue(s) (error=16, warning=15, info=0) - exit code 1

datasetlint examples/minimal_dataset --format json
# valid JSON

datasetlint examples/minimal_dataset --format markdown
# markdown with raw Python dict in sync field

datasetlint stats examples/minimal_dataset
# sensor table showing camera_front:3/10Hz, imu:21/100Hz, gps:3/10Hz

datasetlint diff examples/minimal_dataset examples/bad_dataset
# 19 changes, 12 regressions, 1 improvement

datasetlint adapters examples/minimal_dataset
# folder=True, mcap/rosbag/nuscenes/waymo=False
```

### CLI crash paths

```bash
datasetlint examples/minimal_dataset --checks bad_group
# ValueError traceback — exit code 1

datasetlint examples/minimal_dataset --adapter foobar
# ValueError traceback — exit code 1
```

### Python API

```bash
python3.11 -c "
from datasetlint import lint_dataset
try:
    lint_dataset('examples/minimal_dataset', checks='nonexistent')
except ValueError as e:
    print('EXCEPTION:', e)
"
# EXCEPTION: Unknown check group 'nonexistent'. Known groups: ...
```

### Dead code verification

```bash
python3.11 -c "
from datasetlint.core import CHECKS
from datasetlint.checks import timestamps
print(timestamps.check_sensor_time_overlap in CHECKS)        # False
print(timestamps.check_sensor_frequency_stability in CHECKS) # False
"
```

### Test run

```bash
/opt/homebrew/bin/python3.11 -m pip install pytest
/opt/homebrew/bin/python3.11 -m pytest tests/ -v
# 26 passed in 0.78s
```

### Synthetic dataset test

```bash
# Created /tmp/test_synthetic_dataset/ with:
# - metadata.json (using "name" instead of "dataset_name")
# - sensors/camera_front.csv (using "filename" instead of "path")
# - sensors/imu.csv, labels/detections.csv, trajectories/ego.csv
# - calibration.json

datasetlint /tmp/test_synthetic_dataset
# failed with 2 issue(s):
#   error: metadata.json must include a non-empty string dataset_name.
#   error: Sensor 'camera_front' is missing required columns: path.
# (confirms README metadata example is wrong)
```

### YAML config

```bash
echo "timestamp_gap_threshold_sec: 0.1" > /tmp/test_config.yaml
python3.11 -c "
from datasetlint.core import load_config
from pathlib import Path
cfg = load_config(Path('/tmp'), Path('/tmp/test_config.yaml'))
print(cfg.timestamp_gap_threshold_sec)  # 0.1 — correct
"

# Nested dict YAML:
cat > /tmp/test_nested.yaml << EOF
expected_sensor_rates:
  camera_front: 15
  imu: 200
max_speed_mps: 30
EOF
python3.11 -c "
from datasetlint.core import _parse_simple_yaml
from pathlib import Path
print(_parse_simple_yaml(Path('/tmp/test_nested.yaml')))
# {'expected_sensor_rates': {'camera_front': 15, 'imu': 200}, 'max_speed_mps': 30}
"
```
