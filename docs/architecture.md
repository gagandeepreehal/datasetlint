# Architecture

DatasetLint v0 keeps the production path simple: load a native folder dataset,
build a `DatasetContext`, run check functions, and return a `LintReport`.

## Current Native Folder Linting

The native folder format is the deep-validation path:

```text
metadata.json
calibration.json
sensors/*.csv
labels/*.csv
trajectories/*.csv
```

`datasetlint.core.lint_dataset()` resolves the dataset path, loads
`LintConfig`, selects check groups, loads JSON and CSV files into a
`DatasetContext`, runs checks, and returns a `LintReport`.

This keeps the public API small:

```python
from datasetlint import lint_dataset

report = lint_dataset("examples/minimal_dataset")
```

## Normalized DatasetManifest

Adapters are the right place to inspect foreign formats without forcing heavy
runtime dependencies. The next internal foundation should be a normalized
`DatasetManifest` that records format-agnostic facts such as:

- Dataset root or source file
- Adapter name
- Validation mode: deep, manifest-level, or index-level
- Sensor streams and observed frame counts
- Timestamp ranges when available
- Label and trajectory file references when available
- Calibration references when available
- Known limitations for the source format

Native folder datasets can produce a complete manifest. MCAP, ROS bag, Waymo,
NuScenes, KITTI, COCO, and Hugging Face adapters can start with partial
manifests that clearly state what was not checked.

## Future ValidationContext

Common rules should eventually run over a `ValidationContext` built from the
manifest plus optional loaded tables. That would let DatasetLint reuse checks
for native and adapted datasets when the same normalized facts are available.

The intended direction:

```text
source dataset -> adapter -> DatasetManifest -> ValidationContext -> checks -> LintReport
```

The current `DatasetContext` should remain supported while this foundation
lands. A future `ValidationContext` can wrap or supersede it once common checks
no longer assume folder-local CSV files.

## Migration Plan

1. Keep `lint_dataset(path, config=None, checks=None, adapter="folder")` stable.
2. Add internal `DatasetManifest` models without changing public return types.
3. Teach the folder adapter to emit a full manifest.
4. Teach detection-only adapters to emit partial manifests with explicit
   coverage and limitations.
5. Move checks that only need normalized metadata, timestamps, or counts onto
   the manifest-backed context.
6. Keep folder-specific CSV checks in place until equivalent manifest-backed
   data loaders exist.
7. Add optional parser extras later, such as MCAP or ROS bag parsing, without
   making them core runtime dependencies.

This path improves real-format validation while preserving existing APIs and
the local-first install footprint.
