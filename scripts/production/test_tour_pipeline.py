import copy,json,math,tempfile,unittest
from pathlib import Path
from PIL import Image
from tour_pipeline import rank,finalize_gaze,affected_chapters,run,JointPlanner,apply_timing_locks,revision_scope,scope_check
from tour_contract import inspect
from tour_workflow import markers
from unittest.mock import patch

# Camera-search behaviour only. The real refusal without a route approval is
# tested in test_tour_spatial_plan.EntryGates against this same run().
_entry=patch('tour_stage_chain.require_camera_entry',return_value=None)
def setUpModule():_entry.start()
def tearDownModule():_entry.stop()

class PipelineTests(unittest.TestCase):
 def test_local_target_screen_uses_configured_fov_with_same_edge_reserve(self):
  b,t,c=self.fixture();ch=next(x for x in c['chapters'] if x['phase']=='observe')
  for f in b['state']['furniture']:f['type']='cabinet'
  point=[2800,2000];b['state']['furniture'].append({'id':'angle','type':'cabinet','cx':point[0]+1000*math.cos(math.radians(38)),'cy':point[1]+1000*math.sin(math.radians(38)),'w':10,'d':10,'h':1000,'rot':0})
  ch['subjects']=['angle'];ch['orderedViewTargets']=[]
  item={'point':point,'endPoint':point,'yaw':0,'pan':0,'pitch':0,'source':'test'}
  narrow=JointPlanner(b,t,c,{})
  self.assertIsNone(narrow.local_cost(ch,item))
  c['cameraProfile']['horizontalFovDegrees']=84
  wide=JointPlanner(b,t,c,{})
  self.assertIsNotNone(wide.local_cost(ch,item))
 def test_new_planning_uses_requested_time_not_unconfirmed_seed_inflation(self):
  b,t,c=self.fixture();ch=next(x for x in c['chapters'] if x['phase']=='observe');m=markers(t)
  original=m[ch['to']]-m[ch['from']];ch['minimumSeconds']=original/t['fps']/2
  revision=JointPlanner(b,t,c,{})
  fresh=JointPlanner(b,t,c,{'_planningMode':'new'})
  self.assertEqual(revision.observation_frames(ch),original)
  self.assertEqual(fresh.observation_frames(ch),math.ceil(ch['minimumSeconds']*t['fps']))
  self.assertEqual(revision.c['viewingDurationFloors'][ch['name']],original/t['fps'])
  self.assertEqual(fresh.c['viewingDurationFloors'][ch['name']],ch['minimumSeconds'])
  choices={q['name']:fresh.baseline(q) for _,q in fresh.obs}
  rebuilt,rc=fresh.rebuild(choices,{'closingView':'seed'});rm=markers(rebuilt)
  self.assertEqual(rm[ch['to']]-rm[ch['from']],fresh.observation_frames(ch))
  self.assertEqual(rebuilt['frames'][0]['pointMm'],t['frames'][0]['pointMm'])
  self.assertEqual(rebuilt['frames'][-1]['pointMm'],t['frames'][-1]['pointMm'])
  self.assertEqual(t['seconds'],len(t['frames'])/t['fps'])
 def test_new_planning_preserves_explicit_floors_locks_and_moving_views(self):
  b,t,c=self.fixture();ch=next(x for x in c['chapters'] if x['phase']=='observe');m=markers(t);original=m[ch['to']]-m[ch['from']]
  ch['minimumSeconds']=.5;c['viewingDurationFloors']={ch['name']:1.25}
  p=JointPlanner(b,t,c,{'_planningMode':'new'});self.assertEqual(p.observation_frames(ch),math.ceil(1.25*t['fps']))
  c['timingLocks']={'viewingFrames':{ch['name']:original}}
  self.assertEqual(JointPlanner(b,t,c,{'_planningMode':'new'}).observation_frames(ch),original)
  c.pop('timingLocks');ch['movingView']=True
  self.assertEqual(JointPlanner(b,t,c,{'_planningMode':'new'}).observation_frames(ch),original)
 def test_planning_mode_rejects_unknown_or_frozen_new_request(self):
  from unittest.mock import patch
  b,t,c=self.fixture()
  for mode,scope,reason in [('invalid',None,'planningMode'),('new',{'chapters':['x']},'frozen revision scope')]:
   with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp);job={'schema':'homeowner-production-job/1','bundle':'bundle','seedTour':'tour','seedConfig':'config','planningMode':mode,'revisionScope':scope}
    with patch('tour_pipeline.read',side_effect=[b,t,c]),self.assertRaisesRegex(ValueError,reason):run(job,p/'out')
    self.assertFalse((p/'out').exists())
 def test_new_moving_view_prices_actual_turn_before_selection_and_rebuild(self):
  b,t,c=self.fixture();ch=next(x for x in c['chapters'] if x['phase']=='observe');ch['movingView']=True
  p=JointPlanner(b,t,c,{'_planningMode':'new'});choice=p.baseline(ch)
  choice.update(pan=math.radians(120),endPoint=[choice['point'][0],choice['point'][1]+200],source='case_station_proposal')
  choice['viewPath']=[choice['point'][:],choice['endPoint'][:]]
  expected=max(p.m[ch['to']]-p.m[ch['from']],math.ceil(120/(p.limits['maxYawDegreesPerSecond']*.98)*p.fps))
  self.assertEqual(p.observation_frames(ch,choice),expected)
  choices={q['name']:p.baseline(q) for _,q in p.obs};choices[ch['name']]=choice
  rebuilt,rc=p.rebuild(choices,{'closingView':'seed'});m=markers(rebuilt)
  self.assertEqual(m[ch['to']]-m[ch['from']],expected)
  self.assertLessEqual(abs(120/((m[ch['to']]-m[ch['from']])/p.fps)),p.limits['maxYawDegreesPerSecond'])
  c['timingLocks']={'viewingFrames':{ch['name']:24}}
  locked=JointPlanner(b,t,c,{'_planningMode':'new'});self.assertEqual(locked.observation_frames(ch,choice),24)
  self.assertIsNone(locked.local_cost(ch,choice))
  old=JointPlanner(b,t,c,{})
  self.assertEqual(old.observation_frames(ch,choice),old.m[ch['to']]-old.m[ch['from']])
 def curved_motion_fixture(self,moving_view=False):
  """A real blocker makes the curved source arc essential to body clearance."""
  poly=[[0,0],[6000,0],[6000,6000],[0,6000]]
  b={'schemeSha256':'synthetic-curved-motion','model':{'footprint':poly,'rooms':[{'id':'room','poly':poly}]},
     'state':{'walls':[],'furniture':[{'id':'blocker','type':'synthetic-blocker','cx':3000,'cy':3000,'w':800,'d':800,'rot':0}]}}
  arc=[[3000+1300*math.cos(math.pi-j*math.pi/96),3000+1300*math.sin(math.pi-j*math.pi/96)] for j in range(97)]
  fs=[]
  for i in range(145):
   if i<=24:point=arc[0];yaw=.1*i/24
   elif i<=120:point=arc[i-24];yaw=.1+.9*(i-24)/96
   else:point=arc[-1];yaw=1+.1*(i-120)/24
   fs.append({'frame':i,'pointMm':point[:],'yawRadians':yaw,'pitchRadians':-.1,'eyeMm':1600,'horizontalFovDegrees':76,'shiftY':0})
  t={'schemeSha256':b['schemeSha256'],'fps':24,'seconds':len(fs)/24,'frames':fs,'visits':[{'name':name,'frame':i} for name,i in zip('abcd',[0,24,120,144])]}
  view={'phase':'observe','roomId':'room','episodeId':'room','subjects':['blocker'],'minimumSeconds':1,'singleSweepDegrees':math.degrees(.1)}
  middle={'name':'around blocker','phase':'transit','from':'b','to':'c','subjects':[],
          'navigationPolicy':{'monotoneEndpointGaze':True}}
  if moving_view:middle.update(phase='observe',roomId='room',episodeId='room',subjects=['blocker'],minimumSeconds=0,singleSweepDegrees=math.degrees(.9),movingView=True)
  c={'chapters':[{**view,'name':'first view','from':'a','to':'b'},middle,{**view,'name':'last view','from':'c','to':'d'}],
     'tourContract':{'tourMode':'room_tour','bodyRadiusMm':180},'maximumSeconds':30}
  return b,t,c
 def assert_safe_motion(self,p,t,c):
  from tour_rules import trajectory
  self.assertEqual(trajectory(t,c)['issues'],[])
  self.assertFalse(any(p.p.blocked(f['pointMm']) for f in t['frames']))
  self.assertTrue(all(p.p.line_free(a['pointMm'],z['pointMm']) for a,z in zip(t['frames'],t['frames'][1:])))
 def test_fresh_moving_seed_keeps_safe_curved_arc_and_brakes_between_fixed_views(self):
  b,t,c=self.curved_motion_fixture(True);old=copy.deepcopy(t);p=JointPlanner(b,t,c,{'_planningMode':'new'});ch=c['chapters'][1]
  choices={q['name']:p.baseline(q) for _,q in p.obs};choice=choices[ch['name']]
  self.assertEqual(choice['viewPath'],[f['pointMm'] for f in t['frames'][24:121]])
  self.assertFalse(p.p.line_free(choice['point'],choice['endPoint']))
  new,nc=p.rebuild(choices,{'closingView':'seed'});m=markers(new)
  self.assertGreater(max(f['pointMm'][1] for f in new['frames'][m['b']:m['c']+1]),4200)
  for name,start,end in [('first view','a','b'),('last view','c','d')]:
   point=choices[name]['point'];self.assertTrue(all(f['pointMm']==point for f in new['frames'][m[start]:m[end]+1]))
  self.assert_safe_motion(p,new,nc);self.assertEqual(t,old)
 def test_fresh_stationary_view_does_not_inherit_seed_seam_drift(self):
  b,t,c=self.curved_motion_fixture();t['frames']=t['frames'][:25];t['seconds']=25/24;t['visits']=t['visits'][:2];c['chapters']=c['chapters'][:1]
  for i,f in enumerate(t['frames']):f['pointMm'][0]+=6*i/24
  ch=c['chapters'][0];p=JointPlanner(b,t,c,{'_planningMode':'new'});choice=p.baseline(ch)
  new,nc=p.rebuild({ch['name']:choice},{'closingView':'seed'})
  self.assertTrue(all(f['pointMm']==t['frames'][0]['pointMm'] for f in new['frames']))
  self.assertEqual(len(new['frames']),25);self.assert_safe_motion(p,new,nc)
  revision=JointPlanner(b,t,c,{});old,_=revision.rebuild({ch['name']:revision.baseline(ch)},{'closingView':'seed'})
  self.assertEqual([f['pointMm'] for f in old['frames']],[f['pointMm'] for f in t['frames']])
 def test_fresh_curved_transit_prices_braking_and_preserves_stationary_windows(self):
  b,t,c=self.curved_motion_fixture();p=JointPlanner(b,t,c,{'_planningMode':'new'});choices={q['name']:p.baseline(q) for _,q in p.obs}
  new,nc=p.rebuild(choices,{'closingView':'seed'});m=markers(new)
  self.assert_safe_motion(p,new,nc)
  for name,start,end in [('first view','a','b'),('last view','c','d')]:
   self.assertTrue(all(f['pointMm']==choices[name]['point'] for f in new['frames'][m[start]:m[end]+1]))
   self.assertEqual(m[end]-m[start],24)
  # Zero boundary speed is physically sampled, not a hidden change to a view.
  speed=math.dist(new['frames'][m['b']]['pointMm'],new['frames'][m['b']+1]['pointMm'])*24/1000
  self.assertLess(speed,.1)
 def test_fresh_curved_connection_couples_large_yaw_work_to_safe_walking(self):
  from tour_workflow import metrics
  b,t,c=self.curved_motion_fixture();p=JointPlanner(b,t,c,{'_planningMode':'new'});choices={q['name']:p.baseline(q) for _,q in p.obs}
  choices['last view']['yaw']=math.radians(150)
  new,nc=p.rebuild(choices,{'closingView':'seed'});self.assert_safe_motion(p,new,nc)
  self.assertLessEqual(metrics(new)['maxYawDegreesPerSecond'],32)
  m=markers(new);walking=sum(math.dist(a['pointMm'],z['pointMm']) for a,z in zip(new['frames'][m['b']:m['c']],new['frames'][m['b']+1:m['c']+1]))/1000
  self.assertGreater((m['c']-m['b'])/24,walking/1.2)
 def irregular_clock_fixture(self):
  from unittest.mock import patch
  b,t,c=self.curved_motion_fixture();c['chapters'][1]['navigationPolicy']={}
  p=JointPlanner(b,t,c,{'_planningMode':'new'});choices={q['name']:p.baseline(q) for _,q in p.obs}
  def authored_local_turn(planner,points,distances,start,end,policy):
   # A short reveal carries most of the turn; the coupled clock must slow only
   # this part of the safe arc, which creates a velocity jump at its boundaries.
   return [start+(end-start)*max(0,min(1,(d/distances[-1]-.4)/.2)) for d in distances]
  with patch('tour_pipeline.navigation_gaze',side_effect=authored_local_turn),patch.object(p,'repair_fresh_positions',side_effect=lambda tour,config:tour):
   raw,config=p.rebuild(choices,{'closingView':'seed'})
  return p,choices,raw,config
 def test_fresh_irregular_yaw_clock_gets_native_fixed_time_position_repair(self):
  from tour_rules import trajectory
  p,choices,raw,config=self.irregular_clock_fixture()
  self.assertIn('path_acceleration_spike',{i['code'] for i in trajectory(raw,config)['issues']})
  fixed=markers(raw);before=copy.deepcopy(raw)
  repaired,nc=p.rebuild(choices,{'closingView':'seed'})
  self.assertTrue(repaired['positionProjection']['accepted']);self.assert_safe_motion(p,repaired,nc)
  self.assertEqual(repaired['fps'],raw['fps']);self.assertEqual(repaired['seconds'],raw['seconds']);self.assertEqual(markers(repaired),fixed)
  self.assertEqual(len(repaired['frames']),len(raw['frames']))
  for a,z in [('a','b'),('c','d')]:self.assertEqual(repaired['frames'][fixed[a]:fixed[z]+1],raw['frames'][fixed[a]:fixed[z]+1])
  self.assertEqual(raw,before)
 def test_fresh_position_repair_retains_diagnostic_on_timeout_or_failed_final_check(self):
  from unittest.mock import patch
  import time
  from tour_rules import trajectory
  p,choices,raw,config=self.irregular_clock_fixture();original=copy.deepcopy(raw)
  bad=copy.deepcopy(raw);bad['frames'][markers(raw)['a']]['pointMm']=[3000,3000]
  with patch('tour_connection_motion.repair_positions_numpy',return_value=(bad,{'accepted':True})):
   rejected=p.repair_fresh_positions(raw,config)
  self.assertFalse(rejected['positionProjection']['accepted']);self.assertFalse(rejected['positionProjection']['bodyPointsSafe'])
  self.assertFalse(rejected['positionProjection']['observationFramesPreserved']);self.assertEqual(rejected['frames'],original['frames'])
  p.deadline=time.monotonic()-1;timed=p.repair_fresh_positions(raw,config)
  self.assertFalse(timed['positionProjection']['accepted']);self.assertTrue(timed['positionProjection']['budgetExhausted'])
  self.assertEqual(timed['frames'],original['frames']);self.assertTrue(trajectory(timed,config)['issues'])
 def test_revision_never_calls_fresh_position_projector(self):
  from unittest.mock import patch
  b,t,c=self.curved_motion_fixture();p=JointPlanner(b,t,c,{});choices={q['name']:p.baseline(q) for _,q in p.obs}
  with patch('tour_connection_motion.repair_positions_numpy',side_effect=AssertionError('Revision scope must not invoke the fresh projector')):
   p.rebuild(choices,{'closingView':'seed'})
 def test_fresh_moving_lock_cannot_compress_required_braking(self):
  b,t,c=self.curved_motion_fixture(True);ch=c['chapters'][1];c['timingLocks']={'viewingFrames':{ch['name']:24}}
  p=JointPlanner(b,t,c,{'_planningMode':'new'});choices={q['name']:p.baseline(q) for _,q in p.obs}
  self.assertEqual(p.observation_frames(ch,choices[ch['name']]),24)
  self.assertIsNone(p.local_cost(ch,choices[ch['name']]))
  with self.assertRaisesRegex(ValueError,'cannot brake'):p.rebuild(choices,{'closingView':'seed'})
 def test_fresh_total_lock_preserves_acceleration_clock_and_exact_views(self):
  b,t,c=self.curved_motion_fixture();p=JointPlanner(b,t,c,{'_planningMode':'new'});choices={q['name']:p.baseline(q) for _,q in p.obs}
  new,nc=p.rebuild(choices,{'closingView':'seed'});m=markers(new)
  nc['timingLocks']={'totalFrames':len(new['frames'])+24,'fps':24,'viewingFrames':{'first view':24,'last view':24}}
  locked=apply_timing_locks(new,nc,preserve_connection_clock=True);lm=markers(locked)
  self.assertEqual(len(locked['frames']),len(new['frames'])+24);self.assert_safe_motion(p,locked,nc)
  for a,z in [('a','b'),('c','d')]:
   self.assertEqual([{k:v for k,v in f.items() if k!='frame'} for f in locked['frames'][lm[a]:lm[z]+1]],
                    [{k:v for k,v in f.items() if k!='frame'} for f in new['frames'][m[a]:m[z]+1]])
  nc['timingLocks']['totalFrames']=len(new['frames'])-1
  with self.assertRaisesRegex(ValueError,'cannot fit'):apply_timing_locks(new,nc,preserve_connection_clock=True)
 def combined_braking_fixture(self):
  b,t,c=self.curved_motion_fixture(True);b['state']['furniture'][0].update(w=200,d=200);frames=[]
  for i in range(73):
   if i<=24:angle=math.pi;yaw=.1*i/24
   elif i<=48:angle=math.pi-(i-24)*math.pi/24;yaw=.1+.1*(i-24)/24
   else:angle=0;yaw=.2+.1*(i-48)/24
   f=copy.deepcopy(t['frames'][0]);f.update(frame=i,pointMm=[3000+500*math.cos(angle),3000+500*math.sin(angle)],yawRadians=yaw);frames.append(f)
  t.update(frames=frames,seconds=len(frames)/24,visits=[{'name':name,'frame':i} for name,i in zip('abcd',[0,24,48,72])])
  c['chapters'][1]['singleSweepDegrees']=math.degrees(.1);p=JointPlanner(b,t,c,{'_planningMode':'new'});ch=c['chapters'][1]
  choices={q['name']:p.baseline(q) for _,q in p.obs}
  choices[ch['name']]['viewPath']=[[3000+500*math.cos(math.pi-j*math.pi/192),3000+500*math.sin(math.pi-j*math.pi/192)] for j in range(193)]
  initial=math.ceil(p.position_profile(choices[ch['name']]['viewPath'],p.limits)['seconds']*24-1e-8)
  return p,ch,choices,initial
 def test_fresh_moving_time_certifies_combined_curvature_and_braking_at_actual_fps(self):
  p,ch,choices,initial=self.combined_braking_fixture();choice=choices[ch['name']]
  self.assertIn('path_acceleration_spike',{i['code'] for i in p.observation_motion_report(ch,choice,initial)['issues']})
  count=p.observation_frames(ch,choice);self.assertGreater(count,initial)
  self.assertLessEqual(count,min(initial+48,initial*2));self.assertEqual(p.observation_frames(ch,choice),count)
  self.assertIsNotNone(p.local_cost(ch,choice));new,nc=p.rebuild(choices,{'closingView':'seed'});m=markers(new)
  self.assertEqual(m[ch['to']]-m[ch['from']],count);self.assert_safe_motion(p,new,nc)
  legacy=JointPlanner(p.b,p.t,p.c,{});self.assertEqual(legacy.observation_frames(ch,choice),24)
 def test_locked_moving_time_rejects_sampled_combined_acceleration(self):
  p,ch,choices,initial=self.combined_braking_fixture();p.c['timingLocks']={'viewingFrames':{ch['name']:initial}}
  self.assertEqual(p.observation_frames(ch,choices[ch['name']]),initial)
  self.assertIsNone(p.local_cost(ch,choices[ch['name']]))
  with self.assertRaisesRegex(ValueError,'sampled trajectory'):p.rebuild(choices,{'closingView':'seed'})
 def pitch_pose_fixture(self,pitch_from=None):
  b,t,c=self.fixture();b['state']['furniture'][0].update(type='wardrobe',h=2400)
  ch=next(ch for ch in c['chapters'] if ch['phase']=='observe')
  pose={'point':[2800,2000],'yawDegrees':180,'panDegrees':0,'pitchDegrees':-4}
  if pitch_from is not None:pose['pitchFromDegrees']=pitch_from
  ch['candidatePoses']=[pose]
  return b,t,c,ch
 def test_explicit_starting_pitch_scores_real_interpolated_object_framing(self):
  b,t,c,ch=self.pitch_pose_fixture(-26);p=JointPlanner(b,t,c,{'_planningMode':'new'})
  low={'point':[2800,2000],'endPoint':[2800,2000],'yaw':math.pi,'pan':0,'pitch':math.radians(-26)}
  rising={**low,'pitchFrom':math.radians(-26),'pitch':math.radians(-4)}
  end={**low,'pitch':math.radians(-4)}
  self.assertLess(p.local_cost(ch,rising),p.local_cost(ch,low))
  self.assertGreater(p.local_cost(ch,rising),p.local_cost(ch,end))
  choice=next(v for v in p.candidates(ch,0,True) if v['source']=='case_station_proposal')
  self.assertAlmostEqual(choice['pitchFrom'],math.radians(-26));self.assertAlmostEqual(choice['pitch'],math.radians(-4))
  choices={q['name']:p.baseline(q) for _,q in p.obs};choices[ch['name']]=choice
  new,nc=p.rebuild(choices,{'closingView':'seed'});m=markers(new)
  self.assertAlmostEqual(new['frames'][m[ch['from']]]['pitchRadians'],math.radians(-26))
  self.assertAlmostEqual(new['frames'][m[ch['to']]]['pitchRadians'],math.radians(-4))
 def test_pitch_rate_respects_chapter_ceiling_and_default_constant_pose(self):
  b,t,c,ch=self.pitch_pose_fixture(-26);ch['motionReviewLimits']={'maxPitchDegreesPerSecond':5}
  p=JointPlanner(b,t,c,{'_planningMode':'new'});item={'point':[2800,2000],'endPoint':[2800,2000],'yaw':math.pi,'pan':0,'pitch':math.radians(-4),'pitchFrom':math.radians(-26)}
  self.assertIsNone(p.local_cost(ch,item));item.pop('pitchFrom');self.assertIsNotNone(p.local_cost(ch,item))
  b,t,c,ch=self.pitch_pose_fixture();p=JointPlanner(b,t,c,{'_planningMode':'new'})
  default=next(v for v in p.candidates(ch,0,True) if v['source']=='case_station_proposal')
  ch['candidatePoses'][0]['pitchFromDegrees']=-4
  explicit=next(v for v in p.candidates(ch,0,True) if v['source']=='case_station_proposal')
  self.assertEqual(default['localCost'],explicit['localCost']);self.assertNotIn('pitchFrom',default)
  self.assertEqual(explicit['pitchFrom'],explicit['pitch'])
 def test_invalid_starting_pitch_is_not_a_retained_candidate(self):
  for bad in [float('nan'),float('inf'),-float('inf'),True,'-26']:
   b,t,c,ch=self.pitch_pose_fixture(bad);p=JointPlanner(b,t,c,{'_planningMode':'new'})
   self.assertFalse(any(v['source']=='case_station_proposal' for v in p.candidates(ch,0,True)))
 def test_fresh_baseline_preserves_first_and_last_seed_pitch(self):
  b,t,c,ch=self.pitch_pose_fixture();m=markers(t);a,z=m[ch['from']],m[ch['to']]
  for i in range(a,z+1):t['frames'][i]['pitchRadians']=math.radians(-26+22*(i-a)/(z-a))
  p=JointPlanner(b,t,c,{'_planningMode':'new'});choice=p.baseline(ch)
  self.assertAlmostEqual(choice['pitchFrom'],math.radians(-26));self.assertAlmostEqual(choice['pitch'],math.radians(-4))
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
 def spatial_run(self,offset):
  # Synthetic route record; the real entry refusal is tested in test_tour_spatial_plan.
  b,t,c=self.fixture();tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);p=Path(tmp.name);runtime=p/'runtime';runtime.mkdir()
  for name in ('geometry.bin','three.module.js','three.core.js','THREE-LICENSE.txt'):(runtime/name).write_text('synthetic test asset')
  (runtime/'renderer.html').write_text((Path(__file__).resolve().parents[2]/'assets/h5/runtime/renderer.html').read_text())
  (runtime/'scene.json').write_text(json.dumps({'schemeSha256':b['schemeSha256'],'renderSettings':{'size':[1280,720]}}));Image.new('RGB',(100,100),'white').save(p/'plan.png')
  for name,v in [('bundle.json',b),('tour.json',t),('config.json',c)]:(p/name).write_text(json.dumps(v))
  route=[[f['pointMm'][0]+offset,f['pointMm'][1]] for f in t['frames'][::6]]+[[t['frames'][-1]['pointMm'][0]+offset,t['frames'][-1]['pointMm'][1]]]
  plan={'schema':'homeowner-spatial-plan/1','schemeSha256':b['schemeSha256'],'routeMm':route,'openings':[],'openingSequence':[],'stations':[],'entrance':{'startPointMm':route[0],'endPointMm':route[-1]},'cameraEnvelope':{'maximumDeviationMm':900,'visitedRoomDeviationMm':2800,'maximumLengthRatio':1.3,'stationToleranceMm':2800}}
  (p/'spatial-plan.json').write_text(json.dumps(plan));(p/'spatial-review.json').write_text('{}')
  job={'schema':'homeowner-production-job/1','meshPreflight':False,'bundle':str(p/'bundle.json'),'seedTour':str(p/'tour.json'),'seedConfig':str(p/'config.json'),'runtime':str(runtime),'plan':str(p/'plan.png'),'planBounds':[0,0,5000,5000],'search':{'beamWidth':1,'perRoomCandidates':2,'maximumRounds':1}}
  with patch('tour_stage_chain.require_camera_entry',return_value={'plan':p/'spatial-plan.json','review':p/'spatial-review.json','value':plan}):run(job,p/'out')
  return p/'out'
 def test_camera_inside_approved_route_binds_chain_for_capture(self):
  out=self.spatial_run(0);manifest=json.loads((out/'rehearsal/rehearsal.json').read_text())
  self.assertEqual(manifest['spatialGate'],'approved')
  for key in ('spatialPlan','spatialReview','spatialConformance'):self.assertIn(key,manifest['references'])
  self.assertEqual(json.loads((out/'rehearsal/spatial-conformance.json').read_text())['status'],'pass')
  stages=json.loads((out/'tour-pages.json').read_text())['stages'];self.assertEqual(stages['route'],'approved')
  self.assertEqual(json.loads((out/'contract-report.json').read_text())['checks']['spatialRoute']['issues'],[])
 def test_camera_leaving_approved_route_returns_to_route_confirmation(self):
  out=self.spatial_run(6000);report=json.loads((out/'contract-report.json').read_text())
  self.assertEqual(report['status'],'needs_revision');self.assertIn('spatial_route_deviation',[i['code'] for i in report['issues']])
  self.assertEqual(json.loads((out/'rehearsal/rehearsal.json').read_text())['status'],'needs_revision')
  self.assertEqual(json.loads((out/'workflow-state.json').read_text())['nextAllowedStage'],'return_to_route_confirmation')
  self.assertEqual(json.loads((out/'workflow-state.json').read_text())['spatialRouteApproval'],'approved')
  self.assertEqual(json.loads((out/'tour-pages.json').read_text())['stages']['preview'],'diagnostic_needs_revision')
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
