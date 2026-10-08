import csv
from pathlib import Path

from backend.pipeline import generate_inspection
from backend.preprocessing.csv_processor import process_csv


def test_csv_driven_cscan(tmp_path: Path) -> None:
    csv_path = tmp_path / "plate.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["X", "Y", "Amplitude"])
        writer.writerows([(0, 0, 1), (1, 0, 2), (0, 1, 3), (1, 1, 4)])
    output = tmp_path / "cscan.png"
    details = generate_inspection(csv_path, output, material="CFRP", thickness=3)
    assert output.is_file()
    assert details["csv"]["signal_column"] == "Amplitude"
    assert details["cscan"]["signal_min"] == 1
    assert 0 < details["cscan"]["coverage_ratio"] <= 1
    assert details["inspection_validation"]["spatial_coordinates_detected"]


def test_millimeter_matrix_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "matrix.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["", "0 mm", "1 mm"])
        writer.writerows([["0 mm", 1, 2], ["1 mm", 3, 4]])
    result = process_csv(csv_path)
    assert result["points"].shape == (4, 3)
    assert result["points"][0].tolist() == [0.0, 0.0, 1.0]
    assert result["signal_column"] == "matrix values"
