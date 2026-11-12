import json,math,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tour_spatial_plan as spatial
import tour_stage_chain as chain
from tour_stage_gate import bound
from design_homeowner_tour import entry_apron

# All approvals here are synthetic. They pass only through the test-only patch below,
# and test_synthetic_fixture_rejected_without_test_patch proves the real gate refuses them.
def wall(id,a,b,opens=()):return {'id':id,'a':a,'b':b,'t':120,'height':2700,'opens':list(opens)}
def bundle_value():
 door=lambda id,at:{'kind':'door','at':at,'width':900,'swing':-1,'angle':90,'id':id}
 return {'schema':'floor-visualization-production/1.0','schemeSha256':'a'*64,'caseId':'synthetic','confirmations':{},
  'model':{'title':'合成户型','footprint':[[0,0],[8000,0],[8000,4000],[0,4000]],'rooms':[{'id':'hall','name':'厅','poly':[[60,60],[3940,60],[3940,3940],[60,3940]]},{'id':'east','name':'东室','poly':[[4060,60],[7940,60],[7940,3940],[4060,3940]]}]},
  'state':{'walls':[wall('S',[0,0],[8000,0],[door('IN',1000)]),wall('N',[0,4000],[8000,4000]),wall('W',[0,0],[0,4000]),wall('E',[8000,0],[8000,4000]),wall('M',[4000,0],[4000,4000],[door('MID',1500)])],'furniture':[{'id':'sofa','type':'sofa','cx':1500,'cy':3200,'w':1800,'d':800,'h':800,'rot':0}]}}
def job_value(**extra):
 return {'schema':'homeowner-spatial-job/1','bundle':'bundle.json','entranceOpeningId':'IN','entranceSource':'synthetic fixture','startPoint':[1450,-600],'bodyRadiusMm':180,'gridMm':80,'order':{'mode':'fixed','source':'synthetic'},'visits':[{'name':'厅','roomId':'hall'},{'name':'东室','roomId':'east'}],**extra}
def frames(points,fps=2):return {'schemeSha256':'a'*64,'fps':fps,'seconds':len(points)/fps,'frames':[{'pointMm':p} for p in points]}

