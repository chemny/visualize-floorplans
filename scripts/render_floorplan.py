#!/usr/bin/env python3
"""Render a generic structured floor plan to same-revision editable SVG and PNG."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from vector_tools import canvas, esc, fmt, load_json, point, points_attr, polygon, render_pair, require


def validate(data: dict[str, Any]) -> tuple[int, int]:
    require(data.get("schema_version") == "1.0", "schema_version must be 1.0")
    require(isinstance(data.get("revision"), str) and data["revision"].strip(), "revision is required")
    width, height = canvas(data)
    walls = data.get("walls")
    require(isinstance(walls, list) and walls, "walls must be a non-empty list")
    seen: set[str] = set()
    for collection in ("walls", "rooms", "doors", "openings", "annotations"):
        items = data.get(collection, [])
        require(isinstance(items, list), f"{collection} must be a list")
        for index, item in enumerate(items):
            require(isinstance(item, dict), f"{collection}[{index}] must be an object")
            item_id = item.get("id")
            require(isinstance(item_id, str) and item_id and item_id not in seen,
                    f"{collection}[{index}] needs a unique id")
            seen.add(item_id)
    for wall in walls:
        if "polygon" in wall:
            polygon(wall["polygon"], width, height, f"wall {wall['id']}")
        else:
            start = point(wall.get("start"), width, height, f"wall {wall['id']}.start")
            end = point(wall.get("end"), width, height, f"wall {wall['id']}.end")
            require(math.dist(start, end) > 0, f"wall {wall['id']} has zero length")
            thickness = wall.get("thickness")
            require(isinstance(thickness, (int, float)) and 0 < thickness <= min(width, height) / 3,
                    f"wall {wall['id']} needs a valid thickness")
    for room in data.get("rooms", []):
        polygon(room.get("polygon"), width, height, f"room {room['id']}")
        if room.get("label_point") is not None:
            point(room["label_point"], width, height, f"room {room['id']}.label_point")
    for door in data.get("doors", []):
        hinge = point(door.get("hinge"), width, height, f"door {door['id']}.hinge")
        closed = point(door.get("closed_tip"), width, height, f"door {door['id']}.closed_tip")
        opened = point(door.get("open_tip"), width, height, f"door {door['id']}.open_tip")
        radius = math.dist(hinge, closed)
        require(radius >= 2 and abs(radius - math.dist(hinge, opened)) <= max(1, radius * .03),
                f"door {door['id']} leaf radii differ")
        require(door.get("arc_direction") in {"clockwise", "counterclockwise"},
                f"door {door['id']} arc_direction is required")
    for opening in data.get("openings", []):
        require(opening.get("kind") in {"window", "bay_window", "sliding_door", "open_passage", "fixed_glazing", "unknown_gap"},
                f"opening {opening['id']} has unsupported kind")
        if opening["kind"] == "bay_window":
            polygon(opening.get("outline"), width, height, f"opening {opening['id']}.outline")
        else:
            start = point(opening.get("start"), width, height, f"opening {opening['id']}.start")
            end = point(opening.get("end"), width, height, f"opening {opening['id']}.end")
            require(math.dist(start, end) >= 2, f"opening {opening['id']} is too short")
    for note in data.get("annotations", []):
        point(note.get("point"), width, height, f"annotation {note['id']}.point")
    return width, height


def line(x1: float, y1: float, x2: float, y2: float, class_name: str, item_id: str) -> str:
    styles = {
        "door-leaf": 'fill="none" stroke="#111111" stroke-width="2"',
        "window": 'fill="none" stroke="#2563eb" stroke-width="5"',
        "fixed_glazing": 'fill="none" stroke="#2563eb" stroke-width="5"',
        "sliding_door": 'fill="none" stroke="#ea580c" stroke-width="4"',
        "open_passage": 'fill="none" stroke="#0891b2" stroke-width="4" stroke-dasharray="7 5"',
        "unknown_gap": 'fill="none" stroke="#dc2626" stroke-width="4" stroke-dasharray="3 4"',
    }
    require(class_name in styles, f"unsupported line class {class_name}")
    return (f'<line id="{esc(item_id)}" data-kind="{esc(class_name)}" class="{esc(class_name)}" '
            f'x1="{fmt(x1)}" y1="{fmt(y1)}" x2="{fmt(x2)}" y2="{fmt(y2)}" '
            f'{styles[class_name]}/>')


def door_path(door: dict[str, Any]) -> tuple[str, str]:
    hinge, closed, opened = (tuple(door[key]) for key in ("hinge", "closed_tip", "open_tip"))
    radius = math.dist(hinge, closed)
    start = math.atan2(closed[1] - hinge[1], closed[0] - hinge[0])
    end = math.atan2(opened[1] - hinge[1], opened[0] - hinge[0])
    if door["arc_direction"] == "clockwise":
        sweep = (end - start) % (2 * math.pi)
    else:
        sweep = -((start - end) % (2 * math.pi))
    large = 1 if abs(sweep) > math.pi else 0
    sweep_flag = 1 if sweep > 0 else 0
    leaf = line(hinge[0], hinge[1], opened[0], opened[1], "door-leaf", f"{door['id']}-leaf")
    arc = (f'<path id="{esc(door["id"])}-swing" data-kind="door-swing" class="door-swing" '
           f'd="M {fmt(closed[0])} {fmt(closed[1])} A {fmt(radius)} {fmt(radius)} 0 {large} {sweep_flag} '
           f'{fmt(opened[0])} {fmt(opened[1])}" fill="none" stroke="#111111" stroke-width="2"/>')
    return leaf, arc


def build_svg(data: dict[str, Any]) -> str:
    width, height = validate(data)
    background = data.get("canvas", {}).get("background", "#ffffff")
    show_room_boundaries = bool(data.get("canvas", {}).get("show_room_boundaries", False))
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           '<style>.wall{fill:#222;stroke:#111;stroke-linecap:square}.room{fill:none;stroke:#aaa;stroke-dasharray:5 4}.door-leaf,.door-swing{fill:none;stroke:#111;stroke-width:2}.window,.fixed_glazing{stroke:#2563eb;stroke-width:5}.bay_window{fill:none;stroke:#7c3aed;stroke-width:4}.sliding_door{stroke:#ea580c;stroke-width:4}.open_passage{stroke:#0891b2;stroke-width:4;stroke-dasharray:7 5}.unknown_gap{stroke:#dc2626;stroke-width:4;stroke-dasharray:3 4}.label{font:14px sans-serif;fill:#222}.note{font:12px sans-serif;fill:#555}</style>',
           f'<rect id="canvas-background" data-kind="background" x="0" y="0" width="{width}" height="{height}" fill="{esc(background)}"/>',
           '<g id="rooms" data-layer="rooms">']
    for room in data.get("rooms", []):
        if show_room_boundaries:
            out.append(f'<polygon id="{esc(room["id"])}" data-kind="room" class="room" points="{points_attr([tuple(p) for p in room["polygon"]])}" fill="none" stroke="#aaaaaa" stroke-width="1" stroke-dasharray="5 4"/>')
        if room.get("label") and room.get("label_point"):
            x, y = room["label_point"]
            out.append(f'<text id="{esc(room["id"])}-label" data-kind="room-label" class="label" x="{fmt(x)}" y="{fmt(y)}" text-anchor="middle" fill="#222222" stroke="none" font-family="sans-serif" font-size="14">{esc(room["label"])}</text>')
    out.append('</g><g id="walls" data-layer="walls">')
    for wall in data["walls"]:
        if "polygon" in wall:
            out.append(f'<polygon id="{esc(wall["id"])}" data-kind="wall" class="wall" points="{points_attr([tuple(p) for p in wall["polygon"]])}" fill="#222222" stroke="#111111" stroke-width="1"/>')
        else:
            x1, y1 = wall["start"]; x2, y2 = wall["end"]
            out.append(f'<line id="{esc(wall["id"])}" data-kind="wall" class="wall" x1="{fmt(x1)}" y1="{fmt(y1)}" x2="{fmt(x2)}" y2="{fmt(y2)}" fill="none" stroke="#111111" stroke-linecap="square" stroke-width="{fmt(wall["thickness"])}"/>')
    out.append('</g><g id="access" data-layer="access">')
    for opening in data.get("openings", []):
        if opening["kind"] == "bay_window":
            out.append(f'<polygon id="{esc(opening["id"])}" data-kind="bay_window" class="bay_window" points="{points_attr([tuple(p) for p in opening["outline"]])}" fill="none" stroke="#7c3aed" stroke-width="4"/>')
        else:
            x1, y1 = opening["start"]; x2, y2 = opening["end"]
            out.append(line(x1, y1, x2, y2, opening["kind"], opening["id"]))
    for door in data.get("doors", []):
        out.extend(door_path(door))
    out.append('</g><g id="annotations" data-layer="annotations">')
    for note in data.get("annotations", []):
        x, y = note["point"]
        out.append(f'<text id="{esc(note["id"])}" data-kind="annotation" class="note" x="{fmt(x)}" y="{fmt(y)}" fill="#555555" stroke="none" font-family="sans-serif" font-size="12">{esc(note.get("text", ""))}</text>')
    out.append(f'</g><metadata>revision={esc(data["revision"])}; conceptual_reference=true</metadata></svg>')
    return "\n".join(out)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--svg", required=True, type=Path)
    parser.add_argument("--png", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = load_json(args.input)
    width, height = validate(data)
    result = render_pair(build_svg(data), args.svg, args.png, width, height)
    result.update(status="ok", revision=data["revision"], conceptual_reference=True)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
