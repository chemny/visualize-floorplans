import copy, math, unittest
from design_homeowner_tour import order_groups, select_observation, opening_candidates, design, navigation_gaze
from tour_choreography import inspect
from tour_workflow import intent_check

class DesignTests(unittest.TestCase):
 def test_adjacent_dry_area_to_wet_room_is_transit_not_a_false_inside_room_view(self):
  bundle={'schemeSha256':'dry-wet','model':{'footprint':[[0,0],[6000,0],[6000,4000],[0,4000]],'rooms':[{'id':'dry','poly':[[0,0],[3000,0],[3000,4000],[0,4000]]},{'id':'wet','poly':[[3000,0],[6000,0],[6000,4000],[3000,4000]]}]},'state':{'walls':[],'furniture':[{'id':'wash','type':'vanity','cx':2000,'cy':2000,'w':400,'d':400,'rot':0},{'id':'toilet','type':'toilet','cx':5000,'cy':2000,'w':400,'d':400,'rot':0}]}}
  common={'roomId':'wet','episodeId':'bath','tourRole':'service','viewPurpose':'One dry and wet bathroom introduction','viewSeconds':2,'observationPanDegrees':10,'candidatePointsOnly':True}
  brief={'schema':'homeowner-design-brief/1','tourMode':'indoor_segment','startPoint':[500,2000],'maximumSeconds':60,'coveragePolicy':{'enabled':False},'rooms':[{**common,'observationId':'dry-view','name':'Dry','observationRegionId':'dry','coveredRoomIds':['dry'],'adjacentViewReason':'Actual external wash area','subjectId':'wash','targetMm':[2000,2000,600],'candidatePoints':[[1000,2000]]},{**common,'observationId':'wet-view','name':'Wet','secondPointReason':'A real physical boundary separates dry and wet areas','subjectId':'toilet','targetMm':[5000,2000,600],'candidatePoints':[[4000,2000]]}],'groups':[['dry-view','wet-view']]}
  _,config,_=design(bundle,brief)
  bridge=next(ch for ch in config['chapters'] if ch['name']=='Dry → Wet')
  self.assertEqual(bridge['phase'],'transit');self.assertNotIn('movingView',bridge)
  both=copy.deepcopy(brief);both['rooms'][1].update(observationRegionId='dry',adjacentViewReason='Both positions are in the real external area',candidatePoints=[[1200,2500]])
  _,config,_=design(bundle,both);bridge=next(ch for ch in config['chapters'] if ch['name']=='Dry → Wet')
  self.assertTrue(bridge['movingView']);self.assertEqual(bridge['observationRegionId'],'dry')
 def test_brief_preserves_unordered_subjects_and_explicit_reference_coverage(self):
  bundle={'schemeSha256':'declared-functions','model':{'footprint':[[0,0],[6000,0],[6000,4000],[0,4000]],'rooms':[{'id':'room','poly':[[0,0],[6000,0],[6000,4000],[0,4000]]}]},'state':{'walls':[],'furniture':[{'id':'bed','type':'bed','cx':4000,'cy':2000,'w':500,'d':500,'rot':0},{'id':'storage','type':'wardrobe','cx':4000,'cy':2600,'w':500,'d':300,'rot':0}]}}
  reference={'mode':'reference_not_visual_acceptance','roomTargets':{'room':75},'reviewTolerancePercentagePoints':5}
  brief={'schema':'homeowner-design-brief/1','tourMode':'indoor_segment','startPoint':[1000,2000],'maximumSeconds':60,'coveragePolicy':{'enabled':True,'minimumPercent':1},'coverageReferencePolicy':reference,'rooms':[{'roomId':'room','name':'Room','subjectId':'bed','subjects':['storage'],'orderedViewTargets':['bed'],'targetMm':[4000,2000,800],'candidatePoints':[[2200,2000]],'candidatePointsOnly':True,'viewPurpose':'Read sleep and storage in one composition','tourRole':'primary','viewSeconds':2}]}
  _,config,_=design(bundle,brief)
  view=next(ch for ch in config['chapters'] if ch['phase']=='observe')
  self.assertEqual(view['subjects'],['bed','storage']);self.assertEqual(view['orderedViewTargets'],['bed'])
  self.assertEqual(config['coverageReferencePolicy'],reference)
  brief['rooms'][0]['subjects']=['invented']
  with self.assertRaisesRegex(ValueError,'Unknown'):design(bundle,brief)
 def test_explicit_adjacent_region_and_required_framing(self):
  class Free:
   walls=[]
   leaves=[]
   def blocked(self,p):return False
  bundle={'model':{'rooms':[{'id':'balcony','poly':[[0,2000],[4000,2000],[4000,3000],[0,3000]]},{'id':'living','poly':[[0,0],[4000,0],[4000,2000],[0,2000]]}]},'state':{'furniture':[{'id':'washer'}]}}
  intent={'roomId':'balcony','name':'Balcony','subjectId':'washer','targetMm':[2000,2500,1000],'candidatePoints':[[2000,1000]],'observationRegionId':'living','candidatePointsOnly':True,'viewTargets':[[1800,2400,1000],[2200,2400,1000]]}
  self.assertEqual(select_observation(bundle,Free(),intent)['point'],[2000,1000])
  with self.assertRaisesRegex(ValueError,'Unknown observationRegionId'):select_observation(bundle,Free(),{**intent,'observationRegionId':'invented'})
  with self.assertRaisesRegex(ValueError,'No unoccluded'):select_observation(bundle,Free(),{**intent,'viewTargets':[[3900,1000,1000]]})
 def test_same_room_distinct_entry_return_views_and_inside_requirement(self):
  bundle={'schemeSha256':'two-views','model':{'footprint':[[0,0],[6000,0],[6000,5000],[0,5000]],'rooms':[{'id':'room','poly':[[0,0],[6000,0],[6000,5000],[0,5000]]}]},'state':{'walls':[],'furniture':[{'id':'a','type':'cabinet','cx':4500,'cy':2000,'w':400,'d':400,'rot':0},{'id':'b','type':'cabinet','cx':1500,'cy':3500,'w':400,'d':400,'rot':0}]}}
  common={'roomId':'room','viewPurpose':'Distinct entry and return sides','viewSeconds':2,'requireInsideRoom':True,'candidatePointsOnly':True}
  brief={'roomViewingPolicy':{'singleEpisode':False},'schema':'homeowner-design-brief/1','tourMode':'indoor_segment','startPoint':[1000,1000],'maximumSeconds':120,'coveragePolicy':{'enabled':False},'choreographyPolicy':{'maximumTransitFraction':1},'rooms':[{**common,'observationId':'entry_view','name':'Entry','subjectId':'a','targetMm':[4500,2000,1000],'tourRole':'public','candidatePoints':[[3000,2000]]},{**common,'observationId':'return_view','secondPointReason':'Distinct return-side area not visible from first station','name':'Return','subjectId':'b','targetMm':[1500,3500,1000],'tourRole':'return_public','candidatePoints':[[3000,3000]]}],'groups':[['entry_view'],['return_view']]}
  tour,config,report=design(bundle,brief)
  self.assertEqual(report['order'],['entry_view','return_view']);self.assertEqual([x['roomId'] for x in config['chapters'] if x['phase']=='observe'],['room','room'])
  with self.assertRaisesRegex(ValueError,'one viewing episode'):design(bundle,{**brief,'roomViewingPolicy':{'singleEpisode':True}})
  chain=copy.deepcopy(brief);chain['roomViewingPolicy']={'singleEpisode':True};chain['fixedOrder']=['entry_view','return_view']
  for view in chain['rooms']:view['episodeId']='same_continuous_visit'
  self.assertEqual(design(bundle,chain)[2]['order'],chain['fixedOrder'])
  bad={**brief['rooms'][0],'candidatePoints':[[-100,2000]]}
  with self.assertRaisesRegex(ValueError,'No supported observation'):select_observation(bundle,__import__('plan_route').Planner(bundle,{}),bad)
 def test_declared_exit_turn_does_not_reverse_through_the_room(self):
  class Free:
   walls=[]
   leaves=[]
  points=[[i*100,0] for i in range(21)];distances=[i*100 for i in range(21)]
  yaws=navigation_gaze(Free(),points,distances,math.radians(190),0,{'initialTurnDirection':1,'initialTurnDistanceMm':3000})
  self.assertTrue(all(b>=a-1e-8 for a,b in zip(yaws,yaws[1:])))
  self.assertLess(abs(yaws[-1]-2*math.pi),1e-8)
 def test_order_groups_reduces_zigzag_without_reordering_suite(self):
  x={'entry':0,'north':-3,'living':4,'closet':6,'bath':7,'bed':8}
  d=lambda a,b:abs(x[a]-x[b])
  order,cost=order_groups('entry',[['living'],['north'],['closet','bath','bed']],d,'bed')
  self.assertEqual(order,['north','living','closet','bath','bed']);self.assertEqual(cost,14)
  old=['living','north','closet','bath','bed'];self.assertLess(cost,sum(d(a,b) for a,b in zip(['entry']+old,old)))
 def test_second_layout_end_to_end_has_stationary_observation_and_no_collisions(self):
  rooms=[{'id':'a','poly':[[0,0],[4000,0],[4000,3000],[0,3000]]},{'id':'b','poly':[[4000,0],[8000,0],[8000,3000],[4000,3000]]}]
  furniture=[{'id':k,'type':'cabinet','cx':x,'cy':1500,'w':400,'d':400,'rot':0} for k,x in [('fa',2800),('fb',6500)]]
  bundle={'schemeSha256':'synthetic-second-layout','model':{'rooms':rooms,'footprint':[[0,0],[8000,0],[8000,3000],[0,3000]]},'state':{'walls':[],'furniture':furniture}}
  brief={'coveragePolicy':{'enabled':False},'schema':'homeowner-design-brief/1','tourMode':'indoor_segment','startPoint':[1000,1000],'maximumSeconds':120,'rooms':[{'roomId':'a','name':'A','viewPurpose':'Understand shared room arrangement','tourRole':'public','subjectId':'fa','targetMm':[2800,1500,1000],'candidatePoints':[[1800,1000]],'viewSeconds':3},{'roomId':'b','name':'B','viewPurpose':'Understand secondary room furniture scale','tourRole':'secondary','subjectId':'fb','targetMm':[6500,1500,1000],'candidatePoints':[[5000,1000]],'viewSeconds':3}]}
  tour,config,report=design(bundle,brief)
  self.assertEqual(report['status'],'needs_revision');self.assertFalse(report['collisions'])
  self.assertIn('stationary_camera_hold',{x['code'] for x in report['observationPoints']['issues']})
  marks={v['name']:v['frame'] for v in tour['visits']}
  for ch in config['chapters']:
   if ch['phase']=='observe':
    points=[tuple(f['pointMm']) for f in tour['frames'][marks[ch['from']]:marks[ch['to']]+1]]
    # Frame-grid rounding can place a boundary sample up to one frame before arrival.
    # The reading interior must stay still; no compulsory 250-mm move is allowed.
    self.assertLess(max(math.dist(a,points[len(points)//2]) for a in points),50.001)
    self.assertLess(max(math.dist(a,points[len(points)//2]) for a in points[1:-1]),1e-6)
  self.assertFalse(report['videoGenerated']);self.assertEqual(tour['humanAcceptance'],'pending')
 def test_public_priority_wins_over_shorter_secondary_first_route(self):
  points={'entry':0,'public':9,'primary':8,'secondary':1,'service':2}
  d=lambda a,b:abs(points[a]-points[b])
  groups=[['public'],['primary'],['secondary'],['service']]
  order,cost=order_groups('entry',groups,d,return_to='entry',stages=[0,1,2,3])
  self.assertEqual(order,['public','primary','secondary','service'])
 def test_closed_order_counts_return_distance(self):
  x={'entry':0,'a':1,'b':3}
  order,cost=order_groups('entry',[['a'],['b']],lambda a,b:abs(x[a]-x[b]),return_to='entry')
  self.assertEqual(cost,6)
 def test_full_tour_rejects_unverified_outside_endpoint(self):
  from design_homeowner_tour import entry_apron
  with self.assertRaisesRegex(ValueError,'entranceOpeningId'):
   entry_apron({'state':{'walls':[]}}, {'startPoint':[1000,1000]})
 def test_actual_door_round_trip_uses_external_camera_apron(self):
  bundle={'schemeSha256':'door-fixture','model':{'footprint':[[0,0],[4000,0],[4000,4000],[0,4000]],'rooms':[{'id':'public','poly':[[100,100],[3900,100],[3900,3900],[100,3900]]}]},'state':{'walls':[{'id':'wall','a':[4000,0],'b':[4000,4000],'t':100,'opens':[{'id':'entrance','kind':'door','at':1500,'width':1000,'swing':-1,'angle':90,'hingeEnd':'start'}]}],'furniture':[{'id':'sofa','type':'sofa','cx':1200,'cy':2000,'w':1000,'d':600,'rot':0}]}}
  brief={'coveragePolicy':{'enabled':False},'schema':'homeowner-design-brief/1','tourMode':'full_tour','entranceOpeningId':'entrance','startPoint':[4500,2000],'maximumSeconds':60,'rooms':[{'roomId':'public','name':'Living','viewPurpose':'Reveal public room before returning to entrance','tourRole':'public','subjectId':'sofa','targetMm':[1200,2000,1000],'candidatePoints':[[2800,2000]],'viewSeconds':2}],'observationPanDegrees':10,'choreographyPolicy':{'maximumTransitFraction':.95}}
  tour,config,report=design(bundle,brief)
  self.assertFalse(report['collisions']);self.assertLess(math.dist(tour['frames'][0]['pointMm'],tour['frames'][-1]['pointMm']),1e-6);self.assertEqual(report['entranceOpeningId'],'entrance')
  self.assertEqual(report['tourMode'],'full_tour');self.assertTrue(report['exteriorCameraApron']);self.assertTrue(any(ch['name'].endswith('入户门外') for ch in config['chapters']))
 def test_invalid_end_is_rejected(self):
  with self.assertRaises(ValueError):order_groups('x',[['a','b']],lambda a,b:1,'a')
 def test_repeated_scanning_caught_without_user_thresholds(self):
  yaws=[0,30,60,30,0,30,60,30,0]
  tour={'fps':1,'seconds':9,'frames':[{'pointMm':[0,0],'yawRadians':math.radians(y),'pitchRadians':0} for y in yaws],'visits':[{'name':'a','frame':0},{'name':'b','frame':8}]}
  config={'chapters':[{'name':'room','from':'a','to':'b','phase':'observe','subjects':['bed']}],'choreographyPolicy':{'enabled':True}}
  self.assertIn('repeated_scan',[x['code'] for x in inspect(tour,config)['issues']]);self.assertTrue(intent_check(tour,config)['failures'])
 def test_long_slow_turn_fails_even_when_speed_is_low(self):
  tour={'fps':1,'seconds':31,'frames':[{'pointMm':[i*50,0],'yawRadians':math.radians(i*8),'pitchRadians':0} for i in range(31)],'visits':[{'name':'a','frame':0},{'name':'b','frame':30}]}
  config={'chapters':[{'name':'link','from':'a','to':'b','phase':'transit'}]}
  self.assertIn('excessive_transit_turn',[x['code'] for x in inspect(tour,config)['issues']])
 def test_room_target_must_exist(self):
  bundle={'model':{'rooms':[{'id':'room','poly':[[0,0],[1,0],[1,1]]}]},'state':{'furniture':[]}}
  with self.assertRaisesRegex(ValueError,'Unknown subject'):select_observation(bundle,None,{'roomId':'room','subjectId':'invented'})
 def test_opening_candidates_never_use_a_window(self):
  bundle={'state':{'walls':[{'a':[0,0],'b':[1000,0],'t':100,'opens':[{'id':'window','kind':'window'}]}]}}
  with self.assertRaisesRegex(ValueError,'Window'):opening_candidates(bundle,None,{},'window')
 def test_door_candidates_default_to_shallow_inside_station(self):
  from test_tour_compact import CompactTests
  from plan_route import inside
  bundle,_,_=CompactTests().fixture()
  brief={'schema':'homeowner-design-brief/1','coveragePolicy':{'enabled':False},'tourMode':'full_tour','entranceOpeningId':'entry','startPoint':[4500,2000],'maximumSeconds':120,'rooms':[{'roomId':'room','name':'Room','subjectId':'sofa','targetMm':[1200,2000,1000],'openingId':'entry','viewSeconds':2,'observationPanDegrees':10,'viewPurpose':'Read the room from a shallow inside point','tourRole':'public'}],'choreographyPolicy':{'maximumTransitFraction':1}}
  _,_,report=design(bundle,brief)
  self.assertTrue(inside(report['observations'][0]['point'],bundle['model']['rooms'][0]['poly']))
  self.assertNotIn('requireInsideRoom',brief['rooms'][0])
if __name__=='__main__':unittest.main()