class Base(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=Path(self.tmp.name)
  (self.p/'bundle.json').write_text(json.dumps(bundle_value()))
 def generate(self,name='route',**extra):
  return spatial.run(job_value(**extra),self.p,self.p/name),self.p/name
 def approve(self,out,**fields):
  r=json.loads((out/'spatial-review.pending.json').read_text())
  r.update(status='approved',approvalSource='synthetic_test_fixture',confirmedBy='synthetic user fixture',evidence='Synthetic test only',checks={k:True for k in spatial.CHECKS},**fields)
  path=out/'approved.json';path.write_text(json.dumps(r));return path

class RoutePlanning(Base):
 def test_plan_has_route_data_and_no_camera_or_frames(self):
  plan,out=self.generate()
  self.assertEqual(plan['status'],'pending_user_confirmation');self.assertEqual(plan['openingSequence'],['IN','MID','MID','IN'])
  for key in ('frames','cameraKeys','seconds','tour'):self.assertNotIn(key,plan)
  self.assertFalse(plan['cameraGenerated']);self.assertFalse(plan['approvalGranted'])
  self.assertEqual([s['name'] for s in plan['stations']],['厅','东室'])
  page=(out/'route.html').read_text()
  for word in ('参观路线','路线待确认'):self.assertIn(word,page)
  self.assertNotIn('<video',page);self.assertNotIn('rehearsalPlayback',page);self.assertNotIn('<iframe',page)
  self.assertEqual(json.loads((out/'spatial-review.pending.json').read_text())['status'],'pending')
  stages=json.loads((out/'stage-state.json').read_text())['stages']
  self.assertEqual(stages['route']['status'],'pending_user_confirmation')
  for stage in ('preview','video','narrated'):self.assertEqual(stages[stage]['status'],'blocked_by_upstream')
 def test_invalid_jobs_are_refused(self):
  for key,value,reason in [('schema','x','Explicit spatial job'),('frames',[],'camera or frame'),('cameraKeys',[],'camera or frame'),('bodyRadiusMm',120,'never shrink'),('gridMm',5,'gridMm'),('entranceSource','','entranceSource'),('order',{'mode':'fixed'},'cite its source'),('endPoint',[1450,4600],'openEndReason'),('search',{'maximumPlanningSeconds':99999},'deadline'),('search',{'candidatesPerVisit':500},'candidatesPerVisit')]:
   with self.subTest(key=key),self.assertRaisesRegex(ValueError,reason):spatial.validate_job(job_value(**{key:value}))
  with self.assertRaisesRegex(ValueError,'unique'):spatial.validate_job(job_value(visits=[{'name':'厅','roomId':'hall'},{'name':'厅','roomId':'east'}]))
 def test_outside_point_is_diagnosed_as_undeclared_not_collision(self):
  planner=spatial.Planner(bundle_value(),{'bodyRadiusMm':180,'gridMm':80})
  self.assertEqual([r['code'] for r in spatial.explain_point(planner,[1450,-600])],['outside_declared_domain'])
  access,_=entry_apron(bundle_value(),{'entranceOpeningId':'IN','startPoint':[1450,-600],'bodyRadiusMm':180})
  self.assertEqual(spatial.explain_point(spatial.Planner(bundle_value(),{'bodyRadiusMm':180,'gridMm':80,'accessPolygons':access}),[1450,-600]),[])
 def test_real_collision_names_the_obstacle_and_is_not_relaxed(self):
  value=job_value(visits=[{'name':'厅','roomId':'hall','pointMm':[1500,3200]},{'name':'东室','roomId':'east'}])
  with self.assertRaisesRegex(ValueError,'furniture_clearance') as caught:spatial.run(value,self.p,self.p/'blocked')
  self.assertIn('spatial-diagnostics',str(caught.exception))
  report=json.loads((self.p/'blocked/spatial-diagnostics.json').read_text())
  self.assertEqual(report['details']['reasons'][0]['id'],'sofa');self.assertFalse((self.p/'blocked/spatial-plan.json').exists())
 def test_unreachable_room_reports_openings(self):
  b=bundle_value();b['state']['walls'][4]['opens']=[];(self.p/'bundle.json').write_text(json.dumps(b))
  with self.assertRaisesRegex(ValueError,'connected to the entrance'):spatial.run(job_value(),self.p,self.p/'out')
 def test_unvisited_room_and_exclusion_need_reason(self):
  plan,_=self.generate(visits=[{'name':'厅','roomId':'hall'}])
  self.assertEqual(plan['status'],'needs_revision');self.assertIn('room_not_visited',[i['code'] for i in plan['issues']])
  plan,_=self.generate('excluded',visits=[{'name':'厅','roomId':'hall'}],excludedRooms=[{'roomId':'east','reason':'用户说明不参观'}])
  self.assertEqual(plan['status'],'pending_user_confirmation')
 def test_single_door_return_is_classified_and_allowed(self):
  plan,_=self.generate()
  self.assertTrue(plan['roomExits']['east']['singleExit']);self.assertEqual(plan['status'],'pending_user_confirmation')
  self.assertTrue(all(r['classification'] in ('required_bottleneck','required_single_exit_branch','alternative_exists') for r in plan['retraces']))
 def test_order_is_respected_and_fresh_output_required(self):
  plan,_=self.generate(visits=[{'name':'东室','roomId':'east'},{'name':'厅','roomId':'hall'}])
  self.assertEqual([s['name'] for s in plan['stations']],['东室','厅'])
  with self.assertRaisesRegex(ValueError,'Fresh'):spatial.run(job_value(),self.p,self.p/'route')

class AutomaticRoute(Base):
 def loop_bundle(self):
  # Ring of rooms around a core, door straight ahead into the entry room.
  door=lambda id,at:{'kind':'door','at':at,'width':900,'swing':-1,'angle':90,'id':id}
  room=lambda id,x,y,w,h:{'id':id,'name':id,'poly':[[x+60,y+60],[x+w-60,y+60],[x+w-60,y+h-60],[x+60,y+h-60]]}
  b=bundle_value();b['model'].update(footprint=[[0,0],[9000,0],[9000,9000],[0,9000]],rooms=[room('entry',3000,0,3000,3000),room('west',0,0,3000,9000),room('east',6000,0,3000,9000),room('north',3000,6000,3000,3000)])
  b['state'].update(furniture=[],walls=[wall('S1',[0,0],[3000,0]),wall('S',[3000,0],[6000,0],[door('IN',1000)]),wall('S3',[6000,0],[9000,0]),wall('N',[0,9000],[9000,9000]),wall('W',[0,0],[0,9000]),wall('E',[9000,0],[9000,9000]),wall('A',[3000,0],[3000,9000],[door('AW',1000),door('NW',7000)]),wall('B',[6000,0],[6000,9000],[door('AE',1000),door('NE',7000)]),wall('C',[3000,3000],[6000,3000]),wall('D',[3000,6000],[6000,6000])])
  return b
 def test_minimal_job_reads_entrance_and_needs_no_visits(self):
  (self.p/'case.json').write_text(json.dumps({'entranceOpenings':['IN']}))
  plan=spatial.run({'schema':'homeowner-spatial-job/1','bundle':'bundle.json','caseFile':'case.json'},self.p,self.p/'auto')
  self.assertEqual(plan['entrance']['openingId'],'IN');self.assertEqual(set(plan['autoFilled']),{'entrance','startPoint','visits'})
  self.assertEqual({s['roomId'] for s in plan['stations']},{'hall','east'});self.assertEqual(plan['status'],'pending_user_confirmation');self.assertFalse(plan['approvalGranted'])
 def test_entrance_is_never_guessed(self):
  with self.assertRaisesRegex(ValueError,'never guessed'):spatial.fill_defaults({'schema':'homeowner-spatial-job/1','bundle':'bundle.json'},self.p)
  (self.p/'case.json').write_text(json.dumps({'entranceOpenings':['IN','MID']}))
  with self.assertRaisesRegex(ValueError,'exactly one'):spatial.fill_defaults({'schema':'homeowner-spatial-job/1','bundle':'bundle.json','caseFile':'case.json'},self.p)
 def test_entry_room_goes_first_even_when_reverse_would_be_shorter(self):
  plan,_=self.generate(order={'mode':'shortest'},visits=[{'name':'东室','roomId':'east'},{'name':'厅','roomId':'hall'}])
  self.assertEqual([s['name'] for s in plan['stations']],['厅','东室']);self.assertEqual(plan['order']['direction']['firstVisit'],'厅')
 def test_auto_zones_split_only_multifunction_rooms(self):
  b=bundle_value();b['state']['furniture'].append({'id':'t','type':'table','cx':2800,'cy':1000,'w':900,'d':900,'h':750,'rot':0})
  self.assertEqual([v['name'] for v in spatial.auto_visits(b)],['客厅','餐厅','东室'])
  self.assertEqual([v['name'] for v in spatial.auto_visits(bundle_value())],['厅','东室'])
 def test_direction_tie_goes_by_view_and_real_difference_keeps_distance(self):
  b=self.loop_bundle();(self.p/'bundle.json').write_text(json.dumps(b));job={'schema':'homeowner-spatial-job/1','bundle':'bundle.json','entranceOpeningId':'IN','entranceSource':'synthetic','startPoint':[4450,-600]}
  plan=spatial.run(job,self.p,self.p/'tie');detail=plan['order']['direction']
  self.assertEqual(plan['stations'][0]['roomId'],'entry');self.assertEqual(len(plan['stations']),4)
  self.assertIn(detail['basis'],('first_seen_from_entrance','shortest_walk'));self.assertLessEqual(detail['chosenLengthM'],detail['reverseLengthM']*1.05)
  again=spatial.run(job,self.p,self.p/'tie2');self.assertEqual([s['name'] for s in again['stations']],[s['name'] for s in plan['stations']])
 def test_auto_visit_without_standing_room_is_reported_not_silent(self):
  b=bundle_value();b['model']['rooms'].append({'id':'bay','name':'飘窗','poly':[[7700,3700],[7900,3700],[7900,3900],[7700,3900]]});(self.p/'bundle.json').write_text(json.dumps(b))
  (self.p/'case.json').write_text(json.dumps({'entranceOpenings':['IN']}))
  plan=spatial.run({'schema':'homeowner-spatial-job/1','bundle':'bundle.json','caseFile':'case.json'},self.p,self.p/'bay')
  self.assertEqual([r['roomId'] for r in plan['excludedRooms']],['bay']);self.assertIn('未走入',(self.p/'bay/route.html').read_text())
  with self.assertRaises(ValueError):spatial.run(job_value(visits=[{'name':'飘窗','roomId':'bay'}]),self.p,self.p/'explicit')

class ApprovalGate(Base):
 def gate(self,review,plan,**kw):
  with patch.object(spatial,'ALLOW_SYNTHETIC_FOR_TESTS',True):return spatial.require_approval(review,plan,**kw)
 def test_pending_cannot_pass(self):
  _,out=self.generate()
  with self.assertRaises(ValueError):spatial.require_approval(out/'spatial-review.pending.json',out/'spatial-plan.json')
  with self.assertRaises(ValueError):self.gate(out/'spatial-review.pending.json',out/'spatial-plan.json')
 def test_synthetic_fixture_rejected_without_test_patch(self):
  _,out=self.generate();review=self.approve(out)
  with self.assertRaisesRegex(ValueError,'actual user'):spatial.require_approval(review,out/'spatial-plan.json')
  self.gate(review,out/'spatial-plan.json')
 def test_agents_and_fixtures_cannot_sign_as_user(self):
  _,out=self.generate()
  for signer in ('Claude','codex agent','synthetic user','自动确认'):
   review=self.approve(out);r=json.loads(review.read_text());r.update(approvalSource='explicit_user_confirmation',confirmedBy=signer);review.write_text(json.dumps(r))
   with self.subTest(signer=signer),self.assertRaisesRegex(ValueError,'actual user'):spatial.require_approval(review,out/'spatial-plan.json')
 def test_any_unchecked_item_is_rejected(self):
  _,out=self.generate()
  for key in spatial.CHECKS:
   review=self.approve(out);r=json.loads(review.read_text());r['checks'][key]=False;review.write_text(json.dumps(r))
   with self.subTest(key=key),self.assertRaisesRegex(ValueError,'Incomplete'):self.gate(review,out/'spatial-plan.json')
 def test_changed_plan_bundle_or_page_invalidates(self):
  for name in ('spatial-plan.json','route.html','../bundle.json'):
   _,out=self.generate('r'+str(abs(hash(name))));review=self.approve(out);self.gate(review,out/'spatial-plan.json');target=out/name;before=target.read_bytes();target.write_bytes(before+b' ')
   with self.subTest(name=name),self.assertRaises(ValueError):self.gate(review,None)
   target.write_bytes(before)
 def test_plan_with_issues_cannot_be_approved(self):
  _,out=self.generate(visits=[{'name':'厅','roomId':'hall'}]);review=self.approve(out)
  with self.assertRaisesRegex(ValueError,'unresolved'):self.gate(review,out/'spatial-plan.json')
 def test_internal_bundle_identity_must_match(self):
  _,out=self.generate();review=self.approve(out);other=self.p/'other.json';other.write_text(json.dumps({**bundle_value(),'caseId':'other'}))
  with self.assertRaisesRegex(ValueError,'Changed spatial bundle'):self.gate(review,out/'spatial-plan.json',bundle=other)

class Conformance(Base):
 def route_frames(self,plan):return [list(p) for p in plan['routeMm']]
 def dense(self,points):
  out=[]
  for a,b in zip(points,points[1:]):
   for i in range(10):out.append([a[k]+(b[k]-a[k])*i/10 for k in (0,1)])
  return out+[points[-1]]
 def test_small_safe_rounding_passes(self):
  plan,_=self.generate();points=self.dense(self.route_frames(plan));points=[[x+(40 if 3<i<len(points)-4 else 0),y] for i,(x,y) in enumerate(points)]
  self.assertEqual(spatial.conformance(plan,frames(points))['issues'],[])
 def test_skipping_room_order_or_opening_returns_to_route_stage(self):
  plan,_=self.generate();points=self.dense(self.route_frames(plan));station=plan['stations'][1]['pointMm']
  cut=[p for p in points if p[0]<3000]
  codes=[i['code'] for i in spatial.conformance(plan,frames(cut))['issues']]
  self.assertIn('spatial_opening_sequence',codes);self.assertIn('spatial_visit_order',codes)
  self.assertEqual(spatial.conformance(plan,frames(cut))['status'],'return_to_route_confirmation')
  self.assertIn('spatial_exit_changed',[i['code'] for i in spatial.conformance(plan,frames(points[:len(points)//2]))['issues']])
  self.assertEqual(station,plan['stations'][1]['pointMm'])
 def test_detour_length_and_wrong_scheme_rejected(self):
  plan,_=self.generate();points=self.dense(self.route_frames(plan));padded=points[:5]+[p for _ in range(4) for p in (points[5],points[12])]+points[5:]
  self.assertIn('spatial_route_length',[i['code'] for i in spatial.conformance(plan,frames(padded))['issues']])
  self.assertIn('spatial_scheme_mismatch',[i['code'] for i in spatial.conformance(plan,{**frames(points),'schemeSha256':'b'*64})['issues']])

class EntryGates(Base):
 def test_camera_entries_refuse_without_real_approval(self):
  _,out=self.generate();job={'schema':'homeowner-production-job/1','bundle':str(self.p/'bundle.json')}
  from tour_pipeline import run
  with self.assertRaisesRegex(ValueError,'approved spatial route'):run(job,self.p/'camera')
  with self.assertRaisesRegex(ValueError,'actual user|confirmation'):run({**job,'spatialPlan':str(out/'spatial-plan.json'),'spatialReview':str(out/'spatial-review.pending.json')},self.p/'camera')
  self.assertFalse((self.p/'camera').exists())
 def test_h5_design_and_rehearsal_cli_refuse(self):
  env={**os.environ,'PYTHONPATH':str(Path(__file__).parent)};here=Path(__file__).parent
  result=subprocess.run([sys.executable,str(here/'h5.py'),'design-tour','--bundle',str(self.p/'bundle.json'),'--brief',str(self.p/'bundle.json'),'--out',str(self.p/'design')],capture_output=True,text=True,env=env)
  self.assertNotEqual(result.returncode,0);self.assertIn('approved spatial route',result.stderr);self.assertFalse((self.p/'design').exists())
  result=subprocess.run([sys.executable,str(here/'route_rehearsal.py'),'--tour','x','--config','x','--bundle',str(self.p/'bundle.json'),'--plan','x','--out',str(self.p/'r'),'--runtime','x','--bounds','0','0','1','1','--budget-seconds','1'],capture_output=True,text=True,env=env)
  self.assertNotEqual(result.returncode,0);self.assertIn('approved spatial route',result.stderr)
 def test_camera_entry_accepts_only_matching_bundle(self):
  _,out=self.generate();review=self.approve(out);job={'bundle':str(self.p/'bundle.json'),'spatialPlan':str(out/'spatial-plan.json'),'spatialReview':str(review)}
  with self.assertRaisesRegex(ValueError,'actual user'):chain.require_camera_entry(job)
  with patch.object(spatial,'ALLOW_SYNTHETIC_FOR_TESTS',True):
   self.assertEqual(chain.require_camera_entry(job)['value']['status'],'pending_user_confirmation')
   other=self.p/'other.json';other.write_text(json.dumps({**bundle_value(),'caseId':'other'}))
   with self.assertRaisesRegex(ValueError,'Changed spatial bundle'):chain.require_camera_entry({**job,'bundle':str(other)})
 def test_rehearsal_chain_rejects_missing_and_departed_route(self):
  _,out=self.generate();review=self.approve(out);plan=json.loads((out/'spatial-plan.json').read_text());tour=self.p/'tour.json';tour.write_text(json.dumps(frames(plan['routeMm'])))
  with self.assertRaisesRegex(ValueError,'no approved spatial route'):chain.require_rehearsal_chain({'references':{}},self.p,tour)
  refs={'spatialPlan':bound(out/'spatial-plan.json'),'spatialReview':bound(review),'bundle':bound(self.p/'bundle.json')};manifest={'references':refs,'schemeSha256':'a'*64}
  with patch.object(spatial,'ALLOW_SYNTHETIC_FOR_TESTS',True):
   tour.write_text(json.dumps(frames([plan['routeMm'][0],plan['routeMm'][1]])))
   with self.assertRaisesRegex(ValueError,'left the approved route'):chain.require_rehearsal_chain(manifest,self.p,tour)
  with self.assertRaisesRegex(ValueError,'actual user'):chain.require_rehearsal_chain(manifest,self.p,tour)
 def test_old_plan_only_approval_cannot_stand_in(self):
  _,out=self.generate();r=self.approve(out);value=json.loads(r.read_text());value['schema']='homeowner-route-approval/1';r.write_text(json.dumps(value))
  with patch.object(spatial,'ALLOW_SYNTHETIC_FOR_TESTS',True),self.assertRaisesRegex(ValueError,'confirmation required'):spatial.require_approval(r,out/'spatial-plan.json')
 def test_capture_gate_refuses_rehearsal_without_chain(self):
  import h5
  with self.assertRaisesRegex(ValueError,'route-review'):h5.require_capture_review(SimpleNamespace(tour=self.p/'tour.json',runtime=self.p,full=True,preview=True,range=None))
 def test_node_gate_matches_python_for_direct_browser_capture(self):
  node=os.environ.get('FLOOR_VIS_NODE') or shutil.which('node')
  if not node:self.skipTest('Existing node unavailable')
  module=(Path(__file__).parent/'preview_gate.mjs').as_uri()
  _,out=self.generate();review=json.loads(self.approve(out).read_text());plan=json.loads((out/'spatial-plan.json').read_text())
  tour=self.p/'tour.json';tour.write_text(json.dumps(frames(plan['routeMm'])))
  report=self.p/'report.json';report.write_text(json.dumps({'schema':'homeowner-spatial-conformance/1','status':'pass','tourSha256':bound(tour)['sha256']}))
  # Exercise only the chain: a later gate failure message proves the chain itself passed.
  config=self.p/'config.json';config.write_text(json.dumps({'tourContract':{}}))
  anim=self.p/'a.html';anim.write_text('x');scene=self.p/'scene.json';scene.write_text(json.dumps({'schemeSha256':'a'*64}));geo=self.p/'geometry.bin';geo.write_text('g')
  (self.p/'review-final.json').write_text(json.dumps(review))
  m={'schema':'homeowner-route-rehearsal/1','schemeSha256':'a'*64,'geometrySha256':bound(geo)['sha256'],'timing':{'overBudget':False,'totalSeconds':1,'maximumSeconds':2},'references':{'tour':bound(tour),'config':bound(config),'bundle':bound(self.p/'bundle.json'),'animation':bound(anim),'scene':bound(scene),'spatialPlan':bound(out/'spatial-plan.json'),'spatialReview':bound(self.p/'review-final.json'),'spatialConformance':bound(report)}}
  mp=self.p/'rehearsal.json';mp.write_text(json.dumps(m))
  r={'schema':'homeowner-route-approval/1','status':'approved','approvalSource':'explicit_user_confirmation','confirmedBy':'x','evidence':'x','checks':{k:True for k in ('animationViewed','pathAndFacingApproved','durationAndRhythmApproved')},'rehearsal':bound(mp),'presentedAnimationSha256':bound(anim)['sha256']};rp=self.p/'route-review.json';rp.write_text(json.dumps(r))
  call=lambda allow:subprocess.run([node,'--input-type=module','-e',f"import {{requireRoute,allowSyntheticSpatialFixturesForTests as a}} from {json.dumps(module)};{'a();' if allow else ''}requireRoute(process.argv[1],process.argv[2],process.argv[3]);",str(rp),str(tour),str(self.p)],capture_output=True,text=True)
  refused=call(False);self.assertNotEqual(refused.returncode,0);self.assertIn('actual user',refused.stderr)
  passed=call(True);self.assertNotEqual(passed.returncode,0);self.assertIn('Tour contract report missing',passed.stderr)
  m['references'].pop('spatialReview');mp.write_text(json.dumps(m));r['rehearsal']=bound(mp);rp.write_text(json.dumps(r))
  self.assertIn('no approved spatial route',call(True).stderr)

class StageState(Base):
 def test_each_upstream_change_blocks_downstream(self):
  _,out=self.generate();review=self.approve(out);job={'bundle':str(self.p/'bundle.json'),'spatialPlan':bound(out/'spatial-plan.json'),'spatialReview':str(review)}
  with patch.object(spatial,'ALLOW_SYNTHETIC_FOR_TESTS',True):
   state=chain.evaluate(job,self.p)['stages'];self.assertEqual(state['route']['status'],'approved');self.assertEqual(state['preview']['status'],'not_prepared');self.assertEqual(state['video']['status'],'blocked_by_upstream')
   before=(out/'route.html').read_bytes();(out/'route.html').write_bytes(before+b' ')
   state=chain.evaluate(job,self.p)['stages'];self.assertEqual(state['route']['status'],'stale_or_invalid');self.assertEqual(state['preview']['status'],'blocked_by_upstream');(out/'route.html').write_bytes(before)
   other=self.p/'other.json';other.write_text(json.dumps({**bundle_value(),'caseId':'other'}))
   self.assertEqual(chain.evaluate({**job,'bundle':str(other)},self.p)['stages']['route']['status'],'stale_or_invalid')
  self.assertEqual(chain.evaluate(job,self.p)['stages']['route']['status'],'stale_or_invalid')
 def test_downstream_approval_ignored_when_route_unconfirmed(self):
  _,out=self.generate();job={'bundle':str(self.p/'bundle.json'),'spatialPlan':str(out/'spatial-plan.json'),'routeReview':'x','videoReview':'y','video':'z'}
  stages=chain.evaluate(job,self.p)['stages'];self.assertEqual(stages['route']['status'],'pending_user_confirmation')
  for stage in ('preview','video','narrated'):self.assertEqual(stages[stage]['status'],'blocked_by_upstream')
 def test_no_stage_check_grants_approval(self):
  self.assertFalse(chain.evaluate({},self.p)['approvalGranted'])

class RecordApproval(Base):
 def test_records_only_the_users_words_and_passes_the_real_gate(self):
  from record_approval import record_route
  _,out=self.generate();target=out/'user-approval.json'
  for who,words in (('Claude','确认'),('codex agent','确认'),('synthetic user','确认'),('',''),('王女士','')):
   with self.subTest(who=who),self.assertRaises(ValueError):record_route(out/'spatial-review.pending.json',out/'never.json',who,words)
  self.assertFalse((out/'never.json').exists())
  record=record_route(out/'spatial-review.pending.json',target,'王女士','路线没问题，确认')
  self.assertEqual(record['status'],'approved');spatial.require_approval(target,out/'spatial-plan.json')
  with self.assertRaisesRegex(ValueError,'preserved'):record_route(out/'spatial-review.pending.json',target,'王女士','再确认一次')
 def test_a_recorded_approval_dies_when_the_page_or_plan_changes(self):
  from record_approval import record_route
  _,out=self.generate();target=out/'user-approval.json';record_route(out/'spatial-review.pending.json',target,'王女士','确认')
  page=out/'route.html';before=page.read_bytes();page.write_bytes(before+b' ')
  with self.assertRaises(ValueError):spatial.require_approval(target,out/'spatial-plan.json')
 def test_an_already_approved_or_tampered_pending_file_is_refused(self):
  from record_approval import record_route
  _,out=self.generate();pending=out/'spatial-review.pending.json';value=json.loads(pending.read_text());value['status']='approved';pending.write_text(json.dumps(value))
  with self.assertRaises(ValueError):record_route(pending,out/'x.json','王女士','确认')

class BriefAlignment(unittest.TestCase):
 def plan(self):
  return {'entrance':{'openingId':'D','startPointMm':[0,-500]},'cameraEnvelope':{'stationToleranceMm':2800},'stations':[{'name':'厅','pointMm':[1000,1000]},{'name':'东室','pointMm':[5000,1000]}]}
 def brief(self,**extra):
  return {'entranceOpeningId':'D','startPoint':[0,-500],'fixedOrder':['a','b'],'rooms':[{'observationId':'a','name':'厅','candidatePoints':[[1100,1000]]},{'observationId':'b','name':'东室','candidatePoints':[[5200,1000]]}],**extra}
 def test_a_brief_that_follows_the_route_passes(self):
  self.assertEqual(chain.check_brief_alignment(self.brief(),self.plan()),[])
 def test_a_pass_through_station_is_allowed_but_reported(self):
  p=self.plan();p['stations'].insert(0,{'name':'玄关','pointMm':[500,0]})
  self.assertEqual(chain.check_brief_alignment(self.brief(),p),[]);self.assertEqual(chain.pass_through_stations(self.brief(),p),['玄关'])
  self.assertEqual(chain.check_brief_alignment(self.brief(fixedOrder=['b','a']),p)[0]['code'],'brief_order_differs_from_route')
 def test_each_kind_of_drift_is_named(self):
  p=self.plan()
  self.assertEqual(chain.check_brief_alignment(self.brief(fixedOrder=None),p)[0]['code'],'brief_order_not_fixed')
  self.assertEqual(chain.check_brief_alignment(self.brief(fixedOrder=['b','a']),p)[0]['code'],'brief_order_differs_from_route')
  self.assertEqual(chain.check_brief_alignment(self.brief(fixedOrder=['a','zz']),p)[0]['code'],'brief_unknown_observation')
  self.assertEqual(chain.check_brief_alignment(self.brief(startPoint=[50,-500]),p)[0]['code'],'brief_start_differs_from_route')
  self.assertEqual(chain.check_brief_alignment(self.brief(entranceOpeningId='X'),p)[0]['code'],'brief_entrance_differs_from_route')
  far=self.brief();far['rooms'][1]['candidatePoints']=[[9000,1000]]
  self.assertEqual(chain.check_brief_alignment(far,p)[0]['code'],'brief_station_far_from_route')

class Diagnostics(unittest.TestCase):
 def test_reports_turning_pitch_wall_time_and_maps_screen_issues_to_chapters(self):
  from tour_camera_diagnostics import build
  class Open:
   walls=[];vision_leaves=[];leaves=[]
  fps=10;frames=[{'pointMm':[i*100.,0.],'yawRadians':math.radians(min(i,20)*3),'pitchRadians':math.radians(-4),'eyeMm':1300} for i in range(40)]
  tour={'fps':fps,'seconds':4.0,'frames':frames,'visits':[{'name':'a','frame':0},{'name':'b','frame':19},{'name':'c','frame':39}]}
  config={'chapters':[{'name':'走','from':'a','to':'b','phase':'transit'},{'name':'看','from':'b','to':'c','phase':'observe'}]}
  audit={'status':'fail','screenQuality':{'issues':[{'code':'screen_near_surface_occlusion','startSeconds':2.5,'endSeconds':3.2},{'code':'subject_composition_unreadable','chapter':'看','subjectId':'X','readableSeconds':0}]}}
  report=build({},tour,config,Open(),audit)
  self.assertEqual(report['eyeMm'],[1300]);self.assertEqual([r['name'] for r in report['chapters']],['走','看'])
  self.assertAlmostEqual(report['chapters'][0]['yawTravelDegrees'],57,delta=1);self.assertEqual(report['screenIssues'][0]['chapter'],'看')
  self.assertAlmostEqual(report['chapters'][0]['secondsFacingWallUnderOneMetre'],0);self.assertAlmostEqual(report['transitFraction'],1-report['observeSeconds']/4.0)

 def test_room_wobble_wall_runs_and_time_breakdown(self):
  from tour_camera_diagnostics import room_wobble,wall_facing_runs,time_breakdown
  fps=10;yaws=[0]*5+list(range(0,-30,-3))+list(range(-30,40,5))+[40]*5
  frames=[{'pointMm':[0.,0.],'yawRadians':math.radians(v),'pitchRadians':0.,'eyeMm':1300} for v in yaws]
  tour={'fps':fps,'seconds':len(frames)/fps,'frames':frames}
  marks={'房 · 到达':5,'房 · 看完':len(frames)-6}
  row=room_wobble(tour,marks)[0];self.assertEqual(row['room'],'房');self.assertEqual(row['reversals'],1);self.assertLess(row['swingsDegrees'][0]*row['swingsDegrees'][1],0)
  straight=[{**f,'yawRadians':math.radians(i)} for i,f in enumerate(frames)]
  self.assertEqual(room_wobble({**tour,'frames':straight},marks)[0]['reversals'],0)
  ahead=[3000]*10+[300]*8+[3000]*10
  runs=wall_facing_runs({'fps':fps},ahead,{'房 · 到达':0,'走':6})
  self.assertEqual(len(runs),1);self.assertAlmostEqual(runs[0]['startSeconds'],1.0);self.assertAlmostEqual(runs[0]['seconds'],.8);self.assertEqual(runs[0]['after'],'走')
  self.assertEqual(wall_facing_runs({'fps':fps},[3000]*5+[300]*2+[3000]*5,{}),[])
  self.assertEqual(time_breakdown(tour,marks)['inPlaceSeconds'],(len(frames)-1)/fps)

class BriefFromRoute(Base):
 def furnished(self,*extra):
  b=bundle_value();b['state']['furniture']+= [dict({'id':'t1','type':'table','cx':2500,'cy':1000,'w':1200,'d':800,'h':750,'rot':0,'elevation':0}),dict({'id':'bed1','type':'bed','cx':6000,'cy':2500,'w':1500,'d':2000,'h':600,'rot':0,'elevation':0})]+list(extra)
  (self.p/'bundle.json').write_text(json.dumps(b));return b
 def plan(self,stations):
  self.furnished()
  plan={'schema':'homeowner-spatial-plan/1','status':'pending_user_confirmation','bundle':bound(self.p/'bundle.json'),'budget':{'maximumSeconds':60},'navigation':{'bodyRadiusMm':180},
        'entrance':{'openingId':'IN','startPointMm':[1450,-600]},'cameraEnvelope':{'stationToleranceMm':2800},'stations':stations}
  path=self.p/'plan.json';path.write_text(json.dumps(plan));return path
 def build(self,stations,**options):
  from brief_from_route import build
  return build(self.plan(stations),{'maximumSeconds':60,'coverageMinimumPercent':80,**options})
 def test_a_brief_follows_the_route_and_lists_what_it_assumed(self):
  brief,notes=self.build([{'name':'厅','roomId':'hall','pointMm':[1500,1000]},{'name':'东室','roomId':'east','pointMm':[6000,1500]}])
  self.assertEqual([r['name'] for r in brief['rooms']],['厅','东室']);self.assertEqual(brief['fixedOrder'],['s00','s01'])
  self.assertEqual(chain.check_brief_alignment(brief,json.loads((self.p/'plan.json').read_text())),[])
  self.assertEqual(notes['stations'][1]['subject'],'bed1');self.assertTrue(notes['defaults']);self.assertEqual(brief['coveragePolicy'],{'enabled':True,'minimumPercent':80})
  self.assertEqual(brief['navigationPolicy']['mode'],'forward');self.assertEqual(brief['panPolicy'],'flow')
 def test_a_station_with_nothing_to_show_is_reported_as_pass_through(self):
  brief,notes=self.build([{'name':'厅','roomId':'hall','pointMm':[1500,1000]},{'name':'东室','roomId':'east','pointMm':[6000,1500]}])
  b=bundle_value();b['state']['furniture']=[];(self.p/'bundle.json').write_text(json.dumps(b))
  from brief_from_route import build
  plan=json.loads((self.p/'plan.json').read_text());plan['bundle']=bound(self.p/'bundle.json');(self.p/'plan.json').write_text(json.dumps(plan))
  with self.assertRaisesRegex(ValueError,'nothing to show|No station'):build(self.p/'plan.json',{'maximumSeconds':60,'coverageOff':True})
 def test_case_numbers_are_never_invented(self):
  stations=[{'name':'厅','roomId':'hall','pointMm':[1500,1000]}]
  from brief_from_route import build
  self.plan(stations)
  plan=json.loads((self.p/'plan.json').read_text());plan['budget']={};(self.p/'plan.json').write_text(json.dumps(plan))
  with self.assertRaisesRegex(ValueError,'maximumSeconds'):build(self.p/'plan.json',{'coverageMinimumPercent':80})
  with self.assertRaisesRegex(ValueError,'coverageMinimumPercent'):build(self.p/'plan.json',{'maximumSeconds':60})
  with self.assertRaisesRegex(ValueError,'reason'):build(self.p/'plan.json',{'maximumSeconds':60,'coverageOff':True,'eyeMm':1300})
  brief,_=build(self.p/'plan.json',{'maximumSeconds':60,'coverageOff':True,'eyeMm':1300,'eyeReason':'用户要求降低视高'})
  self.assertEqual(brief['ruleExceptions'][0]['code'],'camera_profile_override');self.assertEqual(brief['coveragePolicy'],{'enabled':False})
 def test_more_than_two_stations_in_one_room_are_filed_under_the_neighbouring_room(self):
  stations=[{'name':'东室甲','roomId':'east','pointMm':[6000,1500]},{'name':'餐桌区','roomId':'hall','pointMm':[2500,2000],'anchor':'t1'},{'name':'沙发区','roomId':'hall','pointMm':[1500,3000],'anchor':'sofa'},{'name':'厅中','roomId':'hall','pointMm':[1000,1000]}]
  brief,notes=self.build(stations);rooms={r['name']:r for r in brief['rooms']}
  self.assertEqual(notes['reassigned'][0]['station'],'餐桌区');self.assertEqual(rooms['餐桌区']['roomId'],'east');self.assertEqual(rooms['餐桌区']['observationRegionId'],'hall')
  from collections import Counter
  self.assertTrue(all(n<=2 for n in Counter(r['roomId'] for r in brief['rooms']).values()))
 def test_unknown_override_and_second_point_reason(self):
  with self.assertRaisesRegex(ValueError,'unknown station'):self.build([{'name':'厅','roomId':'hall','pointMm':[1500,1000]}],overrides={'不存在':{'viewSeconds':2}})
  brief,_=self.build([{'name':'厅','roomId':'hall','pointMm':[1500,1000]},{'name':'东室','roomId':'east','pointMm':[6000,1500]}],overrides={'东室':{'viewSeconds':2}})
  self.assertEqual(brief['rooms'][1]['viewSeconds'],2)

class StageApprovals(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=Path(self.tmp.name)
 def camera_files(self,status='pending_user_review'):
  p=self.p;(p/'animation.html').write_text('<p>shown</p>');(p/'rehearsal.json').write_text(json.dumps({'status':status,'references':{'animation':bound(p/'animation.html')}}))
  (p/'pending.json').write_text(json.dumps({'schema':'homeowner-route-approval/1','status':'pending','approvalSource':'explicit_user_confirmation','confirmedBy':'','evidence':'','presentedAnimationSha256':None,'rehearsal':bound(p/'rehearsal.json'),'checks':{'animationViewed':False,'pathAndFacingApproved':False,'durationAndRhythmApproved':False}}))
 def test_camera_approval_only_for_a_finished_rehearsal_and_only_from_the_user(self):
  from record_approval import record_camera
  self.camera_files('needs_revision')
  with self.assertRaisesRegex(ValueError,'still needs revision'):record_camera(self.p/'pending.json',self.p/'a.json','王女士','确认')
  self.camera_files()
  for who in ('Claude','synthetic user',''):
   with self.subTest(who=who),self.assertRaises(ValueError):record_camera(self.p/'pending.json',self.p/'b.json',who,'确认')
  record=record_camera(self.p/'pending.json',self.p/'ok.json','王女士','镜头看过了，可以');self.assertEqual(record['presentedAnimationSha256'],bound(self.p/'animation.html')['sha256']);self.assertTrue(all(record['checks'].values()))
  with self.assertRaisesRegex(ValueError,'preserved'):record_camera(self.p/'pending.json',self.p/'ok.json','王女士','再来')
 def test_video_approval_uses_the_narration_gate_and_refuses_samples(self):
  from record_approval import record_video
  from tour_stage_gate import pending,require_video
  p=self.p;(p/'v.mp4').write_bytes(b'video');(p/'t.json').write_text('{}')
  (p/'p.json').write_text(json.dumps(pending(p/'v.mp4',p/'t.json')))
  with self.assertRaises(ValueError):record_video(p/'p.json',p/'x.json','Claude','确认')
  record=record_video(p/'p.json',p/'ok.json','王女士','整片看过，同意');self.assertEqual(record['status'],'approved');require_video(p/'ok.json',p/'v.mp4',p/'t.json')
  (p/'v.mp4').write_bytes(b'other')
  with self.assertRaises(ValueError):require_video(p/'ok.json',p/'v.mp4',p/'t.json')
  sample=pending(p/'v.mp4',p/'t.json');sample['purpose']='sample';(p/'s.json').write_text(json.dumps(sample))
  with self.assertRaises(ValueError):record_video(p/'s.json',p/'y.json','王女士','确认')

class CorpusRegression(unittest.TestCase):
 def test_each_regression_is_named_and_improvement_is_not_flagged(self):
  from validate_case import compare
  base={'stationNames':['a','b'],'routeDistanceM':30,'maxTransitTurnDegrees':100,'protectedIssues':[]}
  good={'failure':None,'stages':{},'metrics':{'stationNames':['a','b'],'routeDistanceM':29,'maxTransitTurnDegrees':60,'protectedIssues':[]}}
  self.assertEqual(compare(good,base),[])
  for change,code in ({'maxTransitTurnDegrees':140},'turning_worse'),({'protectedIssues':['excessive_transit_turn']},'new_protected_issue'),({'stationNames':['b','a']},'route_stations_changed'),({'routeDistanceM':40},'route_longer'):
   self.assertEqual([x['code'] for x in compare({**good,'metrics':{**good['metrics'],**change}},base)],[code])
  self.assertEqual(compare({'failure':'draft','stages':{'draft':{'error':'x'}},'metrics':{}},base)[0]['code'],'stage_failed')
 def test_cases_without_usable_inputs_are_skipped_not_failed_or_run_on_the_wrong_bundle(self):
  import tempfile as tf
  from validate_case import unusable
  with tf.TemporaryDirectory() as d:
   p=Path(d);(p/'b.json').write_text(json.dumps({'schemeSha256':'aaa'}));(p/'c.json').write_text('{}')
   ok={'bundle':str(p/'b.json'),'caseFile':str(p/'c.json')}
   self.assertIsNone(unusable(ok))
   self.assertIsNone(unusable({'bundle':str(p/'b.json'),'entranceOpeningId':'W09:0','schemeSha256':'aaa'}))
   self.assertIn('inputs missing',unusable({**ok,'runtime':str(p/'nope')}))
   self.assertIn('inputs missing',unusable({**ok,'bundle':str(p/'gone.json')}))
   self.assertIn('scheme differs',unusable({**ok,'schemeSha256':'bbb'}))
   self.assertIn('needs caseFile or entranceOpeningId',unusable({'bundle':str(p/'b.json')}))
 def test_the_real_chain_runs_on_a_synthetic_case_without_any_approval(self):
  import tempfile as tf
  from validate_case import validate
  with tf.TemporaryDirectory() as d:
   p=Path(d);b=bundle_value();b['state']['furniture']=[{'id':'sofa','type':'sofa','cx':1500,'cy':3200,'w':1800,'d':800,'h':800,'rot':0}];(p/'bundle.json').write_text(json.dumps(b));(p/'case.json').write_text(json.dumps({'entranceOpenings':['IN']}))
   card=validate({'id':'synthetic','bundle':str(p/'bundle.json'),'caseFile':str(p/'case.json'),'maximumSeconds':60,'coverageOff':True},p/'out')
   self.assertEqual(card['stages']['route']['status'],'ok');self.assertFalse(card['approvalGranted']);self.assertFalse(card['videoGenerated'])
   self.assertIn(card['failure'],(None,'brief','draft'));self.assertFalse(list((p/'out').rglob('*.mp4')))
if __name__=='__main__':unittest.main()
