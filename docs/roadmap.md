# Roadmap

This roadmap separates planned work from implemented behavior. Do not treat these items as current features.

## Short Term

- More targeted example datasets for individual rule groups.
- Stronger dataset diff coverage and clearer regression categories.
- CI examples for common repository layouts.
- Documentation for rule extension patterns.
- More report examples and expected-output fixtures.
- Conversion helpers from normalized adapter manifests into the native folder format.

## Medium Term

- Optional deep MCAP channel, schema, compression, and message inspection.
- Optional deep ROS bag topic and message parsing.
- Optional deep Waymo TFRecord frame, label, and calibration parsing.
- Additional dataset adapters such as Argoverse, BDD100K, SemanticKITTI, LeRobot/Open X-Embodiment, and RLDS/TFDS robotics datasets.
- Richer sensor synchronization checks.
- Static HTML report output or report UI.
- Entry-point plugin discovery for third-party adapters.

## Long Term

- Rule plugin system.
- Benchmark sample datasets.
- Large-dataset performance profiling.
- More configurable validation policies.
- Optional machine-readable schema export.

## Non-Goals

- Dataset hosting or storage.
- Dataset version control.
- Model evaluation.
- Simulation or replay.
- Cloud-first dataset management.
