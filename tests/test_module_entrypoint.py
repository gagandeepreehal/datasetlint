from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_python_module_entrypoint_version():
    repo = Path(__file__).resolve().parents[1]

    result = subprocess.run(
        [sys.executable, "-m", "datasetlint", "--version"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "datasetlint 0.1.0"
    assert result.stderr == ""
