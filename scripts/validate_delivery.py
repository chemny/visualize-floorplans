#!/usr/bin/env python3
"""Validate structural and multi-image consistency review for a delivery plan."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from review_contract import required_checks, PACKAGE_CHECKS


class DeliveryReviewError(ValueError):
    pass


def plan_digest(plan: dict[str, Any]) -> str:
    payload = json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DeliveryReviewError(message)


def strict_check(value: Any, label: str, failures: list[str]) -> None:
    require(isinstance(value, dict), f"{label} must be an object with passed and evidence")
    passed = value.get("passed")
    evidence = value.get("evidence")
    require(isinstance(passed, bool), f"{label}.passed must be true or false")
    require(isinstance(evidence, str) and evidence.strip(),
            f"{label}.evidence must be a non-empty string")
    if not passed:
        failures.append(label)


def validate_delivery(plan: dict[str, Any], review: dict[str, Any],
                      require_files: bool = False) -> dict[str, Any]:
    planned_assets = plan.get("assets", [])
    require(isinstance(planned_assets, list) and planned_assets,
            "plan.assets must be a non-empty list")
    plan_version = plan.get("delivery_plan_version")
    review_version = review.get("delivery_review_version")
    if plan_version == "0.3":
        require(review_version == "0.3",
                "delivery plan 0.3 requires delivery review 0.3; review downgrade is not allowed")
        require(review.get("delivery_plan_sha256") == plan_digest(plan),
                "delivery review is stale or belongs to a different delivery plan")
        for index, item in enumerate(planned_assets):
            require(isinstance(item.get("kind"), str) and item["kind"].strip(),
                    f"plan asset {index} requires kind")
            require(item.get("substitution_policy") == "forbidden",
                    f"plan asset {item.get('id', index)} must forbid silent substitution")
            require(isinstance(item.get("structural_lock_ids"), list) and
                    item["structural_lock_ids"],
                    f"plan asset {item.get('id', index)} requires structural_lock_ids")
            require(isinstance(item.get("must_not_change"), list) and
                    item["must_not_change"],
                    f"plan asset {item.get('id', index)} requires must_not_change")
    planned_ids = [item["id"] for item in planned_assets]
    require(len(planned_ids) == len(set(planned_ids)), "plan asset ids must be unique")
    plan_by_id = {item["id"]: item for item in planned_assets}
    records = review.get("assets")
    require(isinstance(records, list), "review.assets must be a list")
    by_id = {record.get("id"): record for record in records if isinstance(record, dict)}
    require(len(records) == len(by_id), "review asset ids must be unique")
    require(set(by_id) == set(planned_ids),
            "review must contain every planned asset exactly once")

    strict = review_version == "0.3"

    failures: list[str] = []
    for asset_id in planned_ids:
        planned = plan_by_id[asset_id]
        record = by_id[asset_id]
        path = record.get("path")
        require(isinstance(path, str), f"{asset_id}.path must be a string")
        if require_files:
            require(bool(path) and Path(path).expanduser().is_file(), f"asset file not found: {asset_id}")
        checks = record.get("hard_checks")
        require(isinstance(checks, dict) and checks, f"{asset_id}.hard_checks must be an object")
        if strict:
            require(required_checks(planned.get("kind")) <= set(checks),
                    f"{asset_id}: missing required inspection checks")
            planned_kind = record.get("planned_kind")
            actual_kind = record.get("actual_kind")
            require(planned_kind == planned.get("kind"),
                    f"{asset_id}.planned_kind must match plan kind {planned.get('kind')}")
            require(isinstance(actual_kind, str) and actual_kind.strip(),
                    f"{asset_id}.actual_kind must be a non-empty string")
            require(actual_kind == planned_kind,
                    f"{asset_id}.actual_kind {actual_kind!r} does not match planned_kind {planned_kind!r}; re-plan the asset instead of silently substituting it")
            authority_refs = record.get("authority_refs")
            require(isinstance(authority_refs, list) and authority_refs and
                    all(isinstance(item, str) and item.strip() for item in authority_refs),
                    f"{asset_id}.authority_refs must contain reviewed source references")
            require(record.get("inspection_method") == "visual_comparison",
                    f"{asset_id}: actual visual_comparison is required")
            require(isinstance(record.get("observations"),str) and record["observations"].strip(),
                    f"{asset_id}: specific visual observations required")
            require(record.get("issues") == [], f"{asset_id}: resolve reported visual issues before passing")
            if require_files:
                from PIL import Image
                with Image.open(Path(path).expanduser()) as image:
                    image.verify()
                require(record.get("image_sha256") == hashlib.sha256(Path(path).expanduser().read_bytes()).hexdigest(),
                        f"{asset_id}: reviewed image content changed or hash missing")
                hashes = record.get("authority_sha256",{})
                require(isinstance(hashes,dict) and set(hashes) == set(authority_refs),
                        f"{asset_id}: authority hashes must cover every inspected reference")
                for reference in authority_refs:
                    authority = Path(reference).expanduser()
                    require(authority.is_file() and hashes[reference] == hashlib.sha256(authority.read_bytes()).hexdigest(),
                            f"{asset_id}: reviewed authority changed or missing")
            if record.get("exception") is not None:
                exception = record["exception"]
                require(isinstance(exception, dict), f"{asset_id}.exception must be null or an object")
                require(isinstance(exception.get("reason"), str) and exception["reason"].strip(),
                        f"{asset_id}.exception.reason is required")
                require(exception.get("approved_by_user") is True,
                        f"{asset_id}.exception must be explicitly approved by the user")
            for name, value in checks.items():
                strict_check(value, f"{asset_id}:{name}", failures)
        else:
            for name, passed in checks.items():
                require(isinstance(passed, bool), f"{asset_id}.{name} must be true or false")
                if not passed:
                    failures.append(f"{asset_id}:{name}")

    consistency = review.get("package_consistency")
    require(isinstance(consistency, dict) and consistency,
            "package_consistency must be an object")
    if strict:
        require(PACKAGE_CHECKS <= set(consistency), "missing required package consistency checks")
        for name, value in consistency.items():
            strict_check(value, f"package:{name}", failures)
    else:
        for name, passed in consistency.items():
            require(isinstance(passed, bool), f"package_consistency.{name} must be true or false")
            if not passed:
                failures.append(f"package:{name}")

    approved_exceptions = review.get("exceptions", []) if strict else []
    require(isinstance(approved_exceptions, list), "review.exceptions must be a list")
    for index, exception in enumerate(approved_exceptions):
        require(isinstance(exception, dict), f"review exception {index} must be an object")
        require(isinstance(exception.get("reason"), str) and exception["reason"].strip(),
                f"review exception {index} requires reason")
        require(exception.get("approved_by_user") is True,
                f"review exception {index} must be explicitly approved by the user")

    require(not failures, "delivery review failed: " + ", ".join(failures))
    exception_count = len(approved_exceptions) + sum(
        1 for record in records if isinstance(record, dict) and record.get("exception") is not None
    )
    return {
        "status": "ok_with_approved_exceptions" if exception_count else "ok",
        "asset_count": len(planned_ids),
        "structural_gate": "passed",
        "consistency_gate": "passed",
        "exception_count": exception_count,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--require-files", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        plan = json.loads(args.plan.expanduser().read_text(encoding="utf-8"))
        review = json.loads(args.review.expanduser().read_text(encoding="utf-8"))
        result = validate_delivery(plan, review, args.require_files)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, json.JSONDecodeError, DeliveryReviewError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
