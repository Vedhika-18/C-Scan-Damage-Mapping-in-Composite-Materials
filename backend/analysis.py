from typing import Any

import numpy as np


def assess_data_quality(csv_data: dict[str, Any], ply_data: dict[str, Any] | None) -> dict[str, Any]:
    points = csv_data["points"]
    valid_ratio = min(csv_data["valid_row_count"] / max(csv_data["row_count"], 1), 1.0)
    coordinate_pairs = len(np.unique(points[:, :2], axis=0))
    uniqueness = coordinate_pairs / max(len(points), 1)
    score = round(100 * (0.55 * valid_ratio + 0.3 * min(uniqueness, 1) + 0.15 * bool(ply_data)))
    checks = [
        {"name": "Valid measurements", "passed": valid_ratio >= 0.9},
        {"name": "Unique spatial coordinates", "passed": uniqueness >= 0.95},
        {"name": "PLY geometry available", "passed": bool(ply_data)},
    ]
    return {"score": score, "valid_ratio": round(valid_ratio, 4), "checks": checks}


def find_potential_indications(points: np.ndarray, limit: int = 12) -> list[dict[str, Any]]:
    """Find high-response spatial clusters; results are not validated damage."""
    signals = points[:, 2]
    threshold = float(np.percentile(signals, 95))
    candidates = points[signals >= threshold]
    if candidates.size == 0:
        return []
    x_step = _spacing(points[:, 0])
    y_step = _spacing(points[:, 1])
    cell_size = max(x_step, y_step, 1e-9)
    cell_keys = np.floor(candidates[:, :2] / cell_size).astype(int)
    groups: dict[tuple[int, int], list[int]] = {}
    for index, key in enumerate(map(tuple, cell_keys)):
        groups.setdefault(key, []).append(index)
    regions = []
    for indices in groups.values():
        region_points = candidates[indices]
        signal = region_points[:, 2]
        width = max(float(np.ptp(region_points[:, 0])), x_step)
        height = max(float(np.ptp(region_points[:, 1])), y_step)
        regions.append(
            {
                "x": round(float(region_points[:, 0].mean()), 3),
                "y": round(float(region_points[:, 1].mean()), 3),
                "area": round(width * height, 3),
                "length": round(max(width, height), 3),
                "width": round(min(width, height), 3),
                "signal": round(float(signal.mean()), 5),
                "severity": _severity(float(signal.mean()), float(signals.min()), float(signals.max())),
            }
        )
    return sorted(regions, key=lambda region: region["area"], reverse=True)[:limit]


def _spacing(values: np.ndarray) -> float:
    unique = np.unique(values)
    differences = np.diff(unique)
    positive = differences[differences > 0]
    return float(np.median(positive)) if positive.size else 1.0


def _severity(value: float, minimum: float, maximum: float) -> str:
    relative = (value - minimum) / max(maximum - minimum, 1e-12)
    return "High" if relative >= 0.8 else "Medium" if relative >= 0.6 else "Low"
