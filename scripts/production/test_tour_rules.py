import copy,json,math,subprocess,unittest
from pathlib import Path
from unittest.mock import patch
from tour_rules import inspect,trajectory,profile,review_state,RULESET
from tour_contract import inspect as contract
from plan_route import Planner
from compact_tour_visits import safe_path

class RuleTests(unittest.TestCase):
 def setUp(self):
  from test_tour_contract import ContractTests
  x=ContractTests();x.setUp();self.b,self.t,self.c=x.b,x.t,x.c
 def codes(self):return {i['code'] for i in contract(self.b,self.t,self.c)['issues']}
 def test_five_previously_missed_inputs_are_rejected(self):
  for name,mutate,expected in [
   ('height',lambda t,c:[f.update(eyeMm=1650) for f in t['frames']],'camera_profile_frame_mismatch'),
   ('targets',lambda t,c:[ch.update(subjects=[],orderedViewTargets=[]) for ch in c['chapters'] if ch['phase']=='observe'],'missing_view_targets'),
   ('role',lambda t,c:[ch.pop('tourRole',None) for ch in c['chapters']],'missing_or_invalid_tour_role'),
   ('budgets',lambda t,c:c.pop('roomBudgetPolicy',None),'missing_room_visit_budgets'),
   ('limits',lambda t,c:c['observationPointPolicy'].update(maximumStillSeconds=100,maximumSecondsPerPoint=100),'unexplained_observation_limit_override')]:
   with self.subTest(name=name):
    t,c=copy.deepcopy(self.t),copy.deepcopy(self.c);mutate(t,c);self.assertIn(expected,{i['code'] for i in contract(self.b,t,c)['issues']})
 def test_shared_profile_matches_all_generation_entries(self):
  self.assertEqual((profile()['eyeMm'],profile()['horizontalFovDegrees']),(1600,76))
  from plan_route import plan
  b=copy.deepcopy(self.b);b['schema']='floor-visualization-production/1.0'
  raw=plan(b,{'stops':[{'name':'a','point':[3400,2000]},{'name':'b','point':[2800,2000]}],'fps':4,'seconds':2},preview=True)
  self.assertEqual({(f['eyeMm'],f['horizontalFovDegrees']) for f in raw['frames']},{(1600,76)})
  self.c['cameraProfile']['eyeMm']=1650
  for f in self.t['frames']:f['eyeMm']=1650
  self.assertIn('unexplained_camera_profile_override',self.codes())
 def test_round_failure_cannot_silently_return_sharp_corner(self):
  p=object.__new__(Planner);p.line_free=lambda a,b:False
  with self.assertRaisesRegex(ValueError,'rounded corner'):p.round([[0,0],[1000,0],[1000,1000]])
  class P:
   astar=lambda s,a,b:[a,[1000,0],b]
   line_free=lambda s,a,b:True
   simplify=lambda s,p:p
   round=lambda s,p:(_ for _ in ()).throw(ValueError('No safe rounded corner'))
  with self.assertRaisesRegex(ValueError,'rounded corner'):safe_path(P(),[0,0],[1000,1000])
 def test_clear_corner_has_smooth_tangent_but_safe_chords(self):
  p=object.__new__(Planner);p.line_free=lambda a,b:True
  points=p.round([[0,0],[1000,0],[1000,1000]])
  self.assertGreater(len(points),20);self.assertNotIn([1000,0],points)
  self.assertEqual(points[0],[0,0]);self.assertEqual(points[-1],[1000,1000])
 def test_path_seam_impulse_is_not_hidden_by_small_camera_turn(self):
  t={'fps':24,'frames':[{'pointMm':[i*30,0] if i<4 else [90,(i-3)*30]} for i in range(8)]}
  codes={i['code'] for i in trajectory(t,{})['issues']};self.assertIn('path_tangent_discontinuity',codes);self.assertIn('path_acceleration_spike',codes)
 def tangent_fixture(self,headings=(0,12.75,12.75,12.75),distance=10):
  points=[[0,0]]
  for heading in headings:
   previous=points[-1];angle=math.radians(heading)
   points.append([previous[0]+distance*math.cos(angle),previous[1]+distance*math.sin(angle)])
  t={'fps':24,'frames':[{'pointMm':p} for p in points],
     'visits':[{'name':'start','frame':0},{'name':'end','frame':len(points)-1}]}
  c={'chapters':[{'name':'exit','from':'start','to':'end','phase':'transit'}],
     'ruleExceptions':[{'code':'path_tangent_step_override','chapter':'exit','offsetFrame':1,'maximumDegrees':13,'reason':'Explicit one-vertex case concession'}]}
  return t,c
 def test_one_vertex_tangent_exception_does_not_change_global_limit(self):
  t,c=self.tangent_fixture();self.assertIn('path_tangent_discontinuity',{i['code'] for i in trajectory(t,{})['issues']})
  result=trajectory(t,c);self.assertFalse(result['issues']);self.assertEqual(result['policy']['maximumMovingHeadingStepDegrees'],12)
  self.assertEqual(result['scopedExceptions'][0]['frame'],1);self.assertTrue(result['scopedExceptions'][0]['needed']);self.assertIn('reason',result['scopedExceptions'][0])
 def test_second_tangent_failure_is_not_masked_by_allowed_peak(self):
  t,c=self.tangent_fixture((0,12.9,12.9,.2))
  failures=[i for i in trajectory(t,c)['issues'] if i['code']=='path_tangent_discontinuity']
  self.assertEqual([i['frame'] for i in failures],[3]);self.assertAlmostEqual(failures[0]['actual'],12.7)
 def test_tangent_exception_does_not_relax_acceleration_or_its_own_ceiling(self):
  t,c=self.tangent_fixture(distance=30)
  self.assertIn('path_acceleration_spike',{i['code'] for i in trajectory(t,c)['issues']})
  t,c=self.tangent_fixture((0,13.1,13.1,13.1))
  self.assertIn('path_tangent_discontinuity',{i['code'] for i in trajectory(t,c)['issues']})
 def test_tangent_exception_rejects_missing_stale_or_duplicate_scope(self):
  for mutation in ({'reason':''},{'chapter':'other'},{'offsetFrame':-1},{'offsetFrame':4},{'offsetFrame':True},{'maximumDegrees':12},{'maximumDegrees':float('nan')}):
   with self.subTest(mutation=mutation):
    t,c=self.tangent_fixture();c['ruleExceptions'][0].update(mutation)
    with self.assertRaises(ValueError):trajectory(t,c)
  t,c=self.tangent_fixture();c['ruleExceptions']*=2
  with self.assertRaisesRegex(ValueError,'Duplicate'):trajectory(t,c)
 def test_tangent_scope_tracks_its_chapter_instead_of_absolute_frame(self):
  t,c=self.tangent_fixture();t['frames'].insert(0,{'pointMm':[-10,0]})
  for m in t['visits']:m['frame']+=1
  result=trajectory(t,c);self.assertFalse(result['issues']);self.assertEqual(result['scopedExceptions'][0]['frame'],2)
 def test_global_repeat_reason_and_unrelated_scoped_reason_cannot_unlock(self):
  self.c['tourContract']['subjectRepeatExceptionReason']='anything';self.assertIn('unscoped_repeat_exception',self.codes())
  from tour_workflow import intent_check
  c={'chapters':[{'name':'a','phase':'observe','from':'a','to':'b','subjects':['bed']},{'name':'b','phase':'observe','from':'b','to':'c','subjects':['bed']}],'ruleExceptions':[{'code':'repeat_subject','chapter':'other','subjectId':'bed','reason':'wrong window'}]}
  t={'fps':1,'frames':[{'pointMm':[i,0],'yawRadians':0,'pitchRadians':0} for i in range(3)],'visits':[{'name':x,'frame':i} for i,x in enumerate('abc')]}
  self.assertTrue(intent_check(t,c)['failures']);c['ruleExceptions'][0]['chapter']='b';self.assertFalse(intent_check(t,c)['failures'])
 def test_exact_timing_locks_are_stronger_than_time_floors(self):
  from tour_workflow import markers
  ch=next(c for c in self.c['chapters'] if c['phase']=='observe');m=markers(self.t)
  self.c['timingLocks']={'fps':self.t['fps'],'totalFrames':len(self.t['frames']),'viewingFrames':{ch['name']:m[ch['to']]-m[ch['from']]}}
  self.assertFalse(inspect(self.t,self.c)['issues'])
  self.c['timingLocks']['totalFrames']+=1;self.c['timingLocks']['viewingFrames'][ch['name']]+=1
  self.assertTrue({'locked_total_duration_changed','locked_viewing_duration_changed'}<={i['code'] for i in inspect(self.t,self.c)['issues']})
 def test_visual_failure_overrides_numeric_reviewable_state(self):
  s=review_state('numeric_pass_visual_pending','pass','needs_revision');self.assertFalse(s['reviewable']);self.assertFalse(s['productionReady'])
 def test_later_pass_does_not_repair_first_visit_coverage(self):
  from tour_coverage import inspect as coverage
  class Free:walls=[];leaves=[]
  b={'model':{'rooms':[{'id':'r','poly':[[0,-500],[2000,-500],[2000,500],[0,500]]}]}}
  frames=[{'pointMm':[100,0],'yawRadians':math.pi} for i in range(4)]+[{'pointMm':[-1000,0],'yawRadians':0} for i in range(8)]
  t={'fps':4,'frames':frames,'visits':[{'name':'a','frame':0},{'name':'b','frame':3},{'name':'c','frame':11}]};c={'chapters':[{'name':'view','from':'a','to':'b','phase':'observe','roomId':'r'},{'name':'return','from':'b','to':'c','phase':'transit'}]}
  all_frames=coverage(b,t,Free(),80,100);first=coverage(b,t,Free(),80,100,config=c)
  self.assertTrue(all_frames['rooms'][0]['meetsProxyMinimum']);self.assertFalse(first['rooms'][0]['meetsProxyMinimum'])

if __name__=='__main__':unittest.main()
