from __future__ import annotations

from datasetlint.stats import compute_dataset_stats
from tests.conftest import write_good_dataset


def test_stats_generation(tmp_path):
    dataset = write_good_dataset(tmp_path / "dataset")

    stats = compute_dataset_stats(dataset)

    assert stats.duration_sec == 0.2
    assert stats.frame_counts["camera_front"] == 3
    assert stats.frame_counts["imu"] == 21
    assert stats.inferred_rates_hz["imu"] == 100.0
    assert stats.label_class_counts == {"car": 3}
    assert stats.confidence_summary.count == 3
    assert stats.track_length_summary.median == 3

    markdown = stats.to_markdown()
    assert "| camera_front | 3 | 10.000 | 0 |" in markdown
    assert "| imu | 21 | 100.000 | 0 |" in markdown
