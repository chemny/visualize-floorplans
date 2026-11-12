import copy,json,subprocess,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PIL import Image
from route_rehearsal import build,require_route,CHECKS,read,dump
from tour_workflow import sha
import h5

class RouteRehearsalTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=Path(self.tmp.name);p=self.p
  # Later-stage gate tests; the chain itself is tested in test_tour_spatial_plan.
  chain=patch('tour_stage_chain.require_rehearsal_chain');chain.start();self.addCleanup(chain.stop)
  self.t={'schemeSha256':'case','fps':2,'seconds':4,'frames':[{'pointMm':[500+i*30,500],'eyeMm':1600,'yawRadians':0,'pitchRadians':0,'horizontalFovDegrees':76} for i in range(8)],'visits':[{'name':'start','frame':0},{'name':'view','frame':3},{'name':'end','frame':7}]}
  self.c={'chapters':[{'name':'连接','from':'start','to':'view','phase':'transit'},{'name':'客厅','from':'view','to':'end','phase':'observe','subjects':['sofa']}]}
  self.b={'schemeSha256':'case','model':{'rooms':[{'id':'living','poly':[[0,0],[2000,0],[2000,2000],[0,2000]]}]},'state':{'walls':[],'furniture':[]}}
  for name,v in [('tour.json',self.t),('config.json',self.c),('bundle.json',self.b),('scene.json',{'schemeSha256':'case','renderSettings':{'size':[640,360]},'materials':['warm']})]:dump(p/name,v)
  (p/'geometry.bin').write_bytes(b'synthetic geometry');Image.new('RGB',(200,200),'white').save(p/'plan.png')
 def generate(self,budget=5):
  p=self.p;m=build(p/'tour.json',p/'config.json',p/'bundle.json',p/'plan.png',[0,0,2000,2000],p/'rehearsal',budget,p)
  if self.c.get('tourContract'):
   from tour_rules import RULESET,fingerprint
   # Synthetic gate evidence, not a renderer test or actual user acceptance.
   common={'tourSha256':sha(p/'tour.json'),'configSha256':sha(p/'config.json'),'geometrySha256':sha(p/'geometry.bin'),'ruleFingerprint':fingerprint()}
   for key,value in {'screenAudit':{**common,'rulesetVersion':RULESET,'status':'pass','screenQuality':{'status':'pass'}},'visualReview':{**common,'result':'pass','observationMode':'continuous_playback','reviewedBy':'synthetic reviewer fixture','evidence':'Synthetic gate test only','checks':{k:True for k in ['transitionsNatural','noRepeatedIntroduction','noSustainedObstruction','noUncomfortableTurns']}}}.items():
    q=p/(key+'.json');dump(q,value);m['references'][key]={'path':str(q),'sha256':sha(q)}
   bundle_ref={'path':str(p/'bundle.json'),'sha256':sha(p/'bundle.json')}
   dump(p/'spatial-plan.json',{'schema':'homeowner-spatial-plan/1','status':'pending_user_confirmation','schemeSha256':'case','bundle':bundle_ref})
   plan_ref={'path':str(p/'spatial-plan.json'),'sha256':sha(p/'spatial-plan.json')}
   dump(p/'spatial-approved.json',{'schema':'homeowner-spatial-approval/1','status':'approved','approvalSource':'synthetic_test_fixture','confirmedBy':'synthetic fixture','evidence':'Synthetic test only','plan':plan_ref,'bundle':bundle_ref,'checks':{k:True for k in ('orderApproved','pathApproved','necessaryReturnsApproved')}})
   dump(p/'spatial-conformance.json',{'schema':'homeowner-spatial-conformance/1','status':'pass','tourSha256':sha(p/'tour.json')})
   for key,name in [('spatialPlan','spatial-plan.json'),('spatialReview','spatial-approved.json'),('spatialConformance','spatial-conformance.json')]:m['references'][key]={'path':str(p/name),'sha256':sha(p/name)}
   dump(p/'rehearsal/rehearsal.json',m);r=read(p/'rehearsal/route-review.pending.json');r['rehearsal']['sha256']=sha(p/'rehearsal/rehearsal.json');dump(p/'rehearsal/route-review.pending.json',r)
  return m
 def approve(self):
  p=self.p/'rehearsal';r=read(p/'route-review.pending.json');m=read(p/'rehearsal.json');r['rehearsal']['sha256']=sha(p/'rehearsal.json');r.update(status='approved',confirmedBy='synthetic user fixture',evidence='Fixture: displayed animation, heading and timing accepted',presentedAnimationSha256=m['references']['animation']['sha256'],checks={k:True for k in CHECKS});dump(p/'approved.json',r);return p/'approved.json'
 def gate(self,r):return require_route(r,self.p/'tour.json',self.p)
 def test_pending_cannot_capture_any_resolution_or_range(self):
  self.generate()
  for full in [False,True]:
   for preview in [False,True]:
    with self.subTest(full=full,preview=preview),self.assertRaisesRegex(ValueError,'route-review'):
     h5.require_capture_review(SimpleNamespace(tour=self.p/'tour.json',runtime=self.p,full=full,preview=preview,range='0:2'))
  with self.assertRaises(ValueError):self.gate(self.p/'rehearsal/route-review.pending.json')
 def test_hash_bound_approval_and_resolution_transfer(self):
  self.configure_contract();dump(self.p/'config.json',self.c);self.generate();r=self.approve();self.gate(r)
  scene=read(self.p/'scene.json');scene['renderSettings']['size']=[1920,1080];dump(self.p/'scene.json',scene);self.gate(r)
  for name in ['tour.json','config.json','plan.png','geometry.bin','rehearsal/index.html','rehearsal/timing.json']:
   path=self.p/name;before=path.read_bytes();path.write_bytes(before+b' ')
   with self.subTest(name=name),self.assertRaises(ValueError):self.gate(r)
   path.write_bytes(before)
  scene['materials']=['changed'];dump(self.p/'scene.json',scene)
  with self.assertRaises(ValueError):self.gate(r)
 def test_itinerary_or_internal_review_does_not_replace_animation(self):
  self.generate();r=self.approve();v=read(r);v['checks']['animationViewed']=False;dump(r,v)
  with self.assertRaises(ValueError):self.gate(r)
  v['checks']['animationViewed']=True;v['approvalSource']='internal_self_review';dump(r,v)
  with self.assertRaises(ValueError):self.gate(r)
 def test_budget_and_complete_chapters(self):
  self.configure_contract();dump(self.p/'config.json',self.c);m=self.generate(3);self.assertTrue(m['timing']['overBudget']);self.assertEqual(m['timing']['observeSeconds'],2);self.assertEqual(m['timing']['transitSeconds'],2)
  with self.assertRaisesRegex(ValueError,'Over-budget'):self.gate(self.approve())
  self.c['chapters']=self.c['chapters'][1:];dump(self.p/'config.json',self.c)
  with self.assertRaisesRegex(ValueError,'full timeline'):build(self.p/'tour.json',self.p/'config.json',self.p/'bundle.json',self.p/'plan.png',[0,0,2000,2000],self.p/'incomplete',5,self.p)
 def test_js_gate_accepts_same_evidence_and_blocks_missing(self):
  self.configure_contract();dump(self.p/'config.json',self.c);self.generate();r=self.approve();import os,shutil
  node=os.environ.get('FLOOR_VIS_NODE') or shutil.which('node')
  if not node:self.skipTest('Existing node unavailable')
  module=(Path(__file__).parent/'preview_gate.mjs').resolve().as_uri();script=f"import {{requireRoute,allowSyntheticSpatialFixturesForTests}} from {json.dumps(module)};allowSyntheticSpatialFixturesForTests();requireRoute(process.argv[1],process.argv[2],process.argv[3]);"
  result=subprocess.run([node,'--input-type=module','-e',script,str(r),str(self.p/'tour.json'),str(self.p)],capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr)
  result=subprocess.run([node,str(Path(__file__).parent/'h5_browser.mjs'),'capture','--runtime',str(self.p),'--tour',str(self.p/'tour.json'),'--out',str(self.p/'capture'),'--full','--preview','--range','0:2'],capture_output=True,text=True);self.assertNotEqual(result.returncode,0);self.assertIn('--route-review',result.stderr);self.assertFalse((self.p/'capture').exists())
 def configure_contract(self):
  from tour_rules import RULESET
  for f in self.t['frames']:f['shiftY']=0
  dump(self.p/'tour.json',self.t)
  self.b['state']['furniture']=[{'id':'sofa','type':'tv','cx':1700,'cy':500,'w':100,'d':20}]
  dump(self.p/'bundle.json',self.b)
  self.c.update(tourContract={'schema':'homeowner-tour-contract/1','tourMode':'indoor_segment','bodyRadiusMm':100},maximumSeconds=5,coveragePolicy={'enabled':True,'minimumPercent':1},roomViewingPolicy={'singleEpisode':True},observationPointPolicy={'defaultPointsPerRoom':1,'maximumPointsPerRoom':2,'maximumSecondsPerPoint':3,'maximumStillSeconds':.5})
  self.c['chapters'][1].update(roomId='living',episodeId='living',viewPurpose='Read room arrangement',singleSweepDegrees=0,tourRole='public')
  self.c['tourContract']['rulesetVersion']=RULESET
  self.c['roomBudgetPolicy']={'maximumTotalSeconds':5,'rooms':[{'name':'Living','roomIds':['living'],'maximumSeconds':5}]}
 def js_gate(self,review):
  import os,shutil
  node=os.environ.get('FLOOR_VIS_NODE') or shutil.which('node')
  if not node:self.skipTest('Existing node unavailable')
  module=(Path(__file__).parent/'preview_gate.mjs').resolve().as_uri()
  script=f"import {{requireRoute,allowSyntheticSpatialFixturesForTests}} from {json.dumps(module)};allowSyntheticSpatialFixturesForTests();requireRoute(process.argv[1],process.argv[2],process.argv[3]);"
  return subprocess.run([node,'--input-type=module','-e',script,str(review),str(self.p/'tour.json'),str(self.p)],capture_output=True,text=True)
 def test_contract_passes_both_capture_gate_implementations(self):
  self.configure_contract();dump(self.p/'config.json',self.c);m=self.generate();r=self.approve()
  self.assertEqual(m['timing']['tourContract']['status'],'numeric_pass_visual_pending');self.gate(r)
  result=self.js_gate(r);self.assertEqual(result.returncode,0,result.stderr)
  self.assertEqual(m['timing']['tourContract']['actual3DVisibility'],'pending')
 def rebind_test_artifact(self,key,value):
  mp=self.p/'rehearsal/rehearsal.json';m=read(mp);q=Path(m['references'][key]['path']);dump(q,value);m['references'][key]['sha256']=sha(q);dump(mp,m);return self.approve()
 def test_failed_or_sampled_playback_cannot_be_hidden_by_user_route_approval(self):
  self.configure_contract();dump(self.p/'config.json',self.c);self.generate()
  q=self.p/'visualReview.json';original=read(q)
  for changes in [{'result':'needs_revision'},{'result':'pending'},{'observationMode':'screenshot_sampling'},{'checks':{}}]:
   r=self.rebind_test_artifact('visualReview',{**original,**changes})
   with self.assertRaisesRegex(ValueError,'playback'):self.gate(r)
   self.assertNotEqual(self.js_gate(r).returncode,0)
 def test_unchanged_tour_cannot_reuse_old_rule_fingerprint(self):
  self.configure_contract();dump(self.p/'config.json',self.c);self.generate()
  value=read(self.p/'screenAudit.json');value['ruleFingerprint']='obsolete';r=self.rebind_test_artifact('screenAudit',value)
  with self.assertRaises(ValueError):self.gate(r)
  self.assertNotEqual(self.js_gate(r).returncode,0)
 def test_missing_full_timeline_screen_audit_blocks_both_gates(self):
  self.configure_contract();dump(self.p/'config.json',self.c);self.generate();mp=self.p/'rehearsal/rehearsal.json';m=read(mp);m['references'].pop('screenAudit');dump(mp,m);r=self.approve()
  with self.assertRaisesRegex(ValueError,'screenAudit'):self.gate(r)
  self.assertNotEqual(self.js_gate(r).returncode,0)
 def test_binding_failed_review_resets_approval_manifest_and_workflow(self):
  from route_rehearsal import bind_quality
  self.configure_contract();dump(self.p/'config.json',self.c);self.generate();self.approve();dump(self.p/'workflow-state.json',{'stage':'rehearsal_pending','events':[]})
  value=read(self.p/'visualReview.json');value['result']='needs_revision';dump(self.p/'failed-review.json',value)
  bind_quality(self.p/'rehearsal/rehearsal.json',self.p/'screenAudit.json',self.p/'failed-review.json')
  self.assertEqual(read(self.p/'rehearsal/route-review.pending.json')['status'],'pending');self.assertEqual(read(self.p/'rehearsal/rehearsal.json')['status'],'needs_revision');self.assertFalse(read(self.p/'self-check.json')['reviewable']);self.assertEqual(read(self.p/'workflow-state.json')['stage'],'repair_required')
  mp=self.p/'rehearsal/rehearsal.json';m=read(mp);m['timing']['tourContract']['issues']=[{'code':'synthetic_numeric_failure'}];m['timing']['tourContract']['status']='needs_revision';dump(mp,m);value['result']='pending';dump(self.p/'pending-review.json',value)
  bind_quality(mp,self.p/'screenAudit.json',self.p/'pending-review.json');self.assertEqual(read(self.p/'workflow-state.json')['stage'],'repair_required')
 def test_total_time_pass_does_not_bypass_room_budget_in_python_or_js(self):
  self.configure_contract();self.c['roomBudgetPolicy']={'maximumTotalSeconds':5,'rooms':[{'name':'Living','roomIds':['living'],'maximumSeconds':.1}]};dump(self.p/'config.json',self.c)
  m=self.generate();r=self.approve();self.assertFalse(m['timing']['overBudget'])
  with self.assertRaisesRegex(ValueError,'Tour contract'):self.gate(r)
  result=self.js_gate(r);self.assertNotEqual(result.returncode,0);self.assertIn('Tour contract',result.stderr)
 def test_direct_gate_rejects_missing_contract_report(self):
  self.configure_contract();dump(self.p/'config.json',self.c);self.generate()
  manifest_path=self.p/'rehearsal/rehearsal.json';m=read(manifest_path);m['references'].pop('contractReport');dump(manifest_path,m);r=self.approve();approval=read(r);approval['rehearsal']['sha256']=sha(manifest_path);dump(r,approval)
  result=self.js_gate(r);self.assertNotEqual(result.returncode,0);self.assertIn('contract report missing',result.stderr)
 def test_old_contract_report_without_camera_evidence_cannot_capture_directly(self):
  self.configure_contract();dump(self.p/'config.json',self.c);self.generate()
  mp=self.p/'rehearsal/rehearsal.json';m=read(mp);rp=Path(m['references']['contractReport']['path']);report=read(rp);report['checks'].pop('cameraEvidence');dump(rp,report)
  m['references']['contractReport']['sha256']=sha(rp);dump(mp,m);r=self.approve();approval=read(r);approval['rehearsal']['sha256']=sha(mp);dump(r,approval)
  result=self.js_gate(r);self.assertNotEqual(result.returncode,0);self.assertIn('Tour contract requires revision',result.stderr)
 def test_legacy_capture_denied_by_python_and_javascript(self):
  self.generate();r=self.approve()
  with self.assertRaisesRegex(ValueError,'missing_tour_contract'):self.gate(r)
  result=self.js_gate(r);self.assertNotEqual(result.returncode,0);self.assertIn('Missing tour contract',result.stderr)
if __name__=='__main__':unittest.main()
