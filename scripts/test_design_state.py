"""Synthetic regression tests; no image-model or real visual-quality claims."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image

import plan_project as planner
import plan_delivery as delivery
import delivery_state as state_module
import validate_delivery as review_module
from test_interpretation import fixture
from interpretation_authority import validate_bundle


class DesignStateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.data, _, _ = fixture(self.root)
        self.data["design"]["scheme"] = {"version":"scheme-v1", "layout":["Keep living room boundary"],
                    "furniture":["Oak sofa along left living-room wall"],"finishes":["Warm white walls, oak floor"]}
        self.save_manifest()
        self.delivery = delivery.compile_delivery(self.data)
        self.plan = planner.compile_plan(self.data,Path(self.data["input_image"]),self.delivery)
        self.plan["execution_mode"] = "confirmed_bundle"
        self.plan["interpretation_authority"] = validate_bundle(self.data,self.root/"project.json")
        self.state = state_module.build_initial_state(self.plan)
        self.layout = self.png("approved-layout.png")
        self.layout_svg = self.root/"approved-layout.svg"
        self.layout_svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"/>')
        state_module.approve_layout(self.plan, self.state, self.layout, self.layout_svg, "L1", "synthetic-user",
                                    "Synthetic layout acceptance", "explicit_user_confirmation")

    def save_manifest(self):
        (self.root/"project.json").write_text(json.dumps(self.data))

    def png(self, name, color="white"):
        path = self.root/name
        Image.new("RGB",(64,64),color).save(path)
        return path

    def generate(self, asset_id):
        state_module.record_generated(self.plan,self.state,asset_id,self.png(asset_id+".png"))

    def primary(self):
        self.generate("primary-birdseye")
        state_module.approve_primary(self.plan,self.state,"primary-birdseye","synthetic-user",
                                    "Synthetic approval fixture only","explicit_user_confirmation")

    def all_images(self):
        self.primary()
        for task in self.plan["tasks"]:
            if task["id"] != "primary-birdseye":
                self.generate(task["id"])

    def review(self):
        review = delivery.review_template(self.delivery)
        review["scheme_sha256"] = self.plan["scheme_sha256"]
        for record in review["assets"]:
            task = state_module.resolve_task(self.plan,self.state,record["id"])
            asset = self.state["assets"][record["id"]]
            refs = task.get("reference_images",[]) or [task["source"]]
            record.update(path=asset["generated_file"],image_sha256=asset["generated_sha256"],actual_kind=record["planned_kind"],
                          authority_refs=refs,authority_sha256={r:state_module.file_digest(r) for r in refs},
                          inspection_method="visual_comparison",observations="Synthetic metadata fixture, not a real visual approval")
            for check in record["hard_checks"].values():
                check.update(passed=True,evidence="Synthetic test evidence")
        for check in review["package_consistency"].values():
            check.update(passed=True,evidence="Synthetic test evidence")
        return review

    def package(self):
        self.all_images()
        review = self.review()
        dp, rp = self.root/"delivery.json", self.root/"review.json"
        state_module.atomic_write(dp,self.delivery)
        state_module.atomic_write(rp,review)
        state_module.record_package_review(self.plan,self.state,self.delivery,review,dp,rp)
        return review

    def test_custom_style_preferences_reach_all_images(self):
        self.data["design"].update(selected_style="custom",custom_style={"name":"Personal style", "description":"Dark wood and green fabric"},
                                   palette=["dark walnut"],preserve_furniture=["retain blue sofa"],requirements=["low storage for child"])
        planner.validate_manifest(self.data,self.root/"project.json",True)
        for shot_list in (None,self.delivery):
            plan = planner.compile_plan(self.data,Path(self.data["input_image"]),shot_list)
            for task in plan["tasks"]:
                if "request" in task:
                    prompt = task["request"]["prompt"]
                    for text in ("dark walnut","retain blue sofa","low storage for child","Dark wood and green fabric"):
                        self.assertIn(text,prompt)

    def test_layout_required_and_injected_into_generation(self):
        fresh = state_module.build_initial_state(self.plan)
        self.assertFalse(state_module.can_run(self.plan, fresh, "primary-birdseye")["runnable"])
        task = state_module.can_run(self.plan, self.state, "primary-birdseye")["resolved_task"]
        self.assertIn(str(self.layout), task["reference_images"])

    def test_acceptance_cli_records_existing_confirmation(self):
        pp, sp = self.root/"plan.json", self.root/"state.json"
        state_module.atomic_write(pp, self.plan)
        state_module.atomic_write(sp, state_module.build_initial_state(self.plan))
        base = [sys.executable, "-B", state_module.__file__]
        common = ["--plan", str(pp), "--state", str(sp), "--approved-by", "synthetic-user",
                  "--approval-source", "explicit_user_confirmation", "--evidence", "Existing synthetic confirmation"]
        result = subprocess.run(base+["approve-layout"]+common+["--file",str(self.layout),"--svg",str(self.layout_svg),"--revision","L1"], capture_output=True,text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        recorded = json.loads(sp.read_text())
        self.assertEqual(recorded["approvals"]["layout"]["generated_sha256"], state_module.file_digest(self.layout))
        self.package()
        state_module.atomic_write(sp, self.state)
        result = subprocess.run(base+["approve-package"]+common, capture_output=True,text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run(base+["can-export","--plan",str(pp),"--state",str(sp)],capture_output=True,text=True)
        self.assertTrue(json.loads(result.stdout)["export_ready"])

    def test_revision_clears_existing_image_acceptance(self):
        self.package()
        state_module.approve_package(self.plan, self.state, "user", "Accepted exact images", "explicit_user_confirmation")
        target = next(t["id"] for t in self.plan["tasks"] if t["kind"] == "room_view")
        state_module.revise_assets(self.plan, self.state, [target], "Correct cabinet only")
        self.assertFalse(state_module.package_acceptance_current(self.plan, self.state))
        self.assertFalse(state_module.can_export(self.plan, self.state)["export_ready"])

    def test_structural_replan_does_not_inherit_layout_acceptance(self):
        new = copy.deepcopy(self.plan)
        new["interpretation_authority"] = {"different-structure": True}
        migrated = state_module.migrate_state(self.plan, self.state, new)
        self.assertNotIn("layout", migrated["approvals"])

    def test_changed_layout_blocks_generation_and_export(self):
        self.package()
        state_module.approve_package(self.plan, self.state, "test-user", "Accept these exact images", "explicit_user_confirmation")
        self.assertTrue(state_module.can_export(self.plan, self.state)["export_ready"])
        self.png("approved-layout.png", "red")
        self.assertFalse(state_module.can_run(self.plan, self.state, "primary-birdseye")["runnable"])
        self.assertFalse(state_module.can_export(self.plan, self.state)["export_ready"])
        with self.assertRaisesRegex(ValueError, "replan first"):
            state_module.approve_layout(self.plan, self.state, self.layout, self.layout_svg, "L2", "user", "accepted", "explicit_user_confirmation")

    def test_changed_layout_svg_blocks_generation(self):
        self.layout_svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"><circle r="4"/></svg>')
        result = state_module.can_run(self.plan, self.state, "primary-birdseye")
        self.assertFalse(result["runnable"])
        self.assertTrue(any("editable layout SVG changed" in item for item in result["blocked_by"]))

    def test_image_acceptance_before_review_needs_no_export_confirmation(self):
        self.all_images()
        state_module.approve_package(self.plan, self.state, "user", "Accepted exact displayed image set", "explicit_user_confirmation")
        self.assertFalse(state_module.can_export(self.plan, self.state)["export_ready"])
        review = self.review()
        dp, rp = self.root/"delivery.json", self.root/"review.json"
        state_module.atomic_write(dp, self.delivery)
        state_module.atomic_write(rp, review)
        state_module.record_package_review(self.plan, self.state, self.delivery, review, dp, rp)
        self.assertEqual(self.state["stage"], "final_export_ready")
        self.assertTrue(state_module.can_export(self.plan, self.state)["export_ready"])

    def test_acceptance_not_inferred_from_review_or_empty_evidence(self):
        self.package()
        self.assertFalse(state_module.can_export(self.plan, self.state)["export_ready"])
        with self.assertRaises(ValueError):
            state_module.approve_package(self.plan, self.state, "user", "", "explicit_user_confirmation")
        with self.assertRaises(ValueError):
            state_module.approve_package(self.plan, self.state, "agent", "looks good", "internal_review")

    def test_layout_reapproval_after_replan_preserves_retained_files(self):
        self.all_images()
        new = copy.deepcopy(self.plan)
        new["scheme_sha256"] = "changed-scheme"
        migrated = state_module.migrate_state(self.plan, self.state, new)
        self.assertTrue(state_module.layout_blockers(new, migrated))
        before = {k: a["generated_sha256"] for k, a in migrated["assets"].items()}
        state_module.approve_layout(new, migrated, self.layout, self.layout_svg, "L1", "user", "unchanged layout acceptance", "explicit_user_confirmation")
        self.assertEqual(before, {k: a["generated_sha256"] for k, a in migrated["assets"].items()})
        self.assertIsNone(migrated["package_review"])

    def test_local_revision_requires_untouched_region_review(self):
        self.all_images()
        target = next(t["id"] for t in self.plan["tasks"] if t["kind"] == "room_view")
        state_module.revise_assets(self.plan, self.state, [target], "Fix cabinet cap only")
        state_module.record_generated(self.plan, self.state, target, self.png("repaired.png"))
        review = self.review()
        record = next(a for a in review["assets"] if a["id"] == target)
        del record["hard_checks"]["must_not_change_preserved"]
        with self.assertRaisesRegex(ValueError, "missing required"):
            review_module.validate_delivery(self.delivery, review, True)

    def test_no_preview_after_direct_style_choice(self):
        self.data["outputs"]["style_preview"] = None
        planner.validate_manifest(self.data,self.root/"project.json",True)
        self.assertTrue(all(t["kind"] != "style_preview" for t in self.plan["tasks"]))

    def test_furniture_waits_and_resolves_real_primary(self):
        self.assertFalse(state_module.can_run(self.plan,self.state,"furnished-floor-plan")["runnable"])
        self.primary()
        task = state_module.can_run(self.plan,self.state,"furnished-floor-plan")["resolved_task"]
        self.assertIn(str(self.root/"primary-birdseye.png"),task["reference_images"])
        self.assertFalse(any(r.startswith("asset://") for r in task["reference_images"]))

    def test_primary_changed_before_approval_rejected(self):
        self.generate("primary-birdseye")
        self.png("primary-birdseye.png","red")
        with self.assertRaisesRegex(ValueError,"primary content"):
            state_module.approve_primary(self.plan,self.state,"primary-birdseye","user","approve","explicit_user_confirmation")

    def test_room_image_correction_preserves_other_images(self):
        self.all_images()
        target = next(t["id"] for t in self.plan["tasks"] if t["kind"] == "room_view")
        unaffected = copy.deepcopy(self.state["assets"]["primary-birdseye"])
        affected = state_module.revise_assets(self.plan,self.state,[target],"Correct this view to match the confirmed oak sofa")
        self.assertEqual(affected,[target])
        self.assertEqual(unaffected,self.state["assets"]["primary-birdseye"])
        task = state_module.can_run(self.plan,self.state,target)["resolved_task"]
        self.assertIn("-r1.png",task["output"])
        self.assertIn(str(self.root/(target+".png")),task["reference_images"])
        self.assertEqual(self.state["video"]["status"],"invalidated")

    def test_primary_revision_invalidates_children_and_review(self):
        self.package()
        affected = state_module.revise_assets(self.plan,self.state,["primary-birdseye"],"Correct primary camera artifact to match scheme")
        self.assertIn("furnished-floor-plan",affected)
        self.assertIsNone(self.state["package_review"])
        self.assertNotIn("primary-birdseye",self.state["approvals"]["primary"])
        self.assertFalse(state_module.can_export(self.plan,self.state)["export_ready"])

    def test_replacement_retains_old_file_and_reapproves(self):
        self.primary()
        previous = (self.root/"primary-birdseye.png").read_bytes()
        state_module.revise_assets(self.plan,self.state,["primary-birdseye"],"Fix primary view")
        with self.assertRaisesRegex(ValueError,"new path"):
            state_module.record_generated(self.plan,self.state,"primary-birdseye",self.root/"primary-birdseye.png")
        state_module.record_generated(self.plan,self.state,"primary-birdseye",self.png("primary-r1.png","blue"))
        self.assertEqual(self.state["assets"]["primary-birdseye"]["status"],"pending_primary_approval")
        self.assertEqual(previous,(self.root/"primary-birdseye.png").read_bytes())

    def test_missing_check_rejected_even_when_remaining_are_true(self):
        self.all_images()
        review = self.review()
        del review["assets"][0]["hard_checks"]["no_blocked_access"]
        with self.assertRaisesRegex(ValueError,"missing required"):
            review_module.validate_delivery(self.delivery,review,True)

    def test_missing_package_check_and_no_visual_method_rejected(self):
        self.all_images()
        review = self.review()
        del review["package_consistency"]["furniture_consistent"]
        with self.assertRaisesRegex(ValueError,"required package"):
            review_module.validate_delivery(self.delivery,review,True)
        review = self.review()
        review["assets"][0]["inspection_method"] = "field_validation_only"
        with self.assertRaisesRegex(ValueError,"visual_comparison"):
            review_module.validate_delivery(self.delivery,review,True)

    def test_reference_image_propagates_and_missing_reference_blocks_cli(self):
        reference = self.png("style-reference.png")
        self.data["design"]["reference_images"] = [str(reference)]
        plan = planner.compile_plan(self.data,Path(self.data["input_image"]),self.delivery)
        for task in plan["tasks"]:
            if "request" in task:
                self.assertIn(str(reference),task["reference_images"])
        reference.unlink()
        self.save_manifest()
        state_module.atomic_write(self.root/"delivery.json",self.delivery)
        result = subprocess.run([sys.executable,planner.__file__,"--manifest",str(self.root/"project.json"),
                  "--delivery-plan",str(self.root/"delivery.json"),"--output-dir",str(self.root/"failed")],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn("design reference missing",result.stderr)

    def test_prepare_review_does_not_grant_visual_approval(self):
        self.all_images()
        for name,value in (("plan",self.plan),("state",self.state),("delivery",self.delivery)):
            state_module.atomic_write(self.root/(name+".json"),value)
        result = subprocess.run([sys.executable,state_module.__file__,"prepare-review","--plan",str(self.root/"plan.json"),
                    "--state",str(self.root/"state.json"),"--delivery-plan",str(self.root/"delivery.json"),
                    "--review",str(self.root/"pending.json")],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        pending = json.loads((self.root/"pending.json").read_text())
        self.assertTrue(pending["assets"][0]["image_sha256"])
        with self.assertRaises(ValueError):
            review_module.validate_delivery(self.delivery,pending,True)

    def test_replaced_reviewed_image_rejected(self):
        self.all_images()
        review = self.review()
        self.png(Path(review["assets"][0]["path"]).name,"red")
        with self.assertRaisesRegex(ValueError,"content changed"):
            review_module.validate_delivery(self.delivery,review,True)

    def test_export_rechecks_review_and_image(self):
        self.package()
        state_module.authorize_final_export(self.plan,self.state,"synthetic-user","synthetic acceptance","explicit_user_confirmation")
        self.assertTrue(state_module.can_export(self.plan,self.state)["export_ready"])
        path = self.root/"review.json"
        original = path.read_bytes()
        path.write_text("{}")
        self.assertFalse(state_module.can_export(self.plan,self.state)["export_ready"])
        path.write_bytes(original)
        self.png("primary-birdseye.png","red")
        self.assertFalse(state_module.can_export(self.plan,self.state)["export_ready"])

    def test_scoped_scheme_change_retains_unaffected_pixels(self):
        data = json.loads((Path(__file__).parents[1]/"assets/sample-project.json").read_text())
        old = planner.compile_plan(data,Path(data["input_image"]),delivery.compile_delivery(data))
        state = state_module.build_initial_state(old)
        for task in sorted(old["tasks"],key=lambda t:bool(t["depends_on"])):
            state_module.record_generated(old,state,task["id"],self.png(task["id"]+".png"))
            if state_module.is_primary(task):
                state_module.approve_primary(old,state,task["id"],"test","test","explicit_user_confirmation")
        data["design"]["room_schemes"] = {"second-bedroom":{"furniture":"replace bedside lamp"}}
        new = planner.compile_plan(data,Path(data["input_image"]),delivery.compile_delivery(data))
        migrated = state_module.migrate_state(old,state,new)
        self.assertEqual(migrated["assets"]["room-second-bedroom"]["status"],"blocked_until_primary_approved")
        primary_room = next(t["id"] for t in new["tasks"] if t["kind"] == "room_view" and t["must_show"] == ["primary-bedroom"])
        self.assertEqual(migrated["assets"][primary_room]["generated_sha256"],state["assets"][primary_room]["generated_sha256"])
        self.assertIsNone(migrated["package_review"])

    def test_failed_replan_preserves_existing_plan_and_state(self):
        script = Path(planner.__file__)
        args = [sys.executable,str(script),"--manifest",str(self.root/"project.json"),"--delivery-plan",str(self.root/"delivery.json"),"--output-dir",str(self.root/"run")]
        state_module.atomic_write(self.root/"delivery.json",self.delivery)
        first = subprocess.run(args,capture_output=True,text=True)
        self.assertEqual(first.returncode,0,first.stderr)
        output = self.root/"run/generation-plan.json"
        state_path = self.root/"run/delivery-state.json"
        before = output.read_bytes(),state_path.read_bytes()
        self.data["design"]["requirements"].append("new requirement changes plan")
        self.save_manifest()
        second = subprocess.run(args,capture_output=True,text=True)
        self.assertNotEqual(second.returncode,0)
        self.assertEqual(before,(output.read_bytes(),state_path.read_bytes()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
