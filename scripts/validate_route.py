#!/usr/bin/env python3
"""Validate floor-plan access topology and an ordered property-tour route."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


TRAVERSABLE_KINDS = {
    "entrance_door",
    "interior_door",
    "sliding_door",
    "balcony_door",
    "open_passage",
    "confirmed_opening",
    "stair",
}
EXTERIOR_ACCESS_KINDS = {"entrance_door", "balcony_door", "confirmed_opening", "stair"}
CERTAINTIES = {"confirmed", "uncertain"}
ROUTE_MODES = {"full_tour", "indoor_segment", "entry_to_interior"}


class TopologyError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise TopologyError(message)


def require_evidence(item: dict[str, Any], label: str) -> None:
    evidence = item.get("evidence")
    require(
        isinstance(evidence, list)
        and bool(evidence)
        and all(isinstance(value, str) and value.strip() for value in evidence),
        f"{label} requires non-empty evidence",
    )


def valid_point(value: Any) -> bool:
    return (
        isinstance(value, (list, tuple))
        and len(value) == 2
        and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                and math.isfinite(v) for v in value)
    )


def point_in_polygon(point: tuple[float, float], polygon: list[list[float]]) -> bool:
    x, y = point
    inside = False
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        ax, ay = a
        bx, by = b
        cross = (x - ax) * (by - ay) - (y - ay) * (bx - ax)
        if abs(cross) < 1e-7 and min(ax, bx) <= x <= max(ax, bx) and min(ay, by) <= y <= max(ay, by):
            return True
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
            inside = not inside
    return inside


def check_indoor_geometry(data: dict[str, Any], recognition: dict[str, Any]) -> str:
    route = data["tour_route"]
    points = data["route_render_points"]
    polygons = {zone.get("id"): zone.get("render_polygon") for zone in recognition.get("zones", [])}
    start_polygon = polygons.get(route["start_zone"])
    end_polygon = polygons.get(route["end_zone"])
    require(isinstance(start_polygon, list) and len(start_polygon) >= 3,
            "recognition lacks start-zone polygon")
    require(isinstance(end_polygon, list) and len(end_polygon) >= 3,
            "recognition lacks end-zone polygon")
    require(all(valid_point(p) for p in start_polygon + end_polygon),
            "recognition has invalid zone polygon coordinates")
    require(point_in_polygon(tuple(points[0]), start_polygon),
            "indoor route start point is outside start zone")
    require(point_in_polygon(tuple(points[-1]), end_polygon),
            "indoor route end point is outside end zone")
    if route["start_zone"] != route["end_zone"]:
        return "endpoints_only; opening and obstacle geometry require visual review"
    for start, end in zip(points, points[1:]):
        length = math.dist(start, end)
        for index in range(math.ceil(length) + 1):
            fraction = index / max(1, math.ceil(length))
            sample = (start[0] + (end[0] - start[0]) * fraction,
                      start[1] + (end[1] - start[1]) * fraction)
            require(point_in_polygon(sample, start_polygon),
                    "indoor route leaves its zone polygon")
    return "same_zone_polygon; furniture clearance requires visual review"


def validate_topology(data: dict[str, Any], allow_uncertain: bool = False,
                      recognition: dict[str, Any] | None = None) -> dict[str, Any]:
    zones = data.get("zones")
    require(isinstance(zones, list) and zones, "zones must contain at least one zone")

    zone_ids: set[str] = set()
    for index, zone in enumerate(zones):
        require(isinstance(zone, dict), f"zone {index} must be an object")
        zone_id = zone.get("id")
        require(isinstance(zone_id, str) and zone_id.strip(), f"zone {index} requires id")
        require(zone_id not in zone_ids, f"duplicate zone id: {zone_id}")
        zone_ids.add(zone_id)
        require(bool(zone.get("label")), f"zone {zone_id} requires label")
        require(bool(zone.get("kind")), f"zone {zone_id} requires kind")
        require(zone.get("certainty") in CERTAINTIES, f"zone {zone_id} has invalid certainty")
        require_evidence(zone, f"zone {zone_id}")

    require("outside" in zone_ids, "zones must include the special outside node")

    access_points = data.get("access_points")
    require(isinstance(access_points, list) and access_points, "access_points must not be empty")
    access_by_id: dict[str, dict[str, Any]] = {}
    for index, access in enumerate(access_points):
        require(isinstance(access, dict), f"access point {index} must be an object")
        access_id = access.get("id")
        require(isinstance(access_id, str) and access_id.strip(), f"access point {index} requires id")
        require(access_id not in access_by_id, f"duplicate access point id: {access_id}")
        access_by_id[access_id] = access
        require(access.get("kind") in TRAVERSABLE_KINDS,
                f"access point {access_id} is not a traversable type")
        connects = access.get("connects")
        require(isinstance(connects, list) and len(connects) == 2,
                f"access point {access_id} must connect exactly two zones")
        require(connects[0] != connects[1], f"access point {access_id} must connect distinct zones")
        require(all(zone_id in zone_ids for zone_id in connects),
                f"access point {access_id} references an unknown zone")
        require(access.get("certainty") in CERTAINTIES,
                f"access point {access_id} has invalid certainty")
        require_evidence(access, f"access point {access_id}")

    route = data.get("tour_route")
    require(isinstance(route, dict), "tour_route must be an object")
    mode = route.get("mode", "full_tour")
    require(mode in ROUTE_MODES,
            "tour_route.mode must be full_tour, indoor_segment, or entry_to_interior")
    entry_access = exit_access = None
    if mode in {"full_tour", "entry_to_interior"}:
        entry_access = route.get("entry_access")
        require(entry_access in access_by_id, "tour_route.entry_access is unknown")
        if mode == "full_tour":
            exit_access = route.get("exit_access")
            require(exit_access in access_by_id, "tour_route.exit_access is unknown")
            exterior_accesses = (("entry", entry_access), ("exit", exit_access))
        else:
            require("exit_access" not in route,
                    "entry-to-interior route must not declare exterior exit access")
            end_zone = route.get("end_zone")
            require(end_zone in zone_ids and end_zone != "outside",
                    "entry-to-interior end_zone must be an interior zone")
            if not allow_uncertain:
                zones_by_id = {zone["id"]: zone for zone in zones}
                require(zones_by_id[end_zone]["certainty"] == "confirmed",
                        "entry-to-interior end_zone is uncertain")
            exterior_accesses = (("entry", entry_access),)
        for role, access_id in exterior_accesses:
            access = access_by_id[access_id]
            require("outside" in access["connects"], f"declared {role} access must connect outside")
            require(access["kind"] in EXTERIOR_ACCESS_KINDS,
                    f"declared {role} access has an invalid exterior type")
            if not allow_uncertain:
                require(access["certainty"] == "confirmed", f"declared {role} access is uncertain")
    if mode == "indoor_segment":
        require("entry_access" not in route and "exit_access" not in route,
                "indoor segment must not declare exterior entry or exit access")
        for endpoint in ("start_zone", "end_zone"):
            zone_id = route.get(endpoint)
            require(zone_id in zone_ids and zone_id != "outside",
                    f"indoor segment {endpoint} must be an interior zone")
        if not allow_uncertain:
            zones_by_id = {zone["id"]: zone for zone in zones}
            for endpoint in ("start_zone", "end_zone"):
                require(zones_by_id[route[endpoint]]["certainty"] == "confirmed",
                        f"indoor segment {endpoint} is uncertain")
        points = data.get("route_render_points")
        require(isinstance(points, list) and len(points) >= 2
                and all(valid_point(p) for p in points),
                "indoor segment requires at least two finite route_render_points")
        require(points[0] != points[-1], "indoor segment start and end points must differ")
        require(all(a != b for a, b in zip(points, points[1:])),
                "indoor segment has duplicate consecutive route points")

    steps = route.get("steps")
    require(isinstance(steps, list) and all(isinstance(step, dict) for step in steps),
            "tour_route.steps must be a list of objects")
    if mode == "full_tour":
        require(len(steps) >= 2, "tour_route.steps must include entry and exit steps")
    elif mode == "entry_to_interior":
        require(len(steps) >= 1, "entry-to-interior route requires entry and interior steps")
    else:
        require(steps or route["start_zone"] == route["end_zone"],
                "cross-zone indoor segment requires access steps")
    require([step.get("order") for step in steps] == list(range(1, len(steps) + 1)),
            "route step order must be consecutive starting at 1")
    if mode == "full_tour":
        require(steps[0].get("from") == "outside", "first route step must start outside")
        require(steps[0].get("via") == entry_access, "first route step must use entry_access")
        require(steps[-1].get("to") == "outside", "last route step must end outside")
        require(steps[-1].get("via") == exit_access, "last route step must use exit_access")
    elif mode == "entry_to_interior":
        require(steps[0].get("from") == "outside", "first route step must start outside")
        require(steps[0].get("via") == entry_access,
                "first route step must use entry_access")
        require(steps[-1].get("to") == route["end_zone"],
                "last route step must end at end_zone")
    elif steps:
        require(steps[0].get("from") == route["start_zone"],
                "first indoor step must start at start_zone")
        require(steps[-1].get("to") == route["end_zone"],
                "last indoor step must end at end_zone")

    visited: list[str] = []
    for index, step in enumerate(steps):
        require(isinstance(step, dict), f"route step {index + 1} must be an object")
        source = step.get("from")
        target = step.get("to")
        access_id = step.get("via")
        require(source in zone_ids and target in zone_ids,
                f"route step {index + 1} references an unknown zone")
        if mode == "indoor_segment":
            require(source != "outside" and target != "outside",
                    f"indoor route step {index + 1} cannot visit outside")
        if mode == "entry_to_interior" and index > 0:
            require(source != "outside" and target != "outside",
                    f"entry-to-interior step {index + 1} cannot return outside")
        require(access_id in access_by_id, f"route step {index + 1} uses unknown access point")
        access = access_by_id[access_id]
        require(access["kind"] in TRAVERSABLE_KINDS,
                f"route step {index + 1} uses a non-traversable element")
        if not allow_uncertain:
            require(access["certainty"] == "confirmed",
                    f"route step {index + 1} uses uncertain access point {access_id}")
        require(set(access["connects"]) == {source, target},
                f"route step {index + 1} access point {access_id} does not connect {source} and {target}")
        if index > 0:
            require(steps[index - 1].get("to") == source,
                    f"route is discontinuous between steps {index} and {index + 1}")
        if target != "outside":
            visited.append(target)

    required_visit_zones = route.get("required_visit_zones", [])
    if mode in {"entry_to_interior", "full_tour"}:
        require(isinstance(required_visit_zones, list)
                and (mode != "entry_to_interior" or required_visit_zones),
                "required_visit_zones must be a list; entry-to-interior route requires visits")
        require(all(zone_id in zone_ids and zone_id != "outside"
                    for zone_id in required_visit_zones),
                "required_visit_zones contains an unknown or exterior zone")
        require(len(set(required_visit_zones)) == len(required_visit_zones),
                "required_visit_zones contains duplicates")
        require(set(required_visit_zones) <= set(visited),
                "route misses a required visit zone")

    access_counts: dict[str, int] = {}
    for step in steps:
        access_id = step["via"]
        access_counts[access_id] = access_counts.get(access_id, 0) + 1
    repeated_access = {key: value for key, value in access_counts.items() if value > 1}

    geometry_check = "not requested"
    if mode == "indoor_segment" and recognition is not None:
        geometry_check = check_indoor_geometry(data, recognition)

    return {
        "status": "ok",
        "route_mode": mode,
        "zone_count": len(zones),
        "access_point_count": len(access_points),
        "route_step_count": len(steps),
        "entry_access": entry_access,
        "exit_access": exit_access,
        "visited_zones": visited,
        "repeated_access": repeated_access,
        "allow_uncertain": allow_uncertain,
        "geometry_check": geometry_check,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topology", required=True, type=Path)
    parser.add_argument("--allow-uncertain", action="store_true")
    parser.add_argument("--recognition", type=Path,
                        help="Recognition JSON with zone polygons for indoor route geometry checks")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = json.loads(args.topology.read_text(encoding="utf-8"))
        recognition = (json.loads(args.recognition.read_text(encoding="utf-8"))
                       if args.recognition else None)
        print(json.dumps(validate_topology(data, args.allow_uncertain, recognition), ensure_ascii=False, indent=2))
        return 0
    except (OSError, json.JSONDecodeError, TopologyError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
