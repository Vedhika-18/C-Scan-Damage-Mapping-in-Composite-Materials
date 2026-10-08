import csv
import math
import re
from pathlib import Path
from typing import Any

import numpy as np


_X_NAMES = ("x", "x_coordinate", "x coord", "width", "column")
_Y_NAMES = ("y", "y_coordinate", "y coord", "length", "row")
_SIGNAL_NAMES = ("amplitude", "signal", "intensity", "value", "depth", "response")


def _pick_column(headers: list[str], candidates: tuple[str, ...]) -> str | None:
    normalized = {header.strip().lower(): header for header in headers}
    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]
    for header in headers:
        if any(candidate in header.strip().lower() for candidate in candidates):
            return header
    return None


def _numbers(rows: list[dict[str, str]], column: str) -> np.ndarray:
    values = []
    for row in rows:
        try:
            value = float(row[column])
            if math.isfinite(value):
                values.append(value)
        except (KeyError, TypeError, ValueError):
            continue
    return np.asarray(values, dtype=float)


def process_csv(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if path.suffix.lower() != ".csv":
        raise ValueError("Inspection data must be a CSV file.")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        rows = list(reader)
    if not headers or not rows:
        raise ValueError("The CSV must contain a header row and at least one data row.")
    matrix_data = _process_matrix_csv(headers, rows)
    if matrix_data is not None:
        return matrix_data

    numeric_columns = [header for header in headers if _numbers(rows, header).size]
    if not numeric_columns:
        raise ValueError("The CSV does not contain any finite numeric columns.")
    x_column = _pick_column(headers, _X_NAMES)
    y_column = _pick_column(headers, _Y_NAMES)
    signal_column = _pick_column(headers, _SIGNAL_NAMES)
    if signal_column is None:
        signal_column = max(numeric_columns, key=lambda column: _numbers(rows, column).size)
    if x_column is None or y_column is None:
        x_column, y_column = _fallback_coordinates(rows, numeric_columns, signal_column)

    points = []
    for row in rows:
        try:
            x, y, signal = float(row[x_column]), float(row[y_column]), float(row[signal_column])
            if all(math.isfinite(value) for value in (x, y, signal)):
                points.append((x, y, signal))
        except (KeyError, TypeError, ValueError):
            continue
    if len(points) < 3:
        raise ValueError("At least three valid rows with coordinates and a signal are required.")
    array = np.asarray(points, dtype=float)
    return {
        "points": array,
        "row_count": len(rows),
        "valid_row_count": len(points),
        "columns": headers,
        "numeric_columns": numeric_columns,
        "x_column": x_column,
        "y_column": y_column,
        "signal_column": signal_column,
    }


def _fallback_coordinates(
    rows: list[dict[str, str]], numeric_columns: list[str], signal_column: str
) -> tuple[str, str]:
    candidates = [column for column in numeric_columns if column != signal_column]
    if len(candidates) < 2:
        raise ValueError("CSV needs X/Y columns, or at least two numeric coordinate columns.")
    return candidates[0], candidates[1]


def _millimeters(value: str) -> float | None:
    match = re.fullmatch(r"\s*(-?(?:\d+(?:\.\d*)?|\.\d+))\s*mm\s*", value, re.IGNORECASE)
    return float(match.group(1)) if match else None


def _process_matrix_csv(
    headers: list[str], rows: list[dict[str, str]]
) -> dict[str, Any] | None:
    """Convert exports with a blank corner cell and mm-labelled grid axes."""
    if headers[0].strip() or len(headers) < 3:
        return None
    x_values = [_millimeters(header) for header in headers[1:]]
    y_values = [_millimeters(row.get(headers[0], "")) for row in rows]
    if any(value is None for value in x_values + y_values):
        return None
    points = []
    for row, y in zip(rows, y_values):
        assert y is not None
        for header, x in zip(headers[1:], x_values):
            assert x is not None
            try:
                signal = float(row[header])
            except (KeyError, TypeError, ValueError):
                continue
            if math.isfinite(signal):
                points.append((x, y, signal))
    if len(points) < 3:
        raise ValueError("The CSV matrix does not contain three valid measurements.")
    return {
        "points": np.asarray(points, dtype=float),
        "row_count": len(rows),
        "valid_row_count": len(points),
        "columns": headers,
        "numeric_columns": headers[1:],
        "x_column": "measurement column labels",
        "y_column": "measurement row labels",
        "signal_column": "matrix values",
    }
