#!/usr/bin/env python3
"""Deterministically place confirmed source images on a labelled contact sheet."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from vector_tools import atomic_write, require


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size: int) -> ImageFont.ImageFont:
    from platform_support import load_font
    return load_font(size)


def assemble(spec: dict, spec_path: Path, output: Path, manifest: Path) -> dict:
    require(spec.get("schema_version") == "1.0", "schema_version must be 1.0")
    require(isinstance(spec.get("confirmed_images"), list) and spec["confirmed_images"],
            "confirmed_images must be a non-empty list")
    columns = spec.get("columns", 2)
    padding = spec.get("padding", 24)
    label_height = spec.get("label_height", 42)
    require(isinstance(columns, int) and 1 <= columns <= 12, "columns must be 1..12")
    require(isinstance(padding, int) and 0 <= padding <= 500, "padding must be 0..500")
    require(isinstance(label_height, int) and 20 <= label_height <= 300, "label_height must be 20..300")
    require(not output.exists() and not manifest.exists(), "output already exists; use a new revision")
    records, opened = [], []
    try:
        for index, item in enumerate(spec["confirmed_images"]):
            require(isinstance(item, dict) and isinstance(item.get("path"), str),
                    f"confirmed_images[{index}] needs path")
            path = Path(item["path"]).expanduser()
            if not path.is_absolute():
                path = (spec_path.parent / path).resolve()
            require(path.is_file(), f"source image not found: {path}")
            before = file_sha(path)
            image = Image.open(path)
            image.load()
            opened.append(image)
            require(image.width > 0 and image.height > 0, f"empty image: {path}")
            records.append({"path": str(path), "label": str(item.get("label", path.stem)),
                            "sha256_before": before, "width": image.width, "height": image.height})
        cell_width = max(image.width for image in opened)
        cell_image_height = max(image.height for image in opened)
        rows = math.ceil(len(opened) / columns)
        sheet_width = padding + columns * (cell_width + padding)
        sheet_height = padding + rows * (label_height + cell_image_height + padding)
        require(sheet_width * sheet_height <= 300_000_000, "contact sheet exceeds 300 megapixels")
        background = spec.get("background", "white")
        sheet = Image.new("RGB", (sheet_width, sheet_height), background)
        draw = ImageDraw.Draw(sheet)
        text_font = font(min(24, max(12, label_height // 2)))
        for index, (image, record) in enumerate(zip(opened, records)):
            row, col = divmod(index, columns)
            cell_x = padding + col * (cell_width + padding)
            label_y = padding + row * (label_height + cell_image_height + padding)
            paste_x = cell_x + (cell_width - image.width) // 2
            y = label_y + label_height + (cell_image_height - image.height) // 2
            sheet.paste(image.convert("RGB"), (paste_x, y))
            draw.text((cell_x + cell_width / 2, label_y + label_height / 2), record["label"],
                      fill="#111111", anchor="mm", font=text_font)
            record.update(placement={"x": paste_x, "y": y, "width": image.width, "height": image.height},
                          sha256_after=file_sha(Path(record["path"])))
            require(record["sha256_before"] == record["sha256_after"], f"source changed during assembly: {record['path']}")
        with __import__("tempfile").TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir) / "sheet.png"
            sheet.save(temp, format="PNG", optimize=False, compress_level=9)
            atomic_write(output, temp.read_bytes())
        result = {"schema_version": "1.0", "status": "ok", "method": "deterministic_pixel_copy",
                  "source_files_unchanged": True, "source_images_resized": False,
                  "source_images_cropped": False, "canvas": {"width": sheet_width, "height": sheet_height},
                  "images": records, "output": str(output.resolve())}
        atomic_write(manifest, json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        return result
    finally:
        for image in opened:
            image.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    spec = json.loads(args.input.read_text(encoding="utf-8"))
    result = assemble(spec, args.input, args.output, args.manifest)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
