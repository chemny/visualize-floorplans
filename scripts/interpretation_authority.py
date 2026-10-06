"""Check the current floor-plan evidence bundle, without granting approval."""

import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from validate_access import validate_access, SWING_DOOR_KINDS
from validate_recognition import validate_recognition, TRAVERSABLE

ARTIFACTS = ("source_image", "topdown_base", "topdown_base_svg", "access_map", "zoning_plan", "recognition", "topology")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def object_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def project_facts(data):
    return {key: data.get(key) for key in ("floor_plan", "structural_locks", "input_assessment")}


def validate_assessment(data):
    assessment = data.get("input_assessment")
    require(isinstance(assessment, dict), "input_assessment required; assess the source before planning")
    require(assessment.get("condition") in {"readable", "partial", "critical_missing"},
            "input_assessment.condition must be readable, partial, or critical_missing")
    require(assessment.get("condition") != "critical_missing",
            "critical structure missing; request the minimum additional evidence")
    items = assessment.get("items")
    require(isinstance(items, list), "input_assessment.items must be a list")
    require(assessment["condition"] != "partial" or bool(items), "partial input requires recorded gaps or completions")
    ids = set()
    for item in items:
        require(isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"],
                "assessment item requires id")
        require(item["id"] not in ids, "duplicate assessment item id")
        ids.add(item["id"])
        require(item.get("origin") in {"source", "user", "hypothesis", "unknown"},
                "assessment origin must distinguish source, user, hypothesis, and unknown")
        require(isinstance(item.get("consequential"), bool), "assessment item needs consequential flag")
        require(isinstance(item.get("description"), str) and item["description"].strip(),
                "assessment item needs description")
        evidence = item.get("evidence")
        require(isinstance(evidence, list) and all(isinstance(x, str) and x.strip() for x in evidence),
                "assessment evidence must be a list of non-empty strings")
        if item["origin"] in {"source", "user"}:
            require(bool(evidence), f"{item['id']}: source/user facts require evidence")
        if item["origin"] == "hypothesis":
            approval = item.get("acceptance", {})
            require(isinstance(approval, dict) and approval.get("approval_source") == "explicit_user_confirmation"
                    and all(isinstance(approval.get(k), str) and approval[k].strip() for k in ("evidence", "confirmed_by")),
                    f"hypothesis {item['id']} needs explicit acceptance before generation")
        if item["consequential"]:
            require(item["origin"] != "unknown" and bool(evidence),
                    f"unresolved consequential item {item['id']}")


def resolve(root, value):
    require(isinstance(value, str) and value.strip(), "artifact path required")
    path = Path(value).expanduser()
    return (root / path).resolve() if not path.is_absolute() else path.resolve()


