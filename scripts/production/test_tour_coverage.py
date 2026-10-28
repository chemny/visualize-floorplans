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
