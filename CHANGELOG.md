# Changelog

All notable changes to DatasetLint will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). This repository has no Git tags in the current checkout, so historical releases are not listed as shipped.

## Unreleased

### Added

- Initial local-first DatasetLint package scaffold for folder-based robotics dataset validation.
- CLI entry point for validation, stats, diffs, and adapter detection.
- Python API exports for linting, stats, diffs, reports, issues, and config.
- Native folder adapter plus detection-only MCAP, ROS bag, NuScenes, and Waymo adapters.
- Config-file rule policy with `rules.enabled`, `rules.disabled`, and per-check severity overrides.
- Full YAML config parsing for nested maps and lists.
- Entry-point discovery for third-party adapters via the `datasetlint.adapters` group.
- Argoverse 2 and LeRobot manifest adapters.
- Deep MCAP and ROS bag timestamp diagnostics for dropped topics and cross-topic desync.
- Example datasets for passing and failing validation paths.
- MkDocs documentation workflow and publishing workflow metadata.

### Docs

- Launch-readiness README, contributor guide, security policy, examples guide, and full docs navigation.
- Troubleshooting guide for row-level issue locations, fix suggestions, adapter plugins, and deep log validation.

### Notes

- Publish the first tagged release before documenting `pip install datasetlint` as the primary install path.
