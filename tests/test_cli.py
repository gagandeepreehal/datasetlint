from __future__ import annotations

from typer.testing import CliRunner

from datasetlint.cli import app
from tests.conftest import write_good_dataset


def test_cli_exits_nonzero_when_fail_on_error_is_triggered(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    (dataset / "metadata.json").unlink()
    runner = CliRunner()

    result = runner.invoke(app, [str(dataset), "--format", "json", "--fail-on", "error"])

    assert result.exit_code == 1
    assert "check_required_files" in result.stdout

