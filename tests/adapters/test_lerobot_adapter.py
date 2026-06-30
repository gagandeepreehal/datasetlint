from __future__ import annotations

from pathlib import Path

from datasetlint.adapters.lerobot import LeRobotAdapter

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_lerobot_adapter_indexes_local_dataset():
    manifest = LeRobotAdapter().load(FIXTURES / "lerobot_local")

    assert manifest.adapter_name == "lerobot"
    assert manifest.dataset_name == "local/robot_pick_place"
    assert {sensor.sensor_id for sensor in manifest.sensors} == {
        "episode_data",
        "observation.images.front",
    }
    assert manifest.annotations[0].annotation_type == "lerobot_task"
    assert manifest.splits == {
        "train": ["000000/data", "000000/observation.images.front"]
    }


def test_lerobot_validation_reports_episode_payloads():
    report = LeRobotAdapter().validate(FIXTURES / "lerobot_local")

    assert report.valid is True
    assert report.coverage["frames"] is True
    assert report.stats["sequence_count"] == 1
