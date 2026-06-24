from __future__ import annotations

from pathlib import Path

from datasetlint import compare_datasets, compute_dataset_stats, lint_dataset

ROOT = Path(__file__).resolve().parents[1]
GOOD = ROOT / "examples" / "minimal_dataset"
BROKEN = ROOT / "examples" / "broken_dataset"


def main() -> None:
    report = lint_dataset(GOOD)
    print(report.summary())

    stats = compute_dataset_stats(GOOD)
    print(f"sensors={stats.sensors}")

    diff = compare_datasets(GOOD, BROKEN)
    print(f"regressions={len(diff.regressions)}")


if __name__ == "__main__":
    main()
