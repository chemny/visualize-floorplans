import ast,importlib.util,sys,unittest
from pathlib import Path
from release_smoke import javascript_module_tests
class ReleaseCollection(unittest.TestCase):
 def test_browser_entrypoints_are_not_module_tests(self):
  files={p.name for p in javascript_module_tests(Path(__file__).resolve().parents[1])}
  self.assertNotIn('test_production_textures_browser.mjs',files);self.assertNotIn('test_replay_lighting_browser.mjs',files)
  for name in ('test_night_lighting.mjs','test_platform_fridge_components.mjs','test_security_door.mjs','test_variant_switch.mjs'):
   self.assertNotIn(name,files)
 def test_blender_checks_are_import_safe(self):
  for name in ('test_blender_source_import','test_blender_room_presentation','test_blender_render_quality'):
   spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);self.assertTrue(callable(m.main))
if __name__=='__main__':unittest.main()
