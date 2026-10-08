from pathlib import Path
from typing import Any

from PIL import Image


def process_image(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        raise ValueError("Surface image must be JPG, JPEG, or PNG.")
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            return {"format": image.format, "width": image.width, "height": image.height}
    except Exception as exc:
        raise ValueError("The uploaded surface image could not be read.") from exc
