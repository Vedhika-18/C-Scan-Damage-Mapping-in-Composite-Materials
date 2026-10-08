from pathlib import Path
import re
import struct
from typing import Any

import numpy as np


def process_ply(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if path.suffix.lower() != ".ply":
        raise ValueError("Geometry data must be a PLY file.")
    with path.open("rb") as handle:
        header = []
        while True:
            line = handle.readline()
            if not line:
                raise ValueError("PLY header is incomplete.")
            decoded = line.decode("ascii", errors="replace").strip()
            header.append(decoded)
            if decoded == "end_header":
                break
    if not header or header[0] != "ply":
        raise ValueError("The geometry file is not a PLY file.")
    format_line = next((line for line in header if line.startswith("format ")), "")
    vertex_line = next((line for line in header if line.startswith("element vertex ")), None)
    if vertex_line is None:
        raise ValueError("PLY does not declare a vertex element.")
    vertex_count = int(vertex_line.split()[-1])
    if "ascii" in format_line:
        with path.open(encoding="ascii", errors="replace") as handle:
            for line in handle:
                if line.strip() == "end_header":
                    break
            points = []
            for line in handle:
                if len(points) >= vertex_count:
                    break
                values = line.split()
                if len(values) >= 3:
                    try:
                        points.append([float(value) for value in values[:3]])
                    except ValueError:
                        continue
    elif "binary_little_endian" in format_line:
        points = _read_binary_vertices(path, header, vertex_count)
    else:
        raise ValueError("PLY must be ASCII or binary little-endian.")
    array = np.asarray(points, dtype=float)
    if array.shape[0] == 0:
        raise ValueError("PLY contains no readable vertices.")
    return {
        "point_count": int(array.shape[0]),
        "points": array,
        "bounds": {
            "x_min": float(array[:, 0].min()),
            "x_max": float(array[:, 0].max()),
            "y_min": float(array[:, 1].min()),
            "y_max": float(array[:, 1].max()),
            "z_min": float(array[:, 2].min()),
            "z_max": float(array[:, 2].max()),
        },
    }


def _read_binary_vertices(path: Path, header: list[str], vertex_count: int) -> list[list[float]]:
    vertex_index = header.index(next(line for line in header if line.startswith("element vertex ")))
    property_lines = []
    for line in header[vertex_index + 1 :]:
        if line.startswith("element ") or line == "end_header":
            break
        if line.startswith("property "):
            property_lines.append(line.split())
    if len(property_lines) < 3 or any(item[1] != "float" for item in property_lines[:3]):
        raise ValueError("Binary PLY must begin each vertex with float X, Y, and Z properties.")
    vertex_size = sum(4 if item[1] == "float" else 8 for item in property_lines)
    header_bytes = path.read_bytes()
    header_end = header_bytes.index(b"end_header") + len(b"end_header")
    while header_end < len(header_bytes) and header_bytes[header_end] in b"\r\n":
        header_end += 1
    points = []
    for index in range(vertex_count):
        offset = header_end + index * vertex_size
        if offset + 12 > len(header_bytes):
            break
        points.append(list(struct.unpack_from("<3f", header_bytes, offset)))
    return points
