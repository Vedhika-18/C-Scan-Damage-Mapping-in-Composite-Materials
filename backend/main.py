import shutil
import uuid
import os
import csv
import io
import json
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from .database import create_inspection, get_inspection, initialize_database, list_inspections
from .pipeline import generate_inspection
from .reporting import build_report
from .storage import download_local, is_remote, public_url, upload_file

ROOT = Path(__file__).resolve().parent.parent
UPLOADS = Path(os.getenv("OUTPUT_DIR", str(ROOT / "outputs")))
UPLOADS.mkdir(exist_ok=True)
FRONTEND = ROOT / "frontend"

app = FastAPI(
    title="C-Scan Image Generation for Internal Damage Characterization of Composite Plates",
    version="0.1.0",
)
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
initialize_database()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/inspections")
def inspections(limit: int = 50) -> dict:
    return {"items": list_inspections(limit)}


def _save_upload(upload: UploadFile, destination: Path) -> None:
    with destination.open("wb") as handle:
        shutil.copyfileobj(upload.file, handle)


@app.post("/api/generate-cscan")
async def generate_cscan_endpoint(
    csv_file: UploadFile = File(...),
    ply_file: UploadFile | None = File(None),
    surface_image: UploadFile | None = File(None),
    material: str = Form(...),
    thickness: float = Form(...),
    plate_id: str = Form(""),
) -> dict:
    if thickness <= 0:
        raise HTTPException(status_code=422, detail="Thickness must be greater than zero.")
    if not material.strip():
        raise HTTPException(status_code=422, detail="Material is required.")
    result_id = uuid.uuid4().hex
    folder = UPLOADS / result_id
    folder.mkdir()
    csv_path = folder / (Path(csv_file.filename or "inspection.csv").name)
    _save_upload(csv_file, csv_path)
    ply_path = None
    image_path = None
    if ply_file and ply_file.filename:
        ply_path = folder / Path(ply_file.filename).name
        _save_upload(ply_file, ply_path)
    if surface_image and surface_image.filename:
        image_path = folder / Path(surface_image.filename).name
        _save_upload(surface_image, image_path)
    cscan_path = folder / "cscan.png"
    try:
        details = generate_inspection(
            csv_path, cscan_path, ply_path, image_path, material.strip(), thickness, plate_id.strip()
        )
        prefix = f"inspections/{result_id}"
        csv_key = upload_file(csv_path, f"{prefix}/{csv_path.name}", "text/csv")
        ply_key = upload_file(ply_path, f"{prefix}/{ply_path.name}", "application/octet-stream") if ply_path else None
        image_key = upload_file(image_path, f"{prefix}/{image_path.name}", "image/*") if image_path else None
        cscan_key = upload_file(cscan_path, f"{prefix}/cscan.png", "image/png")
        coverage_path = folder / "coverage.png"
        coverage_key = upload_file(coverage_path, f"{prefix}/coverage.png", "image/png")
        create_inspection(
            {
                "id": result_id,
                "material": material.strip(),
                "thickness_mm": thickness,
                "csv_filename": csv_path.name,
                "ply_filename": ply_path.name if ply_path else None,
                "surface_filename": image_path.name if image_path else None,
                "cscan_key": cscan_key,
                "coverage_key": coverage_key,
                "status": "success",
                "details": details,
            }
        )
        if is_remote():
            shutil.rmtree(folder, ignore_errors=True)
    except (ValueError, OSError) as exc:
        shutil.rmtree(folder, ignore_errors=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "status": "success",
        "result_id": result_id,
        "material": material.strip(),
        "thickness": thickness,
        "cscan_url": f"/api/results/{result_id}/cscan",
        "surface_image_url": f"/api/results/{result_id}/surface" if image_path else None,
        "details": details,
        "method": "Baseline C-scan visualization generated from uploaded inspection data",
        "plate_id": details["plate_id"],
    }


@app.get("/api/results/{result_id}/cscan")
def get_cscan(result_id: str) -> FileResponse:
    record = get_inspection(result_id)
    if record is None:
        raise HTTPException(status_code=404, detail="C-scan not found.")
    if is_remote():
        return RedirectResponse(public_url(record["cscan_key"]))
    path = download_local(record["cscan_key"])
    if path is None:
        raise HTTPException(status_code=404, detail="C-scan not found.")
    return FileResponse(path, media_type="image/png", filename="cscan.png")


@app.get("/api/results/{result_id}/coverage")
def get_coverage(result_id: str) -> FileResponse:
    record = get_inspection(result_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    key = record["details"]["visualization"]["coverage_file"]
    object_key = f"inspections/{result_id}/{key}"
    if is_remote():
        return RedirectResponse(public_url(object_key))
    path = download_local(object_key)
    if path is None:
        raise HTTPException(status_code=404, detail="Coverage map not found.")
    return FileResponse(path, media_type="image/png", filename="coverage.png")


@app.get("/api/results/{result_id}/surface")
def get_surface(result_id: str) -> FileResponse:
    record = get_inspection(result_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    if record["surface_filename"] is None:
        raise HTTPException(status_code=404, detail="Surface image not found.")
    key = f"inspections/{result_id}/{record['surface_filename']}"
    if is_remote():
        return RedirectResponse(public_url(key))
    path = download_local(key)
    if path is None:
        raise HTTPException(status_code=404, detail="Surface image not found.")
    return FileResponse(path)


@app.get("/api/results/{result_id}/metadata")
def get_metadata(result_id: str, inline: bool = Query(False)) -> Response:
    record = get_inspection(result_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    payload = {
        "inspection_id": record["id"],
        "created_at": record["created_at"],
        "material": record["material"],
        "thickness_mm": record["thickness_mm"],
        "csv_filename": record["csv_filename"],
        "ply_filename": record["ply_filename"],
        "surface_filename": record["surface_filename"],
        "status": record["status"],
        "details": record["details"],
    }
    disposition = "inline" if inline else "attachment"
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'{disposition}; filename="inspection-metadata.json"'},
    )


@app.get("/api/results/{result_id}/indications.csv")
def get_indications(result_id: str, inline: bool = Query(False)) -> Response:
    record = get_inspection(result_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    indications = record["details"].get("potential_indications", [])
    stream = io.StringIO()
    writer = csv.DictWriter(
        stream,
        fieldnames=["region", "x", "y", "area", "length", "width", "signal", "severity"],
    )
    writer.writeheader()
    for index, indication in enumerate(indications, start=1):
        writer.writerow({"region": f"R{index}", **indication})
    disposition = "inline" if inline else "attachment"
    return Response(
        content=stream.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'{disposition}; filename="potential-indications.csv"'},
    )


@app.get("/api/results/{result_id}/report.html")
def get_report(result_id: str, inline: bool = Query(False)) -> Response:
    record = get_inspection(result_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    disposition = "inline" if inline else "attachment"
    return Response(
        content=build_report(record),
        media_type="text/html",
        headers={"Content-Disposition": f'{disposition}; filename="inspection-report.html"'},
    )
