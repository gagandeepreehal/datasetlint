#!/usr/bin/env sh
set -eu

datasetlint lint examples/minimal_dataset
datasetlint lint examples/broken_dataset || true
datasetlint report examples/minimal_dataset --out /tmp/datasetlint-report.json
datasetlint diff examples/minimal_dataset examples/broken_dataset || true
