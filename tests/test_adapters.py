from __future__ import annotations

import pytest

from datasetlint import lint_dataset
from datasetlint.adapters import detect_adapters, get_adapter
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
    with pytest.raises(NotImplementedError, match="MCAP deep parsing"):
        adapter.load_timestamps(mcap_path, "camera_front")


def test_adapter_detection_includes_coverage_metadata(tmp_path):
    mcap_path = tmp_path / "log.mcap"
    mcap_path.write_text("placeholder", encoding="utf-8")

    detections = detect_adapters(mcap_path)
    mcap = next(detection for detection in detections if detection.name == "mcap")
    rosbag = next(detection for detection in detections if detection.name == "rosbag")

    assert mcap.can_load is True
    assert mcap.validation_mode == "index-level"
    assert "message timestamps" in mcap.not_checked
    assert mcap.limitations
    assert rosbag.can_load is False
    assert rosbag.checked == []
    assert rosbag.not_checked == []
    assert rosbag.limitations == []


def test_non_native_validation_report_includes_adapter_limitations(tmp_path):
    mcap_path = tmp_path / "log.mcap"
    mcap_path.write_text("placeholder", encoding="utf-8")

    report = lint_dataset(mcap_path, adapter="auto")

    assert report.passed is False
    assert report.stats["checks_run"] == []
    assert report.stats["adapter"]["name"] == "mcap"
    assert report.stats["adapter"]["validation_mode"] == "index-level"
    assert "message timestamps" in report.stats["adapter"]["not_checked"]
    assert report.stats["adapter"]["limitations"]


def test_named_detection_only_adapters_report_modes(tmp_path):
    kitti = tmp_path / "kitti"
    (kitti / "image_2").mkdir(parents=True)
    (kitti / "calib").mkdir()
    coco = tmp_path / "annotations.json"
    coco.write_text('{"images": [], "annotations": []}', encoding="utf-8")
    hf = tmp_path / "hf"
    hf.mkdir()
    (hf / "dataset_info.json").write_text("{}", encoding="utf-8")

    assert get_adapter(kitti, "auto").name == "kitti"
    assert get_adapter(coco, "auto").name == "coco"
    assert get_adapter(hf, "auto").name == "huggingface"
    assert get_adapter(coco, "auto").coverage().validation_mode == "manifest-level"
