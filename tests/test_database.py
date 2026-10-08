import backend.database as database


def test_inspection_metadata_round_trip(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.sqlite3")
    database.initialize_database()
    database.create_inspection(
        {
            "id": "inspection-1",
            "material": "CFRP",
            "thickness_mm": 3.0,
            "csv_filename": "plate.csv",
            "ply_filename": None,
            "surface_filename": None,
            "cscan_key": "inspections/inspection-1/cscan.png",
            "status": "success",
            "details": {"valid_rows": 4},
        }
    )
    result = database.get_inspection("inspection-1")
    assert result is not None
    assert result["material"] == "CFRP"
    assert result["details"] == {"valid_rows": 4}
