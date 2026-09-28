#!/usr/bin/env python3
"""Compile a client-facing base-plus-adaptive visualization shot list."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from review_contract import required_checks


FEATURE_TYPES = {
    "balcony", "terrace", "garden", "staircase", "double_height",
    "walk_in_closet", "feature_space",
}
SECONDARY_TYPES = {
    "secondary_bedroom", "childrens_room", "study", "multi_function_room",
}
BATH_TYPES = {"bathroom", "shared_bathroom", "primary_bathroom", "powder_room"}
THIRD_BIRDSEYE_TRAITS = {
    "l_shaped", "elongated", "high_occlusion", "split_level", "duplex", "multi_floor",
}


class DeliveryPlanError(ValueError):
    pass


def plan_digest(plan: dict[str, Any]) -> str:
    payload = json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DeliveryPlanError(message)


def slug(value: str) -> str:
    return "".join(character if character.isalnum() else "-" for character in value.lower()).strip("-")


def room_role(room: dict[str, Any]) -> str:
    kind = str(room.get("type", "")).lower()
    name = str(room.get("name", ""))
    if kind in {"living_room", "living_dining", "living_dining_room"} or "客厅" in name or "客餐厅" in name:
        return "living"
    if kind == "kitchen" or "厨房" in name:
        return "kitchen"
    if kind == "primary_bedroom" or "主卧" in name:
        return "primary_bedroom"
    if kind in SECONDARY_TYPES or any(token in name for token in ("次卧", "儿童房", "书房", "多功能")):
        return "secondary"
    if kind in BATH_TYPES or any(token in name for token in ("卫生间", "主卫", "公卫")):
        return "bathroom"
    if kind in FEATURE_TYPES or any(token in name for token in ("阳台", "露台", "花园", "楼梯", "挑空", "衣帽间")):
        return "feature"
    return "other"


def normalized_locks(data: dict[str, Any]) -> list[dict[str, Any]]:
    locks = data.get("structural_locks")
    if isinstance(locks, list) and locks:
        confirmed: list[dict[str, Any]] = []
        seen: set[str] = set()
        for index, lock in enumerate(locks):
            require(isinstance(lock, dict), f"structural lock {index} must be an object")
            lock_id = lock.get("id")
            require(isinstance(lock_id, str) and lock_id.strip(),
                    f"structural lock {index} requires id")
            require(lock_id not in seen, f"duplicate structural lock id: {lock_id}")
            seen.add(lock_id)
            if lock.get("status") != "confirmed":
                continue
            require(isinstance(lock.get("rule"), str) and lock["rule"].strip(),
                    f"structural lock {lock_id} requires rule")
            scope = lock.get("applies_to")
            require(isinstance(scope, list) and scope and
                    all(isinstance(item, str) and item.strip() for item in scope),
                    f"structural lock {lock_id} requires applies_to")
            evidence = lock.get("evidence")
            require(isinstance(evidence, list) and evidence and
                    all(isinstance(item, str) and item.strip() for item in evidence),
                    f"structural lock {lock_id} requires evidence")
            confirmed.append(lock)
        return confirmed
    legacy = data.get("locked_elements", [])
    return [{
        "id": f"legacy-lock-{index + 1}",
        "applies_to": ["all"],
        "rule": statement,
    } for index, statement in enumerate(legacy)
            if isinstance(statement, str) and statement.strip()]


def applicable_locks(locks: list[dict[str, Any]], must_show: list[str]) -> list[dict[str, Any]]:
    visible = set(must_show)
    selected = []
    for lock in locks:
        scope = set(lock.get("applies_to", []))
        if "all" in scope or scope & visible:
            selected.append(lock)
    return selected


def asset(asset_id: str, kind: str, title: str, camera_intent: str,
          must_show: list[str], locks: list[dict[str, Any]], floor: str = "F1",
          adaptive: bool = False) -> dict[str, Any]:
    selected_locks = applicable_locks(locks, must_show)
    return {
        "id": asset_id,
        "kind": kind,
        "title": title,
        "floor": floor,
        "adaptive": adaptive,
        "camera_intent": camera_intent,
        "must_show": must_show,
        "structural_lock_ids": [item["id"] for item in selected_locks],
        "must_not_change": [item["rule"] for item in selected_locks],
        "substitution_policy": "forbidden",
        "status": "planned_preview",
    }


def compile_delivery(data: dict[str, Any]) -> dict[str, Any]:
    require(data.get("interpretation_artifacts", {}).get("status") == "access_confirmed",
            "delivery planning requires access_confirmed")
    require(data.get("design", {}).get("selected_style"),
            "delivery planning requires a selected style")
    rooms = [room for room in data.get("floor_plan", {}).get("rooms", [])
             if room.get("certainty") == "confirmed"]
    require(rooms, "delivery planning requires confirmed rooms")

    config = data.get("delivery", {})
    max_images = int(config.get("max_images", 24))
    require(max_images >= 4, "delivery.max_images must be at least 4")
    featured_ids = set(config.get("featured_room_ids", []))
    omitted_ids = set(config.get("omit_room_ids", []))
    include_bathrooms = bool(config.get("include_bathrooms", False))
    traits = set(data.get("floor_plan", {}).get("layout_traits", []))
    floors = sorted({str(room.get("floor", "F1")) for room in rooms})
    locks = normalized_locks(data)
    require(locks, "delivery planning requires confirmed structural locks")
    all_room_ids = [room["id"] for room in rooms]
    include_structure_reference = bool(config.get("include_structure_reference", True))
    include_furnished_plan = bool(config.get("include_furnished_plan", True))

    assets: list[dict[str, Any]] = []
    if include_structure_reference:
        assets.append(asset(
            "structure-reference-plan", "structure_reference_plan", "结构尺寸基准图",
            "clean orthographic top-down structural reference; no decorative furniture",
            all_room_ids, locks,
        ))
    if include_furnished_plan:
        assets.append(asset(
            "furnished-floor-plan", "furnished_colour_plan", "彩色家具平面图",
            "clean orthographic top-down furnished presentation",
            all_room_ids, locks,
        ))

    for floor in floors:
        floor_rooms = [room for room in rooms if str(room.get("floor", "F1")) == floor]
        room_ids = [room["id"] for room in floor_rooms]
        suffix = "" if len(floors) == 1 else f"-{slug(floor)}"
        assets.append(asset(
            f"primary-birdseye{suffix}", "birdseye", f"{floor} 全屋主鸟瞰",
            "from confirmed entry side toward dominant daylight; 35-45 degree elevation",
            room_ids, locks, floor,
        ))
        assets.append(asset(
            f"complementary-birdseye{suffix}", "birdseye", f"{floor} 全屋补充鸟瞰",
            "reverse or most informative feature side; reveal areas hidden in the primary view",
            room_ids, locks, floor,
        ))
        if traits & THIRD_BIRDSEYE_TRAITS:
            assets.append(asset(
                f"feature-side-birdseye{suffix}", "birdseye", f"{floor} 特征侧鸟瞰",
                "side angle selected only for substantial new visibility",
                room_ids, locks, floor, True,
            ))

    living = next((room for room in rooms if room_role(room) == "living"), None)
    if living:
        assets.extend([
            asset("living-toward-daylight", "room_view", "客厅看向采光面",
                  "eye level near a confirmed entry, looking toward dominant daylight",
                  [living["id"]], locks),
            asset("public-reverse", "room_view", "公共空间反向视角",
                  "eye level from daylight side toward dining and entry",
                  [living["id"]], locks),
        ])

    primary = next((room for room in rooms if room_role(room) == "primary_bedroom"), None)
    if primary:
        assets.append(asset("primary-bedroom", "room_view", "主卧效果图",
                            "eye level near the real bedroom door toward bed, storage, and daylight",
                            [primary["id"]], locks))

    kitchen = next((room for room in rooms if room_role(room) == "kitchen"), None)
    if kitchen:
        assets.append(asset("kitchen", "room_view", "厨房效果图",
                            "eye level showing cabinet run, work triangle, and real opening",
                            [kitchen["id"]], locks))

    for room in rooms:
        room_id = room["id"]
        if room_id in omitted_ids or room in (living, primary, kitchen):
            continue
        role = room_role(room)
        priority = room.get("delivery_priority")
        include = (
            role in {"secondary", "feature"}
            or room_id in featured_ids
            or priority == "featured"
            or (role == "bathroom" and include_bathrooms)
        )
        if not include:
            continue
        assets.append(asset(
            f"room-{slug(room_id)}", "room_view", f'{room["name"]}效果图',
            "eye level near a confirmed access point toward daylight or the primary room feature",
            [room_id], locks, str(room.get("floor", "F1")), True,
        ))

    over_limit = len(assets) > max_images
    return {
        "delivery_plan_version": "0.3",
        "project_id": data.get("project_id"),
        "standard": "base_plus_floorplan_adaptive",
        "product_label": "AI 3D renovation concept image set",
        "accuracy_boundary": "conceptual_not_construction_ready",
        "status": "needs_scope_confirmation" if over_limit else "ready_for_preview",
        "max_images_review_threshold": max_images,
        "asset_count": len(assets),
        "assets": assets,
        "internal_modules": [
            "deliverable_list_planner", "camera_selector",
            "structural_quality_gate", "multi_image_consistency_gate",
        ],
        "approval_gates": [
            "Approve the primary bird's-eye before dependent views",
            "Review the complete preview set as a contact sheet",
            "Pass structural and multi-image consistency review before final export",
        ],
    }


def review_template(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "delivery_review_version": "0.3",
        "project_id": plan["project_id"],
        "delivery_plan_sha256": plan_digest(plan),
        "assets": [{
            "id": item["id"],
            "planned_kind": item["kind"],
            "actual_kind": "",
            "path": "",
            "authority_refs": [],
            "image_sha256": "",
            "authority_sha256": {},
            "inspection_method": "",
            "observations": "",
            "issues": [],
            "exception": None,
            "hard_checks": {name: {"passed":None,"evidence":""} for name in sorted(required_checks(item["kind"]))},
        } for item in plan["assets"]],
        "package_consistency": {
            "style_consistent": {"passed": None, "evidence": ""},
            "materials_consistent": {"passed": None, "evidence": ""},
            "furniture_consistent": {"passed": None, "evidence": ""},
            "opening_geometry_consistent": {"passed": None, "evidence": ""},
            "lighting_consistent": {"passed": None, "evidence": ""},
        },
        "exceptions": [],
        "notes": [],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = json.loads(args.manifest.expanduser().read_text(encoding="utf-8"))
        plan = compile_delivery(data)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        plan_path = args.output_dir / "delivery-plan.json"
        review_path = args.output_dir / "delivery-review-template.json"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        review_path.write_text(json.dumps(review_template(plan), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "ok", "asset_count": plan["asset_count"],
                          "plan": str(plan_path.resolve()), "review": str(review_path.resolve()),
                          "external_api_called": False}, ensure_ascii=False))
        return 0
    except (OSError, json.JSONDecodeError, DeliveryPlanError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
