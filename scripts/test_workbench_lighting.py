import copy,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'production'))
from lighting_checks import lighting_report
from synthetic_cases import fixture_cases
from h5 import validate_case,build
class WorkbenchLighting(unittest.TestCase):
    def setUp(self):self.case=fixture_cases()[0]
    def test_two_shapes(self):
        for c in fixture_cases():self.assertEqual(validate_case(c)['caseId'],c['caseId']);self.assertEqual(lighting_report(c)['status'],'pass')
    def test_missing_main(self):
        self.case['initialState']['furniture']=[];self.assertEqual(len(lighting_report(self.case)['warnings']),2)
    def test_disabled_main(self):
        self.case['initialState']['furniture'][0]['lightOn']=False;self.assertTrue(any(w['code']=='missing-main-light' for w in lighting_report(self.case)['warnings']))
    def test_zero_intensity(self):
        self.case['initialState']['furniture'][0]['lightIntensity']=0;self.assertTrue(lighting_report(self.case)['warnings'])
    def test_exempt_region(self):
        self.case['model']['rooms'][0]['mainLightingRequired']=False;self.case['initialState']['furniture']=[f for f in self.case['initialState']['furniture'] if f['id']!='lamp-left'];self.assertEqual(lighting_report(self.case)['status'],'pass')
    def test_outside(self):
        self.case['initialState']['furniture'][0]['cx']=-500;self.assertTrue(any(w['code']=='fixture-outside-rooms' for w in lighting_report(self.case)['warnings']))
    def test_occluded_nonfollowing_fixture(self):
        self.case['initialState']['ceilings']=[{'roomId':'left','mode':'flat','drop':100,'band':300}];self.case['initialState']['furniture'][0]['mount']='fixed';self.assertTrue(any(w['code']=='fixture-above-finished-ceiling' for w in lighting_report(self.case)['warnings']))
    def test_following_fixture_not_false_warning(self):
        self.case['initialState']['ceilings']=[{'roomId':'left','mode':'flat','drop':100,'band':300}];self.assertEqual(lighting_report(self.case)['status'],'pass')
    def test_invalid_intensity_and_state(self):
        for key,value in [('lightIntensity',float('nan')),('lightIntensity',-1),('lightOn','yes')]:
            c=copy.deepcopy(self.case);c['initialState']['furniture'][0][key]=value
            with self.assertRaises(ValueError):validate_case(c)
    def test_build_evidence_version_and_lighting(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);c=p/'中文案例.json';c.write_text(json.dumps(self.case,ensure_ascii=False),encoding='utf-8');out=p/'新版本.html';build(c,out);meta=json.loads(out.with_suffix('.build.json').read_text(encoding='utf-8'));self.assertEqual(meta['workbenchVersion'],json.loads((Path(__file__).parent.parent/'assets/h5/version.json').read_text(encoding='utf-8'))['version']);self.assertEqual(meta['lightingCheck']['status'],'pass');self.assertIn('templateSha256',meta)

    def test_unsupported_component_rejected_before_build(self):
        self.case['initialState']['furniture'][0]['type']='unsupported_fixture'
        with self.assertRaisesRegex(ValueError,'Unsupported furniture type'):validate_case(self.case)
    def test_light_types_follow_engine_specs(self):
        from lighting_checks import LIT_TYPES
        self.assertTrue({'walllamp','mirrorlight','ledstrip','tracklight'}.issubset(LIT_TYPES))

    def test_invalid_marble_presentation(self):
        self.case['presentation']['materials']['marble']['veins']='false'
        with self.assertRaisesRegex(ValueError,'Marble veins'):validate_case(self.case)
