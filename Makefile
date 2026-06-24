PYTHON ?= $(shell command -v python3.12 || command -v python3.11 || command -v python3.10 || command -v python3 || command -v python)
WHEEL_DIR ?= dist

.PHONY: install test lint format typecheck wheel smoke-examples example check release-check

install:
	$(PYTHON) -m pip install -e ".[dev,docs]"

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff format .

typecheck:
	$(PYTHON) -m mypy datasetlint

wheel:
	$(PYTHON) -m build --outdir $(WHEEL_DIR)

smoke-examples:
	$(PYTHON) -c "from datasetlint import lint_dataset; raise SystemExit(0 if lint_dataset('examples/minimal_dataset').passed else 1)"
	$(PYTHON) -c "from datasetlint import lint_dataset; r = lint_dataset('examples/bad_dataset'); raise SystemExit(0 if (not r.passed and r.count_by_severity()['error'] > 0) else 1)"

example: smoke-examples
	$(PYTHON) examples/python_api_example.py
	$(PYTHON) -m datasetlint report examples/minimal_dataset --out /tmp/datasetlint-example-report.json

check: lint typecheck test
	$(PYTHON) -m ruff format --check .

release-check: check wheel smoke-examples
