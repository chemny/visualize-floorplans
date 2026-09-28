#!/usr/bin/env python3
"""Validate floor-plan access topology and an ordered property-tour route."""

from __future__ import annotations

import argparse
import json
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


def validate_topology(data: dict[str, Any], allow_uncertain: bool = False) -> dict[str, Any]:
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
    entry_access = route.get("entry_access")
    exit_access = route.get("exit_access")
    require(entry_access in access_by_id, "tour_route.entry_access is unknown")
    require(exit_access in access_by_id, "tour_route.exit_access is unknown")
    for role, access_id in (("entry", entry_access), ("exit", exit_access)):
        access = access_by_id[access_id]
        require("outside" in access["connects"], f"declared {role} access must connect outside")
        require(access["kind"] in EXTERIOR_ACCESS_KINDS,
                f"declared {role} access has an invalid exterior type")
        if not allow_uncertain:
            require(access["certainty"] == "confirmed", f"declared {role} access is uncertain")

    steps = route.get("steps")
    require(isinstance(steps, list) and len(steps) >= 2,
            "tour_route.steps must include entry and exit steps")
    require([step.get("order") for step in steps] == list(range(1, len(steps) + 1)),
            "route step order must be consecutive starting at 1")
    require(steps[0].get("from") == "outside", "first route step must start outside")
    require(steps[0].get("via") == entry_access, "first route step must use entry_access")
    require(steps[-1].get("to") == "outside", "last route step must end outside")
    require(steps[-1].get("via") == exit_access, "last route step must use exit_access")

    visited: list[str] = []
    for index, step in enumerate(steps):
        require(isinstance(step, dict), f"route step {index + 1} must be an object")
        source = step.get("from")
        target = step.get("to")
        access_id = step.get("via")
        require(source in zone_ids and target in zone_ids,
                f"route step {index + 1} references an unknown zone")
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

    return {
        "status": "ok",
        "zone_count": len(zones),
        "access_point_count": len(access_points),
        "route_step_count": len(steps),
        "entry_access": entry_access,
        "exit_access": exit_access,
        "visited_zones": visited,
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
        print(json.dumps(validate_topology(data, args.allow_uncertain), ensure_ascii=False, indent=2))
        return 0
    except (OSError, json.JSONDecodeError, TopologyError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
