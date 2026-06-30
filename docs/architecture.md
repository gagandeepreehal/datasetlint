# Architecture

DatasetLint is intentionally small. The current implementation has two related surfaces: the native folder rule engine and the normalized adapter manifest layer.

## Native Folder Linting

`datasetlint lint DATASET` and the shorthand `datasetlint DATASET` run the deep rule engine against the native DatasetLint folder format:

```text
dataset/
  metadata.json
  calibration.json
  sensors/*.csv
  labels/*.csv
  trajectories/*.csv
```

The core API loads those files into `DatasetContext`, applies selected check groups, and returns a `LintReport`. This path is where deep dataset validation currently lives: metadata, file references, timestamps, sensor sync, calibration, labels, trajectories, stats, and dataset diff behavior.

## Normalized DatasetManifest

Adapters for generic folders, COCO, KITTI, Argoverse 2, LeRobot, nuScenes, Waymo, ROS bag, MCAP, Hugging Face, and plugin-provided formats produce a normalized `DatasetManifest`. The manifest captures common records:

- sequences
- frames
- sensors
- annotations
- calibration
- splits
- metadata
- provenance
- limitations

This layer supports inspection, export, and adapter validation without forcing every source dataset into the native folder format first. Adapter validation also runs a small shared rule layer over decoded manifest records when those records are available.

## Current Validation Boundary

Adapter validation reports are explicit about scope:

- `validation_mode` says whether validation is deep, manifest-level, or index-level.
- `checked` lists what was actually inspected.
- `not_checked` lists important gaps.
- `limitations` describes parser and coverage limits.

Today, MCAP, ROS bag, Waymo, and Hugging Face default to index-level for the base install, but `--deep` uses optional parsers or bounded samplers to extract external-format metadata:

- MCAP: channels, schemas, message timestamps, dropped-topic-style gaps where observable, and cross-topic sync diagnostics.
- ROS bag: topics, message types, counts, timestamps, dropped topics, and cross-topic sync diagnostics.
- Waymo: TFRecord frame, sensor, label, calibration, and payload-summary metadata.
- Hugging Face: sampled row payload summaries, feature-derived streams, label/bbox-like annotations, duplicate sample IDs, and malformed sampled bbox payloads.

If a requested deep parser fails to parse the input, adapter validation records the parser error, reports `valid: false`, and the CLI exits with code `1`. A deep parse failure should not look like a successful deep validation pass.

COCO, KITTI, nuScenes, and generic folder adapters are manifest-level. Their validation reports run the shared manifest-rule layer over normalized records when the adapter has decoded enough data for a rule.

Adapter reports now include `coverage.common_rule_inputs` and `stats.common_rule_stats` for the shared manifest-rule layer. These common rules currently check decoded record references, duplicate and non-monotonic timestamps, large timestamp gaps, coarse sensor sync gaps, calibration matrix shape, annotation links, and split references. They only run on records the adapter actually decoded. For example, Waymo index-mode placeholder TFRecord records are excluded from common frame/sensor coverage, while Waymo `--deep` frame metadata is included. Hugging Face default validation stays at cache/index metadata, while Hugging Face `--deep` sampled rows feed common frame and annotation checks. Relative file paths from single-file roots are resolved from the root file's parent directory so `.bag`, `.mcap`, and `.tfrecord` manifests do not produce false missing-file errors for basename paths.

This is still not full native-rule parity. The native folder rule engine remains the deepest validation path for label geometry, track behavior, trajectories, and project-specific CSV/JSON checks.

## Future ValidationContext

A future `ValidationContext` should let common rules operate over either native folder data or normalized manifests. It should provide stable accessors for:

- metadata fields
- sensor streams and timestamps
- frame references
- calibration records
- annotations and track IDs
- trajectories when available
- source-file provenance

The goal is to expand the current shared manifest-rule layer into a fuller context that can reuse checks such as broken references, duplicate timestamps, sensor sync gaps, missing calibration, invalid intrinsics, label geometry, duplicate track IDs, and trajectory speed without duplicating every rule per adapter.

## Migration Plan

1. Keep `lint_dataset()`, `LintReport`, adapter APIs, and CLI commands stable.
2. Keep extending the lightweight manifest-rule layer for low-risk checks that only need normalized records.
3. Add `ValidationContext` internally beside `DatasetContext`.
4. Teach one native rule group to consume `ValidationContext` while preserving native folder behavior.
5. Convert adapter manifests into `ValidationContext` only when the adapter has enough data for that rule group.
6. Keep `validation_mode`, `checked`, `not_checked`, and `limitations` populated so partial coverage remains visible.
7. Gradually move common rules over as tests prove parity.

This avoids a large refactor while creating a path from manifest inspection toward deeper real-format validation.
