"""Portable font discovery; never download fonts or change system settings."""
import os
from pathlib import Path
import warnings

from PIL import ImageFont


def font_candidates():
    override = os.environ.get("FLOORPLAN_FONT")
    if override:
        yield Path(override)
    windows = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    for name in ("msyh.ttc", "msjh.ttc", "simsun.ttc"):
        yield windows / name
    for name in (
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ):
        yield Path(name)


def find_font():
    for candidate in font_candidates():
        if candidate.is_file():
            try:
                ImageFont.truetype(str(candidate), 16)
                return candidate
            except OSError:
                continue
    return None


def load_font(size):
    selected = find_font()
    if selected:
        return ImageFont.truetype(str(selected), size)
    warnings.warn("No CJK font found. Set FLOORPLAN_FONT to a licensed font file; Chinese labels require visual review.", RuntimeWarning)
    return ImageFont.load_default(size=size)
