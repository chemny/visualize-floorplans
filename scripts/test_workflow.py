#!/usr/bin/env python3
"""Local regression tests for the V0 floor-plan planning workflow."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name("plan_project.py")
SPEC = importlib.util.spec_from_file_location("plan_project", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

ROUTE_SCRIPT_PATH = Path(__file__).with_name("validate_route.py")
ROUTE_SPEC = importlib.util.spec_from_file_location("validate_route", ROUTE_SCRIPT_PATH)
ROUTE_MODULE = importlib.util.module_from_spec(ROUTE_SPEC)
assert ROUTE_SPEC.loader is not None
ROUTE_SPEC.loader.exec_module(ROUTE_MODULE)

RECOGNITION_SCRIPT_PATH = Path(__file__).with_name("validate_recognition.py")
RECOGNITION_SPEC = importlib.util.spec_from_file_location(
    "validate_recognition", RECOGNITION_SCRIPT_PATH
)
RECOGNITION_MODULE = importlib.util.module_from_spec(RECOGNITION_SPEC)
assert RECOGNITION_SPEC.loader is not None
RECOGNITION_SPEC.loader.exec_module(RECOGNITION_MODULE)

ACCESS_SCRIPT_PATH = Path(__file__).with_name("validate_access.py")
ACCESS_SPEC = importlib.util.spec_from_file_location("validate_access", ACCESS_SCRIPT_PATH)
ACCESS_MODULE = importlib.util.module_from_spec(ACCESS_SPEC)
assert ACCESS_SPEC.loader is not None
ACCESS_SPEC.loader.exec_module(ACCESS_MODULE)

DELIVERY_SCRIPT_PATH = Path(__file__).with_name("plan_delivery.py")
DELIVERY_SPEC = importlib.util.spec_from_file_location("plan_delivery", DELIVERY_SCRIPT_PATH)
DELIVERY_MODULE = importlib.util.module_from_spec(DELIVERY_SPEC)
assert DELIVERY_SPEC.loader is not None
DELIVERY_SPEC.loader.exec_module(DELIVERY_MODULE)

DELIVERY_VALIDATOR_PATH = Path(__file__).with_name("validate_delivery.py")
DELIVERY_VALIDATOR_SPEC = importlib.util.spec_from_file_location(
    "validate_delivery", DELIVERY_VALIDATOR_PATH
)
DELIVERY_VALIDATOR_MODULE = importlib.util.module_from_spec(DELIVERY_VALIDATOR_SPEC)
assert DELIVERY_VALIDATOR_SPEC.loader is not None
DELIVERY_VALIDATOR_SPEC.loader.exec_module(DELIVERY_VALIDATOR_MODULE)

DELIVERY_STATE_PATH = Path(__file__).with_name("delivery_state.py")
DELIVERY_STATE_SPEC = importlib.util.spec_from_file_location(
    "delivery_state_test", DELIVERY_STATE_PATH
)
DELIVERY_STATE_MODULE = importlib.util.module_from_spec(DELIVERY_STATE_SPEC)
assert DELIVERY_STATE_SPEC.loader is not None
DELIVERY_STATE_SPEC.loader.exec_module(DELIVERY_STATE_MODULE)


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.test_files = tempfile.TemporaryDirectory()
        self.addCleanup(self.test_files.cleanup)
    @classmethod
    def setUpClass(cls) -> None:
        sample_path = Path(__file__).parents[1] / "assets" / "sample-project.json"
        cls.sample = json.loads(sample_path.read_text(encoding="utf-8"))

    def test_sample_compiles_with_dependency_chain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "floorplan.png"
            image.write_bytes(b"not-decoded-by-dry-run")
            manifest_path = root / "project.json"
            data = copy.deepcopy(self.sample)
            data["input_image"] = str(image)
            manifest_path.write_text(json.dumps(data), encoding="utf-8")
            # This historical sample contains placeholder authority paths.
            # Live complete-bundle validation is covered by test_interpretation.py.
            source = MODULE.validate_manifest(data, manifest_path, True)
            plan = MODULE.compile_plan(data, source)

        expected = 1 + len(data["outputs"]["room_views"]) + len(data["outputs"]["style_variants"])
        self.assertEqual(plan["task_count"], expected)
        self.assertEqual(plan["tasks"][0]["kind"], "canonical")
        self.assertEqual(len(plan["tasks"][0]["reference_images"]), 3)
        for task in plan["tasks"][1:]:
            self.assertEqual(task["depends_on"], ["canonical-cutaway-birdseye"])
            self.assertEqual(len(task["reference_images"]), 3)

    def test_unselected_style_compiles_only_one_four_panel_preview(self) -> None:
        data = copy.deepcopy(self.sample)
        data["design"]["selected_style"] = None
        plan = MODULE.compile_plan(data, Path("/tmp/floorplan.png"))
        self.assertEqual(plan["task_count"], 1)
        self.assertEqual(plan["tasks"][0]["kind"], "style_preview")
        self.assertEqual(plan["tasks"][0]["output"], "outputs/styles/four-style-preview.png")
        prompt = plan["tasks"][0]["request"]["prompt"]
        self.assertIn("strict 2x2 grid", prompt)
        for label in ("现代简约", "原木奶油", "现代轻奢", "现代新中式"):
            self.assertIn(label, prompt)

    def test_detailed_plan_requires_selected_style(self) -> None:
        plan = MODULE.compile_plan(self.sample, Path("/tmp/floorplan.png"))
        self.assertEqual(plan["selected_style"], "wood_cream")
        self.assertEqual(plan["tasks"][0]["kind"], "canonical")
        self.assertIn("原木奶油", plan["tasks"][0]["request"]["prompt"])

    def test_twelve_default_styles_compile_three_boards_without_omissions(self):
        template = json.loads((Path(MODULE.__file__).parents[1]/"assets/project-template.json").read_text())
        data = copy.deepcopy(self.sample)
        data["design"]["style_options"] = template["design"]["style_options"]
        data["design"]["selected_style"] = None
        data["outputs"]["style_preview"] = "style_comparison_boards"
        MODULE.validate_manifest(data, Path("/tmp/project.json"), True)
        plan = MODULE.compile_plan(data, Path("/tmp/floorplan.png"))
        self.assertEqual(plan["task_count"], 3)
        ids = [item for task in plan["tasks"] for item in task["style_ids"]]
        self.assertEqual(ids, [o["id"] for o in template["design"]["style_options"]])
        self.assertEqual(len(set(t["output"] for t in plan["tasks"])), 3)
        self.assertEqual([x for t in plan["tasks"] for x in t["panel_labels"]], list("ABCDEFGHIJKL"))
        self.assertTrue(all(t["reference_images"] == plan["tasks"][0]["reference_images"] for t in plan["tasks"]))
        data["design"]["selected_style"] = "champagne_pearl"
        chosen = MODULE.compile_plan(data, Path("/tmp/floorplan.png"))
        self.assertTrue(all(t["kind"] != "style_preview" for t in chosen["tasks"]))
        self.assertIn("香槟珍珠", chosen["tasks"][0]["request"]["prompt"])
        data["outputs"]["style_preview"] = "four_style_grid"
        with self.assertRaises(MODULE.ManifestError):
            MODULE.validate_manifest(data, Path("/tmp/project.json"), True)

    def test_rejects_empty_room_list(self) -> None:
        data = copy.deepcopy(self.sample)
        data["floor_plan"]["rooms"] = []
        with self.assertRaises(MODULE.ManifestError):
            MODULE.validate_manifest(data, Path("/tmp/project.json"), True)

    def test_rejects_invalid_size(self) -> None:
        data = copy.deepcopy(self.sample)
        data["outputs"]["size"] = "1537x1024"
        with self.assertRaises(MODULE.ManifestError):
            MODULE.validate_manifest(data, Path("/tmp/project.json"), True)

    def test_new_project_template_is_not_generation_ready(self) -> None:
        template_path = Path(__file__).parents[1] / "assets" / "project-template.json"
        template = json.loads(template_path.read_text(encoding="utf-8"))
        self.assertEqual(template["interpretation_artifacts"]["status"], "unconfirmed")
        self.assertEqual(template["structural_locks"], [])
        with self.assertRaises(MODULE.ManifestError):
            MODULE.validate_manifest(template, template_path, True)

    def test_rejects_confirmation_for_stale_interpretation_version(self) -> None:
        data = copy.deepcopy(self.sample)
        data["interpretation_artifacts"]["artifact_version"] = "interpretation-v2"
        with self.assertRaisesRegex(MODULE.ManifestError, "current artifact version"):
            MODULE.validate_manifest(data, Path("/tmp/project.json"), True)

    def test_rejects_confirmation_with_missing_access_scope(self) -> None:
        data = copy.deepcopy(self.sample)
        access_scope = data["interpretation_artifacts"]["confirmation"]["scopes"]["access_elements"]
        access_scope["status"] = "unconfirmed"
        access_scope["confirmed_item_ids"] = []
        with self.assertRaisesRegex(MODULE.ManifestError, "access_elements is not confirmed"):
            MODULE.validate_manifest(data, Path("/tmp/project.json"), True)

    def test_rejects_consequential_unresolved_confirmation_item(self) -> None:
        data = copy.deepcopy(self.sample)
        data["interpretation_artifacts"]["confirmation"]["unresolved_items"] = [
            "D2 opening direction remains unknown"
        ]
        with self.assertRaisesRegex(MODULE.ManifestError, "remain unresolved"):
            MODULE.validate_manifest(data, Path("/tmp/project.json"), True)

    def test_prompts_preserve_conceptual_boundary(self) -> None:
        plan = MODULE.compile_plan(self.sample, Path("/tmp/floorplan.png"))
        prompts = "\n".join(task["request"]["prompt"] for task in plan["tasks"])
        self.assertIn("not a construction drawing or precise 3D model", prompts)
        self.assertIn("Do not add, remove, merge, or split rooms", prompts)
        self.assertIn("[lock-balcony-adjacency]", prompts)

    def test_rejects_unconfirmed_or_unsupported_structural_lock(self) -> None:
        data = copy.deepcopy(self.sample)
        data["structural_locks"][0]["status"] = "uncertain"
        with self.assertRaises(MODULE.ManifestError):
            MODULE.validate_manifest(data, Path("/tmp/project.json"), True)

    def test_schema_02_legacy_locked_elements_remain_compatible(self) -> None:
        data = copy.deepcopy(self.sample)
        data["schema_version"] = "0.2"
        data.pop("structural_locks")
        data["locked_elements"] = [
            "Preserve room count",
            "Preserve walls and openings",
            "Preserve room adjacency",
        ]
        MODULE.validate_manifest(data, Path("/tmp/project.json"), True)
        plan = DELIVERY_MODULE.compile_delivery(data)
        self.assertTrue(all(item["must_not_change"] for item in plan["assets"]))

        data = copy.deepcopy(self.sample)
        data["structural_locks"][0]["source"] = "conversation_memory"
        with self.assertRaises(MODULE.ManifestError):
            MODULE.validate_manifest(data, Path("/tmp/project.json"), True)

    def test_workflow_preserves_confirmation_and_defers_route(self) -> None:
        skill_root = Path(__file__).parents[1]
        skill_text = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        prompt_text = (skill_root / "references" / "prompt-contracts.md").read_text(
            encoding="utf-8"
        )
        stage_one = skill_text.index("## Stage 1: confirm the reconstructed floor plan")
        source_check = skill_text.index("Present the reconstructed plan beside the source")
        combined_confirmation = skill_text.index("One confirmation may cover both")
        stage_two = skill_text.index("## Stage 2: create and confirm one coordinated renovation scheme")
        canonical_step = skill_text.index("Generate the detailed canonical")
        stage_three = skill_text.index("## Stage 3: confirm a route and validate a continuous video")
        self.assertLess(stage_one, source_check)
        self.assertLess(source_check, combined_confirmation)
        self.assertLess(combined_confirmation, stage_two)
        self.assertLess(stage_two, canonical_step)
        self.assertLess(canonical_step, stage_three)
        self.assertIn("do not ask\nagain for already recorded items", skill_text)
        self.assertIn("never as “一镜到底”", skill_text)
        self.assertIn("## Normalized 2D top-down reference plan", prompt_text)
        self.assertIn("## Door and passage overlay", prompt_text)
        self.assertIn("## Style selection boards", prompt_text)
        self.assertIn("## Property-tour route overlay", prompt_text)

    def valid_topology(self) -> dict:
        return {
            "zones": [
                {
                    "id": "outside",
                    "label": "户外",
                    "kind": "outside",
                    "certainty": "confirmed",
                    "evidence": ["special exterior node"],
                },
                {
                    "id": "living",
                    "label": "客厅",
                    "kind": "living_room",
                    "certainty": "confirmed",
                    "evidence": ["user confirmed"],
                },
                {
                    "id": "bedroom",
                    "label": "主卧",
                    "kind": "primary_bedroom",
                    "certainty": "confirmed",
                    "evidence": ["user confirmed"],
                },
            ],
            "access_points": [
                {
                    "id": "entry",
                    "kind": "entrance_door",
                    "connects": ["outside", "living"],
                    "hinge_location": "source-image left jamb",
                    "swing_into": "living",
                    "certainty": "confirmed",
                    "evidence": ["visible door and user confirmation"],
                },
                {
                    "id": "bedroom-door",
                    "kind": "interior_door",
                    "connects": ["living", "bedroom"],
                    "hinge_location": "source-image right jamb",
                    "swing_into": "bedroom",
                    "certainty": "confirmed",
                    "evidence": ["visible door swing"],
                },
            ],
            "tour_route": {
                "entry_access": "entry",
                "exit_access": "entry",
                "steps": [
                    {"order": 1, "from": "outside", "to": "living", "via": "entry"},
                    {"order": 2, "from": "living", "to": "bedroom", "via": "bedroom-door"},
                    {"order": 3, "from": "bedroom", "to": "living", "via": "bedroom-door"},
                    {"order": 4, "from": "living", "to": "outside", "via": "entry"},
                ],
            },
        }

    def test_route_validator_accepts_continuous_door_graph(self) -> None:
        result = ROUTE_MODULE.validate_topology(self.valid_topology())
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["entry_access"], "entry")
        self.assertEqual(result["exit_access"], "entry")

    def test_access_validator_accepts_connected_home_without_using_route(self) -> None:
        topology = self.valid_topology()
        topology.pop("tour_route")
        result = ACCESS_MODULE.validate_access(topology)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["reachable_zone_count"], 3)

    def test_access_validator_rejects_missing_swing_direction(self) -> None:
        topology = self.valid_topology()
        topology.pop("tour_route")
        topology["access_points"][1].pop("swing_into")
        with self.assertRaises(ACCESS_MODULE.AccessError):
            ACCESS_MODULE.validate_access(topology)

    def test_access_validator_rejects_inaccessible_room(self) -> None:
        topology = self.valid_topology()
        topology.pop("tour_route")
        topology["access_points"] = topology["access_points"][:1]
        with self.assertRaises(ACCESS_MODULE.AccessError):
            ACCESS_MODULE.validate_access(topology)

    def test_access_proposal_can_use_uncertain_edges_when_explicitly_allowed(self) -> None:
        topology = self.valid_topology()
        topology.pop("tour_route")
        topology["access_points"][1]["certainty"] = "uncertain"
        result = ACCESS_MODULE.validate_access(topology, allow_uncertain=True)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["reachable_zone_count"], 3)

    def test_route_validator_rejects_wall_crossing_without_access(self) -> None:
        topology = self.valid_topology()
        topology["tour_route"]["steps"][1]["via"] = "missing-door"
        with self.assertRaises(ROUTE_MODULE.TopologyError):
            ROUTE_MODULE.validate_topology(topology)

    def test_route_validator_rejects_uncertain_access(self) -> None:
        topology = self.valid_topology()
        topology["access_points"][1]["certainty"] = "uncertain"
        with self.assertRaises(ROUTE_MODULE.TopologyError):
            ROUTE_MODULE.validate_topology(topology)

    def test_ontology_contains_industry_roles_and_no_invention_rule(self) -> None:
        ontology = (
            Path(__file__).parents[1] / "references" / "residential-space-ontology.md"
        ).read_text(encoding="utf-8")
        for label in ("主卧", "次卧", "书房", "主卫", "公卫", "飘窗", "阳台", "露台"):
            self.assertIn(label, ontology)
        self.assertIn("never fill exterior blank space", ontology)

    def sample_recognition(self) -> dict:
        path = Path(__file__).parents[1] / "assets" / "sample-recognition.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_recognition_validator_accepts_evidence_based_elements(self) -> None:
        result = RECOGNITION_MODULE.validate_recognition(self.sample_recognition())
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["traversable_element_count"], 1)

    def test_recognition_validator_rejects_gap_promoted_to_door(self) -> None:
        data = self.sample_recognition()
        data["elements"][0]["evidence_codes"] = ["solid_wall_continuity"]
        with self.assertRaises(RECOGNITION_MODULE.RecognitionError):
            RECOGNITION_MODULE.validate_recognition(data)

    def test_recognition_validator_rejects_window_as_traversable(self) -> None:
        data = self.sample_recognition()
        data["elements"][1]["traversable"] = True
        with self.assertRaises(RECOGNITION_MODULE.RecognitionError):
            RECOGNITION_MODULE.validate_recognition(data)

    def test_recognition_validator_rejects_physical_dashed_line(self) -> None:
        data = self.sample_recognition()
        data["linework"][1]["physical"] = True
        with self.assertRaises(RECOGNITION_MODULE.RecognitionError):
            RECOGNITION_MODULE.validate_recognition(data)

    def test_door_candidate_requires_zone_adjacency_and_is_not_traversable(self) -> None:
        data = self.sample_recognition()
        data["elements"].append({
            "id": "door-candidate-1",
            "kind": "door_candidate",
            "certainty": "uncertain",
            "traversable": False,
            "evidence_codes": ["bounded_polygon", "adjacency", "inferred_pattern"],
        })
        result = RECOGNITION_MODULE.validate_recognition(data)
        self.assertEqual(result["traversable_element_count"], 1)

    def test_skill_orders_recognition_before_room_naming(self) -> None:
        skill_text = (Path(__file__).parents[1] / "SKILL.md").read_text(encoding="utf-8")
        graph_step = skill_text.index("Build a wall-junction graph")
        function_step = skill_text.index("Attach functional names")
        self.assertLess(graph_step, function_step)

    def test_delivery_planner_builds_base_plus_adaptive_package(self) -> None:
        plan = DELIVERY_MODULE.compile_delivery(copy.deepcopy(self.sample))
        asset_ids = {item["id"] for item in plan["assets"]}
        self.assertEqual(plan["standard"], "base_plus_floorplan_adaptive")
        self.assertIn("structure-reference-plan", asset_ids)
        self.assertIn("furnished-floor-plan", asset_ids)
        self.assertIn("primary-birdseye", asset_ids)
        self.assertIn("complementary-birdseye", asset_ids)
        self.assertIn("living-toward-daylight", asset_ids)
        self.assertIn("public-reverse", asset_ids)
        self.assertIn("primary-bedroom", asset_ids)
        self.assertIn("kitchen", asset_ids)
        self.assertIn("room-second-bedroom", asset_ids)
        self.assertIn("room-balcony", asset_ids)
        self.assertNotIn("room-bathroom", asset_ids)
        self.assertTrue(all(item["camera_intent"] for item in plan["assets"]))
        self.assertTrue(all(item["must_show"] for item in plan["assets"]))
        self.assertTrue(all(item["must_not_change"] for item in plan["assets"]))
        self.assertTrue(all(item["structural_lock_ids"] for item in plan["assets"]))
        kinds = {item["id"]: item["kind"] for item in plan["assets"]}
        self.assertEqual(kinds["structure-reference-plan"], "structure_reference_plan")
        self.assertEqual(kinds["furnished-floor-plan"], "furnished_colour_plan")

    def test_delivery_planner_can_omit_either_plan_without_substitution(self) -> None:
        data = copy.deepcopy(self.sample)
        data["delivery"]["include_furnished_plan"] = False
        plan = DELIVERY_MODULE.compile_delivery(data)
        asset_ids = {item["id"] for item in plan["assets"]}
        self.assertIn("structure-reference-plan", asset_ids)
        self.assertNotIn("furnished-floor-plan", asset_ids)

    def test_generation_plan_is_compiled_from_delivery_shot_list(self) -> None:
        delivery = DELIVERY_MODULE.compile_delivery(copy.deepcopy(self.sample))
        generation = MODULE.compile_plan(
            copy.deepcopy(self.sample), Path("/tmp/floorplan.png"), delivery
        )
        self.assertEqual(generation["plan_version"], "0.3")
        self.assertEqual(generation["source_delivery_plan_version"], "0.3")
        self.assertEqual(
            [task["delivery_asset_id"] for task in generation["tasks"]],
            [asset["id"] for asset in delivery["assets"]],
        )
        for task, asset in zip(generation["tasks"], delivery["assets"]):
            self.assertEqual(task["planned_kind"], asset["kind"])
            self.assertEqual(task["camera_intent"], asset["camera_intent"])
            self.assertEqual(task["must_show"], asset["must_show"])
            self.assertEqual(task["structural_lock_ids"], asset["structural_lock_ids"])
            self.assertEqual(task["must_not_change"], asset["must_not_change"])

        by_id = {task["id"]: task for task in generation["tasks"]}
        self.assertEqual(
            by_id["structure-reference-plan"]["execution_mode"],
            "deterministic_copy",
        )
        self.assertEqual(
            by_id["furnished-floor-plan"]["execution_mode"],
            "image_generation",
        )
        self.assertEqual(by_id["primary-birdseye"]["depends_on"], [])
        self.assertEqual(
            by_id["complementary-birdseye"]["depends_on"],
            ["primary-birdseye"],
        )
        self.assertEqual(
            by_id["room-second-bedroom"]["depends_on"],
            ["primary-birdseye"],
        )
        self.assertIn(
            "asset://primary-birdseye",
            by_id["room-second-bedroom"]["reference_images"],
        )

    def test_generation_plan_rejects_delivery_lock_drift(self) -> None:
        delivery = DELIVERY_MODULE.compile_delivery(copy.deepcopy(self.sample))
        delivery["assets"][0]["structural_lock_ids"].append("unknown-lock")
        with self.assertRaises(MODULE.ManifestError):
            MODULE.compile_plan(
                copy.deepcopy(self.sample), Path("/tmp/floorplan.png"), delivery
            )

    def test_generation_plan_rejects_project_mismatch(self) -> None:
        delivery = DELIVERY_MODULE.compile_delivery(copy.deepcopy(self.sample))
        delivery["project_id"] = "different-project"
        with self.assertRaises(MODULE.ManifestError):
            MODULE.compile_plan(
                copy.deepcopy(self.sample), Path("/tmp/floorplan.png"), delivery
            )

    def delivery_generation_plan(self) -> dict:
        delivery = DELIVERY_MODULE.compile_delivery(copy.deepcopy(self.sample))
        return MODULE.compile_plan(
            copy.deepcopy(self.sample), Path("/tmp/floorplan.png"), delivery
        )

    def test_primary_approval_state_blocks_and_unlocks_derived_tasks(self) -> None:
        plan = self.delivery_generation_plan()
        state = DELIVERY_STATE_MODULE.build_initial_state(plan)
        self.assertTrue(
            DELIVERY_STATE_MODULE.can_run(plan, state, "primary-birdseye")["runnable"]
        )
        blocked = DELIVERY_STATE_MODULE.can_run(
            plan, state, "complementary-birdseye"
        )
        self.assertFalse(blocked["runnable"])
        self.assertEqual(blocked["blocked_by"], ["primary-birdseye"])

        with tempfile.TemporaryDirectory() as directory:
            primary_file = Path(self.test_files.name) / "primary.png"
            primary_file.write_bytes(b"preview")
            DELIVERY_STATE_MODULE.record_generated(
                plan, state, "primary-birdseye", primary_file
            )
        self.assertEqual(state["stage"], "primary_pending_approval")
        self.assertFalse(
            DELIVERY_STATE_MODULE.can_run(
                plan, state, "complementary-birdseye"
            )["runnable"]
        )

        DELIVERY_STATE_MODULE.approve_primary(
            plan,
            state,
            "primary-birdseye",
            "user",
            "User confirmed the canonical structure and openings",
            "explicit_user_confirmation",
        )
        self.assertEqual(state["stage"], "primary_approved_derived_ready")
        self.assertTrue(
            DELIVERY_STATE_MODULE.can_run(
                plan, state, "complementary-birdseye"
            )["runnable"]
        )
        self.assertTrue(
            DELIVERY_STATE_MODULE.can_run(
                plan, state, "room-second-bedroom"
            )["runnable"]
        )

    def test_primary_approval_rejects_missing_generation_and_non_user_source(self) -> None:
        plan = self.delivery_generation_plan()
        state = DELIVERY_STATE_MODULE.build_initial_state(plan)
        with self.assertRaises(DELIVERY_STATE_MODULE.DeliveryStateError):
            DELIVERY_STATE_MODULE.approve_primary(
                plan, state, "primary-birdseye", "user", "looks correct",
                "explicit_user_confirmation",
            )

        with tempfile.TemporaryDirectory() as directory:
            primary_file = Path(directory) / "primary.png"
            primary_file.write_bytes(b"preview")
            DELIVERY_STATE_MODULE.record_generated(
                plan, state, "primary-birdseye", primary_file
            )
        with self.assertRaises(DELIVERY_STATE_MODULE.DeliveryStateError):
            DELIVERY_STATE_MODULE.approve_primary(
                plan, state, "primary-birdseye", "reviewer", "self review",
                "internal_review",
            )

    def test_delivery_state_rejects_generation_plan_drift(self) -> None:
        plan = self.delivery_generation_plan()
        state = DELIVERY_STATE_MODULE.build_initial_state(plan)
        changed = copy.deepcopy(plan)
        changed["tasks"][0]["camera_intent"] = "changed camera"
        with self.assertRaises(DELIVERY_STATE_MODULE.DeliveryStateError):
            DELIVERY_STATE_MODULE.validate_state(changed, state)

    def test_complete_package_requires_review_and_explicit_export_authorization(self) -> None:
        delivery = DELIVERY_MODULE.compile_delivery(copy.deepcopy(self.sample))
        plan = MODULE.compile_plan(
            copy.deepcopy(self.sample), Path("/tmp/floorplan.png"), delivery
        )
        state = DELIVERY_STATE_MODULE.build_initial_state(plan)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preview = root / "preview.png"
            preview.write_bytes(b"preview")

            for task in plan["tasks"]:
                if task["id"] == "primary-birdseye" or task["depends_on"]:
                    continue
                DELIVERY_STATE_MODULE.record_generated(
                    plan, state, task["id"], preview
                )
            DELIVERY_STATE_MODULE.record_generated(
                plan, state, "primary-birdseye", preview
            )
            DELIVERY_STATE_MODULE.approve_primary(
                plan, state, "primary-birdseye", "user",
                "User approved the primary birdseye",
                "explicit_user_confirmation",
            )
            for task in plan["tasks"]:
                if task["depends_on"]:
                    DELIVERY_STATE_MODULE.record_generated(
                        plan, state, task["id"], preview
                    )

            self.assertEqual(state["stage"], "package_pending_review")
            self.assertFalse(DELIVERY_STATE_MODULE.can_export(plan, state)["export_ready"])

            review = self.complete_delivery_review(delivery)
            delivery_path = root / "delivery-plan.json"
            review_path = root / "delivery-review.json"
            DELIVERY_STATE_MODULE.record_package_review(
                plan, state, delivery, review, delivery_path, review_path,
                require_files=False,
            )
            self.assertEqual(state["stage"], "package_review_passed")
            self.assertFalse(DELIVERY_STATE_MODULE.can_export(plan, state)["export_ready"])

            with self.assertRaises(DELIVERY_STATE_MODULE.DeliveryStateError):
                DELIVERY_STATE_MODULE.authorize_final_export(
                    plan, state, "user", "User approved the complete package",
                    "explicit_user_confirmation",
                )
            self.assertFalse(DELIVERY_STATE_MODULE.can_export(plan, state)["export_ready"])

    def test_state_01_upgrades_without_losing_primary_approval(self) -> None:
        plan = self.delivery_generation_plan()
        state = DELIVERY_STATE_MODULE.build_initial_state(plan)
        state["state_version"] = "0.1"
        state["approvals"].pop("package")
        state.pop("package_review")
        DELIVERY_STATE_MODULE.sync_state(plan, state)
        self.assertEqual(state["state_version"], "0.2")
        self.assertIn("package", state["approvals"])
        self.assertIn("package_review", state)

    def test_delivery_planner_adds_bathroom_only_when_requested(self) -> None:
        data = copy.deepcopy(self.sample)
        data["delivery"]["include_bathrooms"] = True
        plan = DELIVERY_MODULE.compile_delivery(data)
        self.assertIn("room-bathroom", {item["id"] for item in plan["assets"]})

    def test_delivery_planner_adds_third_birdseye_for_complex_layout(self) -> None:
        data = copy.deepcopy(self.sample)
        data["floor_plan"]["layout_traits"] = ["l_shaped"]
        plan = DELIVERY_MODULE.compile_delivery(data)
        self.assertIn("feature-side-birdseye", {item["id"] for item in plan["assets"]})

    def complete_delivery_review(self, plan: dict) -> dict:
        review = DELIVERY_MODULE.review_template(plan)
        for record in review["assets"]:
            record["path"] = ""
            record["actual_kind"] = record["planned_kind"]
            record["authority_refs"] = ["source plan", "approved access map"]
            record["inspection_method"] = "visual_comparison"
            record["observations"] = "Synthetic logical test only, no real image quality claim"
            for check in record["hard_checks"].values():
                check["passed"] = True
                check["evidence"] = "compared with approved authority references"
        for check in review["package_consistency"].values():
            check["passed"] = True
            check["evidence"] = "reviewed on the complete contact sheet"
        return review

    def test_delivery_validator_accepts_complete_review(self) -> None:
        plan = DELIVERY_MODULE.compile_delivery(copy.deepcopy(self.sample))
        result = DELIVERY_VALIDATOR_MODULE.validate_delivery(
            plan, self.complete_delivery_review(plan)
        )
        self.assertEqual(result["structural_gate"], "passed")
        self.assertEqual(result["consistency_gate"], "passed")

    def test_delivery_validator_rejects_structural_failure(self) -> None:
        plan = DELIVERY_MODULE.compile_delivery(copy.deepcopy(self.sample))
        review = self.complete_delivery_review(plan)
        review["assets"][0]["hard_checks"]["layout_matches_source"]["passed"] = False
        with self.assertRaises(DELIVERY_VALIDATOR_MODULE.DeliveryReviewError):
            DELIVERY_VALIDATOR_MODULE.validate_delivery(plan, review)

    def test_delivery_validator_rejects_silent_asset_kind_substitution(self) -> None:
        plan = DELIVERY_MODULE.compile_delivery(copy.deepcopy(self.sample))
        review = self.complete_delivery_review(plan)
        record = next(item for item in review["assets"] if item["id"] == "furnished-floor-plan")
        record["actual_kind"] = "structure_reference_plan"
        with self.assertRaises(DELIVERY_VALIDATOR_MODULE.DeliveryReviewError):
            DELIVERY_VALIDATOR_MODULE.validate_delivery(plan, review)

    def test_delivery_validator_rejects_boolean_without_evidence(self) -> None:
        plan = DELIVERY_MODULE.compile_delivery(copy.deepcopy(self.sample))
        review = self.complete_delivery_review(plan)
        review["assets"][0]["hard_checks"]["layout_matches_source"]["evidence"] = ""
        with self.assertRaises(DELIVERY_VALIDATOR_MODULE.DeliveryReviewError):
            DELIVERY_VALIDATOR_MODULE.validate_delivery(plan, review)

    def test_delivery_validator_rejects_review_schema_downgrade(self) -> None:
        plan = DELIVERY_MODULE.compile_delivery(copy.deepcopy(self.sample))
        review = self.complete_delivery_review(plan)
        review["delivery_review_version"] = "0.2"
        with self.assertRaises(DELIVERY_VALIDATOR_MODULE.DeliveryReviewError):
            DELIVERY_VALIDATOR_MODULE.validate_delivery(plan, review)

    def test_delivery_validator_rejects_stale_review_plan_hash(self) -> None:
        plan = DELIVERY_MODULE.compile_delivery(copy.deepcopy(self.sample))
        review = self.complete_delivery_review(plan)
        changed = copy.deepcopy(plan)
        changed["assets"][0]["title"] = "changed after review"
        with self.assertRaises(DELIVERY_VALIDATOR_MODULE.DeliveryReviewError):
            DELIVERY_VALIDATOR_MODULE.validate_delivery(changed, review)

    def test_delivery_validator_reports_approved_exception(self) -> None:
        plan = DELIVERY_MODULE.compile_delivery(copy.deepcopy(self.sample))
        review = self.complete_delivery_review(plan)
        review["exceptions"] = [{
            "reason": "Customer approved omitting a non-structural decor detail",
            "approved_by_user": True,
        }]
        result = DELIVERY_VALIDATOR_MODULE.validate_delivery(plan, review)
        self.assertEqual(result["status"], "ok_with_approved_exceptions")
        self.assertEqual(result["exception_count"], 1)

    def test_skill_exposes_delivery_standard_and_four_internal_modules(self) -> None:
        skill_root = Path(__file__).parents[1]
        skill_text = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        standard = (skill_root / "references" / "delivery-standard.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("base set plus floor-plan-aware expansion", skill_text)
        for module in (
            "Deliverable-list planner", "Camera selector",
            "Structural quality gate", "Multi-image consistency gate",
        ):
            self.assertIn(module, standard)


if __name__ == "__main__":
    unittest.main(verbosity=2)
