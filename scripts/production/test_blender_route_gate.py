import copy,json,tempfile,unittest,subprocess,sys
from pathlib import Path
from unittest.mock import patch
from tour_stage_gate import bound
from blender_test_fixtures import approved_route
from blender_draft import validate
class ActualRouteGate(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=Path(self.tmp.name);p=self.p
  # Blender stage checks; the route chain itself is tested in test_tour_spatial_plan.
  chain=patch('tour_stage_chain.require_rehearsal_chain');chain.start();self.addCleanup(chain.stop)
  refs=approved_route(p);(p/'scene.blend').write_bytes(b'synthetic');(p/'still.png').write_bytes(b'synthetic')
  refs['scene']=bound(p/'scene.blend');f=p/'static.json';f.write_text(json.dumps({'status':'user_confirmed','evidence':'SYNTHETIC ONLY','scene':refs['scene'],'image':bound(p/'still.png')}));refs['staticApproval']=bound(f)
  self.auth={'scope':'blender_dynamic_draft','status':'approved','approvalSource':'explicit_user_confirmation','evidence':'SYNTHETIC ONLY','startFrame':1,'endFrameExclusive':3,'anchorFrame':0,**refs}
  self.job={'schema':'homeowner-blender-draft-job/1',**refs,'model':{'width':2000,'depth':2000},'startFrame':1,'endFrameExclusive':3,'anchorFrame':0,'width':320,'samples':8};self.rebind()
 def rebind(self):
  f=self.p/'auth.json';f.write_text(json.dumps(self.auth));self.job['authorization']=bound(f)
 def test_public_gate_accepts_exact_approved_route(self):validate(self.job,self.p)
 def test_missing_pending_or_stale_is_rejected(self):
  for key in ('routeReview','routeScene','routeGeometry'):
   j=copy.deepcopy(self.job);del j[key]
   with self.assertRaises(ValueError):validate(j,self.p)
  f=self.p/'route-approved.json';r=json.loads(f.read_text());r['status']='pending';f.write_text(json.dumps(r));self.job['routeReview']=self.auth['routeReview']=bound(f);self.rebind()
  with self.assertRaisesRegex(ValueError,'Explicit user approval'):validate(self.job,self.p)
 def test_scene_geometry_and_displayed_page_changes_rejected(self):
  for f in ('geometry.bin','scene.json','rehearsal/index.html','tour.json'):
   q=self.p/f;old=q.read_bytes();q.write_bytes(old+b' ')
   with self.subTest(file=f),self.assertRaises(ValueError):validate(self.job,self.p)
   q.write_bytes(old)
 def test_remote_rebase_preserves_route_hashes(self):
  from remote_production import prepare
  p=self.p;jf=p/'capture.json';endpoint={'sshTarget':'synthetic-host','root':'D:/Render/fixture','python':'C:/Python/python.exe','blender':'C:/Blender/blender.exe','ffmpeg':'C:/Tools/ffmpeg.exe','ffprobe':'C:/Tools/ffprobe.exe'}
  profile=p/'execution.json';profile.write_text(json.dumps({'schema':'blender-execution-profile/1','backend':'CPU','allowCpuFallback':False,'requirePackedImages':True}));self.job['executionProfile']=self.auth['executionProfile']=bound(profile);self.rebind();jf.write_text(json.dumps(self.job))
  auth=p/'remote-auth.json';auth.write_text(json.dumps({'scope':'remote_production','status':'approved','approvalSource':'explicit_user_confirmation','evidence':'SYNTHETIC ONLY','job':bound(jf),'kind':'blender','endpoint':endpoint}))
  wrapper={'schema':'homeowner-remote-production-job/1','kind':'blender','job':bound(jf),'endpoint':endpoint,'authorization':bound(auth)}
  with patch('remote_production.ps') as remote:prepare(wrapper,p,p/'transport');remote.assert_not_called()
  transformed=json.loads((p/'transport/transfer/job.json').read_text());self.assertEqual(transformed['tour']['sha256'],self.job['tour']['sha256']);self.assertNotEqual(transformed['routeReview']['sha256'],self.job['routeReview']['sha256'])
  from tour_rules import fingerprint
  script='import sys;sys.path.insert(0,sys.argv[1]);from tour_rules import fingerprint;print(fingerprint())'
  actual=subprocess.check_output([sys.executable,'-B','-c',script,str(p/'transport/transfer/scripts/production')],text=True).strip();self.assertEqual(actual,fingerprint())
if __name__=='__main__':unittest.main()
