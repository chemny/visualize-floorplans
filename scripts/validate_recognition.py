#!/usr/bin/env python3
"""Validate evidence-based architectural floor-plan recognition artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


LINE_KINDS = {
    "solid_wall", "outlined_wall", "column", "dashed_auxiliary",
    "dimension_line", "annotation", "unknown_line",
}
ELEMENT_KINDS = {
    "entrance_door", "interior_door", "sliding_door", "balcony_door",
    "open_passage", "door_candidate", "window", "bay_window", "fixed_glazing", "unknown_gap",
    "shaft", "sanitary_fixture", "drain", "flue", "counter",
}
TRAVERSABLE = {
    "entrance_door", "interior_door", "sliding_door", "balcony_door",
    "open_passage",
}
DOOR_KINDS = {
    "entrance_door", "interior_door", "sliding_door", "balcony_door",
}
DOOR_SIGNALS = {
    "explicit_label", "user_confirmed", "door_leaf", "swing_arc",
    "sliding_panels",
}
WINDOW_SIGNALS = {"explicit_label", "parallel_frame_lines"}
BAY_PROJECTION_SIGNALS = {"exterior_projection"}
BAY_FRAME_SIGNALS = {"parallel_frame_lines", "sill_or_ledge", "explicit_label"}
PASSAGE_SIGNALS = {"explicit_label", "user_confirmed", "clear_walkable_gap"}
CERTAINTIES = {"confirmed", "probable", "uncertain"}


class RecognitionError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RecognitionError(message)


def evidence_codes(item: dict[str, Any], label: str) -> set[str]:
    values = item.get("evidence_codes")
    require(
        isinstance(values, list)
        and bool(values)
        and all(isinstance(value, str) and value.strip() for value in values),
        f"{label} requires non-empty evidence_codes",
    )
    return set(values)


def validate_recognition(data: dict[str, Any]) -> dict[str, Any]:
    require(data.get("schema_version") == "0.2", "schema_version must be 0.2")
    require(bool(data.get("source_image")), "source_image is required")

    linework = data.get("linework")
    require(isinstance(linework, list), "linework must be a list")
    line_ids: set[str] = set()
    for index, line in enumerate(linework):
        require(isinstance(line, dict), f"linework {index} must be an object")
        line_id = line.get("id")
        require(isinstance(line_id, str) and line_id, f"linework {index} requires id")
        require(line_id not in line_ids, f"duplicate linework id: {line_id}")
        line_ids.add(line_id)
        kind = line.get("kind")
        require(kind in LINE_KINDS, f"linework {line_id} has invalid kind")
        require(isinstance(line.get("physical"), bool), f"linework {line_id} requires physical")
        evidence_codes(line, f"linework {line_id}")
        if kind in {"dashed_auxiliary", "dimension_line", "annotation"}:
            require(not line["physical"], f"{kind} {line_id} cannot be physical by default")

    elements = data.get("elements")
    require(isinstance(elements, list), "elements must be a list")
    element_ids: set[str] = set()
    for index, element in enumerate(elements):
        require(isinstance(element, dict), f"element {index} must be an object")
        element_id = element.get("id")
        require(isinstance(element_id, str) and element_id, f"element {index} requires id")
        require(element_id not in element_ids, f"duplicate element id: {element_id}")
        element_ids.add(element_id)
        kind = element.get("kind")
        require(kind in ELEMENT_KINDS, f"element {element_id} has invalid kind")
        require(element.get("certainty") in CERTAINTIES,
                f"element {element_id} has invalid certainty")
        codes = evidence_codes(element, f"element {element_id}")
        traversable = element.get("traversable")
        require(isinstance(traversable, bool), f"element {element_id} requires traversable")
        require(traversable == (kind in TRAVERSABLE),
                f"element {element_id} traversable conflicts with kind {kind}")

        if kind in DOOR_KINDS:
            require(bool(codes & DOOR_SIGNALS),
                    f"door {element_id} lacks door symbol or user confirmation")
        elif kind == "window":
            require(bool(codes & WINDOW_SIGNALS),
                    f"window {element_id} lacks window-frame evidence")
        elif kind == "bay_window":
            require(bool(codes & BAY_PROJECTION_SIGNALS),
                    f"bay window {element_id} lacks exterior projection evidence")
            require(bool(codes & BAY_FRAME_SIGNALS),
                    f"bay window {element_id} lacks frame or sill evidence")
        elif kind == "open_passage":
            require(bool(codes & PASSAGE_SIGNALS),
                    f"open passage {element_id} lacks walkable-passage evidence")
        elif kind == "door_candidate":
            require("bounded_polygon" in codes and "adjacency" in codes,
                    f"door candidate {element_id} lacks bounded-zone adjacency evidence")

    zones = data.get("zones")
    require(isinstance(zones, list) and zones, "zones must not be empty")
    zone_ids: set[str] = set()
    for index, zone in enumerate(zones):
        require(isinstance(zone, dict), f"zone {index} must be an object")
        zone_id = zone.get("id")
        require(isinstance(zone_id, str) and zone_id, f"zone {index} requires id")
        require(zone_id not in zone_ids, f"duplicate zone id: {zone_id}")
        zone_ids.add(zone_id)
        require(zone.get("certainty") in CERTAINTIES, f"zone {zone_id} has invalid certainty")
        codes = evidence_codes(zone, f"zone {zone_id}")
        if zone_id != "outside":
            require("bounded_polygon" in codes,
                    f"zone {zone_id} lacks bounded_polygon geometry evidence")
        require(bool(zone.get("proposed_function")), f"zone {zone_id} requires proposed_function")

    return {
        "status": "ok",
        "linework_count": len(linework),
        "element_count": len(elements),
        "zone_count": len(zones),
        "traversable_element_count": sum(
            1 for item in elements if item["kind"] in TRAVERSABLE
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recognition", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = json.loads(args.recognition.read_text(encoding="utf-8"))
        print(json.dumps(validate_recognition(data), ensure_ascii=False, indent=2))
        return 0
    except (OSError, json.JSONDecodeError, RecognitionError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
