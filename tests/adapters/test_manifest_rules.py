from __future__ import annotations

from datasetlint.adapters.base import (
    AdapterProvenance,
    CalibrationRecord,
    DatasetManifest,
    FrameRecord,
    SensorStream,
    SequenceRecord,
)
from datasetlint.adapters.manifest_rules import run_manifest_rules


def test_manifest_rules_validate_common_semantic_inputs(tmp_path):
    manifest = DatasetManifest(
        dataset_name="example",
        adapter_name="waymo",
        dataset_root=str(tmp_path),
        sequences=[SequenceRecord(sequence_id="sequence")],
        frames=[
            FrameRecord(
                frame_id="frame-1",
                sequence_id="sequence",
                timestamp=2.0,
                sensor_id="camera",
                file_path="missing.jpg",
            ),
            FrameRecord(
                frame_id="frame-2",
                sequence_id="sequence",
                timestamp=2.0,
                sensor_id="camera",
            ),
            FrameRecord(
                frame_id="frame-1",
                sequence_id="sequence",
                timestamp=1.0,
                sensor_id="camera",
            ),
        ],
        sensors=[SensorStream(sensor_id="camera", sensor_type="camera", frame_count=3)],
        calibration=[CalibrationRecord(sensor_id="camera", intrinsic=[[1.0, 0.0]])],
        splits={"train": ["missing-frame"]},
        provenance=AdapterProvenance(
            source_format="test",
            adapter_version="0.1",
            loaded_at="2026-01-01T00:00:00+00:00",
            root_hash=None,
            files_indexed=0,
        ),
    )

    result = run_manifest_rules(manifest, tmp_path)

    assert "common manifest input summary" in result.checked
    assert "common timestamp consistency" in result.checked
    assert result.coverage["frames"] is True
    assert result.coverage["sensors"] is True
    assert result.stats["frame_count"] == 3
    assert any("Duplicate frame id" in error for error in result.errors)
    assert any("Frame file does not exist" in error for error in result.errors)
    assert any("non-monotonic timestamps" in error for error in result.errors)
    assert any("numeric 3x3 matrix" in error for error in result.errors)
    assert any("Split train references missing frame ids" in error for error in result.errors)
    assert any("duplicate timestamp" in warning for warning in result.warnings)


def test_waymo_index_placeholders_are_not_common_semantic_inputs(tmp_path):
    manifest = DatasetManifest(
        dataset_name="waymo",
        adapter_name="waymo",
        dataset_root=str(tmp_path),
        frames=[
            FrameRecord(
                frame_id="segment-1",
                sequence_id="segment-1",
                file_path="segment-1.tfrecord",
                metadata={"indexed_tfrecord": True},
            )
        ],
        sensors=[SensorStream(sensor_id="unknown", sensor_type="unknown", frame_count=1)],
        metadata={"parse_mode": "index"},
        provenance=AdapterProvenance(
            source_format="waymo",
            adapter_version="0.1",
            loaded_at="2026-01-01T00:00:00+00:00",
            root_hash=None,
            files_indexed=1,
        ),
    )

    result = run_manifest_rules(manifest, tmp_path)

    assert result.coverage["frames"] is False
    assert result.coverage["sensors"] is False
    assert result.stats["frame_count"] == 0
    assert result.stats["sensor_count"] == 0
