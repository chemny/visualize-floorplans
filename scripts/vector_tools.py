#!/usr/bin/env python3
"""Shared deterministic SVG helpers for floor-plan tools."""

from __future__ import annotations

import hashlib
import html
import json
import math
import os
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable


class VectorInputError(ValueError):
    """Raised when structured drawing input is unsafe or incomplete."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VectorInputError(message)


def number(value: Any, label: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{label} must be a number")
    require(math.isfinite(value), f"{label} must be finite")
    return float(value)


def point(value: Any, width: float, height: float, label: str) -> tuple[float, float]:
    require(isinstance(value, list) and len(value) == 2, f"{label} must be [x, y]")
    x, y = number(value[0], f"{label}.x"), number(value[1], f"{label}.y")
    require(0 <= x <= width and 0 <= y <= height, f"{label} is outside the canvas")
    return x, y


def polygon(value: Any, width: float, height: float, label: str) -> list[tuple[float, float]]:
    require(isinstance(value, list) and len(value) >= 3, f"{label} needs at least three points")
    pts = [point(v, width, height, f"{label}[{i}]") for i, v in enumerate(value)]
    area = abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1]))) / 2
    require(area > 0.5 and len(set(pts)) == len(pts), f"{label} is degenerate")
    return pts


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def fmt(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def points_attr(points: Iterable[tuple[float, float]]) -> str:
    return " ".join(f"{fmt(x)},{fmt(y)}" for x, y in points)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(data, dict), "input root must be an object")
    return data


def canvas(data: dict[str, Any]) -> tuple[int, int]:
    raw = data.get("canvas")
    require(isinstance(raw, dict), "canvas is required")
    width, height = raw.get("width"), raw.get("height")
    require(isinstance(width, int) and isinstance(height, int), "canvas width and height must be integers")
    require(64 <= width <= 10000 and 64 <= height <= 10000, "canvas size must be between 64 and 10000")
    return width, height


def validate_output_pair(svg_path: Path, png_path: Path) -> None:
    require(svg_path.suffix.lower() == ".svg", "SVG output must use .svg")
    require(png_path.suffix.lower() == ".png", "PNG output must use .png")
    require(svg_path.stem == png_path.stem, "SVG and PNG outputs must share one revision stem")
    require(not svg_path.exists() and not png_path.exists(), "output already exists; use a new revision stem")


def atomic_write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        mode = "wb" if isinstance(content, bytes) else "w"
        kwargs = {} if isinstance(content, bytes) else {"encoding": "utf-8", "newline": "\n"}
        with os.fdopen(fd, mode, **kwargs) as handle:
            handle.write(content)
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def validate_svg(svg_text: str) -> None:
    root = ET.fromstring(svg_text)
    require(root.tag.rsplit("}", 1)[-1] == "svg", "generated XML root is not svg")
    tags = [node.tag.rsplit("}", 1)[-1] for node in root.iter()]
    require("image" not in tags, "embedded raster images are forbidden")
    require(any(tag in {"path", "polygon", "rect", "line", "circle", "ellipse"} for tag in tags),
            "SVG contains no editable vector geometry")


def svg_to_png(svg_path: Path, png_path: Path, width: int, height: int) -> str:
    """Render the exact SVG file to PNG without an image-generation model."""
    svg_bytes = svg_path.read_bytes()
    try:
        import fitz  # type: ignore
        document = fitz.open(stream=svg_bytes, filetype="svg")
        page = document[0]
        matrix = fitz.Matrix(width / page.rect.width, height / page.rect.height)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        atomic_write(png_path, pixmap.tobytes("png"))
        return "pymupdf"
    except ImportError:
        pass
    converter = shutil.which("rsvg-convert")
    if converter:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir) / "render.png"
            subprocess.run([converter, "--width", str(width), "--height", str(height),
                            "--output", str(temp), str(svg_path)], check=True)
            atomic_write(png_path, temp.read_bytes())
        return "rsvg-convert"
    raise RuntimeError("SVG rendering requires PyMuPDF or rsvg-convert; no renderer is available")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_pair(svg_text: str, svg_path: Path, png_path: Path, width: int, height: int) -> dict[str, Any]:
    validate_output_pair(svg_path, png_path)
    validate_svg(svg_text)
    atomic_write(svg_path, svg_text)
    try:
        backend = svg_to_png(svg_path, png_path, width, height)
    except Exception:
        svg_path.unlink(missing_ok=True)
        png_path.unlink(missing_ok=True)
        raise
    return {
        "svg": str(svg_path.resolve()),
        "png": str(png_path.resolve()),
        "svg_sha256": digest(svg_path),
        "png_sha256": digest(png_path),
        "renderer": backend,
    }


def point_in_polygon(point_xy: tuple[float, float], poly: list[tuple[float, float]]) -> bool:
    x, y = point_xy
    inside = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if ((y1 > y) != (y2 > y)) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def orientation(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def segments_intersect(a: tuple[float, float], b: tuple[float, float],
                       c: tuple[float, float], d: tuple[float, float]) -> bool:
    def on_segment(p: tuple[float, float], q: tuple[float, float], r: tuple[float, float]) -> bool:
        return (min(p[0], r[0]) - 1e-9 <= q[0] <= max(p[0], r[0]) + 1e-9
                and min(p[1], r[1]) - 1e-9 <= q[1] <= max(p[1], r[1]) + 1e-9)
    o1, o2, o3, o4 = orientation(a, b, c), orientation(a, b, d), orientation(c, d, a), orientation(c, d, b)
    if o1 * o2 < 0 and o3 * o4 < 0:
        return True
    return any(abs(o) < 1e-9 and on_segment(*triplet) for o, triplet in (
        (o1, (a, c, b)), (o2, (a, d, b)), (o3, (c, a, d)), (o4, (c, b, d))))


def polygons_intersect(a: list[tuple[float, float]], b: list[tuple[float, float]]) -> bool:
    for a1, a2 in zip(a, a[1:] + a[:1]):
        for b1, b2 in zip(b, b[1:] + b[:1]):
            if segments_intersect(a1, a2, b1, b2):
                return True
    return point_in_polygon(a[0], b) or point_in_polygon(b[0], a)


def rectangle(x: float, y: float, width: float, height: float) -> list[tuple[float, float]]:
    return [(x, y), (x + width, y), (x + width, y + height), (x, y + height)]
