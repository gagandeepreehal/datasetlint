"""Dataset adapter interfaces."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field


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


class DatasetAdapter:
    """Base class for dataset adapters."""

    name = "base"

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
