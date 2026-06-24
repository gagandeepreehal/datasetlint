"""Adapter-specific exceptions."""

from __future__ import annotations


class AdapterError(ValueError):
    """Base class for adapter failures."""


class AdapterNotFoundError(AdapterError):
    """Raised when an adapter name is unknown."""


class AdapterDetectionError(AdapterError):
    """Raised when adapter auto-detection is missing or ambiguous."""


class AdapterDependencyError(AdapterError):
    """Raised when an optional dependency is required but unavailable."""


class AdapterValidationError(AdapterError):
    """Raised when an adapter finds invalid dataset content."""


class UnsupportedDatasetFeature(AdapterError):
    """Raised when a dataset feature cannot be represented or parsed yet."""
