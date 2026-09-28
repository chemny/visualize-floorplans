#!/usr/bin/env python3
"""Validate confirmed room access, door operation, and whole-home connectivity."""

from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path
from typing import Any


TRAVERSABLE_KINDS = {
    "entrance_door", "interior_door", "sliding_door", "balcony_door",
    "open_passage", "confirmed_opening", "stair",
}
SWING_DOOR_KINDS = {"entrance_door", "interior_door", "balcony_door"}
CERTAINTIES = {"confirmed", "uncertain"}


class AccessError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AccessError(message)


def require_evidence(item: dict[str, Any], label: str) -> None:
    evidence = item.get("evidence")
    require(
        isinstance(evidence, list)
        and bool(evidence)
        and all(isinstance(value, str) and value.strip() for value in evidence),
        f"{label} requires non-empty evidence",
    )


def validate_access(data: dict[str, Any], allow_uncertain: bool = False) -> dict[str, Any]:
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
    access_ids: set[str] = set()
    graph: dict[str, set[str]] = {zone_id: set() for zone_id in zone_ids}
    for index, access in enumerate(access_points):
        require(isinstance(access, dict), f"access point {index} must be an object")
        access_id = access.get("id")
        require(isinstance(access_id, str) and access_id.strip(), f"access point {index} requires id")
        require(access_id not in access_ids, f"duplicate access point id: {access_id}")
        access_ids.add(access_id)
        kind = access.get("kind")
        require(kind in TRAVERSABLE_KINDS, f"access point {access_id} has invalid kind")
        connects = access.get("connects")
        require(isinstance(connects, list) and len(connects) == 2,
                f"access point {access_id} must connect exactly two zones")
        require(connects[0] != connects[1], f"access point {access_id} must connect distinct zones")
        require(all(zone_id in zone_ids for zone_id in connects),
                f"access point {access_id} references an unknown zone")
        certainty = access.get("certainty")
        require(certainty in CERTAINTIES, f"access point {access_id} has invalid certainty")
        require_evidence(access, f"access point {access_id}")
        if not allow_uncertain:
            require(certainty == "confirmed", f"access point {access_id} is uncertain")

        if kind in SWING_DOOR_KINDS:
            require(isinstance(access.get("hinge_location"), str) and access["hinge_location"].strip(),
                    f"swing door {access_id} requires hinge_location")
            require(access.get("swing_into") in connects,
                    f"swing door {access_id} swing_into must name a connected zone")
        elif kind == "sliding_door":
            require(access.get("slide_axis") in {"horizontal", "vertical"},
                    f"sliding door {access_id} requires horizontal or vertical slide_axis")
            require(isinstance(access.get("panel_evidence"), str) and access["panel_evidence"].strip(),
                    f"sliding door {access_id} requires panel_evidence")

        if certainty == "confirmed" or allow_uncertain:
            left, right = connects
            graph[left].add(right)
            graph[right].add(left)

    reached = {"outside"}
    queue: deque[str] = deque(["outside"])
    while queue:
        current = queue.popleft()
        for neighbor in graph[current] - reached:
            reached.add(neighbor)
            queue.append(neighbor)
    unreachable = sorted(zone_ids - reached)
    require(not unreachable, f"zones lack confirmed access from outside: {', '.join(unreachable)}")

    return {
        "status": "ok",
        "zone_count": len(zones),
        "access_point_count": len(access_points),
        "reachable_zone_count": len(reached),
        "allow_uncertain": allow_uncertain,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topology", required=True, type=Path)
    parser.add_argument("--allow-uncertain", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = json.loads(args.topology.read_text(encoding="utf-8"))
        print(json.dumps(validate_access(data, args.allow_uncertain), ensure_ascii=False, indent=2))
        return 0
    except (OSError, json.JSONDecodeError, AccessError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
