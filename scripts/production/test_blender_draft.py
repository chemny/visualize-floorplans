import unittest,tempfile,json,copy
from pathlib import Path
from blender_draft import validate
from unittest.mock import patch
from blender_test_fixtures import unit_route_refs
from tour_stage_gate import bound
class DraftGate(unittest.TestCase):
 def setUp(self):
  gate=patch('route_rehearsal.require_route',return_value={});gate.start();self.addCleanup(gate.stop)
 def test_bound_scope_time_and_scene(self):
  with tempfile.TemporaryDirectory() as root:
   p=Path(root);(p/'scene.blend').write_bytes(b'fixture-scene');(p/'still.png').write_bytes(b'fixture-still');model={'width':9130,'depth':17160}
   t={'schemeSha256':'s','fps':24,'seconds':4,'frames':[{'pointMm':[0,0],'eyeMm':1600,'yawRadians':0,'pitchRadians':0}]*96}
   (p/'tour.json').write_text(json.dumps(t));(p/'bundle.json').write_text(json.dumps({'schemeSha256':'s','model':model}))
   approval={'status':'user_confirmed','evidence':'synthetic static approval','scene':bound(p/'scene.blend'),'image':bound(p/'still.png')};(p/'static.json').write_text(json.dumps(approval))
   refs={'scene':bound(p/'scene.blend'),'tour':bound(p/'tour.json'),'bundle':bound(p/'bundle.json'),'staticApproval':bound(p/'static.json')}
   refs.update(unit_route_refs(p,refs['bundle']))
   auth={'scope':'blender_dynamic_draft','status':'approved','approvalSource':'explicit_user_confirmation','evidence':'synthetic draft only','startFrame':12,'endFrameExclusive':60,'anchorFrame':30,**refs};(p/'auth.json').write_text(json.dumps(auth))
   j={'schema':'homeowner-blender-draft-job/1',**refs,'authorization':bound(p/'auth.json'),'startFrame':12,'endFrameExclusive':60,'anchorFrame':30,'width':960,'samples':48,'model':model}
   validate(j,p)
   # The static anchor can be outside the selected motion interval, but must remain authorized.
   outside=copy.deepcopy(j);outside['anchorFrame']=80;auth['anchorFrame']=80
   (p/'auth.json').write_text(json.dumps(auth));outside['authorization']=bound(p/'auth.json');validate(outside,p)
   auth['anchorFrame']=30;(p/'auth.json').write_text(json.dumps(auth));j['authorization']=bound(p/'auth.json')
   # Local lighting/background revisions stay bound to explicit draft authorization.
   profile=p/'room.json';profile.write_text(json.dumps({'schema':'blender-room-presentation/1','fixtureLights':[],'exteriorCards':[]}))
   revised=copy.deepcopy(j);revised['roomPresentation']=bound(profile)
   with self.assertRaises(ValueError):validate(revised,p)
   auth['roomPresentation']=bound(profile);(p/'auth.json').write_text(json.dumps(auth));revised['authorization']=bound(p/'auth.json');validate(revised,p)
   profile.write_text('{}')
   with self.assertRaises(ValueError):validate(revised,p)
   del auth['roomPresentation'];(p/'auth.json').write_text(json.dumps(auth));j['authorization']=bound(p/'auth.json')
   for field,value in [('endFrameExclusive',96),('anchorFrame',80),('width',4096),('model',{'width':1,'depth':2})]:
    bad=copy.deepcopy(j);bad[field]=value
    with self.assertRaises(ValueError):validate(bad,p)
   auth['scope']='full_video';(p/'auth.json').write_text(json.dumps(auth));j['authorization']=bound(p/'auth.json')
   with self.assertRaises(ValueError):validate(j,p)
   auth['scope']='blender_dynamic_draft';(p/'auth.json').write_text(json.dumps(auth));j['authorization']=bound(p/'auth.json');(p/'scene.blend').write_bytes(b'changed')
   with self.assertRaises(ValueError):validate(j,p)
if __name__=='__main__':unittest.main()
