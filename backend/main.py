import shutil
import uuid
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .database import create_inspection, get_inspection, initialize_database
from .pipeline import generate_inspection
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
            csv_path, cscan_path, ply_path, image_path, material.strip(), thickness
        )
        prefix = f"inspections/{result_id}"
        csv_key = upload_file(csv_path, f"{prefix}/{csv_path.name}", "text/csv")
        ply_key = upload_file(ply_path, f"{prefix}/{ply_path.name}", "application/octet-stream") if ply_path else None
        image_key = upload_file(image_path, f"{prefix}/{image_path.name}", "image/*") if image_path else None
        cscan_key = upload_file(cscan_path, f"{prefix}/cscan.png", "image/png")
        create_inspection(
            {
                "id": result_id,
                "material": material.strip(),
                "thickness_mm": thickness,
                "csv_filename": csv_path.name,
                "ply_filename": ply_path.name if ply_path else None,
                "surface_filename": image_path.name if image_path else None,
                "cscan_key": cscan_key,
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
    folder = UPLOADS / result_id
    matches = [path for path in folder.iterdir()] if folder.is_dir() else []
    image = next(
        (
            path
            for path in matches
            if path.name != "cscan.png"
            and path.suffix.lower() in {".jpg", ".jpeg", ".png"}
        ),
        None,
    )
    if image is None:
        raise HTTPException(status_code=404, detail="Surface image not found.")
    return FileResponse(image)
