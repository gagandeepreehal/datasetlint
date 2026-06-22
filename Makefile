PYTHON ?= $(shell command -v python3.11 || command -v python3 || command -v python)
WHEEL_DIR ?= dist

.PHONY: test lint typecheck wheel smoke-examples release-check

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .

typecheck:
	$(PYTHON) -m mypy datasetlint

wheel:
	$(PYTHON) -m pip wheel . --wheel-dir $(WHEEL_DIR) --no-deps --no-build-isolation

smoke-examples:
	$(PYTHON) -c "from datasetlint import lint_dataset; raise SystemExit(0 if lint_dataset('examples/minimal_dataset').passed else 1)"
	$(PYTHON) -c "from datasetlint import lint_dataset; r = lint_dataset('examples/bad_dataset'); raise SystemExit(0 if (not r.passed and r.count_by_severity()['error'] > 0) else 1)"

release-check: test lint typecheck wheel smoke-examples
