#!/usr/bin/env python3
"""Validate a V0 floor-plan manifest and compile an Image 2 dry-run plan."""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Any

from delivery_state import atomic_write, build_initial_state, validate_state
from interpretation_authority import validate_bundle
from design_contract import chosen_style, design_block as shared_design_block, digest as design_digest


ALLOWED_MODES = {"conceptual", "structure_verified"}
ALLOWED_USE_CASES = {"renovation", "property_viewing", "real_estate_marketing"}
ALLOWED_QUALITY = {"low", "medium", "high", "auto"}
ALLOWED_FORMAT = {"png", "jpeg", "webp"}
STYLE_OPTION_IDS = {
    "modern_minimal", "wood_cream", "modern_luxury", "modern_chinese",
    "midcentury_modern", "song_eastern", "contemporary_french", "italian_luxury",
    "champagne_pearl", "milan_greige", "paris_art_deco", "sculptural_cream",
}
LOCK_KINDS = {
    "room_count", "wall", "door", "sliding_door", "opening", "window",
    "bay_window", "adjacency", "projection", "other",
}
LOCK_SOURCES = {
    "original_plan", "confirmed_2d", "confirmed_access", "user_confirmation",
}
PROJECT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class ManifestError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ManifestError(message)


def validate_size(size: str) -> None:
    match = re.fullmatch(r"(\d+)x(\d+)", size)
    require(match is not None, "outputs.size must use WIDTHxHEIGHT")
    width, height = (int(value) for value in match.groups())
    require(width % 16 == 0 and height % 16 == 0, "output edges must be multiples of 16")
    require(max(width, height) <= 3840, "maximum output edge is 3840 pixels")
    require(max(width, height) / min(width, height) <= 3, "output aspect ratio must not exceed 3:1")
    pixels = width * height
    require(655_360 <= pixels <= 8_294_400, "output pixel count is outside GPT Image 2 limits")


