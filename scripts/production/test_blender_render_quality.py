import unittest,json,copy,tempfile
from pathlib import Path
from blender_render_quality import validate
class RenderQuality(unittest.TestCase):
 def setUp(self):
  from unittest.mock import patch
  gate=patch('route_rehearsal.require_route',return_value={});gate.start();self.addCleanup(gate.stop)
 def test_fixed_sample_and_auxiliary_settings(self):
  p={'schema':'blender-render-quality/1','adaptiveSampling':False,'minimumSamples':0,'noiseThreshold':.005,'retainDiagnosticPasses':True}
  self.assertEqual(validate(p,64),p)
  for key,value in [('adaptiveSampling',1),('minimumSamples',65),('minimumSamples',True),('noiseThreshold',float('nan')),('retainDiagnosticPasses','yes'),('causticsRefractive',0),('exposure',1)]:
   bad=copy.deepcopy(p);bad[key]=value
   with self.assertRaises(ValueError):validate(bad,64)
 def test_speed_options_that_do_not_change_the_picture_are_checked(self):
  p={'schema':'blender-render-quality/1','persistentData':True,'pngCompression':3,'causticsReflective':False,'causticsRefractive':False}
  self.assertEqual(validate(p,64),p)
  for key,value in [('persistentData',1),('pngCompression',101),('pngCompression',-1),('pngCompression',True),('pngCompression',3.5)]:
   bad=copy.deepcopy(p);bad[key]=value
   with self.assertRaises(ValueError):validate(bad,64)
 def test_capture_quality_profile_requires_same_authorization_and_hash(self):
  from blender_draft import validate as gate
  from tour_stage_gate import bound
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)
   def save(name,value):
    f=p/name;f.write_text(json.dumps(value));return bound(f)
   (p/'scene.blend').write_bytes(b'synthetic scene');(p/'still.png').write_bytes(b'synthetic still');model={'width':2000,'depth':3000}
   refs={'scene':bound(p/'scene.blend'),'tour':save('tour.json',{'schemeSha256':'synthetic','fps':24,'seconds':4,'frames':[{'pointMm':[0,0],'eyeMm':1600,'yawRadians':0,'pitchRadians':0}]*96}),'bundle':save('bundle.json',{'schemeSha256':'synthetic','model':model})}
   refs['staticApproval']=save('static.json',{'status':'user_confirmed','evidence':'synthetic static test','scene':refs['scene'],'image':bound(p/'still.png')})
   quality=save('quality.json',{'schema':'blender-render-quality/1','adaptiveSampling':False,'retainDiagnosticPasses':True})
   from blender_test_fixtures import unit_route_refs
   refs.update(unit_route_refs(p,refs['bundle']))
   auth={'scope':'blender_dynamic_draft','status':'approved','approvalSource':'explicit_user_confirmation','evidence':'synthetic short capture','startFrame':0,'endFrameExclusive':48,'anchorFrame':12,**refs}
   job={'schema':'homeowner-blender-draft-job/1',**refs,'qualityProfile':quality,'model':model,'samples':64,'startFrame':0,'endFrameExclusive':48,'anchorFrame':12,'authorization':save('authorization.json',auth)}
   with self.assertRaises(ValueError):gate(job,p)
   auth['qualityProfile']=quality;job['authorization']=save('authorization.json',auth);gate(job,p)
   save('quality.json',{'schema':'blender-render-quality/1','adaptiveSampling':True})
   with self.assertRaises(ValueError):gate(job,p)
if __name__=='__main__':unittest.main()
