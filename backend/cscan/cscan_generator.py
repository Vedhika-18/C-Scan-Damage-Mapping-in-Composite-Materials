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
    return {
        "grid_shape": [int(matrix.shape[0]), int(matrix.shape[1])],
        "signal_min": float(signal.min()),
        "signal_max": float(signal.max()),
    }
