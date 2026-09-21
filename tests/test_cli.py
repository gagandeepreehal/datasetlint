from __future__ import annotations

import json
import re
import subprocess
import sys

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


def test_cli_stats_json(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    runner = CliRunner()

    result = runner.invoke(app, ["stats", str(dataset), "--format", "json"])

    assert result.exit_code == 0
    assert '"frame_counts"' in result.stdout


def test_cli_diff_fail_on_regression(tmp_path):
    old_dataset = write_good_dataset(tmp_path / "old")
    new_dataset = write_good_dataset(tmp_path / "new")
    (new_dataset / "sensors" / "camera_front.csv").write_text(
        "\n".join(
            [
                "timestamp,path,width,height",
                "0.0,images/000001.jpg,1280,720",
                "0.1,images/000002.jpg,1280,720",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["diff", str(old_dataset), str(new_dataset), "--fail-on-regression"],
    )

    assert result.exit_code == 1
    assert "camera_front" in result.stdout


def test_cli_adapters_json(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    runner = CliRunner()

    result = runner.invoke(app, ["adapters", str(dataset), "--format", "json"])

    assert result.exit_code == 0
    assert '"folder"' in result.stdout


def test_cli_version_flag():
    runner = CliRunner()

    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == "datasetlint 0.0.2"


def test_cli_lint_alias(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    runner = CliRunner()

    result = runner.invoke(app, ["lint", str(dataset), "--format", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["passed"] is True
    assert payload["checks_run"]


def test_cli_report_writes_json(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    output = tmp_path / "report.json"
    runner = CliRunner()

    result = runner.invoke(app, ["report", str(dataset), "--out", str(output)])

    assert result.exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["datasetlint_version"] == "0.0.2"
    assert payload["findings"] == payload["issues"]
    assert payload["adapter"]["name"] == "folder"


def test_cli_report_preserves_user_supplied_dataset_path(tmp_path):
    output = tmp_path / "report.json"
    runner = CliRunner()

    result = runner.invoke(app, ["report", "examples/minimal_dataset", "--out", str(output)])

    assert result.exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["dataset_path"] == "examples/minimal_dataset"


def test_cli_outputs_html_for_lint_command(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    runner = CliRunner()

    result = runner.invoke(app, ["lint", str(dataset), "--format", "html"])

    assert result.exit_code == 0
    assert "<!doctype html>" in result.stdout
    assert "<title>DatasetLint Report</title>" in result.stdout
    assert "Dataset Stats" in result.stdout


def test_cli_shorthand_outputs_html(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    runner = CliRunner()

    result = runner.invoke(app, [str(dataset), "--format", "html"])

    assert result.exit_code == 0
    assert "<!doctype html>" in result.stdout
    assert "DatasetLint Report" in result.stdout


def test_cli_report_writes_html(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    output = tmp_path / "report.html"
    runner = CliRunner()

    result = runner.invoke(app, ["report", str(dataset), "--out", str(output)])

    assert result.exit_code == 0
    html = output.read_text(encoding="utf-8")
    assert "<!doctype html>" in html
    assert "Dataset Summary" in html
    assert "Issue" in html
    assert str(dataset) in html


def test_cli_report_honors_fail_on_warning(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    output = tmp_path / "report.json"
    metadata = json.loads((dataset / "metadata.json").read_text(encoding="utf-8"))
    metadata.pop("version")
    (dataset / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["report", str(dataset), "--out", str(output), "--fail-on", "warning"],
    )

    assert result.exit_code == 1
    assert output.is_file()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert payload["stats"]["issue_count_by_severity"]["warning"] == 1


def test_release_checklist_cli_smoke_commands():
    runner = CliRunner()

    version_result = runner.invoke(app, ["--version"])
    help_result = runner.invoke(app, ["--help"])
    minimal_result = runner.invoke(app, ["examples/minimal_dataset"])
    bad_result = runner.invoke(app, ["examples/bad_dataset"])
    diff_result = runner.invoke(
        app,
        ["diff", "examples/minimal_dataset", "examples/bad_dataset", "--fail-on-regression"],
    )

    assert version_result.exit_code == 0
    assert version_result.stdout.strip() == "datasetlint 0.0.2"
    assert help_result.exit_code == 0
    assert "Usage:" in help_result.stdout
    assert minimal_result.exit_code == 0
    assert "passed with 0" in minimal_result.stdout
    assert "issue(s)" in minimal_result.stdout
    assert bad_result.exit_code == 1
    assert "failed" in bad_result.stdout
    assert diff_result.exit_code == 1
    assert "DatasetLint diff" in diff_result.stdout


def test_python_module_help_entrypoint():
    result = subprocess.run(
        [sys.executable, "-m", "datasetlint", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    output = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", result.stdout)
    assert "python -m datasetlint" in output
    assert "--help" in output


def test_cli_invalid_checks_returns_usage_error(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    runner = CliRunner()

    result = runner.invoke(app, [str(dataset), "--checks", "bad_group"])

    assert result.exit_code == 2
    assert "Error: Unknown check group 'bad_group'. Valid groups:" in result.stderr
    assert "Traceback" not in result.output


def test_cli_invalid_adapter_returns_usage_error(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    runner = CliRunner()

    result = runner.invoke(app, [str(dataset), "--adapter", "foobar"])

    assert result.exit_code == 2
    assert "Error: Unknown adapter 'foobar'. Valid adapters:" in result.stderr
    assert "Traceback" not in result.output


def test_cli_rejects_removed_config_key(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    (dataset / "datasetlint.yaml").write_text("max_timestamp_gap_sec: 1.0\n", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(app, [str(dataset)])

    assert result.exit_code == 2
    assert "max_timestamp_gap_sec" in result.stderr
    assert "Traceback" not in result.output


def test_cli_stats_rejects_removed_config_key(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    (dataset / "datasetlint.yaml").write_text("max_timestamp_gap_sec: 1.0\n", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(app, ["stats", str(dataset)])

    assert result.exit_code == 2
    assert "max_timestamp_gap_sec" in result.stderr
    assert "Traceback" not in result.output


def test_cli_diff_rejects_removed_config_key(tmp_path):
    old_dataset = write_good_dataset(tmp_path / "old")
    new_dataset = write_good_dataset(tmp_path / "new")
    (new_dataset / "datasetlint.yaml").write_text("max_timestamp_gap_sec: 1.0\n", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(app, ["diff", str(old_dataset), str(new_dataset)])

    assert result.exit_code == 2
    assert "max_timestamp_gap_sec" in result.stderr
    assert "Traceback" not in result.output
