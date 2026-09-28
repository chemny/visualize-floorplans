"""Synthetic regression tests for incomplete input, geometry, and authority."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
import interpretation_authority as authority
import render_interpretation as renderer
import plan_project


def fixture(root):
    """Create a coherent small home without borrowing case-specific geometry."""
    data = json.loads((Path(__file__).parents[1]/"assets/sample-project.json").read_text())
    data["input_image"] = str(root/"source.png")
    data["input_assessment"] = {"condition": "readable", "items": []}
    rooms = [{"id": "living", "name": "Living", "type": "living_room", "certainty": "confirmed"}]
    data["floor_plan"] = {"rooms": rooms, "relationships": [], "uncertainties": []}
    zones = [{"id": "outside", "proposed_function": "outside", "certainty": "confirmed", "evidence_codes": ["drawing_legend"]},
             {"id": "living", "proposed_function": "living_room", "certainty": "confirmed", "evidence_codes": ["bounded_polygon"],
              "render_polygon": [[20,20],[380,20],[380,280],[20,280]]}]
    door = {"id": "D1", "kind": "entrance_door", "certainty": "confirmed", "traversable": True,
            "evidence_codes": ["door_leaf", "swing_arc"], "connects": ["outside","living"],
            "hinge_location": "left jamb", "swing_into": "living", "render_point": [90,260],
            "render_geometry": {"hinge": [60,270], "closed_tip": [120,270], "open_tip": [60,210], "arc_direction": "counterclockwise"}}
    elements = [door]
    for name, kind, x in [("W1","window",170),("S1","sliding_door",250),("O1","open_passage",330)]:
        elements.append({"id": name,"kind":kind,"certainty":"confirmed", "traversable":kind != "window",
                         "evidence_codes": ["user_confirmed", "parallel_frame_lines"],
                         "connects":["outside","living"], "render_point":[x,80],
                         "render_geometry":{"start":[x-25,90],"end":[x+25,90]}})
    elements[2].update(slide_axis="horizontal",panel_evidence="visible parallel sliding panels")
    elements.append({"id":"B1","kind":"bay_window","certainty":"confirmed","traversable":False,
                     "evidence_codes":["exterior_projection","parallel_frame_lines"],"render_point":[240,190],
                     "render_geometry":{"outline":[[200,200],[200,160],[280,160],[280,200]]}})
    recognition = {"schema_version":"0.2","artifact_version":"interpretation-v1", "source_image":str(root/"source.png"),
                   "linework":[],"zones":zones,"elements":elements, "coverage_polygon":zones[1]["render_polygon"]}
    topology = {"artifact_version":"interpretation-v1", "zones":[{"id":z["id"],"label":z["id"],"kind":z["proposed_function"],
                "certainty":"confirmed","evidence":["synthetic fixture"]} for z in zones],
                "access_points":[dict(e, evidence=["synthetic fixture"]) for e in elements if e["traversable"]]}
    art = data["interpretation_artifacts"]
    art["confirmation"]["source_self_check"] = {"method":"visual_comparison", "evidence":"Synthetic fixture only; production requires actual source review"}
    for key in authority.ARTIFACTS:
        art[key] = str(root/(key+ (".json" if key in {"recognition","topology"} else ".png")))
    art["topdown_base"] = str(root/"topdown-base-v1.png")
    art["topdown_base_svg"] = str(root/"topdown-base-v1.svg")
    art["source_image"] = data["input_image"]
    art["confirmation"]["scopes"]["structure_and_zones"]["confirmed_item_ids"] = ["living"]
    art["confirmation"]["scopes"]["access_elements"]["confirmed_item_ids"] = [e["id"] for e in elements]
    for key in ("source_image","topdown_base","access_map","zoning_plan"):
        Image.new("RGB",(400,300),"white").save(art[key])
    Path(art["topdown_base_svg"]).write_text('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300"><path d="M20 20H380V280H20Z"/></svg>')
    Path(art["recognition"]).write_text(json.dumps(recognition))
    Path(art["topology"]).write_text(json.dumps(topology))
    snapshot = authority.inspect_bundle(data, root/"project.json")
    art["confirmation"]["artifact_sha256"] = {k:v["sha256"] for k,v in snapshot.items()}
    art["confirmation"]["facts_sha256"] = authority.object_digest(authority.project_facts(data))
    (root/"project.json").write_text(json.dumps(data))
    return data, recognition, topology


class InterpretationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data, self.recognition, self.topology = fixture(self.root)
        self.manifest = self.root/"project.json"
        self.base = Image.new("RGB", (400,300), "white")

    def test_complete_bundle_plans(self):
        plan_project.validate_manifest(self.data, self.manifest, False)

    def test_missing_confirmation_image(self):
        Path(self.data["interpretation_artifacts"]["access_map"]).unlink()
        with self.assertRaisesRegex(ValueError,"file not found"):
            authority.validate_bundle(self.data,self.manifest)

    def test_floorplan_requires_same_revision_valid_svg(self):
        svg = Path(self.data["interpretation_artifacts"]["topdown_base_svg"])
        svg.write_text("not svg")
        with self.assertRaisesRegex(ValueError, "invalid XML"):
            authority.inspect_bundle(self.data, self.manifest)
        svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        renamed = svg.with_name("topdown-base-v2.svg")
        svg.rename(renamed)
        self.data["interpretation_artifacts"]["topdown_base_svg"] = str(renamed)
        with self.assertRaisesRegex(ValueError, "same revision"):
            authority.inspect_bundle(self.data, self.manifest)

    def test_same_path_changed_image_rejected(self):
        Image.new("RGB",(400,300),"red").save(self.data["interpretation_artifacts"]["access_map"])
        with self.assertRaisesRegex(ValueError,"content changed"):
            authority.validate_bundle(self.data,self.manifest)

    def test_snapshot_detects_later_file_change(self):
        snapshot = authority.validate_bundle(self.data,self.manifest)
        self.manifest.write_text("{}")
        with self.assertRaisesRegex(ValueError,"authority changed"):
            authority.check_snapshot(snapshot)

    def test_conflicting_door_direction_rejected(self):
        self.recognition["elements"][0]["swing_into"] = "unknown"
        Path(self.data["interpretation_artifacts"]["recognition"]).write_text(json.dumps(self.recognition))
        with self.assertRaisesRegex(ValueError,"swing_into"):
            authority.inspect_bundle(self.data,self.manifest)

    def test_missing_window_confirmation_rejected(self):
        self.data["interpretation_artifacts"]["confirmation"]["scopes"]["access_elements"]["confirmed_item_ids"].remove("W1")
        with self.assertRaisesRegex(ValueError,"omits openings"):
            authority.inspect_bundle(self.data,self.manifest)

    def test_room_mismatch_rejected(self):
        self.data["floor_plan"]["rooms"][0]["id"] = "other"
        with self.assertRaisesRegex(ValueError,"room IDs"):
            authority.inspect_bundle(self.data,self.manifest)

    def test_critical_missing_rejected(self):
        self.data["input_assessment"]["condition"] = "critical_missing"
        with self.assertRaisesRegex(ValueError,"critical structure"):
            authority.validate_assessment(self.data)

    def test_hypothesis_requires_specific_acceptance(self):
        item = {"id":"door-gap", "description":"Proposed door in unreadable gap", "origin":"hypothesis", "evidence":["user supplied crop"], "consequential":True}
        self.data["input_assessment"] = {"condition":"partial","items":[item]}
        with self.assertRaisesRegex(ValueError,"explicit acceptance"):
            authority.validate_assessment(self.data)
        item["acceptance"] = {"approval_source":"explicit_user_confirmation","confirmed_by":"test-user","evidence":"accept door-gap as shown"}
        authority.validate_assessment(self.data)
        self.assertEqual(item["origin"],"hypothesis")

    def test_nonconsequential_unknown_allowed(self):
        self.data["input_assessment"]["items"] = [{"id":"height", "description":"Unknown ceiling height", "origin":"unknown", "evidence":[], "consequential":False}]
        authority.validate_assessment(self.data)
        self.data["input_assessment"]["items"][0]["consequential"] = True
        with self.assertRaisesRegex(ValueError,"unresolved consequential"):
            authority.validate_assessment(self.data)

    def test_missing_coordinates_fail_before_output(self):
        del self.recognition["elements"][0]["render_point"]
        with self.assertRaisesRegex(ValueError,"coordinates"):
            renderer.render_access(self.base,self.recognition,self.root/"bad.png")
        self.assertFalse((self.root/"bad.png").exists())

    def test_missing_polygon_rejected(self):
        del self.recognition["zones"][1]["render_polygon"]
        with self.assertRaisesRegex(ValueError,"polygon"):
            renderer.validate_geometry(self.base,self.recognition)

    def test_overlap_and_out_of_bounds_rejected(self):
        self.recognition["zones"].append(dict(self.recognition["zones"][1],id="duplicate-area"))
        with self.assertRaisesRegex(ValueError,"overlap"):
            renderer.validate_geometry(self.base,self.recognition)
        self.recognition["zones"].pop()
        self.recognition["zones"][1]["render_polygon"][0] = [-1,20]
        with self.assertRaisesRegex(ValueError,"out-of-bounds"):
            renderer.validate_geometry(self.base,self.recognition)

    def test_unassigned_area_warns(self):
        self.recognition["zones"][1]["render_polygon"] = [[20,20],[200,20],[200,280],[20,280]]
        self.assertTrue(renderer.validate_geometry(self.base,self.recognition))

    def test_symbols_render_distinct_geometry(self):
        path = self.root/"symbols.png"
        renderer.render_access(self.base,self.recognition,path)
        image = Image.open(path)
        for xy in [(60,235),(150,87),(235,93),(200,170),(308,90)]:
            self.assertNotEqual(image.getpixel(xy),(255,255,255),xy)

    def test_static_topology_does_not_require_tour_route(self):
        output = self.root/"static-overlays"
        arguments = ["render_interpretation.py", "--base", self.data["interpretation_artifacts"]["topdown_base"],
                     "--recognition", self.data["interpretation_artifacts"]["recognition"],
                     "--topology", self.data["interpretation_artifacts"]["topology"],
                     "--output-dir", str(output)]
        with patch("sys.argv", arguments):
            self.assertEqual(renderer.main(), 0)
        self.assertTrue((output/"topdown-access-v2.png").exists())
        self.assertTrue((output/"topdown-zoning-v2.png").exists())
        self.assertFalse((output/"topdown-tour-route-v2.png").exists())

    def test_clockwise_swing_renders_on_opposite_side(self):
        door = self.recognition["elements"][0]
        door["render_geometry"] = {"hinge":[60,150],"closed_tip":[120,150],"open_tip":[60,210],"arc_direction":"clockwise"}
        path = self.root/"clockwise.png"
        renderer.render_access(self.base,self.recognition,path)
        with Image.open(path) as image:
            self.assertNotEqual(image.getpixel((60,180)),(255,255,255))
            self.assertEqual(image.getpixel((60,120)),(255,255,255))

    def test_source_review_record_required(self):
        self.data["interpretation_artifacts"]["confirmation"].pop("source_self_check")
        with self.assertRaisesRegex(ValueError,"source_self_check"):
            authority.validate_bundle(self.data,self.manifest)

    def test_accepted_completion_enters_both_planning_paths(self):
        import plan_delivery
        self.data["input_assessment"]["items"] = [{"id":"gap-D1", "origin":"hypothesis", "description":"Door at the shown left jamb"}]
        for delivery in (None,plan_delivery.compile_delivery(self.data)):
            plan = plan_project.compile_plan(self.data,Path(self.data["input_image"]),delivery)
            for task in plan["tasks"]:
                if "request" in task:
                    self.assertIn("[gap-D1]",task["request"]["prompt"])

    def test_dry_run_is_not_executable(self):
        import delivery_state
        import plan_delivery
        data = copy.deepcopy(self.data)
        delivery = plan_delivery.compile_delivery(data)
        plan = plan_project.compile_plan(data, Path(data["input_image"]), delivery)
        plan["execution_mode"] = "sample_only"
        state = delivery_state.build_initial_state(plan)
        self.assertFalse(delivery_state.can_run(plan,state,plan["tasks"][0]["id"])["runnable"])

    def test_execution_rechecks_bundle(self):
        import delivery_state
        import plan_delivery
        plan = plan_project.compile_plan(self.data,Path(self.data["input_image"]),plan_delivery.compile_delivery(self.data))
        plan["execution_mode"] = "confirmed_bundle"
        plan["interpretation_authority"] = authority.validate_bundle(self.data,self.manifest)
        state = delivery_state.build_initial_state(plan)
        task_id = plan["tasks"][0]["id"]
        delivery_state.approve_layout(plan, state,
                                     Path(self.data["interpretation_artifacts"]["topdown_base"]),
                                     Path(self.data["interpretation_artifacts"]["topdown_base_svg"]), "synthetic-L1",
                                     "synthetic-user", "Synthetic layout fixture", "explicit_user_confirmation")
        self.assertTrue(delivery_state.can_run(plan,state,task_id)["runnable"])
        Path(self.data["interpretation_artifacts"]["access_map"]).write_bytes(b"changed")
        self.assertFalse(delivery_state.can_run(plan,state,task_id)["runnable"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
