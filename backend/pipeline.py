from pathlib import Path
from typing import Any

from .analysis import assess_data_quality, find_potential_indications
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
    plate_id: str = "",
) -> dict[str, Any]:
    csv_data = process_csv(csv_path)
    ply_data = process_ply(ply_path) if ply_path else None
    image_data = process_image(surface_image_path) if surface_image_path else None
    coverage_path = Path(output_path).with_name("coverage.png")
    cscan_data = generate_cscan(
        csv_data["points"], output_path, material, thickness, coverage_output_path=coverage_path
    )
    quality = assess_data_quality(csv_data, ply_data)
    indications = find_potential_indications(csv_data["points"])
    return {
        "csv": {
            "rows": csv_data["row_count"],
            "valid_rows": csv_data["valid_row_count"],
            "x_column": csv_data["x_column"],
            "y_column": csv_data["y_column"],
            "signal_column": csv_data["signal_column"],
            "missing_values": csv_data["missing_values"],
            "duplicate_rows": csv_data["duplicate_rows"],
            "numeric_ranges": csv_data["numeric_ranges"],
            "depth_available": csv_data["depth_available"],
            "coordinate_bounds": csv_data["coordinate_bounds"],
        },
        "ply": {"point_count": ply_data["point_count"], "bounds": ply_data["bounds"]}
        if ply_data
        else None,
        "surface_image": image_data,
        "cscan": cscan_data,
        "data_quality": quality,
        "potential_indications": indications,
        "plate_id": plate_id or "Unspecified plate",
        "inspection_validation": {
            "csv_detected": True,
            "spatial_coordinates_detected": True,
            "measurement_data_detected": True,
            "ply_detected": bool(ply_data),
            "surface_image_detected": bool(image_data),
            "material_specified": bool(material.strip()),
            "thickness_specified": thickness > 0,
        },
        "visualization": {
            "inspection_points": csv_data["points"][:: max(1, len(csv_data["points"]) // 5000)].round(5).tolist(),
            "geometry_points": ply_data["sample_points"] if ply_data else [],
            "coverage_file": coverage_path.name,
        },
        "analysis_note": (
            "Regions are analytical potential damage indications based on high relative "
            "signal response; they are not validated defects."
        ),
        "capabilities": {
            "depth_analysis": bool(csv_data["depth_available"]),
            "reference_comparison": False,
            "surface_registration": False,
            "three_d_geometry": bool(ply_data),
            "a_scan": False,
            "b_scan": False,
            "ml_prediction": False,
            "reference_comparison": False,
            "previous_inspection_comparison": False,
        },
    }