def structural_locks(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return normalized structural locks, preserving v0.2 compatibility."""
    if data.get("schema_version") == "0.2":
        legacy = data.get("locked_elements")
        require(isinstance(legacy, list) and len(legacy) >= 3,
                "locked_elements must contain at least three structural constraints")
        require(all(isinstance(item, str) and item.strip() for item in legacy),
                "locked_elements entries must be non-empty strings")
        return [{
            "id": f"legacy-lock-{index + 1}",
            "kind": "other",
            "applies_to": ["all"],
            "rule": item,
            "source": "user_confirmation",
            "evidence": ["legacy schema 0.2 locked_elements"],
            "status": "confirmed",
        } for index, item in enumerate(legacy)]

    locks = data.get("structural_locks")
    require(isinstance(locks, list) and len(locks) >= 3,
            "structural_locks must contain at least three confirmed locks")
    lock_ids: set[str] = set()
    for index, lock in enumerate(locks):
        require(isinstance(lock, dict), f"structural lock {index} must be an object")
        lock_id = lock.get("id")
        require(isinstance(lock_id, str) and lock_id.strip(),
                f"structural lock {index} requires id")
        require(lock_id not in lock_ids, f"duplicate structural lock id: {lock_id}")
        lock_ids.add(lock_id)
        require(lock.get("kind") in LOCK_KINDS,
                f"structural lock {lock_id} kind must be one of {sorted(LOCK_KINDS)}")
        applies_to = lock.get("applies_to")
        require(isinstance(applies_to, list) and applies_to and
                all(isinstance(item, str) and item.strip() for item in applies_to),
                f"structural lock {lock_id} requires non-empty applies_to")
        require(isinstance(lock.get("rule"), str) and lock["rule"].strip(),
                f"structural lock {lock_id} requires rule")
        require(lock.get("source") in LOCK_SOURCES,
                f"structural lock {lock_id} source must be one of {sorted(LOCK_SOURCES)}")
        evidence = lock.get("evidence")
        require(isinstance(evidence, list) and evidence and
                all(isinstance(item, str) and item.strip() for item in evidence),
                f"structural lock {lock_id} requires evidence")
        require(lock.get("status") == "confirmed",
                f"structural lock {lock_id} must be confirmed")
    return locks


def validate_interpretation_confirmation(data: dict[str, Any]) -> None:
    """Require current, scoped user confirmation before renovation planning."""
    interpretation = data.get("interpretation_artifacts")
    require(isinstance(interpretation, dict),
            "interpretation_artifacts must be an object")
    require(interpretation.get("status") == "access_confirmed",
            "renovation planning requires confirmed structure, zones, and access elements")

    # Schema 0.2 stays readable for existing projects. New schema 0.3 manifests
    # must carry evidence that cannot be inferred from a status string alone.
    if data.get("schema_version") == "0.2":
        return

    artifact_version = interpretation.get("artifact_version")
    require(isinstance(artifact_version, str) and artifact_version.strip(),
            "interpretation_artifacts.artifact_version is required")
    confirmation = interpretation.get("confirmation")
    require(isinstance(confirmation, dict),
            "interpretation_artifacts.confirmation is required")
    require(confirmation.get("confirmed_version") == artifact_version,
            "floor-plan confirmation does not match the current artifact version")
    require(isinstance(confirmation.get("confirmed_by"), str) and
            confirmation["confirmed_by"].strip(),
            "floor-plan confirmation requires confirmed_by")
    require(confirmation.get("approval_source") == "explicit_user_confirmation",
            "floor-plan confirmation requires explicit_user_confirmation")

    scopes = confirmation.get("scopes")
    require(isinstance(scopes, dict), "floor-plan confirmation scopes are required")
    for scope_name in ("structure_and_zones", "access_elements"):
        scope = scopes.get(scope_name)
        require(isinstance(scope, dict),
                f"floor-plan confirmation scope {scope_name} is required")
        require(scope.get("status") == "confirmed",
                f"floor-plan confirmation scope {scope_name} is not confirmed")
        item_ids = scope.get("confirmed_item_ids")
        require(isinstance(item_ids, list) and item_ids and
                all(isinstance(item, str) and item.strip() for item in item_ids),
                f"floor-plan confirmation scope {scope_name} requires confirmed item IDs")
        evidence = scope.get("evidence")
        require(isinstance(evidence, list) and evidence and
                all(isinstance(item, str) and item.strip() for item in evidence),
                f"floor-plan confirmation scope {scope_name} requires review evidence")

    unresolved = confirmation.get("unresolved_items")
    require(isinstance(unresolved, list) and
            all(isinstance(item, str) and item.strip() for item in unresolved),
            "floor-plan confirmation unresolved_items must be a list of non-empty strings")
    require(not unresolved,
            "consequential floor-plan confirmation items remain unresolved")


def validate_manifest(data: dict[str, Any], manifest_path: Path, allow_missing_input: bool) -> Path:
    require(data.get("schema_version") in {"0.2", "0.3"},
            "schema_version must be 0.2 or 0.3")
    project_id = data.get("project_id", "")
    require(isinstance(project_id, str) and PROJECT_ID_RE.fullmatch(project_id) is not None,
            "project_id must contain lowercase letters, digits, hyphens, or underscores")
    require(data.get("mode") in ALLOWED_MODES, f"mode must be one of {sorted(ALLOWED_MODES)}")
    require(data.get("use_case") in ALLOWED_USE_CASES,
            f"use_case must be one of {sorted(ALLOWED_USE_CASES)}")

    image_value = data.get("input_image")
    require(isinstance(image_value, str) and image_value.strip(), "input_image is required")
    image_path = Path(image_value).expanduser()
    if not image_path.is_absolute():
        image_path = (manifest_path.parent / image_path).resolve()
    if not allow_missing_input:
        require(image_path.is_file(), f"input image not found: {image_path}")

    floor_plan = data.get("floor_plan")
    require(isinstance(floor_plan, dict), "floor_plan must be an object")
    rooms = floor_plan.get("rooms")
    require(isinstance(rooms, list) and rooms, "floor_plan.rooms must contain at least one room")
    room_ids: set[str] = set()
    for index, room in enumerate(rooms):
        require(isinstance(room, dict), f"room {index} must be an object")
        room_id = room.get("id")
        require(isinstance(room_id, str) and room_id, f"room {index} requires id")
        require(room_id not in room_ids, f"duplicate room id: {room_id}")
        room_ids.add(room_id)
        require(bool(room.get("name")), f"room {room_id} requires name")
        require(room.get("certainty") in {"confirmed", "uncertain"},
                f"room {room_id} certainty must be confirmed or uncertain")

    structural_locks(data)

    validate_interpretation_confirmation(data)
    interpretation = data["interpretation_artifacts"]
    for field in ("topdown_base", "topdown_base_svg", "access_map", "topology"):
        require(isinstance(interpretation.get(field), str) and interpretation[field].strip(),
                f"interpretation_artifacts.{field} is required")

    design = data.get("design")
    require(isinstance(design, dict), "design must be an object")
    style_options = design.get("style_options")
    require(isinstance(style_options, list) and len(style_options) in {4, 8, 12},
            "design.style_options must contain 4, 8 or 12 styles (new-project default: 12)")
    style_ids: set[str] = set()
    for index, option in enumerate(style_options):
        require(isinstance(option, dict), f"style option {index} must be an object")
        style_id = option.get("id")
        require(isinstance(style_id, str) and style_id, f"style option {index} requires id")
        require(style_id not in style_ids, f"duplicate style option id: {style_id}")
        style_ids.add(style_id)
        require(bool(option.get("name")), f"style option {style_id} requires name")
        for field in ("palette", "materials"):
            values = option.get(field)
            require(isinstance(values, list) and values,
                    f"style option {style_id} requires non-empty {field}")
    require(style_ids <= STYLE_OPTION_IDS,
            f"style option ids must come from {sorted(STYLE_OPTION_IDS)}")
    selected_style = design.get("selected_style")
    require(selected_style is None or selected_style in style_ids or selected_style == "custom",
            "design.selected_style must be null, a default ID, or custom")
    if selected_style is not None:
        try:
            chosen_style(design)
        except ValueError as exc:
            raise ManifestError(str(exc)) from exc
    for field in ("requirements", "preserve_furniture", "reference_images", "palette", "materials"):
        values = design.get(field, [])
        require(isinstance(values,list) and all(isinstance(v,str) and v.strip() for v in values),
                f"design.{field} must be a list of non-empty strings")
    room_schemes = design.get("room_schemes", {})
    require(isinstance(room_schemes,dict) and set(room_schemes) <= room_ids,
            "design.room_schemes must reference known room IDs")
    require(all(isinstance(v,dict) and v for v in room_schemes.values()), "room schemes must be non-empty objects")
    scheme = design.get("scheme", {})
    require(isinstance(scheme,dict), "design.scheme must be an object")
    outputs = data.get("outputs")
    require(isinstance(outputs, dict), "outputs must be an object")
    require(outputs.get("style_preview") in {None,"four_style_grid","style_comparison_boards"},
            "outputs.style_preview must be null, four_style_grid or style_comparison_boards")
    require(outputs.get("style_preview") != "four_style_grid" or len(style_options) == 4,
            "four_style_grid requires four options; use style_comparison_boards for expanded selection")
    require(selected_style is not None or outputs.get("style_preview") in {"four_style_grid","style_comparison_boards"},
            "specify a style or request the comparison board before planning")
    require(outputs.get("canonical_view") == "cutaway_birdseye",
            "V0 canonical_view must be cutaway_birdseye")
    require(outputs.get("quality") in ALLOWED_QUALITY,
            f"outputs.quality must be one of {sorted(ALLOWED_QUALITY)}")
    require(outputs.get("format") in ALLOWED_FORMAT,
            f"outputs.format must be one of {sorted(ALLOWED_FORMAT)}")
    validate_size(str(outputs.get("size", "")))
    for field in ("room_views", "style_variants"):
        require(isinstance(outputs.get(field), list), f"outputs.{field} must be a list")
    if not allow_missing_input:
        try:
            validate_bundle(data, manifest_path)
        except ValueError as exc:
            raise ManifestError(str(exc)) from exc
    return image_path


def lines(values: list[str]) -> str:
    return "\n".join(f"- {value}" for value in values) if values else "- None provided"


def completion_constraints(data):
    items = data.get("input_assessment", {}).get("items", [])
    return "Accepted input completions (hypotheses, not measured source facts):\n" + lines([
        f"[{item['id']}] {item['description']}; preserve exactly as shown in the confirmed reconstructed plan"
        for item in items if item.get("origin") == "hypothesis"
    ])


def delivery_structural_block(data: dict[str, Any]) -> str:
    rooms = data["floor_plan"]["rooms"]
    room_summary = [
        f'{room["name"]} ({room.get("type", "unspecified")}, {room["certainty"]})'
        for room in rooms
    ]
    relationships = data["floor_plan"].get("relationships", [])
    locked = [
        f'[{item["id"]}] {item["rule"]}' for item in structural_locks(data)
    ]
    return f"""Confirmed or declared rooms:\n{lines(room_summary)}

Spatial relationships:\n{lines(relationships)}

Locked structural requirements:\n{lines(locked)}

{completion_constraints(data)}

Hard constraints:
- Do not add, remove, merge, or split rooms.
- Do not move visible walls, doors, or windows.
- Do not invent measurements or construction details.
- Produce an AI concept image, not a construction drawing or precise 3D model.
- No watermark, logo, plan labels, or generated annotations."""


def validate_delivery_plan(data: dict[str, Any], plan: dict[str, Any]) -> None:
    require(plan.get("delivery_plan_version") == "0.3",
            "linked delivery plan must use version 0.3")
    require(plan.get("project_id") == data.get("project_id"),
            "delivery plan project_id must match manifest project_id")
    assets = plan.get("assets")
    require(isinstance(assets, list) and assets,
            "delivery plan must contain at least one asset")
    known_lock_ids = {item["id"] for item in structural_locks(data)}
    asset_ids: set[str] = set()
    for index, item in enumerate(assets):
        require(isinstance(item, dict), f"delivery asset {index} must be an object")
        asset_id = item.get("id")
        require(isinstance(asset_id, str) and asset_id.strip(),
                f"delivery asset {index} requires id")
        require(asset_id not in asset_ids, f"duplicate delivery asset id: {asset_id}")
        asset_ids.add(asset_id)
        require(isinstance(item.get("kind"), str) and item["kind"].strip(),
                f"delivery asset {asset_id} requires kind")
        require(isinstance(item.get("camera_intent"), str) and item["camera_intent"].strip(),
                f"delivery asset {asset_id} requires camera_intent")
        require(isinstance(item.get("must_show"), list) and item["must_show"],
                f"delivery asset {asset_id} requires must_show")
        lock_ids = item.get("structural_lock_ids")
        require(isinstance(lock_ids, list) and lock_ids,
                f"delivery asset {asset_id} requires structural_lock_ids")
        require(set(lock_ids) <= known_lock_ids,
                f"delivery asset {asset_id} references unknown structural locks")
        must_not_change = item.get("must_not_change")
        require(isinstance(must_not_change, list) and must_not_change and
                all(isinstance(value, str) and value.strip() for value in must_not_change),
                f"delivery asset {asset_id} requires must_not_change")
        require(item.get("substitution_policy") == "forbidden",
                f"delivery asset {asset_id} must forbid silent substitution")

    by_id = {item["id"]: item for item in assets}
    if "structure-reference-plan" in by_id:
        require(by_id["structure-reference-plan"]["kind"] == "structure_reference_plan",
                "structure-reference-plan must use structure_reference_plan kind")
    if "furnished-floor-plan" in by_id:
        require(by_id["furnished-floor-plan"]["kind"] == "furnished_colour_plan",
                "furnished-floor-plan must use furnished_colour_plan kind")


def compile_delivery_tasks(data: dict[str, Any], source_image: Path,
                           delivery_plan: dict[str, Any]) -> dict[str, Any]:
    validate_delivery_plan(data, delivery_plan)
    design = data["design"]
    selected_style = design.get("selected_style")
    require(selected_style is not None,
            "linked delivery planning requires design.selected_style")
    chosen = chosen_style(design)
    chosen = {**chosen, "palette":design.get("palette") or chosen["palette"],
              "materials":design.get("materials") or chosen["materials"]}
    outputs = data["outputs"]
    interpretation = data["interpretation_artifacts"]
    structural_block = delivery_structural_block(data)
    assets = delivery_plan["assets"]
    extension = outputs["format"]
    output_by_id = {
        item["id"]: f'outputs/delivery/{index:02d}-{item["id"]}.{extension}'
        for index, item in enumerate(assets, start=1)
    }
    primary_by_floor = {
        item.get("floor", "F1"): item["id"]
        for item in assets if item["id"].startswith("primary-birdseye")
    }
    confirmed_references = [
        str(source_image), interpretation["topdown_base"], interpretation["access_map"]
    ]
    tasks: list[dict[str, Any]] = []

    for item in assets:
        asset_id = item["id"]
        kind = item["kind"]
        floor = item.get("floor", "F1")
        task_base = {
            "id": asset_id,
            "kind": kind,
            "delivery_asset_id": asset_id,
            "planned_kind": kind,
            "floor": floor,
            "camera_intent": item["camera_intent"],
            "must_show": item["must_show"],
            "structural_lock_ids": item["structural_lock_ids"],
            "must_not_change": item["must_not_change"],
            "output": output_by_id[asset_id],
        }

        if kind == "structure_reference_plan":
            tasks.append({
                **task_base,
                "status": "ready_for_deterministic_copy",
                "depends_on": [],
                "execution_mode": "deterministic_copy",
                "source": interpretation["topdown_base"],
            })
            continue

        if kind == "furnished_colour_plan":
            prompt = f"""Create one furnished colour floor plan as a clean orthographic top-down AI concept image. Treat reference 1 as the structural authority and references 2 and 3 as the approved geometry and access authorities. Add only furniture, floor finishes, restrained material colour, and room-function presentation. Do not convert this into a structure-only reference plan.

Camera intent: {item['camera_intent']}
Must show: {', '.join(item['must_show'])}
Must not change:
{lines(item['must_not_change'])}

Selected style: {chosen['name']} ({selected_style})
- Palette: {', '.join(chosen['palette'])}
- Materials: {', '.join(chosen['materials'])}

{structural_block}"""
            primary_id = primary_by_floor.get(floor)
            require(primary_id is not None, f"furnished plan requires primary for floor {floor}")
            dependencies = [primary_id]
            references = confirmed_references + [f"asset://{primary_id}"]
            prompt += "\nReference 4 is the approved primary scheme. Project its furniture positions into plan view without redesigning them."
            status = "blocked_until_primary_approved"
        elif asset_id.startswith("primary-birdseye"):
            prompt = f"""Create the primary cutaway bird's-eye AI 3D concept image for this delivery asset. Treat reference 1 as the structural authority and references 2 and 3 as the approved geometry and access authorities.

Camera intent: {item['camera_intent']}
Must show: {', '.join(item['must_show'])}
Must not change:
{lines(item['must_not_change'])}

Selected style: {chosen['name']} ({selected_style})
- Palette: {', '.join(chosen['palette'])}
- Materials: {', '.join(chosen['materials'])}

{structural_block}"""
            dependencies = []
            references = confirmed_references
            status = "ready_for_generation"
        elif kind in {"birdseye", "room_view"}:
            primary_id = primary_by_floor.get(floor)
            require(primary_id is not None,
                    f"delivery asset {asset_id} requires a primary birdseye for floor {floor}")
            prompt = f"""Create one derived {kind} AI 3D concept image for this approved delivery asset. Use reference 1 as the structural authority, reference 2 as the approved access authority, and reference 3 as the approved primary bird's-eye visual authority. Preserve design identity and implement exactly this shot-list entry.

Camera intent: {item['camera_intent']}
Must show: {', '.join(item['must_show'])}
Structural lock IDs: {', '.join(item['structural_lock_ids'])}
Must not change:
{lines(item['must_not_change'])}

Selected style: {chosen['name']} ({selected_style})
- Palette: {', '.join(chosen['palette'])}
- Materials: {', '.join(chosen['materials'])}

{structural_block}"""
            dependencies = [primary_id]
            references = [str(source_image), interpretation["access_map"], f"asset://{primary_id}"]
            status = "blocked_until_primary_approved"
        else:
            raise ManifestError(f"unsupported delivery asset kind: {kind}")

        tasks.append({
            **task_base,
            "status": status,
            "depends_on": dependencies,
            "execution_mode": "image_generation",
            "reference_images": references + design.get("reference_images", []),
            "scheme_sha256": design_digest(shared_design_block(design,item["must_show"])),
            "request": {
                "model": "gpt-image-2",
                "operation": "edit",
                "size": outputs["size"],
                "quality": outputs["quality"],
                "format": extension,
                "prompt": prompt + "\n\n" + shared_design_block(design,item["must_show"]),
            },
        })

    return {
        "plan_version": "0.3",
        "design_scheme": copy.deepcopy(design),
        "scheme_sha256": design_digest(design),
        "project_id": data["project_id"],
        "source_delivery_plan_version": delivery_plan["delivery_plan_version"],
        "product_label": "AI 3D floor-plan client delivery task plan",
        "accuracy_boundary": "conceptual_not_construction_ready",
        "source_image": str(source_image),
        "selected_style": selected_style,
        "task_count": len(tasks),
        "tasks": tasks,
        "approval_gates": delivery_plan.get("approval_gates", []),
    }


def compile_plan(data: dict[str, Any], source_image: Path,
                 delivery_plan: dict[str, Any] | None = None) -> dict[str, Any]:
    if delivery_plan is not None:
        return compile_delivery_tasks(data, source_image, delivery_plan)

    rooms = data["floor_plan"]["rooms"]
    room_summary = [f'{room["name"]} ({room.get("type", "unspecified")}, {room["certainty"]})' for room in rooms]
    relationships = data["floor_plan"].get("relationships", [])
    locks = structural_locks(data)
    locked = [f'[{item["id"]}] {item["rule"]}' for item in locks]
    design = data["design"]
    outputs = data["outputs"]
    interpretation = data["interpretation_artifacts"]
    confirmed_references = [
        str(source_image),
        interpretation["topdown_base"],
        interpretation["access_map"],
    ]

    structural_block = f"""Confirmed or declared rooms:\n{lines(room_summary)}

Spatial relationships:\n{lines(relationships)}

Locked structural requirements:\n{lines(locked)}

{completion_constraints(data)}

Hard constraints:
- Do not add, remove, merge, or split rooms.
- Do not move visible walls, doors, or windows.
- Do not invent measurements or construction details.
- Produce an AI concept image, not a construction drawing or precise 3D model.
- No watermark, logo, plan labels, or generated annotations."""

    selected_style = design.get("selected_style")
    if selected_style is None:
        options = design["style_options"]
        tasks = []
        for offset in range(0, len(options), 4):
            group = options[offset:offset+4]
            labels = [chr(65 + offset + i) for i in range(4)]
            style_lines = [
                f'{label}. {option["name"]} ({option["id"]}): '
                f'palette {", ".join(option["palette"])}; materials {", ".join(option["materials"])}'
                for label, option in zip(labels, group)
            ]
            preview_prompt = f"""Create one renovation style-selection preview image as a strict 2x2 grid with exactly four equally sized panels. Use the same representative living-dining room, identical camera position, focal length, major furniture arrangement, daylight direction, and exposure in every panel and across all comparison boards. Change only palette, finishes, furniture design language, lighting fixtures, textiles, and decor. Keep the panels clearly separated and label them {', '.join(labels)} with their style names. This board is for style selection, not structural approval or final delivery. Make materials, upholstery, lighting and detailing visibly distinct, not just beige palette swaps. Preserve the confirmed furniture footprints and access. Style names describe design directions, not market rankings or standardized categories.

Style options:
{lines(style_lines)}

Use the supplied floor-plan, approved 2D base, and approved access map only to keep the representative room plausible. Do not add or remove doors or windows. Do not render four independent whole-home plans. No watermark or logo."""
            tasks.append({
            "id": "style-preview-grid" if len(options) == 4 else f"style-preview-grid-{offset//4+1}",
            "kind": "style_preview",
            "status": "ready_for_generation",
            "depends_on": [],
            "reference_images": confirmed_references,
            "style_ids": [option["id"] for option in group],
            "panel_labels": labels,
            "output": "outputs/styles/four-style-preview.png" if len(options) == 4 else f"outputs/styles/style-preview-{offset//4+1}.png",
            "request": {
                "model": "gpt-image-2",
                "operation": "edit",
                "size": outputs["size"],
                "quality": "low" if outputs["quality"] == "high" else outputs["quality"],
                "format": outputs["format"],
                "prompt": preview_prompt,
            },
        })
        return {
            "plan_version": "0.2",
            "project_id": data["project_id"],
            "product_label": "AI renovation style selection board",
            "accuracy_boundary": "style_selection_not_structural_authority",
            "source_image": str(source_image),
            "selected_style": None,
            "task_count": len(tasks),
            "approval_gates": [
                "Structure and room functions confirmed",
                "Doors, windows, opening directions, and connectivity confirmed",
                "Furniture/equipment layout confirmed; supply its exact image as an additional reference before executing style previews",
                f"Choose one of the {len(options)} styles or specify a custom direction before detailed 3D generation",
            ],
            "tasks": tasks,
        }

    option_by_id = {option["id"]: option for option in design["style_options"]}
    chosen = chosen_style(design)
    chosen = {**chosen, "palette":design.get("palette") or chosen["palette"],
              "materials":design.get("materials") or chosen["materials"]}
    structural_block += "\n\n" + shared_design_block(design)
    canonical_prompt = f"""Create a clean, detailed cutaway bird's-eye AI 3D concept image from the supplied references. Treat reference 1, the source floor plan, as the structural authority; use the approved 2D base and approved access map to preserve every confirmed door/window type and opening direction. Use a consistent 45-degree axonometric camera, open ceiling, complete apartment visible, soft daylight, and practical furniture.

Selected design style: {chosen['name']} ({chosen['id']})
- Palette: {', '.join(chosen['palette'])}
- Materials: {', '.join(chosen['materials'])}

{structural_block}"""

    canonical_output = "outputs/canonical/cutaway_birdseye.png"
    tasks: list[dict[str, Any]] = [{
        "id": "canonical-cutaway-birdseye",
        "kind": "canonical",
        "status": "ready_for_generation",
        "depends_on": [],
        "reference_images": confirmed_references,
        "output": canonical_output,
        "request": {
            "model": "gpt-image-2",
            "operation": "edit",
            "size": outputs["size"],
            "quality": outputs["quality"],
            "format": outputs["format"],
            "prompt": canonical_prompt,
        },
    }]

    design_block = f"""Design direction:
- Style: {chosen['name']} ({chosen['id']})
- Household: {design.get('household') or 'not specified'}
- Budget tier: {design.get('budget_tier') or 'not specified'}
- Palette: {', '.join(chosen['palette'])}
- Materials: {', '.join(chosen['materials'])}
- Requirements: {', '.join(design.get('requirements', [])) or 'none'}"""

    for view in outputs["room_views"]:
        task_id = f"room-{view.replace('_', '-')}"
        prompt = f"""Create one photorealistic renovation concept view for camera intent: {view}. Use reference 1 as the structural authority, reference 2 as the approved access authority, and reference 3 as the approved visual authority. Preserve their room layout, openings, opening directions, design language, furniture identity, palette, and material system. Show only a plausible view from inside the named room; do not reveal geometry that conflicts with the source plan.

{structural_block}

{design_block}"""
        tasks.append({
            "id": task_id,
            "kind": "room_view",
            "status": "blocked_until_canonical_approved",
            "depends_on": ["canonical-cutaway-birdseye"],
            "reference_images": [str(source_image), interpretation["access_map"], canonical_output],
            "output": f"outputs/rooms/{view}.png",
            "request": {
                "model": "gpt-image-2",
                "operation": "edit",
                "size": outputs["size"],
                "quality": outputs["quality"],
                "format": outputs["format"],
                "prompt": prompt,
            },
        })

    for style in outputs["style_variants"]:
        task_id = f"style-{style.replace('_', '-')}"
        prompt = f"""Restyle the approved canonical cutaway view as {style}. Change only finishes, furniture design, lighting, textiles, and decor. Preserve the exact camera framing and all visible spatial relationships from both references.

{structural_block}"""
        tasks.append({
            "id": task_id,
            "kind": "style_variant",
            "status": "blocked_until_canonical_approved",
            "depends_on": ["canonical-cutaway-birdseye"],
            "reference_images": [str(source_image), interpretation["access_map"], canonical_output],
            "output": f"outputs/styles/{style}.png",
            "request": {
                "model": "gpt-image-2",
                "operation": "edit",
                "size": outputs["size"],
                "quality": outputs["quality"],
                "format": outputs["format"],
                "prompt": prompt,
            },
        })

    for task in tasks:
        task["reference_images"] = list(task["reference_images"]) + design.get("reference_images", [])
    return {
        "plan_version": "0.2",
        "project_id": data["project_id"],
        "product_label": "AI 3D floor-plan concept images",
        "accuracy_boundary": "conceptual_not_construction_ready",
        "source_image": str(source_image),
        "selected_style": selected_style,
        "task_count": len(tasks),
        "approval_gates": [
            "Structure and room functions confirmed",
            "Doors, windows, opening directions, and connectivity confirmed",
            "Four-style preview completed and one style selected",
            "Compare canonical doors and windows against the approved access map",
            "Approve canonical cutaway view before derived tasks",
            "Approve previews before high-quality final generation"
        ],
        "tasks": tasks,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--delivery-plan", type=Path,
                        help="Compile tasks from an approved delivery-plan.json")
    parser.add_argument("--allow-missing-input", action="store_true",
                        help="Allow a placeholder input path for dry-run samples only")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest_path = args.manifest.expanduser().resolve()
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        source_image = validate_manifest(data, manifest_path, args.allow_missing_input)
        delivery_plan = None
        if args.delivery_plan is not None:
            delivery_plan = json.loads(
                args.delivery_plan.expanduser().read_text(encoding="utf-8")
            )
        snapshot = validate_bundle(data, manifest_path) if not args.allow_missing_input else None
        compile_data = copy.deepcopy(data)
        if snapshot:
            for key, record in snapshot.items():
                if key != "manifest":
                    compile_data["interpretation_artifacts"][key] = record["path"]
        reference_paths = []
        for value in data["design"].get("reference_images", []):
            reference = Path(value).expanduser()
            if not reference.is_absolute():
                reference = manifest_path.parent/reference
            reference = reference.resolve()
            require(args.allow_missing_input or reference.is_file(), f"design reference missing: {reference}")
            reference_paths.append(str(reference))
            if snapshot is not None:
                from interpretation_authority import digest
                snapshot[f"design_reference_{len(reference_paths)}"] = {"path":str(reference),"sha256":digest(reference)}
        compile_data["design"]["reference_images"] = reference_paths
        plan = compile_plan(compile_data, source_image, delivery_plan)
        plan["execution_mode"] = "sample_only" if args.allow_missing_input else "confirmed_bundle"
        if not args.allow_missing_input:
            plan["interpretation_authority"] = snapshot
        args.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = args.output_dir / "generation-plan.json"
        state_path = None
        if delivery_plan is not None:
            state_path = args.output_dir / "delivery-state.json"
            if state_path.exists():
                validate_state(plan, json.loads(state_path.read_text(encoding="utf-8")))
        # Validate all predictable failure conditions before replacing a valid plan.
        new_state = build_initial_state(plan) if delivery_plan is not None and not state_path.exists() else None
        atomic_write(output_path, plan)
        if new_state is not None:
            atomic_write(state_path, new_state)
        print(json.dumps({
            "status": "ok",
            "project_id": plan["project_id"],
            "task_count": plan["task_count"],
            "plan": str(output_path.resolve()),
            "state": str(state_path.resolve()) if state_path else None,
            "external_api_called": False,
        }, ensure_ascii=False))
        return 0
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
