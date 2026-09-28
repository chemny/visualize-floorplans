#!/usr/bin/env python3
"""Render a generic furniture plan and reject wall, object, and door-swing conflicts."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import render_floorplan
from vector_tools import (canvas, esc, fmt, load_json, point_in_polygon, polygon,
                          polygons_intersect, rectangle, render_pair, require)

SYMBOLS = {"bed", "sofa", "table", "chair", "cabinet", "sink", "toilet", "appliance", "generic"}


def item_rect(item: dict[str, Any]) -> list[tuple[float, float]]:
    return rectangle(float(item["x"]), float(item["y"]), float(item["width"]), float(item["height"]))


def wall_polygon(wall: dict[str, Any]) -> list[tuple[float, float]]:
    if "polygon" in wall:
        return [tuple(p) for p in wall["polygon"]]
    (x1, y1), (x2, y2), thickness = wall["start"], wall["end"], wall["thickness"]
    length = math.dist((x1, y1), (x2, y2))
    require(length > 0, f"wall {wall['id']} has zero length")
    nx, ny = -(y2 - y1) / length * thickness / 2, (x2 - x1) / length * thickness / 2
    return [(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)]


def door_conflict(item: dict[str, Any], door: dict[str, Any]) -> bool:
    rect = item_rect(item)
    x, y, w, h = item["x"], item["y"], item["width"], item["height"]
    hinge, closed, opened = (tuple(door[key]) for key in ("hinge", "closed_tip", "open_tip"))
    radius = math.dist(hinge, closed)
    start = math.atan2(closed[1] - hinge[1], closed[0] - hinge[0])
    end = math.atan2(opened[1] - hinge[1], opened[0] - hinge[0])
    sweep = ((end - start) % (2 * math.pi) if door["arc_direction"] == "clockwise"
             else -((start - end) % (2 * math.pi)))
    samples = [(hinge[0] + radius * math.cos(start + sweep * i / 90),
                hinge[1] + radius * math.sin(start + sweep * i / 90)) for i in range(91)]
    samples.extend((hinge[0] + radius * t * math.cos(angle), hinge[1] + radius * t * math.sin(angle))
                   for angle in (start, start + sweep) for t in (0, .25, .5, .75, 1))
    def inside_sector(candidate: tuple[float, float]) -> bool:
        if math.dist(hinge, candidate) > radius:
            return False
        angle = math.atan2(candidate[1] - hinge[1], candidate[0] - hinge[0])
        travelled = ((angle - start) % (2 * math.pi) if sweep > 0
                     else -((start - angle) % (2 * math.pi)))
        return 0 <= travelled <= sweep if sweep > 0 else sweep <= travelled <= 0

    return (any(x <= px <= x + w and y <= py <= y + h for px, py in samples)
            or point_in_polygon(hinge, rect) or any(inside_sector(corner) for corner in rect))


def validate(data: dict[str, Any]) -> tuple[int, int, list[str]]:
    require(data.get("schema_version") == "1.0", "schema_version must be 1.0")
    require(isinstance(data.get("plan"), dict), "plan is required")
    width, height = render_floorplan.validate(data["plan"])
    require(data.get("revision") == data["plan"].get("revision"),
            "layout and plan revision must match")
    furniture = data.get("furniture")
    require(isinstance(furniture, list), "furniture must be a list")
    rooms = {room["id"]: [tuple(p) for p in room["polygon"]] for room in data["plan"].get("rooms", [])}
    walls_by_id = {wall["id"]: wall for wall in data["plan"].get("walls", [])}
    bay_windows = {opening["id"]: opening for opening in data["plan"].get("openings", [])
                   if opening.get("kind") == "bay_window"}
    seen: set[str] = set()
    for index, item in enumerate(furniture):
        require(isinstance(item, dict), f"furniture[{index}] must be an object")
        item_id = item.get("id")
        require(isinstance(item_id, str) and item_id and item_id not in seen,
                f"furniture[{index}] needs a unique id")
        seen.add(item_id)
        require(item.get("symbol") in SYMBOLS, f"furniture {item_id} has unsupported symbol")
        for key in ("x", "y", "width", "height"):
            require(isinstance(item.get(key), (int, float)) and not isinstance(item.get(key), bool),
                    f"furniture {item_id}.{key} must be numeric")
        require(item["width"] > 0 and item["height"] > 0, f"furniture {item_id} size must be positive")
        require(item["x"] >= 0 and item["y"] >= 0 and item["x"] + item["width"] <= width
                and item["y"] + item["height"] <= height, f"furniture {item_id} is outside the canvas")
        if item.get("label_point") is not None:
            label_point = item["label_point"]
            require(isinstance(label_point, list) and len(label_point) == 2
                    and all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in label_point)
                    and 0 <= label_point[0] <= width and 0 <= label_point[1] <= height,
                    f"furniture {item_id}.label_point must be inside the canvas")
        room_id = item.get("room_id")
        require(room_id in rooms, f"furniture {item_id} needs an existing room_id")
        recess_wall_ids = item.get("wall_recess_wall_ids", [])
        require(isinstance(recess_wall_ids, list) and all(isinstance(value, str) for value in recess_wall_ids),
                f"furniture {item_id}.wall_recess_wall_ids must be a list of wall ids")
        if recess_wall_ids:
            require(isinstance(item.get("proposal_reason"), str) and item["proposal_reason"].strip(),
                    f"wall-recess furniture {item_id} needs proposal_reason")
            require(all(wall_id in walls_by_id for wall_id in recess_wall_ids),
                    f"wall-recess furniture {item_id} references an unknown wall")
            require(any(polygons_intersect(item_rect(item), wall_polygon(walls_by_id[wall_id]))
                        for wall_id in recess_wall_ids),
                    f"wall-recess furniture {item_id} does not intersect its declared wall")
        placement_polygon = rooms[room_id]
        if item.get("bay_window_id") is not None:
            bay_id = item["bay_window_id"]
            require(bay_id in bay_windows, f"furniture {item_id} references unknown bay window {bay_id}")
            require(room_id in bay_windows[bay_id].get("connects", []),
                    f"bay window {bay_id} is not connected to room {room_id}")
            placement_polygon = [tuple(p) for p in bay_windows[bay_id]["outline"]]
        if not recess_wall_ids:
            require(all(point_in_polygon(corner, placement_polygon) for corner in item_rect(item)),
                    f"furniture {item_id} extends outside its declared placement area")
    conflicts: list[str] = []
    for item in furniture:
        recess_wall_ids = set(item.get("wall_recess_wall_ids", []))
        for wall in data["plan"]["walls"]:
            if wall["id"] not in recess_wall_ids and polygons_intersect(item_rect(item), wall_polygon(wall)):
                conflicts.append(f"wall:{item['id']}:{wall['id']}")
        for door in data["plan"].get("doors", []):
            if door_conflict(item, door):
                conflicts.append(f"door_swing:{item['id']}:{door['id']}")
    for index, first in enumerate(furniture):
        for second in furniture[index + 1:]:
            allowed = set(first.get("allow_overlap_with", [])) | set(second.get("allow_overlap_with", []))
            if second["id"] not in allowed and first["id"] not in allowed and polygons_intersect(item_rect(first), item_rect(second)):
                conflicts.append(f"furniture_overlap:{first['id']}:{second['id']}")
    return width, height, sorted(set(conflicts))


def symbol_svg(item: dict[str, Any]) -> str:
    x, y, w, h = (float(item[k]) for k in ("x", "y", "width", "height"))
    item_id, kind = esc(item["id"]), item["symbol"]
    recess = bool(item.get("wall_recess_wall_ids"))
    dash = ' stroke-dasharray="6 4"' if recess else ""
    stroke = "#ffffff" if recess else "#444444"
    base = (f'<g id="{item_id}" data-kind="furniture" data-symbol="{esc(kind)}" class="furniture" '
            f'fill="none" stroke="{stroke}" stroke-width="1.5"{dash}>')
    rect = f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" rx="2"/>'
    parts = [base, rect]
    if kind == "bed":
        parts += [f'<line x1="{fmt(x)}" y1="{fmt(y+h*.22)}" x2="{fmt(x+w)}" y2="{fmt(y+h*.22)}"/>',
                  f'<rect x="{fmt(x+w*.08)}" y="{fmt(y+h*.04)}" width="{fmt(w*.35)}" height="{fmt(h*.14)}" rx="3"/>',
                  f'<rect x="{fmt(x+w*.57)}" y="{fmt(y+h*.04)}" width="{fmt(w*.35)}" height="{fmt(h*.14)}" rx="3"/>']
    elif kind == "sofa":
        parts += [f'<line x1="{fmt(x+w*.12)}" y1="{fmt(y+h*.25)}" x2="{fmt(x+w*.88)}" y2="{fmt(y+h*.25)}"/>',
                  f'<line x1="{fmt(x+w*.5)}" y1="{fmt(y+h*.25)}" x2="{fmt(x+w*.5)}" y2="{fmt(y+h)}"/>']
    elif kind == "table":
        parts += [f'<ellipse cx="{fmt(x+w/2)}" cy="{fmt(y+h/2)}" rx="{fmt(w*.38)}" ry="{fmt(h*.38)}"/>']
    elif kind == "chair":
        parts += [f'<line x1="{fmt(x+w*.15)}" y1="{fmt(y+h*.25)}" x2="{fmt(x+w*.85)}" y2="{fmt(y+h*.25)}"/>']
    elif kind == "cabinet":
        parts += [f'<line x1="{fmt(x+w/2)}" y1="{fmt(y)}" x2="{fmt(x+w/2)}" y2="{fmt(y+h)}"/>']
    elif kind == "sink":
        parts += [f'<ellipse cx="{fmt(x+w/2)}" cy="{fmt(y+h/2)}" rx="{fmt(w*.32)}" ry="{fmt(h*.28)}"/>']
    elif kind == "toilet":
        parts += [f'<rect x="{fmt(x+w*.2)}" y="{fmt(y+h*.05)}" width="{fmt(w*.6)}" height="{fmt(h*.22)}"/>',
                  f'<ellipse cx="{fmt(x+w/2)}" cy="{fmt(y+h*.58)}" rx="{fmt(w*.3)}" ry="{fmt(h*.28)}"/>']
    elif kind == "appliance":
        parts += [f'<circle cx="{fmt(x+w/2)}" cy="{fmt(y+h/2)}" r="{fmt(min(w,h)*.3)}"/>']
    if item.get("label"):
        label_x, label_y = item.get("label_point", [x + w / 2, y + h + 14])
        parts += [f'<text x="{fmt(label_x)}" y="{fmt(label_y)}" text-anchor="middle" fill="#333333" stroke="none" font-family="sans-serif" font-size="11">{esc(item["label"])}</text>']
    parts.append('</g>')
    return "".join(parts)


def build_svg(data: dict[str, Any]) -> str:
    _, _, conflicts = validate(data)
    require(not conflicts, "layout conflicts: " + ", ".join(conflicts))
    base = render_floorplan.build_svg(data["plan"])
    layer = ['<style>.furniture{fill:none;stroke:#444;stroke-width:1.5}.furniture text{fill:#333;stroke:none;font:11px sans-serif}</style>',
             '<g id="furniture" data-layer="furniture">']
    layer.extend(symbol_svg(item) for item in data["furniture"])
    layer.append('</g>')
    return base.replace('</svg>', "\n" + "\n".join(layer) + '\n</svg>')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--svg", type=Path)
    parser.add_argument("--png", type=Path)
    parser.add_argument("--check-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = load_json(args.input)
    width, height, conflicts = validate(data)
    if args.check_only:
        print(json.dumps({"status": "ok" if not conflicts else "conflict", "conflicts": conflicts},
                         ensure_ascii=False, sort_keys=True))
        return 0 if not conflicts else 2
    require(args.svg is not None and args.png is not None, "--svg and --png are required unless --check-only")
    require(not conflicts, "layout conflicts: " + ", ".join(conflicts))
    result = render_pair(build_svg(data), args.svg, args.png, width, height)
    result.update(status="ok", revision=data["revision"], conflicts=[],
                  limitations=["unmeasured clearances and real-world operation remain unverified"])
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
