"""Synthetic tests for deterministic SVG/PNG and contact-sheet tools."""

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

import assemble_contact_sheet
import render_floorplan
import render_furniture_layout
import vector_tools


def plan_fixture():
    return {
        "schema_version": "1.0",
        "revision": "test-v1",
        "canvas": {"width": 400, "height": 300, "background": "#ffffff"},
        "walls": [
            {"id": "wall-top", "start": [20, 20], "end": [380, 20], "thickness": 10},
            {"id": "wall-left", "start": [20, 20], "end": [20, 280], "thickness": 10},
            {"id": "wall-right", "start": [380, 20], "end": [380, 280], "thickness": 10},
            {"id": "wall-bottom-a", "start": [20, 280], "end": [180, 280], "thickness": 10},
            {"id": "wall-bottom-b", "start": [240, 280], "end": [380, 280], "thickness": 10},
        ],
        "rooms": [{"id": "room-a", "label": "Room A", "label_point": [200, 150],
                   "polygon": [[26, 26], [374, 26], [374, 274], [26, 274]]}],
        "doors": [{"id": "door-a", "hinge": [180, 280], "closed_tip": [240, 280],
                   "open_tip": [180, 220], "arc_direction": "counterclockwise"}],
        "openings": [
            {"id": "window-a", "kind": "window", "start": [120, 20], "end": [180, 20]},
            {"id": "bay-a", "kind": "bay_window",
             "outline": [[260, 20], [260, 5], [330, 5], [330, 20]],
             "connects": ["room-a", "outside"]},
        ],
        "annotations": [{"id": "note-a", "point": [30, 295], "text": "concept only"}],
    }


def layout_fixture():
    return {
        "schema_version": "1.0", "revision": "test-v1", "plan": plan_fixture(),
        "furniture": [
            {"id": "bed-a", "symbol": "bed", "room_id": "room-a",
             "x": 50, "y": 50, "width": 90, "height": 120, "label": "Bed"},
            {"id": "cabinet-a", "symbol": "cabinet", "room_id": "room-a",
             "x": 280, "y": 60, "width": 60, "height": 30, "label": "Cabinet"},
        ]}


class DeterministicRenderingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_floorplan_contains_editable_elements_and_same_revision_png(self):
        svg, png = self.root / "plan-v1.svg", self.root / "plan-v1.png"
        result = vector_tools.render_pair(render_floorplan.build_svg(plan_fixture()), svg, png, 400, 300)
        with Image.open(png) as preview:
            self.assertEqual(preview.size, (400, 300))
            rgb = preview.convert("RGB")
            non_white = sum(pixel != (255, 255, 255) for pixel in rgb.getdata())
            self.assertGreater(non_white, 4_000)
            self.assertLess(sum(rgb.getpixel((x, y)) != (255, 255, 255)
                                for x in range(190, 220) for y in range(240, 270)), 220)
        root = ET.fromstring(svg.read_text())
        tags = [node.tag.rsplit("}", 1)[-1] for node in root.iter()]
        self.assertNotIn("image", tags)
        self.assertIn("line", tags)
        self.assertIn("path", tags)
        self.assertTrue(any(node.attrib.get("data-kind") == "bay_window" for node in root.iter()))
        self.assertFalse(any(node.attrib.get("data-kind") == "room" for node in root.iter()))
        self.assertEqual(result["renderer"], "pymupdf")

    def test_output_pair_rejects_revision_mismatch_and_overwrite(self):
        with self.assertRaisesRegex(ValueError, "share one revision"):
            vector_tools.validate_output_pair(self.root / "plan-v1.svg", self.root / "plan-v2.png")
        svg, png = self.root / "plan-v1.svg", self.root / "plan-v1.png"
        svg.write_text("existing")
        with self.assertRaisesRegex(ValueError, "already exists"):
            vector_tools.validate_output_pair(svg, png)

    def test_furniture_symbols_are_independent_vectors(self):
        data = layout_fixture()
        svg_text = render_furniture_layout.build_svg(data)
        root = ET.fromstring(svg_text)
        groups = [node for node in root.iter() if node.attrib.get("data-kind") == "furniture"]
        self.assertEqual({node.attrib["id"] for node in groups}, {"bed-a", "cabinet-a"})
        svg, png = self.root / "layout-v1.svg", self.root / "layout-v1.png"
        vector_tools.render_pair(svg_text, svg, png, 400, 300)
        with Image.open(png) as preview:
            self.assertEqual(preview.size, (400, 300))
            self.assertNotEqual(preview.convert("RGB").getpixel((280, 70)), (255, 255, 255))

    def test_wall_conflict_is_reported(self):
        data = layout_fixture()
        data["plan"]["walls"].append(
            {"id": "wall-interior", "start": [150, 30], "end": [150, 200], "thickness": 10})
        data["furniture"][0].update(x=145, y=50)
        _, _, conflicts = render_furniture_layout.validate(data)
        self.assertIn("wall:bed-a:wall-interior", conflicts)

    def test_bay_window_can_be_declared_as_scoped_placement_area(self):
        data = layout_fixture()
        data["furniture"] = [{"id": "bay-desk", "symbol": "table", "room_id": "room-a",
                              "bay_window_id": "bay-a", "x": 270, "y": 6,
                              "width": 50, "height": 8}]
        _, _, conflicts = render_furniture_layout.validate(data)
        self.assertEqual(conflicts, [])

    def test_wall_recess_requires_scoped_wall_and_reason(self):
        data = layout_fixture()
        data["furniture"] = [{"id": "recess", "symbol": "cabinet", "room_id": "room-a",
                              "x": 15, "y": 80, "width": 10, "height": 80,
                              "wall_recess_wall_ids": ["wall-left"],
                              "proposal_reason": "Existing confirmed recess proposal"}]
        _, _, conflicts = render_furniture_layout.validate(data)
        self.assertEqual(conflicts, [])
        del data["furniture"][0]["proposal_reason"]
        with self.assertRaisesRegex(ValueError, "proposal_reason"):
            render_furniture_layout.validate(data)

    def test_furniture_overlap_is_reported_and_explicit_exception_is_scoped(self):
        data = layout_fixture()
        data["furniture"][1].update(x=100, y=80)
        _, _, conflicts = render_furniture_layout.validate(data)
        self.assertIn("furniture_overlap:bed-a:cabinet-a", conflicts)
        data["furniture"][0]["allow_overlap_with"] = ["cabinet-a"]
        _, _, conflicts = render_furniture_layout.validate(data)
        self.assertNotIn("furniture_overlap:bed-a:cabinet-a", conflicts)

    def test_door_swing_conflict_is_reported(self):
        data = layout_fixture()
        data["furniture"][1].update(x=165, y=215, width=50, height=50)
        _, _, conflicts = render_furniture_layout.validate(data)
        self.assertIn("door_swing:cabinet-a:door-a", conflicts)

    def test_furniture_inside_swept_door_sector_is_reported(self):
        data = layout_fixture()
        data["furniture"][1].update(x=195, y=245, width=12, height=12)
        _, _, conflicts = render_furniture_layout.validate(data)
        self.assertIn("door_swing:cabinet-a:door-a", conflicts)

    def test_contact_sheet_keeps_sources_unchanged_uncropped_and_unscaled(self):
        red, blue = self.root / "red.png", self.root / "blue.png"
        Image.new("RGB", (30, 20), "red").save(red)
        Image.new("RGB", (10, 40), "blue").save(blue)
        hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in (red, blue)}
        spec_path = self.root / "sheet.json"
        spec = {"schema_version": "1.0", "columns": 2, "padding": 5, "label_height": 20,
                "confirmed_images": [{"path": str(red), "label": "A"}, {"path": str(blue), "label": "B"}]}
        spec_path.write_text(json.dumps(spec))
        output, manifest = self.root / "sheet-v1.png", self.root / "sheet-v1.manifest.json"
        result = assemble_contact_sheet.assemble(spec, spec_path, output, manifest)
        self.assertFalse(result["source_images_resized"])
        self.assertFalse(result["source_images_cropped"])
        sheet = Image.open(output)
        for path, record in zip((red, blue), result["images"]):
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), hashes[path])
            box = record["placement"]
            pasted = sheet.crop((box["x"], box["y"], box["x"] + box["width"], box["y"] + box["height"]))
            with Image.open(path) as source:
                self.assertEqual(pasted.tobytes(), source.convert("RGB").tobytes())

    def test_contact_sheet_is_deterministic(self):
        source = self.root / "source.png"
        Image.new("RGB", (16, 12), (12, 34, 56)).save(source)
        spec_path = self.root / "spec.json"
        spec = {"schema_version": "1.0", "columns": 1, "padding": 4, "label_height": 20,
                "confirmed_images": [{"path": str(source), "label": "Confirmed"}]}
        spec_path.write_text(json.dumps(spec))
        first, second = self.root / "first.png", self.root / "second.png"
        assemble_contact_sheet.assemble(spec, spec_path, first, self.root / "first.json")
        assemble_contact_sheet.assemble(spec, spec_path, second, self.root / "second.json")
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_floorplan_and_layout_cli_entrypoints(self):
        plan_path = self.root / "plan.json"
        plan_path.write_text(json.dumps(plan_fixture()))
        result = subprocess.run(
            [sys.executable, "-B", render_floorplan.__file__, "--input", str(plan_path),
             "--svg", str(self.root / "cli-plan.svg"), "--png", str(self.root / "cli-plan.png")],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "ok")
        layout_path = self.root / "layout.json"
        layout_path.write_text(json.dumps(layout_fixture()))
        result = subprocess.run(
            [sys.executable, "-B", render_furniture_layout.__file__, "--input", str(layout_path),
             "--svg", str(self.root / "cli-layout.svg"), "--png", str(self.root / "cli-layout.png")],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["conflicts"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
