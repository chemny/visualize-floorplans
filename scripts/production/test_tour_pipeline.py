import copy,json,math,tempfile,unittest
from pathlib import Path
from PIL import Image
from tour_pipeline import rank,finalize_gaze,affected_chapters,run,JointPlanner,apply_timing_locks,revision_scope,scope_check
from tour_contract import inspect
from tour_workflow import markers

class PipelineTests(unittest.TestCase):
 def test_scoped_revision_freezes_observations_and_rejects_any_undeclared_axis(self):
  b,t,c=self.fixture();name=c['chapters'][0]['name'];scope=revision_scope(t,c,{'chapters':[name],'axes':['yawRadians']})
  m=markers(t);i=m[c['chapters'][0]['from']]+1
  candidate=copy.deepcopy(t);candidate['frames'][i]['yawRadians']+=.001
  self.assertEqual(scope_check(t,candidate,c,scope)['status'],'pass')
  candidate['frames'][-1]['eyeMm']+=1
  self.assertEqual(scope_check(t,candidate,c,scope)['issues'][0]['code'],'revision_scope_changed')
  altered=copy.deepcopy(c);altered['maximumSeconds']+=1
  self.assertEqual(scope_check(t,t,altered,scope)['status'],'failed')
  for value in [{'chapters':[c['chapters'][1]['name']]},{'chapters':[name,name]},{'chapters':['unknown']},{'chapters':[name],'axes':['eyeMm']},{'chapters':[name],'preserveViewingWindows':False}]:
   with self.assertRaises(ValueError):revision_scope(t,c,value)
 def test_doorway_soft_score_cannot_pay_for_hard_failures(self):
  good={'issues':[],'checks':{'doorwayComposition':{'score':50}}}
  bad={'issues':[{'code':'motion_limit'}],'checks':{'doorwayComposition':{'score':0}}}
  self.assertLess(rank(good,{'seconds':75}),rank(bad,{'seconds':10}))
  bad['issues']=[{'code':'revision_scope_changed'}]
  self.assertLess(rank(good,{'seconds':75}),rank(bad,{'seconds':10}))
 def test_invalid_final_target_binding_fails_engineering_stage_even_if_raw_mesh_passes(self):
  from unittest.mock import patch
  from types import SimpleNamespace
  from tour_workflow import sha
  b,t,c=self.fixture();valid={'status':'numeric_pass_visual_pending','issues':[],'checks':{k:{'issues':[]} for k in ['coreTargets','choreography','cameraEvidence','trajectory','forwardMotion']}}
  valid['checks']['geometry']={'collisionFrames':[]}
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);runtime=p/'runtime';runtime.mkdir()
   for name in ('geometry.bin','renderer.html','three.module.js','three.core.js','THREE-LICENSE.txt'):(runtime/name).write_text('synthetic fixture for target binding boundary')
   (runtime/'scene.json').write_text(json.dumps({'schemeSha256':b['schemeSha256'],'renderSettings':{'size':[1280,720]}}));Image.new('RGB',(100,100),'white').save(p/'plan.png')
   for name,value in [('bundle.json',b),('tour.json',t),('config.json',c)]:(p/name).write_text(json.dumps(value))
   def mesh(command,**kwargs):
    file=Path(command[command.index('--out')+1]);file.write_text(json.dumps({'status':'pass','tourSha256':sha(command[command.index('--tour')+1]),'chapters':[],'coreTargets':{'status':'pass','issues':[]},'screenQuality':{'status':'pass','issues':[]}}));return SimpleNamespace(returncode=0,stdout='',stderr='')
   job={'schema':'homeowner-production-job/1','bundle':str(p/'bundle.json'),'seedTour':str(p/'tour.json'),'seedConfig':str(p/'config.json'),'runtime':str(runtime),'plan':str(p/'plan.png'),'planBounds':[0,0,5000,5000],'searchOnly':True,'revisionScope':{'chapters':[c['chapters'][0]['name']]},'search':{'maximumRounds':1,'maximumDoorwayCandidates':0}}
   with patch('tour_pipeline.contract',return_value=valid),patch('tour_pipeline.subprocess.run',side_effect=mesh),patch('tour_pipeline.shutil.which',return_value='node'),patch('tour_camera_evidence.require_actual_targets',side_effect=ValueError('wrong target order')):
    result=run(job,p/'out')
   self.assertEqual(result['engineeringStatus'],'failed')
   report=json.loads((p/'out/contract-report.json').read_text());self.assertIn('actual_mesh_target_binding_invalid',{x['code'] for x in report['issues']})
 def test_native_scoped_repair_runs_on_soft_defect_without_global_smoothing(self):
  from unittest.mock import patch
  b,t,c=self.fixture();name=c['chapters'][0]['name'];m=markers(t);inside=m[c['chapters'][0]['from']]+1
  scoped=revision_scope(t,c,{'chapters':[name],'axes':['yawRadians']})
  candidate=copy.deepcopy(t);candidate['frames'][inside]['yawRadians']+=.00001
  illegal=copy.deepcopy(candidate);illegal['frames'][-1]['eyeMm']+=1
  def doorway(bundle,tour,config):
   return {'status':'reference_only','score':10 if tour['frames'][inside]['yawRadians']==t['frames'][inside]['yawRadians'] else 0,'chapters':[]}
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);runtime=p/'runtime';runtime.mkdir()
   for file in ('geometry.bin','three.module.js','three.core.js','THREE-LICENSE.txt'):(runtime/file).write_text('synthetic fixture')
   (runtime/'renderer.html').write_text((Path(__file__).resolve().parents[2]/'assets/h5/runtime/renderer.html').read_text())
   (runtime/'scene.json').write_text(json.dumps({'schemeSha256':b['schemeSha256'],'renderSettings':{'size':[1280,720]}}));Image.new('RGB',(100,100),'white').save(p/'plan.png')
   for file,value in [('bundle.json',b),('tour.json',t),('config.json',c)]:(p/file).write_text(json.dumps(value))
   job={'schema':'homeowner-production-job/1','bundle':str(p/'bundle.json'),'seedTour':str(p/'tour.json'),'seedConfig':str(p/'config.json'),'runtime':str(runtime),'plan':str(p/'plan.png'),'planBounds':[0,0,5000,5000],'meshPreflight':False,'searchOnly':True,'revisionScope':{'chapters':[name],'axes':['yawRadians']},'search':{'maximumRounds':1,'maximumFullEvaluations':2,'maximumDoorwayCandidates':2}}
   proposals=[{'tour':illegal,'config':c,'evidence':{}},{'tour':candidate,'config':c,'evidence':{}}]
   with patch('tour_doorway.doorway_report',side_effect=doorway),patch('tour_doorway.repair_candidates',return_value=proposals) as native,patch('tour_pipeline.finalize_gaze',side_effect=AssertionError('Scoped repair must not globally smooth')):
    result=run(job,p/'out')
   native.assert_called_once();self.assertEqual(native.call_args.kwargs['maximum_candidates'],2)
   attempts=json.loads((p/'out/search-report.json').read_text())['attempts']
   self.assertTrue(any('revision_scope_changed' in {x['code'] for x in a.get('issues',[])} for a in attempts))
   final=json.loads((p/'out/tour.json').read_text());self.assertEqual(final['frames'][-1],t['frames'][-1])
   self.assertEqual(final['frames'][inside],candidate['frames'][inside])
   self.assertEqual(json.loads((p/'out/closeout-report.json').read_text())['revisionOutcome']['status'],'selected_revision')
   self.assertFalse((p/'out/index.html').exists());self.assertTrue((p/'out/closeout-report.json').exists());self.assertFalse(result['videoGenerated'])
   with patch('tour_doorway.doorway_report',side_effect=doorway),patch('tour_doorway.repair_candidates',return_value=[proposals[0]]):
    run(job,p/'retained')
   retained=json.loads((p/'retained/closeout-report.json').read_text())['revisionOutcome']
   self.assertEqual(retained,{'status':'baseline_retained','selectedOrigin':'frozen_seed','changedFrames':0,'automaticVisualAcceptance':False})
   self.assertEqual(json.loads((p/'retained/tour.json').read_text()),json.loads(json.dumps(t)))
   with patch('tour_doorway.doorway_report',side_effect=doorway),patch('tour_doorway.repair_candidates',side_effect=TimeoutError('deadline exhausted')):
    exhausted=run(job,p/'exhausted')
   closed=json.loads((p/'exhausted/closeout-report.json').read_text())
   self.assertNotEqual(closed['engineeringStatus'],'pass');self.assertIn('native_repair_budget_exhausted',{x['code'] for x in exhausted['remainingIssues']})
 def test_closing_view_optional_offset_keeps_exact_confirmed_exit(self):
  p=JointPlanner.__new__(JointPlanner)
  p.b={'state':{'walls':[{'a':[0,0],'b':[0,4000],'opens':[{'id':'entry','at':1000,'width':1000}]}]}}
  p.t={'frames':[{'pointMm':[-400,1500],'yawRadians':0,'pitchRadians':0,'eyeMm':1600}]}
  p.c={'tourContract':{'tourMode':'full_tour','entranceOpeningId':'entry'}}
  default=p.closing_pose();self.assertAlmostEqual(default['yawRadians'],math.pi)
  p.c['exitView']={'yawOffsetDegrees':-27};shifted=p.closing_pose()
  self.assertEqual(shifted['pointMm'],[-400,1500]);self.assertEqual(shifted['eyeMm'],1600)
  self.assertEqual(shifted['closingTargetOpeningId'],'entry')
  self.assertAlmostEqual(shifted['yawRadians'],math.pi-math.radians(27))
  self.assertEqual(p.t['frames'][0]['yawRadians'],0)
  for bad in [True,float('nan'),float('inf'),61,-61,'27']:
   p.c['exitView']={'yawOffsetDegrees':bad}
   with self.assertRaisesRegex(ValueError,'forward 60-degree'):p.closing_pose()
 def test_chapter_navigation_policy_is_not_skipped_when_endpoints_are_unchanged(self):
  from unittest.mock import patch
  from design_homeowner_tour import navigation_gaze
  b,t,c=self.fixture();c['chapters'][0]['navigationPolicy']={'forwardWeight':1.234}
  p=JointPlanner(b,t,c,{});choices={ch['name']:p.baseline(ch) for _,ch in p.obs}
  with patch('tour_pipeline.navigation_gaze',wraps=navigation_gaze) as spy:
   p.rebuild(choices,{'closingView':'seed'})
  self.assertTrue(any(call.args[-1].get('forwardWeight')==1.234 for call in spy.call_args_list))
 def test_exact_total_lock_adds_only_connection_slack_and_preserves_each_view(self):
  b,t,c=self.fixture();m=markers(t);c['timingLocks']={'totalFrames':len(t['frames'])+24,'fps':t['fps'],'viewingFrames':{ch['name']:m[ch['to']]-m[ch['from']] for ch in c['chapters'] if ch['phase']=='observe'}}
  result=apply_timing_locks(t,c);n=markers(result)
  self.assertEqual(len(result['frames']),len(t['frames'])+24)
  for ch in c['chapters']:
   if ch['phase']=='observe':self.assertEqual([f['pointMm'] for f in result['frames'][n[ch['from']]:n[ch['to']]+1]],[f['pointMm'] for f in t['frames'][m[ch['from']]:m[ch['to']]+1]])
 def test_timing_lock_rejects_connections_that_cannot_fit_without_acceleration(self):
  b,t,c=self.fixture();m=markers(t);c['timingLocks']={'totalFrames':1+sum(m[ch['to']]-m[ch['from']] for ch in c['chapters'] if ch['phase']=='observe')}
  with self.assertRaisesRegex(ValueError,'cannot fit'):apply_timing_locks(t,c)
 def fixture(self):
  from test_tour_contract import ContractTests
  x=ContractTests();x.setUp();return x.b,x.t,x.c
 def test_collision_is_not_traded_for_shorter_duration_or_fewer_other_errors(self):
  bad={'issues':[{'code':'body_path_collision'}]};safe={'issues':[{'code':'room_visit_over_budget','seconds':5,'maximumSeconds':3}]*5}
  self.assertGreater(rank(bad,{'seconds':10}),rank(safe,{'seconds':50}))
 def test_final_regularization_preserves_timing_positions_and_scan_direction(self):
  b,t,c=self.fixture();original=copy.deepcopy(t);new=finalize_gaze(t,c,.2);m=markers(new)
  self.assertEqual(t,original);self.assertEqual(len(new['frames']),len(t['frames']));self.assertEqual(new['seconds'],t['seconds'])
  self.assertEqual([f['pointMm'] for f in new['frames']],[f['pointMm'] for f in t['frames']])
  for ch in c['chapters']:
   if ch['phase']=='observe':
    a,z=m[ch['from']],m[ch['to']];sign=1 if ch['singleSweepDegrees']>0 else -1
    self.assertTrue(all((g['yawRadians']-f['yawRadians'])*sign>=-1e-6 for f,g in zip(new['frames'][a:z],new['frames'][a+1:z+1])))
 def test_injected_transit_angular_spike_is_repaired_and_not_only_reported(self):
  from tour_workflow import metrics
  b,t,c=self.fixture();t=copy.deepcopy(t);t['frames'][20]['yawRadians']+=.15
  self.assertGreater(metrics(t)['maxYawDegreesPerSecond'],32)
  new=finalize_gaze(t,c,.2);m=metrics(new)
  self.assertLessEqual(m['maxYawDegreesPerSecond'],32.01);self.assertLessEqual(m['maxYawAccelerationDegreesPerSecondSquared'],240.1)
 def test_final_selection_does_not_exchange_room_coverage_for_seconds(self):
  short={'issues':[{'code':'room_coverage_below_case_minimum'}]}
  complete={'issues':[{'code':'room_visit_over_budget','seconds':4,'maximumSeconds':3}]}
  self.assertGreater(rank(short,{'seconds':55}),rank(complete,{'seconds':59}))
 def test_budget_failure_targets_that_room_and_neighbouring_connections(self):
  b,t,c=self.fixture();c['roomBudgetPolicy']={'maximumTotalSeconds':120,'rooms':[{'name':'Room','roomIds':['room'],'maximumSeconds':.1}]};r=inspect(b,t,c)
  self.assertIn(c['chapters'][1]['name'],affected_chapters(t,c,r))
 def test_unified_job_writes_bound_pending_rehearsal_without_video_or_source_mutation(self):
  b,t,c=self.fixture()
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);runtime=p/'runtime';runtime.mkdir()
   for name in ('geometry.bin','three.module.js','three.core.js','THREE-LICENSE.txt'):(runtime/name).write_text('synthetic test asset')
   # The adapter must see a real supported frame API, not arbitrary HTML.
   (runtime/'renderer.html').write_text((Path(__file__).resolve().parents[2]/'assets/h5/runtime/renderer.html').read_text())
   (runtime/'scene.json').write_text(json.dumps({'schemeSha256':b['schemeSha256'],'renderSettings':{'size':[1280,720]}}));Image.new('RGB',(100,100),'white').save(p/'plan.png')
   for name,v in [('bundle.json',b),('tour.json',t),('config.json',c)]:(p/name).write_text(json.dumps(v))
   before=(p/'tour.json').read_bytes();job={'schema':'homeowner-production-job/1','meshPreflight':False,'bundle':str(p/'bundle.json'),'seedTour':str(p/'tour.json'),'seedConfig':str(p/'config.json'),'runtime':str(runtime),'plan':str(p/'plan.png'),'planBounds':[0,0,5000,5000],'search':{'beamWidth':1,'perRoomCandidates':2,'maximumRounds':1}}
   result=run(job,p/'out');self.assertFalse(result['videoGenerated']);self.assertEqual((p/'tour.json').read_bytes(),before)
   self.assertFalse(list((p/'out').rglob('*.mp4')));self.assertEqual(json.loads((p/'out/rehearsal/route-review.pending.json').read_text())['status'],'pending')
   manifest=json.loads((p/'out/rehearsal/rehearsal.json').read_text());self.assertEqual(Path(manifest['references']['animation']['path']),(p/'out/index.html').resolve())
   self.assertEqual(json.loads((p/'out/workflow-state.json').read_text())['video'],'not_requested')
   from tour_pages import sha as page_sha
   self.assertEqual(json.loads((p/'out/tour-pages.json').read_text())['inputs']['rehearsal']['sha256'],page_sha(p/'out/rehearsal/rehearsal.json'))
   self.assertTrue((p/'out/video.html').is_file());self.assertTrue((p/'out/narrated.html').is_file());self.assertTrue((p/'out/camera-preview.html').is_file());self.assertNotIn('<iframe',(p/'out/index.html').read_text());self.assertNotIn('<video',(p/'out/index.html').read_text());self.assertEqual(json.loads((p/'out/tour-pages.json').read_text())['stages']['video'],'not_generated')
   self.assertIn('replayRenderer',manifest['references']);self.assertIn('rehearsalPlayback',((p/'out/index.html').resolve()).read_text());self.assertNotIn('p.eval(', ((p/'out/index.html').resolve()).read_text())
   with self.assertRaisesRegex(ValueError,'Fresh'):run(job,p/'out')
 def test_invalid_search_is_rejected_without_creating_output(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);(p/'bundle.json').write_text('{}')
   with self.assertRaisesRegex(ValueError,'Bounded'):run({'schema':'homeowner-production-job/1','bundle':str(p/'bundle.json'),'search':{'beamWidth':100000}},p/'out')
   self.assertFalse((p/'out').exists())
 def test_real_screen_failures_participate_in_candidate_ranking(self):
  clean={'issues':[]};blocked={'issues':[{'code':'screen_near_surface_occlusion'}]};repeat={'issues':[{'code':'approach_view_reverses_into_observation'}]}
  self.assertLess(rank(clean,{'seconds':59}),rank(blocked,{'seconds':50}));self.assertLess(rank(clean,{'seconds':59}),rank(repeat,{'seconds':50}))
 def test_explicit_adjacent_region_is_respected_during_joint_selection(self):
  b,t,c=self.fixture();b['model']['rooms'].append({'id':'adjacent','poly':[[0,0],[1500,0],[1500,4000],[0,4000]]})
  ch=next(x for x in c['chapters'] if x['phase']=='observe');ch.update(roomId='adjacent',observationRegionId='room',adjacentViewReason='Synthetic visible adjacent space')
  p=JointPlanner(b,t,c,{});self.assertIsNotNone(p.local_cost(ch,p.baseline(ch)))
 def test_pipeline_consumes_actual_mesh_candidate_failure_not_only_final_report(self):
  from unittest.mock import patch
  from types import SimpleNamespace
  from tour_workflow import sha
  b,t,c=self.fixture();c['maximumSeconds']=1
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);runtime=p/'runtime';runtime.mkdir()
   for name in ('geometry.bin','renderer.html','three.module.js','three.core.js','THREE-LICENSE.txt'):(runtime/name).write_text('synthetic asset for mocked mesh boundary')
   (runtime/'scene.json').write_text(json.dumps({'schemeSha256':b['schemeSha256'],'renderSettings':{'size':[1280,720]}}));Image.new('RGB',(100,100),'white').save(p/'plan.png')
   for name,value in [('bundle.json',b),('tour.json',t),('config.json',c)]:(p/name).write_text(json.dumps(value))
   calls=[]
   def mesh(command,**kwargs):
    calls.append(command);q=Path(command[command.index('--out')+1]);tt=Path(command[command.index('--tour')+1]);cfg=Path(command[command.index('--config')+1])
    q.write_text(json.dumps({'status':'fail','tourSha256':sha(tt),'schemeSha256':b['schemeSha256'],'chapters':[],'screenQuality':{'status':'needs_revision','issues':[{'code':'screen_near_surface_occlusion','startSeconds':1,'endSeconds':2}]}}));return SimpleNamespace(returncode=0,stdout='synthetic mesh boundary',stderr='')
   job={'schema':'homeowner-production-job/1','bundle':str(p/'bundle.json'),'seedTour':str(p/'tour.json'),'seedConfig':str(p/'config.json'),'runtime':str(runtime),'plan':str(p/'plan.png'),'planBounds':[0,0,5000,5000],'maximumMeshRepairPasses':0,'searchOnly':True,'search':{'beamWidth':1,'perRoomCandidates':2,'maximumRounds':1,'maximumFullEvaluations':2,'maximumCandidateMeshEvaluations':2}}
   with patch('tour_pipeline.subprocess.run',side_effect=mesh),patch('tour_pipeline.shutil.which',return_value='node'):result=run(job,p/'out')
   report=json.loads((p/'out/search-report.json').read_text());self.assertIn('screen_near_surface_occlusion',{i['code'] for i in report['attempts'][0]['issues']});self.assertTrue(any('candidate-mesh' in ' '.join(cmd) for cmd in calls));self.assertFalse(result['videoGenerated']);self.assertEqual(result['status'],'diagnostic_search_only')
   self.assertFalse((p/'out/index.html').exists());self.assertFalse((p/'out/rehearsal').exists())
   for attempt in report['attempts'][:2]:
    self.assertIn('total_over_budget',{x['code'] for x in attempt['issues']})
    self.assertEqual(attempt['checks']['screenEvidence']['status'],'checked')
if __name__=='__main__':unittest.main()
