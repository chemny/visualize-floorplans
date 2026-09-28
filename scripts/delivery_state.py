#!/usr/bin/env python3
"""Gate floor-plan delivery tasks on explicit primary-birdseye approval."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validate_delivery import DeliveryReviewError, validate_delivery as validate_delivery_review


class DeliveryStateError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DeliveryStateError(message)


def plan_digest(plan: dict[str, Any]) -> str:
    payload = json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_primary(task: dict[str, Any]) -> bool:
    return str(task.get("id", "")).startswith("primary-birdseye")


def build_initial_state(plan: dict[str, Any]) -> dict[str, Any]:
    require(plan.get("plan_version") == "0.3",
            "delivery state requires generation plan version 0.3")
    tasks = plan.get("tasks")
    require(isinstance(tasks, list) and tasks, "generation plan must contain tasks")
    task_ids = [task.get("id") for task in tasks]
    require(all(isinstance(task_id, str) and task_id for task_id in task_ids),
            "every generation task requires id")
    require(len(task_ids) == len(set(task_ids)), "generation task ids must be unique")
    primary_ids = [task["id"] for task in tasks if is_primary(task)]
    require(primary_ids, "generation plan requires at least one primary birdseye")

    assets = {}
    for task in tasks:
        dependencies = task.get("depends_on", [])
        require(isinstance(dependencies, list),
                f"task {task['id']} depends_on must be a list")
        assets[task["id"]] = {
            "kind": task.get("kind"),
            "floor": task.get("floor", "F1"),
            "depends_on": dependencies,
            "output": task.get("output"),
            "status": "blocked_until_primary_approved" if dependencies else "ready",
            "generated_file": None,
        }

    return {
        "state_version": "0.2",
        "project_id": plan.get("project_id"),
        "generation_plan_sha256": plan_digest(plan),
        "stage": "primary_ready",
        "primary_asset_ids": primary_ids,
        "assets": assets,
        "approvals": {"primary": {}, "package": {}},
        "package_review": None,
        "history": [{"event": "initialized", "at": now_utc()}],
    }


def validate_state(plan: dict[str, Any], state: dict[str, Any]) -> None:
    require(state.get("state_version") in {"0.1", "0.2"},
            "state_version must be 0.1 or 0.2")
    require(state.get("project_id") == plan.get("project_id"),
            "state project_id does not match generation plan")
    require(state.get("generation_plan_sha256") == plan_digest(plan),
            "generation plan changed; create a new state file instead of reusing approvals")
    planned_ids = {task["id"] for task in plan.get("tasks", [])}
    assets = state.get("assets")
    require(isinstance(assets, dict) and set(assets) == planned_ids,
            "state assets must exactly match generation tasks")
    if state.get("state_version") == "0.2":
        require(isinstance(state.get("approvals", {}).get("package"), dict),
                "state approvals.package must be an object")
        require("package_review" in state, "state 0.2 requires package_review")


def upgrade_state(state: dict[str, Any]) -> dict[str, Any]:
    if state.get("state_version") == "0.1":
        state["state_version"] = "0.2"
        state.setdefault("approvals", {}).setdefault("package", {})
        state.setdefault("package_review", None)
        state.setdefault("history", []).append({"event": "state_upgraded", "at": now_utc()})
    return state


def refresh_stage(plan: dict[str, Any], state: dict[str, Any]) -> str:
    if state.get("stage") in {"package_review_passed", "final_export_ready"}:
        return state["stage"]
    primary_statuses = [state["assets"][item]["status"]
                        for item in state["primary_asset_ids"]]
    if any(status == "pending_primary_approval" for status in primary_statuses):
        state["stage"] = "primary_pending_approval"
    elif all(status == "approved" for status in primary_statuses):
        complete = all(
            asset["status"] in {"generated", "approved"}
            for asset in state["assets"].values()
        )
        state["stage"] = (
            "package_pending_review" if complete
            else "primary_approved_derived_ready"
        )
    else:
        state["stage"] = "primary_ready"
    return state["stage"]


def sync_state(plan: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    validate_state(plan, state)
    previous = state.get("stage")
    upgrade_state(state)
    stale = [asset_id for asset_id,asset in state["assets"].items()
             if asset["status"] in {"generated","approved","pending_primary_approval"} and not content_current(asset)]
    if stale:
        revise_assets(plan,state,stale,"Recorded image changed or disappeared; restore or regenerate and review")
    current = refresh_stage(plan, state)
    if current != previous:
        state["history"].append({
            "event": "stage_synchronized", "from": previous, "to": current,
            "at": now_utc(),
        })
    return state


def task_by_id(plan: dict[str, Any], asset_id: str) -> dict[str, Any]:
    task = next((item for item in plan.get("tasks", []) if item.get("id") == asset_id), None)
    require(task is not None, f"unknown generation task: {asset_id}")
    return task


def file_digest(path):
    return hashlib.sha256(Path(path).expanduser().read_bytes()).hexdigest()


def content_current(asset):
    path = asset.get("generated_file")
    return bool(path and asset.get("generated_sha256") and Path(path).is_file()
                and file_digest(path) == asset["generated_sha256"])


def layout_blockers(plan, state):
    """Bind production to an accepted layout; this is not a geometry detector."""
    if plan.get("execution_mode") != "confirmed_bundle":
        return []
    record = state.get("approvals", {}).get("layout", {})
    if not record or record.get("approval_source") != "explicit_user_confirmation":
        return ["approved pre-render layout required; use approve-layout"]
    if record.get("scheme_sha256") != plan.get("scheme_sha256"):
        return ["layout approval belongs to a different scheme; replan and review"]
    if not content_current(record):
        return ["approved layout changed or missing; replan and review"]
    svg = record.get("svg_file")
    if not (svg and record.get("svg_sha256") and Path(svg).is_file()
            and file_digest(svg) == record["svg_sha256"]):
        return ["approved editable layout SVG changed or missing; replan and review"]
    return []


def approve_layout(plan, state, layout_file, svg_file, revision, approved_by, evidence, approval_source):
    validate_state(plan, state)
    require(approval_source == "explicit_user_confirmation", "layout requires explicit_user_confirmation")
    require(all(isinstance(v, str) and v.strip() for v in (revision, approved_by, evidence)),
            "layout revision, approved_by and confirmation evidence are required")
    require(layout_file.expanduser().is_file(), "layout file missing")
    require(layout_file.suffix.lower() == ".png", "layout preview must be PNG")
    require(svg_file.expanduser().is_file(), "editable layout SVG missing")
    require(svg_file.suffix.lower() == ".svg", "editable layout source must be SVG")
    require(layout_file.stem == svg_file.stem, "layout SVG and PNG preview must use the same revision name")
    try:
        import xml.etree.ElementTree as ET
        root = ET.parse(svg_file.expanduser()).getroot()
    except ET.ParseError as exc:
        raise DeliveryStateError(f"layout SVG is invalid XML: {exc}") from exc
    require(root.tag.rsplit("}", 1)[-1] == "svg", "layout SVG root element must be svg")
    record = {"generated_file": str(layout_file.expanduser().resolve()),
              "generated_sha256": file_digest(layout_file), "revision": revision,
              "svg_file": str(svg_file.expanduser().resolve()),
              "svg_sha256": file_digest(svg_file),
              "scheme_sha256": plan.get("scheme_sha256"), "approved_by": approved_by,
              "evidence": evidence, "approval_source": approval_source}
    previous = state["approvals"].get("layout")
    if previous == record:
        return state
    migrated = state.get("history", [{}])[-1]
    retained_only = (migrated.get("event") == "replanned" and
                     all(key in migrated["reused"] for key, a in state["assets"].items() if a.get("generated_file")))
    require(retained_only or not any(a.get("generated_file") for a in state["assets"].values()),
            "cannot attach new layout approval to generated images; replan first")
    state["approvals"]["layout"] = record
    state["history"].append({"event": "layout_approved", **record, "at": now_utc()})
    return state


def resolve_task(plan, state, asset_id):
    task = copy.deepcopy(task_by_id(plan, asset_id))
    require(not layout_blockers(plan, state), "; ".join(layout_blockers(plan, state)))
    references = []
    for reference in task.get("reference_images", []):
        if reference.startswith("asset://"):
            dependency = reference[len("asset://"):]
            require(dependency in task.get("depends_on", []), "undeclared reference dependency")
            asset = state["assets"][dependency]
            require(asset["status"] == "approved" and content_current(asset),
                    f"reference {dependency} is not currently approved")
            reference = asset["generated_file"]
        references.append(reference)
    if "reference_images" in task:
        task["reference_images"] = references
    layout = state.get("approvals", {}).get("layout")
    if layout and "request" in task:
        refs = task.setdefault("reference_images", [])
        if layout["generated_file"] not in refs:
            refs.append(layout["generated_file"])
        task["request"]["prompt"] += "\nApproved pre-render layout reference: " + layout["generated_file"] + "; preserve furniture positions, identities and access clearances."
    if state["assets"][asset_id].get("revision_instruction"):
        instruction = state["assets"][asset_id]["revision_instruction"]
        if "request" in task:
            task["request"]["prompt"] += "\nTargeted revision (preserve all unrelated content): " + instruction
        previous = state["assets"][asset_id].get("revision_reference")
        if previous and "request" in task:
            require(content_current(previous), "revision reference changed or missing")
            task.setdefault("reference_images",[]).append(previous["generated_file"])
            task["request"]["prompt"] += "\nLast reference is the previous image to edit; preserve its unaffected areas."
        task["output"] = state["assets"][asset_id]["output"]
    return task


def revise_assets(plan, state, asset_ids, reason):
    """Reopen selected assets and dependents, retaining files and audit history."""
    validate_state(plan, state)
    require(isinstance(reason,str) and reason.strip(), "revision requires specific reason/instruction")
    require(asset_ids and set(asset_ids) <= set(state["assets"]), "revision requires known asset IDs")
    affected = set(asset_ids)
    while True:
        expanded = affected | {t["id"] for t in plan["tasks"] if affected.intersection(t.get("depends_on",[]))}
        if expanded == affected:
            break
        affected = expanded
    for asset_id in affected:
        asset = state["assets"][asset_id]
        state["history"].append({"event":"asset_reopened", "asset_id":asset_id,
                                 "previous":copy.deepcopy(asset), "reason":reason, "at":now_utc()})
        asset["revision"] = asset.get("revision",0)+1
        if content_current(asset):
            asset["revision_reference"] = {"generated_file":asset["generated_file"],"generated_sha256":asset["generated_sha256"]}
        output = Path(task_by_id(plan,asset_id)["output"])
        asset["output"] = str(output.with_name(f"{output.stem}-r{asset['revision']}{output.suffix}"))
        asset["revision_instruction"] = reason
        asset["status"] = "blocked_until_primary_approved" if asset["depends_on"] else "ready"
        asset["generated_file"] = None
        asset["generated_sha256"] = None
        state["approvals"]["primary"].pop(asset_id,None)
    state["package_review"] = None
    state["approvals"]["package"] = {}
    if state.get("video"):
        state["history"].append({"event":"video_invalidated","previous":copy.deepcopy(state["video"]),"at":now_utc()})
    state["video"] = {"status":"invalidated", "reason":reason, "at":now_utc()}
    state["stage"] = "primary_ready"
    for asset in state["assets"].values():
        if asset["status"] == "blocked_until_primary_approved" and all(
                state["assets"][d]["status"] == "approved" and content_current(state["assets"][d])
                for d in asset["depends_on"]):
            asset["status"] = "ready"
    refresh_stage(plan,state)
    return sorted(affected)


def migrate_state(old_plan, old_state, new_plan):
    """Reuse only unchanged tasks with current files and unchanged dependencies."""
    validate_state(old_plan,old_state)
    new_state = build_initial_state(new_plan)
    layout = old_state.get("approvals", {}).get("layout")
    old_tasks = {t["id"]:t for t in old_plan["tasks"]}
    old_authority = {k:v for k,v in old_plan.get("interpretation_authority",{}).items() if k != "manifest"}
    new_authority = {k:v for k,v in new_plan.get("interpretation_authority",{}).items() if k != "manifest"}
    if (layout and content_current(layout) and old_authority == new_authority
            and old_plan.get("scheme_sha256") == new_plan.get("scheme_sha256")):
        new_state["approvals"]["layout"] = copy.deepcopy(layout)
    reusable = set()
    if old_authority == new_authority:
        for task in new_plan["tasks"]:
            asset_id = task["id"]
            asset = old_state["assets"].get(asset_id,{})
            if old_tasks.get(asset_id) == task and asset.get("status") in {"generated","approved"} and content_current(asset):
                reusable.add(asset_id)
    # A task with unchanged visible requirements may keep its pixels even if
    # the whole-home primary changes elsewhere. A new full package review must
    # compare retained images against that new primary before export.
    for asset_id in reusable:
        new_state["assets"][asset_id] = copy.deepcopy(old_state["assets"][asset_id])
        new_state["assets"][asset_id]["scheme_sha256"] = new_plan.get("scheme_sha256")
        if asset_id in old_state["approvals"]["primary"]:
            new_state["approvals"]["primary"][asset_id] = copy.deepcopy(old_state["approvals"]["primary"][asset_id])
    for asset in new_state["assets"].values():
        if asset["status"] == "blocked_until_primary_approved" and all(new_state["assets"][d]["status"] == "approved" for d in asset["depends_on"]):
            asset["status"] = "ready"
    new_state["video"] = {"status":"invalidated", "reason":"new generation plan"}
    if old_state.get("video"):
        new_state["history"].append({"event":"previous_video", "previous":copy.deepcopy(old_state["video"]),"at":now_utc()})
    new_state["history"].append({"event":"replanned", "previous_plan_sha256":plan_digest(old_plan), "reused":sorted(reusable), "at":now_utc()})
    refresh_stage(new_plan,new_state)
    return new_state


def can_run(plan: dict[str, Any], state: dict[str, Any], asset_id: str) -> dict[str, Any]:
    validate_state(plan, state)
    task = task_by_id(plan, asset_id)
    asset_state = state["assets"][asset_id]
    dependencies = task.get("depends_on", [])
    blocked_by = [
        dependency for dependency in dependencies
        if state["assets"][dependency]["status"] != "approved"
    ]
    blocked_by += [f"changed_or_missing:{d}" for d in dependencies
                   if state["assets"][d]["status"] == "approved" and not content_current(state["assets"][d])]
    blocked_by += layout_blockers(plan, state)
    if plan.get("execution_mode") == "sample_only":
        blocked_by.append("sample_only_plan_is_not_executable")
    if plan.get("execution_mode") == "confirmed_bundle":
        from interpretation_authority import check_snapshot
        try:
            require(bool(plan.get("interpretation_authority")), "missing interpretation authority")
            check_snapshot(plan["interpretation_authority"])
        except (ValueError, OSError) as exc:
            blocked_by.append(str(exc))
    runnable = asset_state["status"] == "ready" and not blocked_by
    result = {
        "status": "ok",
        "asset_id": asset_id,
        "runnable": runnable,
        "asset_status": asset_state["status"],
        "blocked_by": blocked_by,
    }
    if runnable:
        result["resolved_task"] = resolve_task(plan,state,asset_id)
    return result


def record_generated(plan: dict[str, Any], state: dict[str, Any], asset_id: str,
                     generated_file: Path) -> dict[str, Any]:
    upgrade_state(state)
    result = can_run(plan, state, asset_id)
    require(result["runnable"],
            f"task {asset_id} is not runnable; blocked by {result['blocked_by'] or result['asset_status']}")
    require(generated_file.expanduser().is_file(),
            f"generated file not found: {generated_file}")
    task = task_by_id(plan, asset_id)
    asset_state = state["assets"][asset_id]
    previous = asset_state.get("revision_reference")
    if previous:
        require(str(generated_file.expanduser().resolve()) != previous["generated_file"],
                "replacement must use a new path; preserve the previous image")
    asset_state["generated_file"] = str(generated_file.expanduser().resolve())
    asset_state["generated_sha256"] = file_digest(generated_file)
    asset_state["scheme_sha256"] = plan.get("scheme_sha256")
    asset_state["input_asset_sha256"] = {d:state["assets"][d]["generated_sha256"] for d in task.get("depends_on",[])}
    if is_primary(task):
        asset_state["status"] = "pending_primary_approval"
    else:
        asset_state["status"] = "generated"
    state["history"].append({
        "event": "generated",
        "asset_id": asset_id,
        "file": asset_state["generated_file"],
        "at": now_utc(),
    })
    refresh_stage(plan, state)
    return state


def approve_primary(plan: dict[str, Any], state: dict[str, Any], asset_id: str,
                    approved_by: str, evidence: str,
                    approval_source: str) -> dict[str, Any]:
    validate_state(plan, state)
    upgrade_state(state)
    task = task_by_id(plan, asset_id)
    require(is_primary(task), f"task {asset_id} is not a primary birdseye")
    require(state["assets"][asset_id]["status"] == "pending_primary_approval",
            f"primary birdseye {asset_id} must be generated before approval")
    require(approval_source == "explicit_user_confirmation",
            "primary approval requires explicit_user_confirmation")
    require(isinstance(approved_by, str) and approved_by.strip(),
            "approved_by is required")
    require(isinstance(evidence, str) and evidence.strip(),
            "approval evidence is required")
    require(content_current(state["assets"][asset_id]), "primary content changed or missing; reopen and record the current image")
    if plan.get("execution_mode") == "confirmed_bundle":
        scheme = plan.get("design_scheme",{}).get("scheme",{})
        require(isinstance(scheme.get("version"),str) and scheme["version"].strip(), "record current design scheme version")
        require(all(isinstance(scheme.get(k),list) and scheme[k]
                    and all(isinstance(v,str) and v.strip() for v in scheme[k])
                    for k in ("layout","furniture","finishes")),
                "primary approval requires explicit layout, furniture, and finish records")

    state["assets"][asset_id]["status"] = "approved"
    approval = {
        "approved_by": approved_by.strip(),
        "approval_source": approval_source,
        "evidence": evidence.strip(),
        "image_sha256": state["assets"][asset_id]["generated_sha256"],
        "scheme_sha256": plan.get("scheme_sha256"),
        "at": now_utc(),
    }
    state["approvals"]["primary"][asset_id] = approval
    state["history"].append({"event": "primary_approved", "asset_id": asset_id, **approval})

    for task_item in plan["tasks"]:
        task_id = task_item["id"]
        asset_state = state["assets"][task_id]
        dependencies = task_item.get("depends_on", [])
        if asset_state["status"] != "blocked_until_primary_approved":
            continue
        if all(state["assets"][dependency]["status"] == "approved"
               for dependency in dependencies):
            asset_state["status"] = "ready"

    refresh_stage(plan, state)
    return state


def record_package_review(plan: dict[str, Any], state: dict[str, Any],
                          delivery_plan: dict[str, Any], review: dict[str, Any],
                          delivery_plan_path: Path, review_path: Path,
                          require_files: bool = True) -> dict[str, Any]:
    sync_state(plan, state)
    require(state["stage"] == "package_pending_review",
            "all planned assets must be generated and primaries approved before package review")
    require(delivery_plan.get("project_id") == plan.get("project_id"),
            "delivery plan project_id does not match generation plan")
    delivery_ids = [item.get("id") for item in delivery_plan.get("assets", [])]
    generation_ids = [item.get("delivery_asset_id") for item in plan.get("tasks", [])]
    require(delivery_ids == generation_ids,
            "delivery plan asset order does not match generation plan")
    result = validate_delivery_review(delivery_plan, review, require_files=require_files)
    if require_files:
        require(review.get("scheme_sha256") == plan.get("scheme_sha256"), "review scheme differs from current plan")
        for record in review["assets"]:
            asset_id = record["id"]
            asset = state["assets"][asset_id]
            require(content_current(asset), f"asset changed or missing: {asset_id}")
            require(str(Path(record["path"]).expanduser().resolve()) == asset["generated_file"]
                    and record["image_sha256"] == asset["generated_sha256"],
                    f"review does not match recorded output: {asset_id}")
            task = resolve_task(plan,state,asset_id)
            expected = set(task.get("reference_images", []))
            if task.get("source"):
                expected.add(task["source"])
            require(expected <= set(record["authority_refs"]), f"{asset_id}: actual task authorities were not all reviewed")
        require(load_json(delivery_plan_path) == delivery_plan and load_json(review_path) == review,
                "save exact delivery plan and review before recording approval")
        for task in plan["tasks"]:
            state["assets"][task["id"]]["input_asset_sha256"] = {
                d:state["assets"][d]["generated_sha256"] for d in task.get("depends_on",[])}
    state["package_review"] = {
        "status": result["status"],
        "delivery_plan": str(delivery_plan_path.expanduser().resolve()),
        "delivery_plan_sha256": plan_digest(delivery_plan),
        "review": str(review_path.expanduser().resolve()),
        "structural_gate": result["structural_gate"],
        "consistency_gate": result["consistency_gate"],
        "exception_count": result["exception_count"],
        "at": now_utc(),
        "files_verified": require_files,
        "review_sha256": file_digest(review_path) if require_files else None,
        "delivery_file_sha256": file_digest(delivery_plan_path) if require_files else None,
    }
    state["stage"] = "package_review_passed"
    if package_acceptance_current(plan, state) and not export_blockers(plan, state):
        state["stage"] = "final_export_ready"
    state["history"].append({
        "event": "package_review_passed",
        "review": state["package_review"]["review"],
        "delivery_plan_sha256": state["package_review"]["delivery_plan_sha256"],
        "at": state["package_review"]["at"],
    })
    return state


def export_blockers(plan,state):
    blockers = layout_blockers(plan, state)
    package = state.get("package_review") or {}
    if not package.get("files_verified"):
        return blockers + ["live file-bound package review is required; diagnostics cannot authorize export"]
    try:
        for asset_id, asset in state["assets"].items():
            require(content_current(asset), f"changed or missing image: {asset_id}")
            for dependency, sha in asset.get("input_asset_sha256",{}).items():
                require(sha == state["assets"][dependency].get("generated_sha256"), f"stale dependency: {asset_id}")
        require(file_digest(package["review"]) == package["review_sha256"], "review file changed")
        require(file_digest(package["delivery_plan"]) == package["delivery_file_sha256"], "delivery plan file changed")
        validate_delivery_review(load_json(Path(package["delivery_plan"])),load_json(Path(package["review"])),require_files=True)
        if plan.get("execution_mode") == "confirmed_bundle":
            from interpretation_authority import check_snapshot
            check_snapshot(plan["interpretation_authority"])
        elif plan.get("execution_mode") == "sample_only":
            blockers.append("sample-only plan cannot export")
    except (ValueError,OSError,KeyError) as exc:
        blockers.append(str(exc))
    return blockers


def package_acceptance_current(plan, state):
    approval = state.get("approvals", {}).get("package", {})
    return bool(approval.get("approval_source") == "explicit_user_confirmation"
                and approval.get("evidence") and approval.get("approved_by")
                and approval.get("generation_plan_sha256") == plan_digest(plan)
                and approval.get("asset_sha256") == {
                    key: asset.get("generated_sha256") for key, asset in state["assets"].items()}
                and all(content_current(a) for a in state["assets"].values()))


def approve_package(plan, state, approved_by, evidence, approval_source):
    """Record existing image acceptance, before or after QA; never invent it."""
    validate_state(plan, state)
    require(all(a["status"] in {"generated", "approved"} and content_current(a)
                for a in state["assets"].values()), "all current images and primary approvals required")
    require(not layout_blockers(plan, state), "; ".join(layout_blockers(plan, state)))
    require(approval_source == "explicit_user_confirmation", "package requires explicit_user_confirmation")
    require(all(isinstance(v, str) and v.strip() for v in (approved_by, evidence)),
            "approved_by and concrete image confirmation evidence required")
    approval = {"approved_by": approved_by.strip(), "evidence": evidence.strip(),
                "approval_source": approval_source, "generation_plan_sha256": plan_digest(plan),
                "asset_sha256": {k: a["generated_sha256"] for k, a in state["assets"].items()},
                "at": now_utc()}
    state["approvals"]["package"] = approval
    state["history"].append({"event": "package_images_accepted", **approval})
    if not export_blockers(plan, state):
        state["stage"] = "final_export_ready"
    return state


def authorize_final_export(plan: dict[str, Any], state: dict[str, Any],
                           approved_by: str, evidence: str,
                           approval_source: str) -> dict[str, Any]:
    validate_state(plan, state)
    upgrade_state(state)
    require(state.get("stage") == "package_review_passed",
            "package review must pass before final export authorization")
    blockers = export_blockers(plan,state)
    require(not blockers, "; ".join(blockers))
    require(approval_source == "explicit_user_confirmation",
            "final export authorization requires explicit_user_confirmation")
    require(isinstance(approved_by, str) and approved_by.strip(),
            "approved_by is required")
    require(isinstance(evidence, str) and evidence.strip(),
            "approval evidence is required")
    return approve_package(plan, state, approved_by, evidence, approval_source)


def can_export(plan: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    validate_state(plan, state)
    ready = package_acceptance_current(plan, state)
    blockers = [] if ready else [
        "current image acceptance is required; record existing confirmation with approve-package"
    ]
    blockers += export_blockers(plan,state)
    ready = ready and not blockers
    return {"status": "ok", "export_ready": ready,
            "stage": state.get("stage"), "blockers": blockers}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.expanduser().read_text(encoding="utf-8"))


def atomic_write(path: Path, data: dict[str, Any]) -> None:
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("--plan", required=True, type=Path)
    init.add_argument("--state", required=True, type=Path)

    for command in ("approve-layout", "approve-package"):
        acceptance = subparsers.add_parser(command)
        acceptance.add_argument("--plan", required=True, type=Path)
        acceptance.add_argument("--state", required=True, type=Path)
        acceptance.add_argument("--approved-by", required=True)
        acceptance.add_argument("--evidence", required=True)
        acceptance.add_argument("--approval-source", required=True, choices=["explicit_user_confirmation"])
        if command == "approve-layout":
            acceptance.add_argument("--file", required=True, type=Path)
            acceptance.add_argument("--svg", required=True, type=Path)
            acceptance.add_argument("--revision", required=True)

    check = subparsers.add_parser("can-run")
    check.add_argument("--plan", required=True, type=Path)
    check.add_argument("--state", required=True, type=Path)
    check.add_argument("--asset-id", required=True)

    generated = subparsers.add_parser("record-generated")
    generated.add_argument("--plan", required=True, type=Path)
    generated.add_argument("--state", required=True, type=Path)
    generated.add_argument("--asset-id", required=True)
    generated.add_argument("--file", required=True, type=Path)

    approve = subparsers.add_parser("approve-primary")
    approve.add_argument("--plan", required=True, type=Path)
    approve.add_argument("--state", required=True, type=Path)
    approve.add_argument("--asset-id", required=True)
    approve.add_argument("--approved-by", required=True)
    approve.add_argument("--evidence", required=True)
    approve.add_argument("--approval-source", required=True,
                         choices=["explicit_user_confirmation"])

    sync = subparsers.add_parser("sync-state")
    sync.add_argument("--plan", required=True, type=Path)
    sync.add_argument("--state", required=True, type=Path)

    package_review = subparsers.add_parser("record-package-review")
    package_review.add_argument("--plan", required=True, type=Path)
    package_review.add_argument("--state", required=True, type=Path)
    package_review.add_argument("--delivery-plan", required=True, type=Path)
    package_review.add_argument("--review", required=True, type=Path)
    package_review.add_argument("--allow-missing-files", action="store_true")

    final_export = subparsers.add_parser("authorize-final-export")
    final_export.add_argument("--plan", required=True, type=Path)
    final_export.add_argument("--state", required=True, type=Path)
    final_export.add_argument("--approved-by", required=True)
    final_export.add_argument("--evidence", required=True)
    final_export.add_argument("--approval-source", required=True,
                              choices=["explicit_user_confirmation"])

    export_check = subparsers.add_parser("can-export")
    export_check.add_argument("--plan", required=True, type=Path)
    export_check.add_argument("--state", required=True, type=Path)
    revise = subparsers.add_parser("revise", aliases=["reject", "reopen"])
    revise.add_argument("--plan", required=True, type=Path)
    revise.add_argument("--state", required=True, type=Path)
    revise.add_argument("--asset-id", action="append", required=True)
    revise.add_argument("--reason", required=True)
    replan = subparsers.add_parser("replan")
    replan.add_argument("--plan", required=True, type=Path, help="old generation plan")
    replan.add_argument("--state", required=True, type=Path, help="old state")
    replan.add_argument("--new-plan", required=True, type=Path)
    replan.add_argument("--new-state", required=True, type=Path)
    prepare = subparsers.add_parser("prepare-review")
    prepare.add_argument("--plan", required=True, type=Path)
    prepare.add_argument("--state", required=True, type=Path)
    prepare.add_argument("--delivery-plan", required=True, type=Path)
    prepare.add_argument("--review", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        plan = load_json(args.plan)
        if args.command == "init":
            require(not args.state.expanduser().exists(),
                    "state file already exists; refusing to overwrite approvals")
            state = build_initial_state(plan)
            atomic_write(args.state, state)
            result = {"status": "ok", "stage": state["stage"], "state": str(args.state)}
        else:
            state = load_json(args.state)
            if args.command == "approve-layout":
                approve_layout(plan, state, args.file, args.svg, args.revision, args.approved_by, args.evidence, args.approval_source)
                atomic_write(args.state, state)
                result = {"status": "ok", "layout": state["approvals"]["layout"]}
            elif args.command == "approve-package":
                approve_package(plan, state, args.approved_by, args.evidence, args.approval_source)
                atomic_write(args.state, state)
                result = {"status": "ok", "stage": state["stage"]}
            elif args.command == "can-run":
                result = can_run(plan, state, args.asset_id)
            elif args.command in {"revise", "reject", "reopen"}:
                affected = revise_assets(plan,state,args.asset_id,args.reason)
                atomic_write(args.state,state)
                result = {"status":"ok","affected_assets":affected,"video":"invalidated"}
            elif args.command == "replan":
                require(not args.new_state.exists(), "new state path exists; preserve it and choose a new path")
                migrated = migrate_state(plan,state,load_json(args.new_plan))
                atomic_write(args.new_state,migrated)
                result = {"status":"ok","state":str(args.new_state.resolve()),"reused":migrated["history"][-1]["reused"]}
            elif args.command == "prepare-review":
                from plan_delivery import review_template
                validate_state(plan,state)
                require(not args.review.exists(), "review output already exists; use a new revision")
                review = review_template(load_json(args.delivery_plan))
                review["scheme_sha256"] = plan.get("scheme_sha256")
                for record in review["assets"]:
                    asset_id = record["id"]
                    asset = state["assets"][asset_id]
                    require(content_current(asset), f"current file required: {asset_id}")
                    task = resolve_task(plan,state,asset_id)
                    refs = list(task.get("reference_images",[]))
                    if task.get("source"):
                        refs.append(task["source"])
                    record.update(path=asset["generated_file"],image_sha256=asset["generated_sha256"],
                                  authority_refs=refs,authority_sha256={r:file_digest(r) for r in refs})
                atomic_write(args.review,review)
                result = {"status":"pending_visual_review","review":str(args.review.resolve())}
            elif args.command == "record-generated":
                state = record_generated(plan, state, args.asset_id, args.file)
                atomic_write(args.state, state)
                result = {"status": "ok", "stage": state["stage"], "asset_id": args.asset_id}
            elif args.command == "approve-primary":
                state = approve_primary(
                    plan, state, args.asset_id, args.approved_by,
                    args.evidence, args.approval_source,
                )
                atomic_write(args.state, state)
                result = {"status": "ok", "stage": state["stage"], "asset_id": args.asset_id}
            elif args.command == "sync-state":
                state = sync_state(plan, state)
                atomic_write(args.state, state)
                result = {"status": "ok", "stage": state["stage"],
                          "state_version": state["state_version"]}
            elif args.command == "record-package-review":
                delivery_plan = load_json(args.delivery_plan)
                review = load_json(args.review)
                state = record_package_review(
                    plan, state, delivery_plan, review,
                    args.delivery_plan, args.review,
                    require_files=not args.allow_missing_files,
                )
                atomic_write(args.state, state)
                result = {"status": "ok", "stage": state["stage"],
                          "review_status": state["package_review"]["status"]}
            elif args.command == "authorize-final-export":
                state = authorize_final_export(
                    plan, state, args.approved_by, args.evidence,
                    args.approval_source,
                )
                atomic_write(args.state, state)
                result = {"status": "ok", "stage": state["stage"]}
            else:
                result = can_export(plan, state)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, json.JSONDecodeError, DeliveryStateError, DeliveryReviewError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
