from __future__ import annotations

import json
from pathlib import Path


def write_good_dataset(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "sensors").mkdir()
    (path / "labels").mkdir()
    (path / "trajectories").mkdir()
    (path / "images").mkdir()
    for name in ("000001.jpg", "000002.jpg", "000003.jpg"):
        (path / "images" / name).write_text("placeholder", encoding="utf-8")
    _write_json(
        path / "metadata.json",
        {
            "dataset_name": "sample_log",
            "version": "0.1",
            "sensors": ["camera_front", "imu", "gps"],
            "duration_sec": 0.2,
        },
    )
    _write_json(
        path / "calibration.json",
        {
            "camera_front": {
                "intrinsics": [[1000, 0, 640], [0, 1000, 360], [0, 0, 1]],
                "extrinsics": {
                    "translation": [0.5, 0.0, 1.2],
                    "rotation_quat": [1, 0, 0, 0],
                },
            },
            "imu": {
                "extrinsics": {
                    "translation": [0.0, 0.0, 0.0],
                    "rotation_quat": [1, 0, 0, 0],
                }
            },
            "gps": {
                "extrinsics": {
                    "translation": [0.0, 0.0, 1.5],
                    "rotation_quat": [1, 0, 0, 0],
                }
            },
        },
    )
    (path / "sensors" / "camera_front.csv").write_text(
        "\n".join(
            [
                "timestamp,path,width,height",
                "0.0,images/000001.jpg,1280,720",
                "0.1,images/000002.jpg,1280,720",
                "0.2,images/000003.jpg,1280,720",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (path / "sensors" / "imu.csv").write_text(
        "\n".join(
            [
                "timestamp,ax,ay,az,gx,gy,gz",
                "0.0,0.0,0.0,9.8,0.0,0.0,0.0",
                "0.01,0.0,0.0,9.8,0.0,0.0,0.0",
                "0.02,0.0,0.0,9.8,0.0,0.0,0.0",
                "0.03,0.0,0.0,9.8,0.0,0.0,0.0",
                "0.04,0.0,0.0,9.8,0.0,0.0,0.0",
                "0.05,0.0,0.0,9.8,0.0,0.0,0.0",
                "0.06,0.0,0.0,9.8,0.0,0.0,0.0",
                "0.07,0.0,0.0,9.8,0.0,0.0,0.0",
                "0.08,0.0,0.0,9.8,0.0,0.0,0.0",
                "0.09,0.0,0.0,9.8,0.0,0.0,0.0",
                "0.10,0.0,0.0,9.8,0.0,0.0,0.0",
                "0.11,0.0,0.0,9.8,0.0,0.0,0.0",
                "0.12,0.0,0.0,9.8,0.0,0.0,0.0",
                "0.13,0.0,0.0,9.8,0.0,0.0,0.0",
                "0.14,0.0,0.0,9.8,0.0,0.0,0.0",
                "0.15,0.0,0.0,9.8,0.0,0.0,0.0",
                "0.16,0.0,0.0,9.8,0.0,0.0,0.0",
                "0.17,0.0,0.0,9.8,0.0,0.0,0.0",
                "0.18,0.0,0.0,9.8,0.0,0.0,0.0",
                "0.19,0.0,0.0,9.8,0.0,0.0,0.0",
                "0.20,0.0,0.0,9.8,0.0,0.0,0.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (path / "sensors" / "gps.csv").write_text(
        "\n".join(
            [
                "timestamp,lat,lon,alt",
                "0.0,37.0,-122.0,10.0",
                "0.1,37.00001,-122.00001,10.1",
                "0.2,37.00002,-122.00002,10.2",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (path / "labels" / "detections.csv").write_text(
        "\n".join(
            [
                "timestamp,track_id,class,x,y,width,height,confidence",
                "0.0,track-1,car,10,20,50,40,0.95",
                "0.1,track-1,car,12,20,50,40,0.96",
                "0.2,track-1,car,14,20,50,40,0.94",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (path / "trajectories" / "ego.csv").write_text(
        "\n".join(
            [
                "timestamp,x,y,yaw,vx,vy",
                "0.0,0.0,0.0,0.0,10.0,0.0",
                "0.1,1.0,0.0,0.0,10.0,0.0",
                "0.2,2.0,0.0,0.0,10.0,0.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _write_json(path: Path, value: dict[str, object]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