def inspect_bundle(data, manifest_path):
    """Read/validate current files. Returns a snapshot, never a user approval."""
    root = Path(manifest_path).resolve().parent
    artifacts = data["interpretation_artifacts"]
    require(isinstance(artifacts.get("confirmation"), dict) and bool(artifacts.get("artifact_version")),
            "legacy evidence needs a new versioned confirmation bundle; preserve original project")
    paths = {key: resolve(root, artifacts.get(key)) for key in ARTIFACTS}
    for key, path in paths.items():
        require(path.is_file(), f"{key} file not found: {path}")
    require(paths["topdown_base"].suffix.lower() == ".png", "topdown_base must be a PNG preview")
    require(paths["topdown_base_svg"].suffix.lower() == ".svg", "topdown_base_svg must be an editable SVG")
    require(paths["topdown_base"].stem == paths["topdown_base_svg"].stem,
            "topdown base SVG and PNG preview must use the same revision name")
    try:
        svg_root = ET.parse(paths["topdown_base_svg"]).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"topdown_base_svg is invalid XML: {exc}") from exc
    require(svg_root.tag.rsplit("}", 1)[-1] == "svg", "topdown_base_svg root element must be svg")
    require(paths["source_image"] == resolve(root, data["input_image"]), "source_image differs from input_image")
    recognition = json.loads(paths["recognition"].read_text(encoding='utf-8'))
    topology = json.loads(paths["topology"].read_text(encoding='utf-8'))
    validate_recognition(recognition)
    validate_access(topology)
    from PIL import Image
    from render_interpretation import validate_geometry
    for key in ("source_image", "topdown_base", "access_map", "zoning_plan"):
        with Image.open(paths[key]) as image:
            image.verify()
    with Image.open(paths["topdown_base"]) as base:
        validate_geometry(base, recognition)
        for key in ("access_map", "zoning_plan"):
            with Image.open(paths[key]) as overlay:
                require(overlay.size == base.size, f"{key}: overlay dimensions differ from fixed base")
    for record in (recognition, topology):
        require(record.get("artifact_version") == artifacts.get("artifact_version"),
                "recognition/topology artifact version differs from current interpretation")
    require(resolve(paths["recognition"].parent, recognition["source_image"]) == paths["source_image"],
            "recognition references a different source image")
    rz = {z["id"]: z for z in recognition["zones"]}
    tz = {z["id"]: z for z in topology["zones"]}
    rooms = {z["id"] for z in data["floor_plan"]["rooms"]}
    require(set(rz) == set(tz) and rooms == set(rz) - {"outside"},
            "room IDs differ between manifest, recognition, and topology")
    for zone_id in rz:
        require(rz[zone_id]["certainty"] == tz[zone_id]["certainty"] == "confirmed",
                f"zone {zone_id} is not consistently confirmed")
        require(rz[zone_id]["proposed_function"] == tz[zone_id]["kind"],
                f"zone {zone_id} has conflicting functions")
    for room in data["floor_plan"]["rooms"]:
        require(room.get("certainty") == "confirmed" and room.get("type") == tz[room["id"]]["kind"],
                f"room {room['id']} function/certainty differs from confirmed topology")
    elements = {e["id"]: e for e in recognition["elements"]}
    access = {e["id"]: e for e in topology["access_points"]}
    require(set(access) == {k for k, e in elements.items() if e["kind"] in TRAVERSABLE},
            "traversable element IDs differ between recognition and topology")
    for key, a in access.items():
        e = elements[key]
        fields = ["kind", "certainty", "connects"]
        if a["kind"] in SWING_DOOR_KINDS:
            fields += ["hinge_location", "swing_into"]
        if a["kind"] == "sliding_door":
            fields += ["slide_axis", "panel_evidence"]
        for field in fields:
            left, right = e.get(field), a.get(field)
            if field == "connects":
                left, right = sorted(left or []), sorted(right or [])
            require(left == right, f"{key}: conflicting or missing {field} between recognition and topology")
    scope = artifacts["confirmation"]["scopes"]
    require(rooms <= set(scope["structure_and_zones"]["confirmed_item_ids"]),
            "structure confirmation omits room IDs")
    opening_kinds = TRAVERSABLE | {"window", "bay_window", "fixed_glazing", "unknown_gap", "door_candidate"}
    opening_ids = {k for k, e in elements.items() if e["kind"] in opening_kinds}
    require(opening_ids <= set(scope["access_elements"]["confirmed_item_ids"]) <= set(elements),
            "access confirmation omits openings or references nonexistent elements")
    for key in opening_ids:
        require(elements[key]["certainty"] == "confirmed"
                and elements[key]["kind"] not in {"unknown_gap", "door_candidate"},
                f"opening {key} remains unresolved in recognition")
    return {key: {"path": str(path), "sha256": digest(path)} for key, path in paths.items()}


def validate_bundle(data, manifest_path):
    validate_assessment(data)
    snapshot = inspect_bundle(data, manifest_path)
    confirmation = data["interpretation_artifacts"]["confirmation"]
    self_check = confirmation.get("source_self_check", {})
    require(isinstance(self_check, dict) and self_check.get("method") == "visual_comparison"
            and isinstance(self_check.get("evidence"), str) and self_check["evidence"].strip(),
            "source_self_check requires visual_comparison and specific evidence; hashes alone are not source review")
    require(confirmation.get("artifact_sha256") == {k: v["sha256"] for k, v in snapshot.items()},
            "confirmed artifact content changed or missing hashes; review and confirm current files")
    require(confirmation.get("facts_sha256") == object_digest(project_facts(data)),
            "confirmed manifest facts changed or missing digest; review current facts")
    snapshot["manifest"] = {"path": str(Path(manifest_path).resolve()), "sha256": digest(manifest_path)}
    return snapshot


def check_snapshot(snapshot):
    for key, record in snapshot.items():
        path = Path(record["path"])
        require(path.is_file() and digest(path) == record["sha256"],
                f"current floor-plan authority changed or missing: {key}; re-plan after confirmation")


if __name__ == "__main__":
    import argparse
    import sys
    parser = argparse.ArgumentParser(description="Inspect current evidence and print candidate hashes; does not approve anything")
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.manifest.read_text(encoding='utf-8'))
        bundle = inspect_bundle(data, args.manifest)
        print(json.dumps({"status": "candidate_only", "artifact_sha256": {k: v["sha256"] for k,v in bundle.items()},
                          "facts_sha256": object_digest(project_facts(data))}, indent=2))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        sys.exit(2)
