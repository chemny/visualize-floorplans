import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tour_render import engine,validate_route,prepare
from tour_stage_gate import bound
class RenderBranches(unittest.TestCase):
 def tour(self):return {'schemeSha256':'fixture','fps':24,'seconds':2/24,'frames':[{'pointMm':[0,0],'eyeMm':1600,'yawRadians':0,'pitchRadians':-.1}]*2}
 def test_default_and_invalid_engine(self):
  self.assertEqual(engine({}),'h5');self.assertEqual(engine({'rendering':{'engine':'blender'}}),'blender')
  with self.assertRaises(ValueError):engine({'rendering':{'engine':'other'}})
 def test_route_not_replanned_or_retimed(self):
  t=self.tour();self.assertIs(validate_route(t,'fixture'),t)
  with self.assertRaises(ValueError):validate_route(t,'other')
  t['seconds']=3
  with self.assertRaises(ValueError):validate_route(t,'fixture')
 def test_prepare_exact_bytes_gate_and_static_commands(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);b={'schemeSha256':'fixture','model':{},'state':{}}
   for name,data in [('bundle',b),('tour',self.tour()),('review',{}),('config',{}),('scene',b)]: (p/(name+'.json')).write_text(json.dumps(data))
   (p/'geometry.bin').write_bytes(b'mesh')
   job={'schema':'homeowner-render-job/1','runtime':str(p),**{k:bound(p/(n+'.json')) for k,n in [('bundle','bundle'),('tour','tour'),('routeReview','review'),('config','config')]}}
   with patch('route_rehearsal.require_route',side_effect=ValueError('not approved')):
    with self.assertRaisesRegex(ValueError,'not approved'):prepare(job,p,p/'blocked')
    self.assertFalse((p/'blocked').exists())
   for e in ('h5','blender'):
    job['rendering']={'engine':e}
    with patch('route_rehearsal.require_route') as gate:r=prepare(job,p,p/e);gate.assert_called_once()
    self.assertEqual((p/e/'tour.json').read_bytes(),(p/'tour.json').read_bytes());self.assertFalse(r['blenderFullAnimationEnabled']);self.assertFalse(r['videoGenerated'])
    plan=json.loads((p/e/'render-plan.json').read_text())
    if e=='blender':
     self.assertTrue(plan['staticCommands']);self.assertTrue(all('--route' in cmd and '--animation' not in cmd for cmd in plan['staticCommands']))
   (p/'tour.json').write_text('{}')
   with self.assertRaises(ValueError):prepare(job,p,p/'tampered')
if __name__=='__main__':unittest.main()
