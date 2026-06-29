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

Adapters for generic folders, COCO, KITTI, nuScenes, Waymo, ROS bag, MCAP, and Hugging Face produce a normalized `DatasetManifest`. The manifest captures common records:

- sequences
- frames
- sensors
- annotations
- calibration
- splits
- metadata
- provenance
- limitations

This layer supports inspection, export, and adapter validation without forcing every source dataset into the native folder format first.

## Current Validation Boundary

Adapter validation reports are explicit about scope:

- `validation_mode` says whether validation is deep, manifest-level, or index-level.
- `checked` lists what was actually inspected.
- `not_checked` lists important gaps.
- `limitations` describes parser and coverage limits.

Today, MCAP, ROS bag, and Waymo default to index-level for the base install, but `--deep` uses optional parsers to extract external-format metadata:

- MCAP: channels, schemas, and message timestamps.
- ROS bag: topics, message types, counts, and timestamps.
- Waymo: TFRecord frames, sensors, labels, and calibration metadata.

COCO, KITTI, nuScenes, Hugging Face, and generic folder adapters are manifest-level. Deep common-rule validation still remains the native folder path until common rules can run over normalized manifests.

## Future ValidationContext

A future `ValidationContext` should let common rules operate over either native folder data or normalized manifests. It should provide stable accessors for:

- metadata fields
- sensor streams and timestamps
- frame references
- calibration records
- annotations and track IDs
- trajectories when available
- source-file provenance

The goal is to reuse checks such as broken references, duplicate timestamps, sensor sync gaps, missing calibration, invalid intrinsics, label geometry, duplicate track IDs, and trajectory speed without duplicating every rule per adapter.

## Migration Plan

1. Keep `lint_dataset()`, `LintReport`, adapter APIs, and CLI commands stable.
2. Add `ValidationContext` internally beside `DatasetContext`.
3. Teach one low-risk rule group to consume `ValidationContext` while preserving native folder behavior.
4. Convert adapter manifests into `ValidationContext` only when the adapter has enough data for that rule group.
5. Keep `validation_mode`, `checked`, `not_checked`, and `limitations` populated so partial coverage remains visible.
6. Gradually move common rules over as tests prove parity.

This avoids a large refactor while creating a path from manifest inspection toward deeper real-format validation.
