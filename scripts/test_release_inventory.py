"""Keep the closeout runner and version boundaries explicit; no external work."""
import re,json,unittest
from pathlib import Path
from release_smoke import javascript_module_tests
ROOT=Path(__file__).resolve().parent.parent
class ReleaseInventoryTests(unittest.TestCase):
 def test_all_module_tests_including_route_panel_are_collected(self):
  found=javascript_module_tests(ROOT)
  self.assertIn(ROOT/'scripts/production/test_tour_route_panel.mjs',found)
  self.assertIn(ROOT/'scripts/test_lamp_models.mjs',found)
  self.assertTrue(all(not p.name.endswith('_browser.mjs') for p in found))
  self.assertEqual(len(found),len(set(found)));self.assertNotIn(ROOT/'scripts/test_sliding_editor.mjs',found)
 def test_skill_version_is_separate_from_workbench_build(self):
  text=(ROOT/'SKILL.md').read_text(encoding='utf-8');version=re.search(r'version:\s*"([^"\n]+)"',text).group(1)
  workbench=json.loads((ROOT/'assets/h5/version.json').read_text(encoding='utf-8'))['version']
  doc=(ROOT/'references/local-version-closeout.md').read_text(encoding='utf-8')
  self.assertIn('Skills '+version,doc);self.assertIn('工作台 '+workbench,doc)
  for name in ('README.md','README.zh.md'):self.assertIn(version,(ROOT/name).read_text(encoding='utf-8'))
