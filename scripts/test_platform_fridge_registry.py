"""Static facts for the platform (step) component and the double-door fridge; the browser check is optional.

The browser regression (test_platform_fridge_components.mjs) runs when INTERIOR_PLAYWRIGHT_MODULE,
INTERIOR_BROWSER and INTERIOR_PLATFORM_TEST_URL (a served generated workbench) are all set.
"""
import json, os, re, subprocess, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
H5 = ROOT / 'assets/h5'


class PlatformAndFridgeRegistry(unittest.TestCase):
    def test_registry_and_engine_know_the_platform(self):
        types = json.loads((H5 / 'component-types.json').read_text(encoding='utf-8'))['types']
        self.assertIn('platform', types)
        self.assertIn('fridge', types)
        engine = (H5 / 'engine.js').read_text(encoding='utf-8')
        # esbuild escapes non-ASCII text, so compare against both spellings.
        for text in ('飘窗台阶', '双开门冰箱'):
            escaped = ''.join('\\u%04x' % ord(c) for c in text)
            self.assertTrue(text in engine or escaped in engine.lower(), text)
        self.assertIn('platform', engine)

    def test_source_offers_both_fridges_in_the_kitchen_group_and_a_construction_group(self):
        app = (H5 / 'source/app.js').read_text(encoding='utf-8')
        self.assertIn("['fridge','单开门冰箱',700,700", app)
        kitchen = re.search(r"\{cat:'餐厨', items:\[(.*?)\]\},", app, re.S).group(1)
        self.assertIn("['fridge','双开门冰箱',910,700", kitchen)
        self.assertIn("LIB.push({cat:'构造'", app)
        dims = (H5 / 'source/dimensions-v9.js').read_text(encoding='utf-8')
        self.assertIn("platform:{label:'台阶/平台',h:550", dims)

    def test_tv_sizes_and_default_flush_doorways(self):
        app = (H5 / 'source/app.js').read_text(encoding='utf-8')
        for inch, width in ((55, 1230), (65, 1450), (75, 1680), (85, 1900)):
            self.assertIn("['tv','%d 寸电视',%d,35" % (inch, width), app)
        self.assertIn("opts.threshold===true", app)  # threshold stones are opt-in, never raised by default
        self.assertIn("function switchVariant(", app)
        lighting = (H5 / 'source/lighting-profile.js').read_text(encoding='utf-8')
        self.assertIn('roomLightScale', lighting)
        self.assertIn('roomLightRange', lighting)
        self.assertIn("['sofabed','沙发床 1.2m（收起）',1200,820", app)
        self.assertIn("['bed','双人床 2.2m',2200,2000", app)
        self.assertIn("const CUSTOM_SIZE_TYPES=new Set(", app)
        self.assertIn("const VARIANT_LABELS={", app)
        self.assertIn("['coffee','圆茶几 Ø800',800,800", app)
        self.assertIn("['coffeetable','方茶几 1200×600',1200,600", app)
        self.assertIn("function fitAgainstWalls(", app)

    def test_platform_stays_out_of_the_kitchen_group(self):
        app = (H5 / 'source/app.js').read_text(encoding='utf-8')
        self.assertRegex(app, r"filter\(c=>!\['pendant','downlight','tracklight','platform'\]")

    @unittest.skipUnless(all(os.environ.get(k) for k in ('INTERIOR_PLAYWRIGHT_MODULE', 'INTERIOR_BROWSER', 'INTERIOR_PLATFORM_TEST_URL')),
                         'browser environment and a served workbench URL are not provided')
    def test_browser_regression(self):
        for script in ('test_platform_fridge_components.mjs', 'test_variant_switch.mjs', 'test_security_door.mjs', 'test_night_lighting.mjs'):
            with tempfile.TemporaryDirectory() as tmp:
                report = Path(tmp) / 'report.json'
                subprocess.run(['node', str(ROOT / 'scripts' / script), os.environ['INTERIOR_PLATFORM_TEST_URL'], str(report)], check=True)
                self.assertEqual(json.loads(report.read_text(encoding='utf-8'))['status'], 'pass', script)


if __name__ == '__main__':
    unittest.main()
