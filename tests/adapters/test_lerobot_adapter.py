from __future__ import annotations

import json
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
    assert manifest.splits == {"train": ["000000/data", "000000/observation.images.front"]}


def test_lerobot_validation_reports_episode_payloads():
    report = LeRobotAdapter().validate(FIXTURES / "lerobot_local")

    assert report.valid is True
    assert report.coverage["frames"] is True
    assert report.stats["sequence_count"] == 1


def test_lerobot_adapter_parses_range_style_splits(tmp_path: Path):
    dataset_root = tmp_path / "lerobot"
    meta_dir = dataset_root / "meta"
    data_dir = dataset_root / "data" / "chunk-000"
    video_dir = dataset_root / "videos" / "chunk-000" / "observation.images.front"
    meta_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)
    video_dir.mkdir(parents=True)
    (data_dir / "episode_000000.parquet").touch()
    (video_dir / "episode_000000.mp4").touch()
    (meta_dir / "info.json").write_text(
        json.dumps(
            {
                "repo_id": "local/range_splits",
                "splits": {
                    "train": "0:1",
                    "eval": "000000",
                },
            }
        ),
        encoding="utf-8",
    )

    manifest = LeRobotAdapter().load(dataset_root)

    assert manifest.splits == {
        "train": ["000000/data", "000000/observation.images.front"],
        "eval": ["000000/data", "000000/observation.images.front"],
    }
