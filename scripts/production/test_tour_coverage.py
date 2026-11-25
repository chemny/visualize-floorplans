import unittest,math
from unittest.mock import patch
from tour_coverage import inspect
class Free:
 walls=[]
 leaves=[]
class CoverageTests(unittest.TestCase):
 def test_explicit_reference_keeps_measured_gaps_pending_instead_of_claiming_a_pass(self):
  b,t,c=self.scoped_fixture();c['ruleExceptions']=[]
  c['coverageReferencePolicy']={'mode':'reference_not_visual_acceptance','roomTargets':{'hall':80,'bed':80},'reviewTolerancePercentagePoints':5}
  with patch('design_homeowner_tour.clear_distance',return_value=0):r=inspect(b,t,Free(),80,100,config=c)
  self.assertEqual(r['status'],'reference_review_required');self.assertEqual(r['proxyMinimumStatus'],'needs_revision')
  self.assertEqual(len(r['referenceFindings']),2);self.assertTrue(all(x['severity']=='material_gap' and x['visualAcceptance']=='pending' for x in r['referenceFindings']))
  self.assertTrue(all(not x['meetsProxyMinimum'] for x in r['rooms']))
 def test_reference_mode_does_not_accept_missing_or_unknown_room_targets(self):
  b,t,c=self.scoped_fixture();c['coverageReferencePolicy']={'mode':'reference_not_visual_acceptance','roomTargets':{'hall':80},'reviewTolerancePercentagePoints':5}
  with self.assertRaisesRegex(ValueError,'every room'):inspect(b,t,Free(),80,100,config=c)
  c['coverageReferencePolicy']['mode']='skip'
  with self.assertRaisesRegex(ValueError,'Unknown'):inspect(b,t,Free(),80,100,config=c)
 def test_all_rooms_including_unvisited_are_checked(self):
  bundle={'model':{'rooms':[{'id':'seen','poly':[[100,-100],[500,-100],[500,100],[100,100]]},{'id':'behind','poly':[[-500,-100],[-100,-100],[-100,100],[-500,100]]}]}}
  tour={'fps':4,'frames':[{'pointMm':[0,0],'yawRadians':0,'horizontalFovDegrees':76}]}
  result=inspect(bundle,tour,Free(),80,100)
  self.assertEqual(result['status'],'needs_revision');self.assertTrue(result['rooms'][0]['meetsProxyMinimum']);self.assertFalse(result['rooms'][1]['meetsProxyMinimum']);self.assertEqual(result['actual3DVisibility'],'pending')
 def test_threshold_is_not_silently_relaxed(self):
  for bad in [0,101,float('nan')]:
   with self.assertRaises(ValueError):inspect({}, {'frames':[]},Free(),bad)
 def test_rooms_the_route_declares_as_not_entered_leave_the_denominator_with_their_reason(self):
  bundle,tour,config=self.scoped_fixture();config['ruleExceptions']=[]
  config['coveragePolicy']={'enabled':True,'minimumPercent':80,'excludedRooms':[{'roomId':'bed','reason':'用户：并入客厅，不单独设站'}]}
  with patch('design_homeowner_tour.clear_distance',return_value=0):result=inspect(bundle,tour,Free(),80,100,config=config)
  self.assertEqual([r['roomId'] for r in result['rooms']],['hall'])
  self.assertEqual(result['excludedRooms'],[{'roomId':'bed','reason':'用户：并入客厅，不单独设站'}])
 def test_an_exclusion_needs_a_known_room_a_reason_and_no_duplicate(self):
  bundle,tour,config=self.scoped_fixture();config['ruleExceptions']=[]
  for bad in ([{'roomId':'nowhere','reason':'x'}],[{'roomId':'bed','reason':'  '}],[{'roomId':'bed'}],[{'roomId':'bed','reason':'a'},{'roomId':'bed','reason':'b'}]):
   config['coveragePolicy']={'enabled':True,'minimumPercent':80,'excludedRooms':bad}
   with self.subTest(bad=bad),self.assertRaises(ValueError):inspect(bundle,tour,Free(),80,100,config=config)
 def class_case(self,**policy):
  # hall: 75% in view and holds a sofa (a main room); bed: 0% in view and holds a toilet (an other room).
  bundle,tour,config=self.scoped_fixture();config['ruleExceptions']=[]
  bundle['state']={'furniture':[{'id':'s1','type':'sofa','cx':100,'cy':100},{'id':'t1','type':'toilet','cx':100,'cy':100}]}
  bundle['model']['rooms'][1]['poly']=[[1000,1000],[1200,1000],[1200,1200],[1000,1200]];bundle['state']['furniture'][1].update(cx=1100,cy=1100)
  config['chapters']=[{'name':'view','phase':'observe','roomId':'hall','coveredRoomIds':['bed'],'from':'a','to':'b'}];tour['visits']=[{'name':'a','frame':0},{'name':'b','frame':0}]
  config['coveragePolicy']={'enabled':True,'minimumPercent':80,**policy};return bundle,tour,config
 def run_case(self,bundle,tour,config,minimum=80):
  with patch('design_homeowner_tour.clear_distance',side_effect=lambda p,origin,yaw,d:0 if yaw<0 and d<600 else d):return inspect(bundle,tour,Free(),minimum,100,config=config)
 def test_other_rooms_use_their_own_lower_minimum_and_main_rooms_keep_theirs(self):
  from tour_room_class import classify
  bundle,tour,config=self.class_case(otherMinimumPercent=50);self.assertEqual(classify(bundle),{'hall':'major','bed':'other'})
  rows={r['roomId']:r for r in self.run_case(bundle,tour,config)['rooms']}
  self.assertEqual((rows['hall']['roomClass'],rows['bed']['roomClass']),('major','other'))
  self.assertEqual((rows['hall']['requiredPercent'],rows['bed']['requiredPercent']),(80,50))
  # The main room (75%) misses 80; the other room is checked against 50, not 80.
  self.assertFalse(rows['hall']['meetsProxyMinimum']);self.assertEqual(rows['hall']['horizontalAreaPercent'],75)
 def test_the_lower_minimum_lets_an_other_room_pass_while_it_is_still_measured(self):
  bundle,tour,config=self.class_case(otherMinimumPercent=50);config['coveragePolicy']['roomClasses']={'hall':'other'}
  rows={r['roomId']:r for r in self.run_case(bundle,tour,config)['rooms']}
  self.assertTrue(rows['hall']['meetsProxyMinimum']);self.assertEqual(rows['hall']['requiredPercent'],50)
 def test_a_case_can_name_a_rooms_class_and_other_minimum_must_not_exceed_the_main_one(self):
  for bad in (90,0,True):
   bundle,tour,config=self.class_case(otherMinimumPercent=bad)
   with self.subTest(bad=bad),self.assertRaises(ValueError):self.run_case(bundle,tour,config)
  bundle,tour,config=self.class_case(otherMinimumPercent=50,roomClasses={'nowhere':'major'})
  with self.assertRaises(ValueError):self.run_case(bundle,tour,config)
 def scoped_fixture(self):
  bundle={'model':{'rooms':[{'id':name,'poly':[[0,0],[200,0],[200,200],[0,200]]} for name in ('hall','bed')]}}
  tour={'fps':4,'frames':[{'pointMm':[-500,100],'yawRadians':0,'horizontalFovDegrees':76}]}
  config={'chapters':[],'ruleExceptions':[{'code':'room_coverage_minimum_override','roomId':'hall','minimumPercent':75,'reason':'Explicit passage-only case concession'}]}
  return bundle,tour,config
 def test_coverage_concession_only_changes_named_room_and_preserves_denominator(self):
  bundle,tour,config=self.scoped_fixture()
  # One occluded sample out of the same full four-sample room polygon.
  with patch('design_homeowner_tour.clear_distance',side_effect=lambda p,origin,yaw,d:0 if yaw<0 and d<600 else d):
   baseline=inspect(bundle,tour,Free(),80,100)
   # A declared adjacent first observation makes the one camera sample available
   # to both room polygons; changing the threshold cannot alter this window.
   config['chapters']=[{'name':'view','phase':'observe','roomId':'hall','coveredRoomIds':['bed'],'from':'a','to':'b'}]
   tour['visits']=[{'name':'a','frame':0},{'name':'b','frame':0}]
   result=inspect(bundle,tour,Free(),80,100,config=config)
  hall,bed=result['rooms'];self.assertEqual(hall['horizontalAreaPercent'],75)
  self.assertEqual([(r['sampleCount'],r['visibleSamples']) for r in baseline['rooms']],[(r['sampleCount'],r['visibleSamples']) for r in result['rooms']])
  self.assertTrue(hall['meetsProxyMinimum']);self.assertFalse(hall['meetsDefaultMinimum']);self.assertFalse(bed['meetsProxyMinimum'])
  self.assertEqual(result['minimumPercent'],80);self.assertEqual(hall['thresholdException']['roomId'],'hall');self.assertEqual(result['status'],'needs_revision')
 def test_coverage_exception_rejects_unreasoned_unknown_duplicate_or_global_scope(self):
  for mutation in ({'reason':''},{'roomId':'unknown'},{'roomId':'*'},{'minimumPercent':80},{'minimumPercent':0},{'minimumPercent':True},{'minimumPercent':float('nan')}):
   with self.subTest(mutation=mutation):
    bundle,tour,config=self.scoped_fixture();config['ruleExceptions'][0].update(mutation)
    with self.assertRaises(ValueError):inspect(bundle,tour,Free(),80,100,config=config)
  bundle,tour,config=self.scoped_fixture();config['ruleExceptions']*=2
  with self.assertRaisesRegex(ValueError,'Duplicate'):inspect(bundle,tour,Free(),80,100,config=config)
 def test_wall_blocks_horizontal_coverage(self):
  wall=Free();wall.walls=[([200,-1000],[200,1000],50)]
  bundle={'model':{'rooms':[{'id':'room','poly':[[400,-100],[800,-100],[800,100],[400,100]]}]}}
  result=inspect(bundle,{'fps':4,'frames':[{'pointMm':[0,0],'yawRadians':0}]},wall,80,100)
  self.assertEqual(result['rooms'][0]['horizontalAreaPercent'],0)

 def test_unrelated_prefix_does_not_shift_room_observation_samples(self):
  import copy
  bundle={'model':{'rooms':[{'id':'room','poly':[[200,-200],[900,-200],[900,200],[200,200]]}]}}
  frames=[{'pointMm':[0,0],'yawRadians':math.pi} for _ in range(5)]+[{'pointMm':[0,0],'yawRadians':0 if i%3==0 else math.pi} for i in range(20)]
  t={'fps':24,'frames':frames,'visits':[{'name':'start','frame':0},{'name':'view','frame':5},{'name':'end','frame':24}]}
  shifted=copy.deepcopy(t);shifted['frames'].insert(0,copy.deepcopy(frames[0]))
  for marker in shifted['visits'][1:]:marker['frame']+=1
  a=inspect(bundle,t,Free(),80,100);b=inspect(bundle,shifted,Free(),80,100)
  self.assertEqual(a['rooms'],b['rooms']);self.assertEqual(a['temporalSampling'],'interval-anchored with endpoints')

 def separate_fixture(self):
  bundle={'model':{'rooms':[{'id':'public','poly':[[0,0],[1000,0],[1000,200],[0,200]]},
   {'id':'other','poly':[[1200,0],[1800,0],[1800,200],[1200,200]]}]}}
  positions=[-100]+[500]*3+[1500]*3+[500]*4+[1500]*2+[500]*3
  tour={'fps':4,'frames':[{'pointMm':[x,100],'yawRadians':0 if i<7 else math.pi,'horizontalFovDegrees':76} for i,x in enumerate(positions)],
   'visits':[{'name':name,'frame':frame} for name,frame in [('a',1),('b',2),('c',5),('d',6),('e',8),('f',9)]]}
  config={'roomViewingPolicy':{'singleEpisode':False},'tourContract':{'singleEpisodeExceptionReason':'The user explicitly requests public functions in separate visits.'},'chapters':[
   {'name':'first','phase':'observe','roomId':'public','episodeId':'first','from':'a','to':'b'},
   {'name':'other','phase':'observe','roomId':'other','from':'c','to':'d'},
   {'name':'later','phase':'observe','roomId':'public','episodeId':'later','from':'e','to':'f'}]}
  return bundle,tour,config
 def test_explicit_disjoint_introductions_aggregate_without_changing_denominator_or_reference(self):
  b,t,c=self.separate_fixture();c['chapters'][0].update(roomId='other',coveredRoomIds=['public'],observationRegionId='public')
  c['coverageReferencePolicy']={'mode':'reference_not_visual_acceptance','roomTargets':{'public':90,'other':90},'reviewTolerancePercentagePoints':5}
  r=inspect(b,t,Free(),80,100,config=c);row=r['rooms'][0]
  self.assertEqual(row['visitWindows'],[[1,3],[7,10]]);self.assertEqual(row['visitFrames'],[1,10])
  self.assertEqual((row['sampleCount'],row['visibleSamples'],row['horizontalAreaPercent']),(20,16,80))
  self.assertTrue(row['meetsProxyMinimum']);self.assertEqual(r['minimumPercent'],80)
  self.assertEqual(r['referencePolicy'],c['coverageReferencePolicy'])
  self.assertEqual(r['referenceFindings'][0]['gapPercentagePoints'],10)
  self.assertEqual(r['scope'],'declared_introduction_visits')
 def test_default_or_unjustified_policy_cannot_fill_first_visit_from_later_intro_or_pass(self):
  b,t,c=self.separate_fixture()
  for policy,reason in [({},'reason'),({'singleEpisode':False},''),({'singleEpisode':False},'  '),({'singleEpisode':False},True)]:
   with self.subTest(policy=policy,reason=reason):
    c['roomViewingPolicy']=policy;c['tourContract']['singleEpisodeExceptionReason']=reason
    r=inspect(b,t,Free(),80,100,config=c);row=r['rooms'][0]
    self.assertEqual(row['visitFrames'],[1,3]);self.assertEqual(row['horizontalAreaPercent'],40)
    self.assertNotIn('visitWindows',row);self.assertFalse(row['meetsProxyMinimum'])
    self.assertEqual(r['scope'],'first_continuous_visit')
 def test_justified_policy_still_excludes_unintroduced_later_pass_through(self):
  b,t,c=self.separate_fixture();c['chapters']=c['chapters'][:2]
  r=inspect(b,t,Free(),80,100,config=c);row=r['rooms'][0]
  self.assertEqual(row['visitWindows'],[[1,3]]);self.assertEqual(row['horizontalAreaPercent'],40)
  self.assertFalse(row['meetsProxyMinimum'])
 def test_another_room_introduction_never_fills_public_coverage_in_shared_camera_region(self):
  b,t,c=self.separate_fixture();t['frames']=[{'pointMm':[500,100],'yawRadians':math.pi if 4<=i<=7 else 0,'horizontalFovDegrees':76} for i in range(13)]
  t['visits']=[{'name':name,'frame':frame} for name,frame in [('a',1),('b',2),('c',4),('d',7),('e',10),('f',11)]]
  c['chapters'][1]['observationRegionId']='public'
  row=inspect(b,t,Free(),80,100,config=c)['rooms'][0]
  self.assertEqual(row['visitWindows'],[[0,3],[8,12]])
  self.assertEqual(row['horizontalAreaPercent'],40);self.assertFalse(row['meetsProxyMinimum'])
