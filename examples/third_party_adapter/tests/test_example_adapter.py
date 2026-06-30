from __future__ import annotations

import sys
from pathlib import Path


def test_example_adapter_loads_sample_dataset() -> None:
    root = Path(__file__).resolve().parents[1] / "sample_dataset"
    sys.path.insert(0, str(root.parent / "src"))
    from datasetlint_example_adapter import ExampleTelemetryAdapter

    manifest = ExampleTelemetryAdapter().load(root)

    assert manifest.adapter_name == "example_telemetry"
    assert len(manifest.frames) == 4
    assert {sensor.sensor_id for sensor in manifest.sensors} == {"camera", "lidar"}
