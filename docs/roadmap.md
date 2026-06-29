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

- Deeper semantic decoding beyond current metadata manifests: MCAP and ROS bag message payloads, Waymo image/lidar payloads, richer nuScenes payload semantics, and richer Hugging Face row schemas.
- Additional dataset adapters such as Argoverse, BDD100K, SemanticKITTI, LeRobot/Open X-Embodiment, and RLDS/TFDS robotics datasets.
- Richer sensor synchronization checks.
- Richer static HTML report styling while keeping reports dependency-free.
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
