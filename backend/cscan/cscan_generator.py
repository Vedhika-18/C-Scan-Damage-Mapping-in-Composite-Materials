from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def generate_cscan(
    points: np.ndarray,
    output_path: str | Path,
    material: str,
    thickness: float,
    grid_size: int = 160,
    coverage_output_path: str | Path | None = None,
) -> dict[str, float | list[int]]:
    if points.shape[0] < 3:
        raise ValueError("At least three inspection points are required.")
    x, y, signal = points.T
    x_edges = np.linspace(x.min(), x.max(), grid_size + 1)
    y_edges = np.linspace(y.min(), y.max(), grid_size + 1)
    weighted, _, _ = np.histogram2d(y, x, bins=(y_edges, x_edges), weights=signal)
    counts, _, _ = np.histogram2d(y, x, bins=(y_edges, x_edges))
    matrix = np.divide(weighted, counts, out=np.full_like(weighted, np.nan), where=counts > 0)
    if np.isnan(matrix).all():
        raise ValueError("Inspection points do not cover a usable scan area.")
    # Nearest-neighbour fill keeps the image data-driven without inventing smooth features.
    finite = np.argwhere(np.isfinite(matrix))
    for row, column in np.argwhere(~np.isfinite(matrix)):
        nearest = finite[np.argmin((finite[:, 0] - row) ** 2 + (finite[:, 1] - column) ** 2)]
        matrix[row, column] = matrix[nearest[0], nearest[1]]
    coverage = counts / max(float(counts.max()), 1.0)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(8, 5.5), constrained_layout=True)
    image = axis.imshow(
        matrix,
        origin="lower",
        extent=(float(x.min()), float(x.max()), float(y.min()), float(y.max())),
        aspect="auto",
        cmap="viridis",
    )
    axis.set(title=f"Generated C-Scan | {material} | {thickness:g} mm", xlabel="X", ylabel="Y")
    figure.colorbar(image, ax=axis, label="Inspection signal")
    figure.savefig(output_path, dpi=150)
    plt.close(figure)
    if coverage_output_path:
        coverage_figure, coverage_axis = plt.subplots(figsize=(8, 5.5), constrained_layout=True)
        coverage_image = coverage_axis.imshow(
            coverage, origin="lower",
            extent=(float(x.min()), float(x.max()), float(y.min()), float(y.max())),
            aspect="auto", cmap="magma", vmin=0, vmax=1,
        )
        coverage_axis.set(title="Measurement coverage", xlabel="X", ylabel="Y")
        coverage_figure.colorbar(coverage_image, ax=coverage_axis, label="Relative coverage")
        coverage_figure.savefig(coverage_output_path, dpi=150)
        plt.close(coverage_figure)
    return {
        "grid_shape": [int(matrix.shape[0]), int(matrix.shape[1])],
        "signal_min": float(signal.min()),
        "signal_max": float(signal.max()),
        "bounds": {
            "x_min": float(x.min()), "x_max": float(x.max()),
            "y_min": float(y.min()), "y_max": float(y.max()),
        },
        "coverage_mean": round(float(coverage.mean()), 4),
        "coverage_max": round(float(coverage.max()), 4),
        "coverage_ratio": round(float(np.count_nonzero(counts) / counts.size), 4),
    }
