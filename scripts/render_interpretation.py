#!/usr/bin/env python3
"""Render deterministic access and zoning overlays on a fixed floor-plan base."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SWING_KINDS = {"entrance_door", "interior_door", "balcony_door"}
SEGMENT_KINDS = {"sliding_door", "open_passage", "window", "fixed_glazing"}


def point(value, size, label):
    if not (isinstance(value, (list, tuple)) and len(value) == 2
            and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                    and math.isfinite(v) for v in value)
            and 0 <= value[0] < size[0] and 0 <= value[1] < size[1]):
        raise ValueError(f"{label}: missing or out-of-bounds coordinates")
    return tuple(value)


def polygon_points(value, size, label):
    if not isinstance(value, list) or len(value) < 3:
        raise ValueError(f"{label}: polygon requires at least three vertices")
    vertices = [point(p, size, label) for p in value]
    area = abs(sum(a[0]*b[1]-b[0]*a[1] for a, b in zip(vertices, vertices[1:]+vertices[:1]))) / 2
    if area < 1 or len(set(vertices)) != len(vertices):
        raise ValueError(f"{label}: degenerate polygon")
    # Reject crossing edges; shared endpoints of adjacent edges are expected.
    def cross(a, b, c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    edges = list(zip(vertices, vertices[1:]+vertices[:1]))
    for i, (a, b) in enumerate(edges):
        for j, (c, d) in enumerate(edges):
            if j > i+1 and not (i == 0 and j == len(edges)-1):
                if cross(a,b,c)*cross(a,b,d) < 0 and cross(c,d,a)*cross(c,d,b) < 0:
                    raise ValueError(f"{label}: self-intersecting polygon")
    return vertices


def validate_geometry(base, data):
    """Fail before rendering if an interior zone or element would be skipped."""
    for e in data.get("elements", []):
        label = e["id"]
        point(e.get("render_point"), base.size, label)
        kind = e["kind"]
        geometry = e.get("render_geometry", {})
        if kind in SWING_KINDS:
            hinge, closed, opened = [point(geometry.get(k), base.size, f"{label}.{k}")
                                     for k in ("hinge", "closed_tip", "open_tip")]
            r, s = math.dist(hinge, closed), math.dist(hinge, opened)
            if r < 2 or abs(r-s) > max(1, r*.03):
                raise ValueError(f"{label}: unequal or zero door leaf radii")
            if geometry.get("arc_direction") not in {"clockwise", "counterclockwise"}:
                raise ValueError(f"{label}: arc_direction required")
            start = math.atan2(closed[1]-hinge[1], closed[0]-hinge[0])
            end = math.atan2(opened[1]-hinge[1], opened[0]-hinge[0])
            sweep = ((end-start) if geometry["arc_direction"] == "clockwise" else (start-end)) % (2*math.pi)
            if not 0 < sweep <= math.pi:
                raise ValueError(f"{label}: invalid door swing angle")
            if not e.get("swing_into") or not e.get("hinge_location"):
                raise ValueError(f"{label}: swing_into and hinge_location required")
        elif kind in SEGMENT_KINDS:
            a, b = [point(geometry.get(k), base.size, f"{label}.{k}") for k in ("start", "end")]
            if math.dist(a, b) < 2:
                raise ValueError(f"{label}: opening segment is too short")
        elif kind == "bay_window":
            polygon_points(geometry.get("outline"), base.size, label)
    interior = [z for z in data.get("zones", []) if z["id"] != "outside"]
    if not interior:
        raise ValueError("no interior zones to render")
    masks = []
    for zone in interior:
        vertices = polygon_points(zone.get("render_polygon"), base.size, zone["id"])
        mask = Image.new("1", base.size)
        drawing = ImageDraw.Draw(mask)
        drawing.polygon(vertices, fill=1)
        # Exclude shared boundary pixels from overlap checks.
        drawing.line(vertices+[vertices[0]], fill=0, width=1)
        from PIL import ImageChops
        for other_id, other in masks:
            if ImageChops.logical_and(mask, other).getbbox():
                raise ValueError(f"zones overlap: {other_id}, {zone['id']}")
        masks.append((zone["id"], mask))
    warnings = []
    if data.get("coverage_polygon"):
        from PIL import ImageChops
        coverage = Image.new("1", base.size)
        ImageDraw.Draw(coverage).polygon(polygon_points(data["coverage_polygon"], base.size, "coverage"), fill=1)
        union = Image.new("1", base.size)
        for zone in interior:
            mask = Image.new("1", base.size)
            ImageDraw.Draw(mask).polygon(zone["render_polygon"], fill=1)
            union = ImageChops.logical_or(union, mask)
        for excluded in data.get("coverage_exclusions", []):
            if not excluded.get("reason"):
                raise ValueError("coverage exclusion needs a reason (wall/shaft/etc.)")
            ImageDraw.Draw(union).polygon(polygon_points(excluded.get("polygon"), base.size, "exclusion"), fill=1)
        if ImageChops.subtract(coverage.convert("L"), union.convert("L")).getbbox():
            warnings.append("Unassigned footprint area: inspect walls, shafts, and omitted zones before confirmation")
        if ImageChops.subtract(union.convert("L"), coverage.convert("L")).getbbox():
            raise ValueError("zone or exclusion extends outside coverage polygon")
    else:
        warnings.append("No coverage_polygon: completeness against the source requires visual review")
    return warnings


def draw_symbol(draw, item, color):
    geometry = item.get("render_geometry", {})
    kind = item["kind"]
    if kind in SWING_KINDS:
        h, c, o = [tuple(geometry[k]) for k in ("hinge", "closed_tip", "open_tip")]
        radius = math.dist(h, c)
        start = math.atan2(c[1]-h[1], c[0]-h[0])
        end = math.atan2(o[1]-h[1], o[0]-h[0])
        sweep = (end-start) % (2*math.pi)
        if geometry["arc_direction"] == "counterclockwise":
            sweep = -((start-end) % (2*math.pi))
        if not 0 < abs(sweep) <= math.pi:
            raise ValueError(f"{item['id']}: invalid door swing angle")
        arc = [(h[0]+radius*math.cos(start+sweep*i/30), h[1]+radius*math.sin(start+sweep*i/30)) for i in range(31)]
        draw.line([h, o], fill=color, width=4)
        draw.line(arc, fill=color, width=2)
        draw.ellipse((h[0]-3,h[1]-3,h[0]+3,h[1]+3), fill=color)
    elif kind in SEGMENT_KINDS:
        a, b = tuple(geometry["start"]), tuple(geometry["end"])
        length = math.dist(a,b)
        normal = (-(b[1]-a[1])/length*3, (b[0]-a[0])/length*3)
        if kind == "open_passage":
            for i in range(0, 10, 2):
                draw.line([(a[0]+(b[0]-a[0])*t/10,a[1]+(b[1]-a[1])*t/10) for t in (i,i+1)], fill=color, width=3)
        elif kind == "sliding_door":
            for lo, hi, sign in ((0,.65,1),(.35,1,-1)):
                draw.line([(a[0]+(b[0]-a[0])*t+sign*normal[0],a[1]+(b[1]-a[1])*t+sign*normal[1]) for t in (lo,hi)], fill=color, width=3)
        else:
            for sign in (-1,1):
                draw.line([(p[0]+sign*normal[0], p[1]+sign*normal[1]) for p in (a,b)], fill=color, width=2)
    elif kind == "bay_window":
        vertices = [tuple(p) for p in geometry["outline"]]
        draw.line(vertices+[vertices[0]], fill=color, width=4)


COLORS = {
    "confirmed": (22, 163, 74, 220),
    "probable": (234, 88, 12, 220),
    "uncertain": (220, 38, 38, 220),
    "window": (37, 99, 235, 230),
    "bay_window": (124, 58, 237, 230),
    "unknown_gap": (220, 38, 38, 230),
    "door_candidate": (217, 119, 6, 230),
    "door": (22, 163, 74, 230),
    "sliding_door": (234, 88, 12, 230),
    "open_passage": (8, 145, 178, 230),
}

ZONE_PALETTE = [
    (37, 99, 235, 230),
    (234, 88, 12, 230),
    (14, 165, 233, 230),
    (22, 163, 74, 230),
    (147, 51, 234, 230),
    (219, 39, 119, 230),
    (202, 138, 4, 230),
    (13, 148, 136, 230),
    (220, 38, 38, 230),
]


def prepare_base(base: Image.Image, data: dict) -> Image.Image:
    """Apply only user-confirmed graphic removals before drawing overlays."""
    image = base.copy().convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    for item in data.get("ignored_graphics", []):
        for rectangle in item.get("rectangles", []):
            draw.rectangle(tuple(rectangle), fill=(255, 255, 255, 255))
    return image


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    from platform_support import load_font
    return load_font(size)


def text_box(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str,
             fill: tuple[int, int, int, int], text_font: ImageFont.ImageFont) -> None:
    box = draw.textbbox(xy, text, font=text_font, anchor="mm")
    pad = 5
    draw.rounded_rectangle(
        (box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad),
        radius=5,
        fill=(255, 255, 255, 225),
        outline=fill,
        width=2,
    )
    draw.text(xy, text, font=text_font, fill=(20, 20, 20, 255), anchor="mm")


def render_access(base: Image.Image, data: dict, output: Path) -> None:
    validate_geometry(base, data)
    image = prepare_base(base, data)
    draw = ImageDraw.Draw(image, "RGBA")
    label_font = font(18)
    for item in data.get("elements", []):
        point = item.get("render_point")
        kind = item["kind"]
        if kind == "sliding_door":
            color = COLORS["sliding_door"]
        elif kind.endswith("door"):
            color = COLORS["door"]
        elif kind == "open_passage":
            color = COLORS["open_passage"]
        else:
            color = COLORS.get(kind, COLORS[item["certainty"]])
        x, y = point
        draw_symbol(draw, item, color)
        draw.ellipse((x - 10, y - 10, x + 10, y + 10), fill=color,
                     outline=(255, 255, 255, 255), width=2)
        text_box(draw, (x, y - 25), item.get("display_label", item["id"]), color, label_font)
    image.convert("RGB").save(output, quality=95)


def render_zoning(base: Image.Image, data: dict, output: Path) -> None:
    validate_geometry(base, data)
    image = prepare_base(base, data)
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    label_font = font(20)
    for index, zone in enumerate(data.get("zones", [])):
        polygon = zone.get("render_polygon")
        if zone["id"] == "outside":
            continue
        explicit_color = zone.get("render_color")
        if isinstance(explicit_color, list) and len(explicit_color) == 3:
            color = (*explicit_color, 230)
        else:
            color = ZONE_PALETTE[index % len(ZONE_PALETTE)]
        draw.polygon([tuple(point) for point in polygon], fill=(*color[:3], 68),
                     outline=color, width=3)
        xs = [point[0] for point in polygon]
        ys = [point[1] for point in polygon]
        center = (sum(xs) // len(xs), sum(ys) // len(ys))
        label = f'{zone["id"]} {zone.get("display_label", zone.get("proposed_function", "待确认"))}'
        text_box(draw, center, label, color, label_font)
    result = Image.alpha_composite(image, overlay)
    result.convert("RGB").save(output, quality=95)


def render_route(base: Image.Image, recognition: dict, topology: dict, output: Path) -> None:
    image = prepare_base(base, recognition)
    draw = ImageDraw.Draw(image, "RGBA")
    points = [tuple(point) for point in topology.get("route_render_points", [])]
    if len(points) < 2:
        raise ValueError("topology.route_render_points requires at least two points")
    draw.line(points, fill=(234, 88, 12, 230), width=7, joint="curve")
    number_font = font(18)
    stop_points = topology.get("route_stop_points") or [
        {"order": index, "point": list(point)}
        for index, point in enumerate(points, start=1)
    ]
    for stop in stop_points:
        index = stop["order"]
        point = tuple(stop["point"])
        x, y = point
        draw.ellipse((x - 11, y - 11, x + 11, y + 11),
                     fill=(234, 88, 12, 245), outline=(255, 255, 255, 255), width=2)
        draw.text((x, y), str(index), font=number_font, fill=(255, 255, 255, 255),
                  anchor="mm")
    image.convert("RGB").save(output, quality=95)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--recognition", required=True, type=Path)
    parser.add_argument("--topology", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = json.loads(args.recognition.read_text(encoding="utf-8"))
    topology = json.loads(args.topology.read_text(encoding="utf-8")) if args.topology else None
    has_route = topology is not None and topology.get("tour_route") is not None
    base = Image.open(args.base)
    warnings = validate_geometry(base, data)
    targets = [args.output_dir/name for name in ("topdown-access-v2.png", "topdown-zoning-v2.png")]
    if has_route:
        targets.append(args.output_dir/"topdown-tour-route-v2.png")
    if any(target.exists() for target in targets):
        raise ValueError("overlay output already exists; use a new version directory")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    render_access(base, data, args.output_dir / "topdown-access-v2.png")
    render_zoning(base, data, args.output_dir / "topdown-zoning-v2.png")
    result = {
        "status": "ok",
        "warnings": warnings,
        "access": str((args.output_dir / "topdown-access-v2.png").resolve()),
        "zoning": str((args.output_dir / "topdown-zoning-v2.png").resolve()),
    }
    if has_route:
        route_output = args.output_dir / "topdown-tour-route-v2.png"
        render_route(base, data, topology, route_output)
        result["route"] = str(route_output.resolve())
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
