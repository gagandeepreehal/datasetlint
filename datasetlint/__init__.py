"""DatasetLint public API."""

from datasetlint._version import __version__
from datasetlint.core import lint_dataset
from datasetlint.diff import DatasetDiffReport, compare_datasets
from datasetlint.report import LintReport
from datasetlint.schemas import Issue, LintConfig
from datasetlint.stats import DatasetStats, compute_dataset_stats

__all__ = [
    "DatasetDiffReport",
    "DatasetStats",
    "Issue",
    "LintConfig",
    "LintReport",
    "__version__",
    "compare_datasets",
    "compute_dataset_stats",
    "lint_dataset",
]
