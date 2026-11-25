import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import h5

class TourExposure(unittest.TestCase):
    def bundle(self,d):
        b={'schema':'floor-visualization-production/1.0','schemeSha256':'a'*64,'confirmations':{},'state':{},'model':{'width':1000,'depth':1000},'finishes':{},
           'scene':{'meshes':[{'id':'m','positions':[0.,0.,0.,1.,0.,0.,0.,1.,0.],'normals':[0.,0.,1.]*3,'uv':None,'indices':[0,1,2]}]}}
        path=Path(d)/'bundle.json';path.write_text(json.dumps(b));return path
    def scene(self,illumination=None,**kw):
        with tempfile.TemporaryDirectory() as d:
            b=json.loads(self.bundle(d).read_text());b['scene']['illumination']=illumination or [];Path(d,'b2.json').write_text(json.dumps(b))
            out=Path(d)/'runtime';h5.prepare(Path(d)/'b2.json',out,preview=True,**kw);return json.loads((out/'scene.json').read_text())
    def prepared(self,**kw):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'runtime'
            h5.prepare(self.bundle(d),out,preview=True,**kw)
            return json.loads((out/'scene.json').read_text())['renderSettings']
    def test_default_exposure_is_modest_and_light_comes_from_fixtures(self):
        self.assertEqual(h5.TOUR_EXPOSURE,1.2);self.assertEqual(self.prepared()['exposure'],1.2)
        self.assertEqual(self.prepared()['lighting'],{'hemisphere':.9,'ambient':.2})
    def test_fixture_intensity_defaults_to_twenty_and_is_capped(self):
        lamp=lambda i:{'fixtureId':'f','type':'PointLight','intensity':i,'enabled':True}
        self.assertEqual(self.scene([lamp(1)])['illumination'][0]['intensity'],20)
        self.assertEqual(self.scene([lamp(4)])['illumination'][0]['intensity'],50)
        self.assertEqual(self.scene([lamp(1)],fixture_gain=1)['illumination'][0]['intensity'],1)
        with self.assertRaises(ValueError):self.scene([lamp(1)],fixture_gain=0)
    def test_a_case_can_choose_another_exposure_but_not_a_silly_one(self):
        self.assertEqual(self.prepared(exposure=1.4)['exposure'],1.4)
        for bad in (0,.2,5,True):
            with self.subTest(bad=bad),self.assertRaises(ValueError):self.prepared(exposure=bad)

if __name__=='__main__':unittest.main()
