"""Case-neutral regressions for the shared tour contract; no real case coordinates."""
import copy,math,unittest
from tour_contract import inspect,from_brief,preserve_viewing_floors
from tour_workflow import markers

class ContractTests(unittest.TestCase):
 def test_reference_area_mode_retains_gaps_and_does_not_waive_collision_or_backward_motion(self):
  self.c['coveragePolicy']['minimumPercent']=100
  strict=inspect(self.b,self.t,self.c)
  self.assertIn('room_coverage_below_case_minimum',{x['code'] for x in strict['issues']})
  self.c['coverageReferencePolicy']={'mode':'reference_not_visual_acceptance','roomTargets':{r['id']:100 for r in self.b['model']['rooms']},'reviewTolerancePercentagePoints':5}
  r=inspect(self.b,self.t,self.c)
  self.assertNotIn('room_coverage_below_case_minimum',{x['code'] for x in r['issues']})
  self.assertEqual(r['checks']['coverage']['status'],'reference_review_required');self.assertEqual(r['humanAcceptance'],'pending')
  self.assertIn('sustained_backward_walking',{x['code'] for x in r['issues']})
  self.t['frames'][30]['pointMm']=[1200,2000]
  self.assertIn('body_path_collision',self.codes())
 def setUp(self):
  from test_tour_compact import CompactTests
  self.b,self.t,self.c=CompactTests().fixture()
  self.c['coveragePolicy']={'enabled':True,'minimumPercent':1} # Synthetic fixture policy, not a shared default.
  self.c['tourContract']['diagnosticOnly']=False
  self.c['maximumSeconds']=120
  self.c['ruleExceptions']=[{'code':'choreography_limit_override','reason':'Synthetic single-room round-trip fixture; unavoidable transit proportion'}]
  self.c['roomBudgetPolicy']={'maximumTotalSeconds':120,'rooms':[{'name':'Synthetic room','roomIds':['room'],'maximumSeconds':120}]}
  # The positive fixture has smooth starts/stops; real cases remain subject to the same checks.
  old=copy.deepcopy(self.t);marks=markers(old);out=[copy.deepcopy(old['frames'][0])];newmarks={}
  for ch in self.c['chapters']:
   a,z=marks[ch['from']],marks[ch['to']];newmarks[ch['from']]=len(out)-1
   if ch['phase']=='transit':
    p=old['frames'][a]['pointMm'] if a==0 else [2800,2000];q=old['frames'][z]['pointMm'] if z==len(old['frames'])-1 else [2800,2000];n=max(z-a,math.ceil(math.dist(p,q)/500*old['fps']))
    for j in range(1,n+1):
     u=j/n;v=u*u*(3-2*u);f=copy.deepcopy(old['frames'][a+round(u*(z-a))]);f['pointMm']=[p[k]+(q[k]-p[k])*v for k in (0,1)];f['yawRadians']=old['frames'][a]['yawRadians']+(old['frames'][z]['yawRadians']-old['frames'][a]['yawRadians'])*v;out.append(f)
   else:
    for f in copy.deepcopy(old['frames'][a+1:z+1]):f['pointMm']=[2800,2000];out.append(f)
   newmarks[ch['to']]=len(out)-1
  # Synthetic view is a small continuous west-facing pan. Chapter-seam impulse tests add faults separately.
  for i,f in enumerate(out):f.update(frame=i,yawRadians=math.pi+i*.0001)
  for ch in self.c['chapters']:
   if ch['phase']=='observe':ch['singleSweepDegrees']=1
  self.t.update(frames=out,seconds=len(out)/old['fps'],visits=[{'name':name,'frame':i} for name,i in newmarks.items()])
 def codes(self,t=None,c=None,b=None):return {x['code'] for x in inspect(b or self.b,t or self.t,c or self.c)['issues']}
 def test_legacy_fixed_facing_return_is_rejected_and_visual_acceptance_stays_pending(self):
  r=inspect(self.b,self.t,self.c)
  # This historical fixture returns east while still looking west. The new
  # walking rule must expose it rather than grandfathering a former pass.
  self.assertEqual([i['code'] for i in r['issues']],['sustained_backward_walking'])
  self.assertEqual(r['checks']['forwardMotion']['status'],'needs_revision')
  self.assertNotEqual(r['status'],'numeric_pass_visual_pending')
  for key in ('actual3DVisibility','dynamicComfort','humanAcceptance'):self.assertEqual(r[key],'pending')
 def test_new_cases_need_their_own_coverage_threshold(self):
  for brief in ({},{'coveragePolicy':{'enabled':True}},{'coveragePolicy':{'enabled':True,'minimumPercent':float('nan')}},{'coveragePolicy':{'enabled':True,'minimumPercent':True}}):
   with self.assertRaises(ValueError):from_brief(brief)
  for minimum in (25,85):
   p=from_brief({'coveragePolicy':{'enabled':True,'minimumPercent':minimum}})
   self.assertNotIn('minimumPercent',p);self.assertNotIn('maximumSeconds',p)
 def test_disabled_coverage_is_diagnostic_and_cannot_pass(self):
  self.c['coveragePolicy']={'enabled':False};self.c['tourContract']['diagnosticOnly']=True
  self.assertIn('coverage_not_configured_for_capture',self.codes());self.assertIn('diagnostic_only_contract',self.codes())
 def test_legacy_is_distinct_from_current_contract_acceptance(self):
  self.c.pop('tourContract');r=inspect(self.b,self.t,self.c)
  self.assertEqual(r['status'],'legacy_not_contracted');self.assertEqual(r['humanAcceptance'],'pending')
 def test_full_tour_cannot_finish_inside_room(self):
  self.t['frames'][-1]['pointMm']=[2800,2000]
  self.assertIn('full_tour_does_not_return_to_entrance',self.codes())
 def test_finish_point_needs_the_users_reason_and_must_be_reached(self):
  self.t['frames'][-1]['pointMm']=[2800,2000];self.c['tourContract']['finishPoint']=[2800,2000]
  self.assertIn('finish_point_needs_user_reason',self.codes())
  self.c['tourContract']['finishReason']='   ';self.assertIn('finish_point_needs_user_reason',self.codes())
  self.c['tourContract']['finishReason']='Synthetic: the user chose to end the tour here'
  codes=self.codes();self.assertNotIn('finish_point_needs_user_reason',codes);self.assertNotIn('full_tour_does_not_return_to_entrance',codes);self.assertNotIn('full_tour_does_not_reach_finish_point',codes)
  self.c['tourContract']['finishPoint']=[2000,2000];self.assertIn('full_tour_does_not_reach_finish_point',self.codes())
 def test_final_frame_body_collisions_are_rechecked(self):
  self.t['frames'][30]['pointMm']=[1200,2000]
  self.assertIn('body_path_collision',self.codes())
 def test_declared_single_sweep_catches_back_and_forth_motion(self):
  ch=self.c['chapters'][1];m=markers(self.t);a,z=m[ch['from']],m[ch['to']]
  for i in range(a,z+1):self.t['frames'][i]['yawRadians']=math.sin((i-a)/(z-a)*4*math.pi)*.2
  self.assertIn('observation_sweep_reversal',self.codes())
 def test_disguised_stationary_furniture_stop_is_not_a_moving_link(self):
  ch=self.c['chapters'][1];ch['movingView']=True
  self.assertIn('invalid_moving_view_continuation',self.codes())
 def test_each_window_time_floor_is_enforced(self):
  self.c['viewingDurationFloors']=preserve_viewing_floors(self.t,self.c);name=self.c['chapters'][1]['name']
  self.c['viewingDurationFloors'][name]+=1/self.t['fps']
  self.assertIn('viewing_time_compressed',self.codes())
  self.c['viewingDurationFloors']={'removed window':2}
  self.assertIn('missing_preserved_viewing_window',self.codes())
 def test_time_floors_survive_multiple_revisions(self):
  name=self.c['chapters'][1]['name'];self.c['viewingDurationFloors']={name:10}
  self.assertEqual(preserve_viewing_floors(self.t,self.c)[name],10)
 def split_view(self,room_ids,roles):
  old=self.c['chapters'][1];m=markers(self.t);a,z=m[old['from']],m[old['to']];n=len(room_ids);indices=[round(a+(z-a)*i/n) for i in range(n+1)]
  for i,index in enumerate(indices):self.t['visits'].append({'name':f'cut{i}','frame':index})
  self.c['chapters']=self.c['chapters'][:1]+[{**old,'name':f'view{i}','from':old['from'] if i==0 else f'cut{i}','to':old['to'] if i==n-1 else f'cut{i+1}','roomId':rid,'episodeId':'one_group','tourRole':role,'secondPointReason':'Distinct screened area' if i else ''} for i,(rid,role) in enumerate(zip(room_ids,roles))]+self.c['chapters'][2:]
 def test_renaming_episode_cannot_allow_leaving_and_returning_to_room(self):
  self.b['model']['rooms'].append({**copy.deepcopy(self.b['model']['rooms'][0]),'id':'other'})
  self.split_view(['room','other','room'],['public','public','public'])
  self.assertIn('split_room_view',self.codes())
 def test_stage_order_exception_needs_a_reason(self):
  self.split_view(['room','room'],['service','public'])
  self.assertIn('unjustified_presentation_order',self.codes())
  self.c['tourContract']['orderOverrideReason']='User explicitly requested the service area first'
  self.assertNotIn('unjustified_presentation_order',self.codes())
 def test_total_success_does_not_hide_full_room_visit_failure(self):
  self.c['roomBudgetPolicy']={'maximumTotalSeconds':120,'rooms':[{'name':'Room','roomIds':['room'],'maximumSeconds':.1}]}
  codes=self.codes();self.assertIn('room_visit_over_budget',codes);self.assertNotIn('total_over_budget',codes)
 def test_station_count_policy_cannot_be_relaxed_in_final_config(self):
  self.c['observationPointPolicy']['maximumPointsPerRoom']=99
  with self.assertRaisesRegex(ValueError,'maximum two'):inspect(self.b,self.t,self.c)
 def test_two_points_do_not_authorize_reintroducing_the_same_furniture(self):
  self.split_view(['room','room'],['public','public'])
  self.assertIn('duplicate_subject_introduction',self.codes())
if __name__=='__main__':unittest.main()
