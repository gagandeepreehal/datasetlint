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


def test_cli_stats_json(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    runner = CliRunner()

    result = runner.invoke(app, ["stats", str(dataset), "--format", "json"])

    assert result.exit_code == 0
    assert '"frame_counts"' in result.stdout


def test_cli_lint_alias_outputs_html(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    runner = CliRunner()

    result = runner.invoke(app, ["lint", str(dataset), "--format", "html"])

    assert result.exit_code == 0
    assert "<!doctype html>" in result.stdout
    assert "DatasetLint Report" in result.stdout
    assert "Validation mode" in result.stdout


def test_cli_report_writes_html_file(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    output = tmp_path / "report.html"
    runner = CliRunner()

    result = runner.invoke(app, ["report", str(dataset), "--out", str(output)])

    assert result.exit_code == 0
    assert result.stdout == ""
    html = output.read_text(encoding="utf-8")
    assert "<!doctype html>" in html
    assert str(dataset) in html


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
    assert result.stdout.strip() == "datasetlint 0.1.0"


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
