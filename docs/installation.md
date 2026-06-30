# Installation

DatasetLint requires Python 3.10 or newer.

## Install From Source

```bash
git clone https://github.com/gagandeepreehal/datasetlint.git
cd datasetlint
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev,docs]"
```

Use another supported interpreter if needed:

```bash
python3.10 -m venv .venv
python3.12 -m venv .venv
```

## Runtime-Only Editable Install

For a minimal editable install without dev or docs tools:

```bash
python -m pip install -e .
```

## Adapter Extras

Heavy dataset runtimes are optional. Install only the extras you need:

```bash
python -m pip install -e ".[adapters]"
python -m pip install -e ".[hf]"
python -m pip install -e ".[mcap]"
python -m pip install -e ".[ros]"
python -m pip install -e ".[nuscenes]"
python -m pip install -e ".[waymo]"
python -m pip install -e ".[all-adapters]"
```

The base install can still inspect COCO, KITTI, generic folders, nuScenes
metadata tables, index-mode Waymo, ROS bag, and MCAP datasets, and cache-like
Hugging Face metadata without those heavy optional packages. Install the
matching extra and use `--deep` when you want parser-backed MCAP
channel/schema/timestamp metadata, ROS bag topic/message metadata, Waymo
frame/label/calibration metadata, or sampled Hugging Face row diagnostics.

## Package Install Status

This repository has package metadata and a publish workflow, but the current checkout has no Git tags. Until the first PyPI release is published, use the source install rather than documenting `pip install datasetlint` as the default path.

## Verify The Install

```bash
datasetlint --help
datasetlint --version
datasetlint examples/minimal_dataset
pytest
```

## Troubleshooting

### `Python 3.9` On macOS

The macOS system `python3` can be Python 3.9. DatasetLint requires Python 3.10 or newer.

Use Homebrew, pyenv, uv, asdf, or your preferred Python manager to install a supported interpreter, then create the virtual environment with that executable.

### `datasetlint: command not found`

Activate the virtual environment and confirm the editable install completed:

```bash
source .venv/bin/activate
python -m pip install -e ".[dev,docs]"
python -m datasetlint --help
```

### Missing Dev Tools

If `pytest`, `ruff`, `mypy`, or `mkdocs` are missing, install the dev and docs extras:

```bash
python -m pip install -e ".[dev,docs]"
```

### Invalid Config Keys

DatasetLint rejects unknown config keys. Check [Configuration](configuration.md) for the supported keys.
