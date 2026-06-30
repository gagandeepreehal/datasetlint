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

- Deeper semantic decoding beyond current metadata manifests: MCAP and ROS bag message payloads, Waymo image/lidar payload bytes, full nuScenes devkit/map/point-cloud semantics, and dataset-specific Hugging Face row schemas.
- Additional dataset adapters such as BDD100K, SemanticKITTI, Open X-Embodiment, and RLDS/TFDS robotics datasets.
- Richer sensor synchronization checks.
- Richer static HTML report styling while keeping reports dependency-free.

## Long Term

- Rule plugin system.
- Benchmark sample datasets.
- Large-dataset performance profiling.
- Rule plugin system beyond config-file rule policy.
- Optional machine-readable schema export.

## Non-Goals

- Dataset hosting or storage.
- Dataset version control.
- Model evaluation.
- Simulation or replay.
- Cloud-first dataset management.
