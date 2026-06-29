"""Dataset adapter interfaces."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, Field

ValidationMode = Literal["deep", "manifest-level", "index-level"]


class AdapterCoverage(BaseModel):
    """What an adapter validates without overstating parser coverage."""

    validation_mode: ValidationMode
    checked: list[str] = Field(default_factory=list)
    not_checked: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class DatasetMetadata(BaseModel):
    """Normalized metadata returned by adapters."""

    dataset_path: str
    name: str | None = None
    version: str | None = None
    sensors: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class SensorInfo(BaseModel):
    """Basic sensor stream information."""

    name: str
    path: str | None = None
    frame_count: int | None = None
    start_time: float | None = None
    end_time: float | None = None
    inferred_frequency_hz: float | None = None


class AdapterDetection(BaseModel):
    """Adapter detection result for CLI reporting."""

    name: str
    can_load: bool
    message: str
    validation_mode: ValidationMode
    checked: list[str] = Field(default_factory=list)
    not_checked: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class DatasetAdapter:
    """Base class for dataset adapters."""

    name = "base"

    def coverage(self) -> AdapterCoverage:
        """Return validation coverage for reports and adapter discovery."""

        return AdapterCoverage(
            validation_mode="index-level",
            checked=["adapter detection"],
            not_checked=[
                "metadata schema",
                "file references",
                "timestamps",
                "sensor synchronization",
                "calibration",
                "labels",
                "trajectories",
            ],
            limitations=["This adapter does not implement deep DatasetLint validation."],
        )

    def can_load(self, path: str | Path) -> bool:
        raise NotImplementedError

    def load_metadata(self, path: str | Path) -> DatasetMetadata:
        raise NotImplementedError

    def list_sensors(self, path: str | Path) -> list[SensorInfo]:
        raise NotImplementedError

    def load_timestamps(self, path: str | Path, sensor_name: str) -> pd.Series:
        raise NotImplementedError

    def load_labels(self, path: str | Path) -> pd.DataFrame | None:
        raise NotImplementedError

    def load_trajectory(self, path: str | Path) -> pd.DataFrame | None:
        raise NotImplementedError

    def load_calibration(self, path: str | Path) -> dict[str, Any] | None:
        raise NotImplementedError
