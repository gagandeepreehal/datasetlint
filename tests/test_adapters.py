from __future__ import annotations

import pytest

from datasetlint.adapters import AdapterDependencyError, get_adapter
from tests.conftest import write_good_dataset


def test_folder_adapter_loading(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")
    adapter = get_adapter(dataset, "folder")

    metadata = adapter.load_metadata(dataset)
    sensors = adapter.list_sensors(dataset)
    labels = adapter.load_labels(dataset)

    assert metadata.name == "sample_log"
    assert {sensor.name for sensor in sensors} == {"camera_front", "gps", "imu"}
    assert labels is not None
    assert len(labels) == 3


def test_adapter_auto_detection(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")

    adapter = get_adapter(dataset, "auto")

    assert adapter.name == "folder"


def test_partial_adapter_raises_clear_not_implemented(tmp_path):
    mcap_path = tmp_path / "log.mcap"
    mcap_path.write_text("placeholder", encoding="utf-8")
    adapter = get_adapter(mcap_path, "auto")

    assert adapter.name == "mcap"
    with pytest.raises(AdapterDependencyError, match="Deep MCAP parsing requires"):
        adapter.load_timestamps(mcap_path, "camera_front")
