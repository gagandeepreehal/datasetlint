"""Calibration checks."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

import numpy as np

from datasetlint.schemas import DatasetContext, Issue, make_issue


def check_calibration_exists(ctx: DatasetContext) -> list[Issue]:
    if ctx.calibration is None:
        return []
    if not isinstance(ctx.calibration, dict):
        return [
            make_issue(
                "check_calibration_exists",
                "error",
                "calibration.json must contain a JSON object.",
                file="calibration.json",
            )
        ]
    issues: list[Issue] = []
    for sensor in ctx.declared_sensors():
        if sensor not in ctx.calibration:
            issues.append(
                make_issue(
                    "check_calibration_exists",
                    "error",
                    f"Missing calibration entry for sensor '{sensor}'.",
                    file="calibration.json",
                    metadata={"sensor": sensor},
                )
            )
    return issues


def check_intrinsics_shape(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    for sensor, calibration in _calibration_items(ctx):
        intrinsics = calibration.get("intrinsics")
        if intrinsics is None and "camera" not in sensor:
            continue
        if not _is_matrix(intrinsics, 3, 3):
            issues.append(
                make_issue(
                    "check_intrinsics_shape",
                    "error",
                    f"Calibration intrinsics for '{sensor}' must be a 3x3 matrix.",
                    file="calibration.json",
                    metadata={"sensor": sensor},
                )
            )
    return issues


def check_intrinsics_values(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    for sensor, calibration in _calibration_items(ctx):
        intrinsics = calibration.get("intrinsics")
        if intrinsics is None:
            continue
        if not _is_matrix(intrinsics, 3, 3):
            continue
        matrix = np.asarray(intrinsics, dtype=float)
        if not np.isfinite(matrix).all() or matrix[0, 0] <= 0 or matrix[1, 1] <= 0:
            issues.append(
                make_issue(
                    "check_intrinsics_values",
                    "error",
                    f"Calibration intrinsics for '{sensor}' must contain positive focal lengths.",
                    file="calibration.json",
                    metadata={"sensor": sensor},
                )
            )
    return issues


def check_extrinsics_shape(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    for sensor, calibration in _calibration_items(ctx):
        extrinsics = calibration.get("extrinsics")
        if not isinstance(extrinsics, dict):
            issues.append(
                make_issue(
                    "check_extrinsics_shape",
                    "error",
                    f"Calibration extrinsics for '{sensor}' must be an object.",
                    file="calibration.json",
                    metadata={"sensor": sensor},
                )
            )
            continue
        translation = extrinsics.get("translation")
        rotation = extrinsics.get("rotation_quat")
        if not _is_vector(translation, 3) or not _is_vector(rotation, 4):
            issues.append(
                make_issue(
                    "check_extrinsics_shape",
                    "error",
                    f"Calibration extrinsics for '{sensor}' must include "
                    "translation[3] and rotation_quat[4].",
                    file="calibration.json",
                    metadata={"sensor": sensor},
                )
            )
    return issues


def check_quaternion_norm(ctx: DatasetContext) -> list[Issue]:
    issues: list[Issue] = []
    for sensor, calibration in _calibration_items(ctx):
        extrinsics = calibration.get("extrinsics")
        if not isinstance(extrinsics, dict):
            continue
        rotation = extrinsics.get("rotation_quat")
        if not _is_vector(rotation, 4):
            continue
        norm = float(np.linalg.norm(np.asarray(rotation, dtype=float)))
        if not math.isclose(norm, 1.0, rel_tol=0.01, abs_tol=0.01):
            issues.append(
                make_issue(
                    "check_quaternion_norm",
                    "error",
                    f"Quaternion for '{sensor}' is not normalized.",
                    file="calibration.json",
                    metadata={"sensor": sensor, "norm": norm},
                )
            )
    return issues


def _calibration_items(ctx: DatasetContext) -> list[tuple[str, dict[str, Any]]]:
    if not isinstance(ctx.calibration, dict):
        return []
    items: list[tuple[str, dict[str, Any]]] = []
    for sensor, value in ctx.calibration.items():
        if isinstance(sensor, str) and isinstance(value, dict):
            items.append((sensor, value))
    return items


def _is_matrix(value: Any, rows: int, columns: int) -> bool:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return False
    if len(value) != rows:
        return False
    return all(_is_vector(row, columns) for row in value)


def _is_vector(value: Any, length: int) -> bool:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return False
    if len(value) != length:
        return False
    return all(isinstance(item, (int, float)) and math.isfinite(float(item)) for item in value)
