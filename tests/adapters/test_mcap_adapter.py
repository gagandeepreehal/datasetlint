from __future__ import annotations

from pathlib import Path

from datasetlint.adapters.mcap import MCAPAdapter

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_mcap_adapter_indexes_files():
    manifest = MCAPAdapter().load(FIXTURES / "mcap_index_only")

    assert len(manifest.sequences) == 1
    assert manifest.metadata["files"][0]["path"] == "log.mcap"


def test_mcap_validation_warns_for_empty_file(tmp_path):
    (tmp_path / "empty.mcap").write_text("", encoding="utf-8")

    report = MCAPAdapter().validate(tmp_path)

    assert any("empty MCAP" in warning for warning in report.warnings)
