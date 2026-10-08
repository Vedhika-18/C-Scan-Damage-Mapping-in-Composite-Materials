import os
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(ROOT / "data" / "cscan.sqlite3")))
DATABASE_URL = os.getenv("DATABASE_URL")


def _connect() -> sqlite3.Connection:
    if DATABASE_URL:
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("Install psycopg[binary] to use PostgreSQL.") from exc
        return psycopg.connect(DATABASE_URL, row_factory=psycopg.rows.dict_row)
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _execute(connection: Any, query: str, parameters: tuple[Any, ...] = ()) -> Any:
    if DATABASE_URL:
        return connection.execute(query.replace("?", "%s"), parameters)
    return connection.execute(query, parameters)


def initialize_database() -> None:
    with _connect() as connection:
        _execute(
            connection,
            """
            CREATE TABLE IF NOT EXISTS inspections (
                id TEXT PRIMARY KEY,
                material TEXT NOT NULL,
                thickness_mm REAL NOT NULL,
                csv_filename TEXT NOT NULL,
                ply_filename TEXT,
                surface_filename TEXT,
                cscan_key TEXT NOT NULL,
                status TEXT NOT NULL,
                details_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        if not DATABASE_URL:
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(inspections)").fetchall()
            }
            if "cscan_key" not in columns and "cscan_path" in columns:
                connection.execute("ALTER TABLE inspections RENAME TO inspections_legacy")
                connection.execute(
                    """
                    CREATE TABLE inspections (
                        id TEXT PRIMARY KEY,
                        material TEXT NOT NULL,
                        thickness_mm REAL NOT NULL,
                        csv_filename TEXT NOT NULL,
                        ply_filename TEXT,
                        surface_filename TEXT,
                        cscan_key TEXT NOT NULL,
                        status TEXT NOT NULL,
                        details_json TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT INTO inspections (
                        id, material, thickness_mm, csv_filename, ply_filename,
                        surface_filename, cscan_key, status, details_json, created_at
                    )
                    SELECT id, material, thickness_mm, csv_filename, ply_filename,
                        surface_filename, cscan_path, status, details_json, created_at
                    FROM inspections_legacy
                    """
                )
                connection.execute("DROP TABLE inspections_legacy")


def create_inspection(record: dict[str, Any]) -> None:
    import json

    with _connect() as connection:
        _execute(
            connection,
            """
            INSERT INTO inspections (
                id, material, thickness_mm, csv_filename, ply_filename,
                surface_filename,                 cscan_key, status, details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record["material"],
                record["thickness_mm"],
                record["csv_filename"],
                record.get("ply_filename"),
                record.get("surface_filename"),
                record["cscan_key"],
                record["status"],
                json.dumps(record["details"]),
            ),
        )


def get_inspection(inspection_id: str) -> dict[str, Any] | None:
    import json

    with _connect() as connection:
        row = _execute(
            connection,
            "SELECT * FROM inspections WHERE id = ?", (inspection_id,)
        ).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["details"] = json.loads(result.pop("details_json"))
    return result


def list_inspections(limit: int = 50) -> list[dict[str, Any]]:
    import json

    limit = max(1, min(limit, 200))
    with _connect() as connection:
        rows = _execute(
            connection,
            "SELECT * FROM inspections ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    inspections = []
    for row in rows:
        result = dict(row)
        details = json.loads(result.pop("details_json"))
        result["data_quality"] = details.get("data_quality", {}).get("score")
        result["potential_indications"] = len(details.get("potential_indications", []))
        inspections.append(result)
    return inspections
