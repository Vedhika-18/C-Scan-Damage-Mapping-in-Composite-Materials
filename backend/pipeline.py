from pathlib import Path
from typing import Any

from .cscan.cscan_generator import generate_cscan
from .preprocessing.csv_processor import process_csv
from .preprocessing.image_processor import process_image
from .preprocessing.ply_processor import process_ply


def generate_inspection(
    csv_path: str | Path,
    output_path: str | Path,
    ply_path: str | Path | None = None,
    surface_image_path: str | Path | None = None,
    material: str = "",
    thickness: float = 0,
) -> dict[str, Any]:
    csv_data = process_csv(csv_path)
    ply_data = process_ply(ply_path) if ply_path else None
    image_data = process_image(surface_image_path) if surface_image_path else None
    cscan_data = generate_cscan(csv_data["points"], output_path, material, thickness)
    return {
        "csv": {
            "rows": csv_data["row_count"],
            "valid_rows": csv_data["valid_row_count"],
            "x_column": csv_data["x_column"],
            "y_column": csv_data["y_column"],
            "signal_column": csv_data["signal_column"],
        },
        "ply": {"point_count": ply_data["point_count"], "bounds": ply_data["bounds"]}
        if ply_data
        else None,
        "surface_image": image_data,
        "cscan": cscan_data,
    }
