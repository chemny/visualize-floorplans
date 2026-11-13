import copy,math,subprocess,sys,tempfile,unittest
from pathlib import Path
from tour_camera_evidence import ordered_bearings,target_anchor,target_samples,inspect
from tour_workflow import markers
from tour_contract import inspect as contract

class CameraEvidenceTests(unittest.TestCase):
 def test_elevated_fixtures_use_world_height_for_anchor_and_samples(self):
  b={'state':{'furniture':[{'id':'hob','cx':1000,'cy':2000,'w':600,'d':500,'h':20,'elevation':905},
                            {'id':'sink','cx':2000,'cy':2000,'w':800,'d':450,'h':230,'elevation':900},
                            {'id':'floor','cx':3000,'cy':2000,'h':800}]}}
  self.assertEqual(target_anchor(b,'hob'),[1000,2000,915])
  self.assertEqual(target_anchor(b,'sink'),[2000,2000,1015])
  self.assertEqual({p[2] for p in target_samples(b,'sink')},{1015})
  self.assertEqual(target_anchor(b,'floor')[2],400)
 def setUp(self):
  from test_tour_contract import ContractTests
  self.x=ContractTests();self.x.setUp();self.b,self.t,self.c=self.x.b,self.x.t,self.x.c
 def codes(self):return {v['code'] for v in contract(self.b,self.t,self.c)['issues']}
 def test_unknown_target_cannot_be_metadata_only(self):
  self.c['chapters'][1]['orderedViewTargets']=['required-but-missing-object']
  self.assertIn('invalid_ordered_view_target',self.codes())
 def test_final_visibility_and_sequence_not_just_declared_ids(self):
  ch=self.c['chapters'][1];self.b['state']['furniture'] += [{'id':'behind','cx':-5000,'cy':-5000,'type':'tv','w':100,'d':20}]
  ch['orderedViewTargets']=['behind']
  self.assertIn('ordered_target_not_visible_in_sequence',self.codes())
 def test_room_aggregate_rejects_two_individually_one_way_opposite_sweeps(self):
  self.x.split_view(['room','room'],['public','public']);ch=self.c['chapters'][1:3];m=markers(self.t)
  for ix,c in enumerate(ch):
   a,z=m[c['from']],m[c['to']];c['singleSweepDegrees']=8 if ix==0 else -8
   for i in range(a,z+1):self.t['frames'][i]['yawRadians']=math.radians(8*(i-a)/(z-a) if ix==0 else 8-8*(i-a)/(z-a))
  self.assertIn('room_wide_sweep_reversal',self.codes())
 def test_normal_exit_not_counted_as_second_sweep(self):
  before=contract(self.b,self.t,self.c)['checks']['cameraEvidence']['roomSweeps']
  m=markers(self.t);ch=self.c['chapters'][-1];a,z=m[ch['from']],m[ch['to']]
  for i in range(a+1,z+1):self.t['frames'][i]['yawRadians']+=math.sin((i-a)/(z-a)*math.pi)*.5
  self.assertEqual(before,contract(self.b,self.t,self.c)['checks']['cameraEvidence']['roomSweeps'])
 def test_explicit_separate_introductions_keep_direction_checks_inside_each_episode(self):
  self.x.split_view(['room','room'],['public','public']);chapters=self.c['chapters'][1:3];m=markers(self.t)
  for index,ch in enumerate(chapters):
   ch['episodeId']='intent-'+str(index);a,z=m[ch['from']],m[ch['to']]
   ch['singleSweepDegrees']=8 if index==0 else -8
   for i in range(a,z+1):self.t['frames'][i]['yawRadians']=math.radians(8*(i-a)/(z-a) if index==0 else 8-8*(i-a)/(z-a))
  self.c['roomViewingPolicy']={'singleEpisode':False}
  self.assertIn('room_wide_sweep_reversal',self.codes())
  self.c['tourContract']['singleEpisodeExceptionReason']='Explicit separate functional introductions in the requested order'
  self.assertNotIn('room_wide_sweep_reversal',self.codes())
  chapters[1]['episodeId']=chapters[0]['episodeId']
  self.assertIn('room_wide_sweep_reversal',self.codes())
 def test_sustained_wall_and_angular_kink_are_checked_without_chapter_refinement(self):
  class Wall:
   walls=[];leaves=[]
  from unittest.mock import patch
  with patch('design_homeowner_tour.clear_distance',return_value=100):
   r=inspect(self.b,self.t,self.c,Wall())
  self.assertIn('sustained_wall_facing',{x['code'] for x in r['issues']})
  self.t['frames'][len(self.t['frames'])//2]['yawRadians']+=.3
  self.assertIn('camera_angular_acceleration',self.codes())
 def test_ordered_target_geometry_controls_sweep_and_rejects_zigzag(self):
  b={'state':{'furniture':[{'id':str(i),'cx':1000*math.cos(a),'cy':1000*math.sin(a)} for i,a in enumerate([0,.3,.6])]}}
  self.assertEqual(ordered_bearings(b,['0','1','2'],[0,0]),[0,.3,.6])
  with self.assertRaisesRegex(ValueError,'reversing'):ordered_bearings(b,['0','2','1'],[0,0])
  with self.assertRaisesRegex(ValueError,'Unknown'):target_anchor(b,'missing')
 def test_missing_room_ids_are_not_merged_as_one_room(self):
  self.x.split_view(['room','room'],['public','public'])
  for ch in self.c['chapters']:
   if ch.get('phase')=='observe':ch.pop('roomId',None)
  r=contract(self.b,self.t,self.c)
  self.assertNotIn('room_wide_sweep_reversal',{x['code'] for x in r['issues']})
  self.assertEqual(r['checks']['cameraEvidence']['roomAggregationStatus'],'metadata_incomplete')
 def test_target_host_wall_is_excluded_but_intervening_wall_remains(self):
  from tour_camera_evidence import visibility_planner
  from design_homeowner_tour import clear_distance
  from plan_route import Planner
  b=copy.deepcopy(self.b);b['state']['furniture'].append({'id':'trim','type':'windowtrim','cx':0,'cy':2000,'w':100,'d':100,'assemblyOwner':{'wallId':'host'}})
  b['state']['walls']=[{'id':name,'a':[x,0],'b':[x,4000],'t':100,'opens':[]} for name,x in [('host',0),('obstruction',1000)]]
  p=visibility_planner(b,Planner(b,{}),'trim')
  self.assertLess(clear_distance(p,[2000,2000],math.pi,2000),1500)
  b['state']['walls']=b['state']['walls'][:1];p=visibility_planner(b,Planner(b,{}),'trim')
  self.assertEqual(clear_distance(p,[2000,2000],math.pi,2000),2000)
 def test_generator_uses_real_ordered_targets_instead_of_stale_target_coordinate(self):
  from design_homeowner_tour import design
  b={'schemeSha256':'ordered-targets','model':{'footprint':[[0,0],[6000,0],[6000,5000],[0,5000]],'rooms':[{'id':'room','poly':[[0,0],[6000,0],[6000,5000],[0,5000]]}]},'state':{'walls':[],'furniture':[{'id':name,'type':'cabinet','cx':4500,'cy':y,'w':100,'d':100} for name,y in [('a',2000),('b',3000)]]}}
  brief={'schema':'homeowner-design-brief/1','tourMode':'indoor_segment','startPoint':[1000,2500],'maximumSeconds':120,'coveragePolicy':{'enabled':True,'minimumPercent':1},'rooms':[{'roomId':'room','name':'Room','viewPurpose':'Read two sides in order','viewSeconds':2,'subjectId':'a','targetMm':[0,0,0],'orderedViewTargets':['a','b'],'candidatePoints':[[3000,2500]],'candidatePointsOnly':True,'tourRole':'public'}]}
  t,c,r=design(b,brief);ch=next(x for x in c['chapters'] if x['phase']=='observe')
  self.assertAlmostEqual(ch['singleSweepDegrees'],math.degrees(2*math.atan2(500,1500)))
  self.assertEqual(ch['subjects'],['a','b'])
  self.assertEqual(len(r['contract']['checks']['cameraEvidence']['orderedTargetWindows']),2)
  brief['rooms'][0]['orderedViewTargets']=['a','missing']
  with self.assertRaisesRegex(ValueError,'Unknown ordered'):design(b,brief)
 def test_actual_mesh_audit_must_cover_same_targets_in_order(self):
  from tour_camera_evidence import require_actual_targets
  t={'fps':24,'visits':[{'name':'a','frame':0},{'name':'z','frame':48}]}
  c={'chapters':[{'name':'view','from':'a','to':'z','phase':'observe','orderedViewTargets':['first','second']}]}
  good={'unoccludedSamples':3,'totalSamples':4,'screenAreaFraction':.1}
  audit={'policy':{'sampleHz':4,'minContinuousSeconds':.25},'chapters':[{'startSeconds':0,'endSeconds':2,'samples':[{'seconds':i/4,'subjects':{'first' if i<4 else 'second':good}} for i in range(9)]}]}
  self.assertTrue(require_actual_targets(c,t,audit))
  c['chapters'][0]['orderedViewTargets']=['second','first']
  with self.assertRaisesRegex(ValueError,'out of order'):require_actual_targets(c,t,audit)
  audit['chapters'][0]['samples']=[]
  with self.assertRaises(ValueError):require_actual_targets(c,t,audit)
 def test_javascript_actual_target_gate_rejects_reversed_sample_order(self):
  import json,shutil
  node=shutil.which('node')
  if not node:self.skipTest('Existing node unavailable')
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)
   values={'route.json':{'rehearsal':{'path':str(p/'manifest.json')}},'manifest.json':{'references':{'config':{'path':str(p/'config.json')}}},'config.json':{'chapters':[{'name':'view','from':'a','to':'z','phase':'observe','orderedViewTargets':['first','second']}]},'preview.json':{'artifacts':{'subjectAudit':{'path':str(p/'audit.json')}}},'tour.json':{'fps':24,'visits':[{'name':'a','frame':0},{'name':'z','frame':48}]},'audit.json':{'policy':{'sampleHz':4,'minContinuousSeconds':.25},'chapters':[{'startSeconds':0,'endSeconds':2,'samples':[{'seconds':i/4,'subjects':{'second' if i<4 else 'first':{'unoccludedSamples':3,'totalSamples':4,'screenAreaFraction':.1}}} for i in range(9)]}]}}
   for k,v in values.items():(p/k).write_text(json.dumps(v))
   module=Path(__file__).with_name('preview_gate.mjs').resolve().as_uri();script=f"import {{requireTargetAudit}} from {json.dumps(module)};requireTargetAudit(...process.argv.slice(1));"
   args=[node,'--input-type=module','-e',script,str(p/'route.json'),str(p/'preview.json'),str(p/'tour.json')]
   r=subprocess.run(args,capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertIn('out of order',r.stderr)
   values['config.json']['chapters'][0]['orderedViewTargets']=['second','first'];(p/'config.json').write_text(json.dumps(values['config.json']))
   r=subprocess.run(args,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
 def test_blender_animation_rejected_before_output_or_dependency_lookup(self):
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp)/'must-not-exist'
   r=subprocess.run([sys.executable,str(Path(__file__).with_name('run_production.py')),'--engine','blender','--bundle','missing','--config','missing','--out',str(out),'--animation'],capture_output=True,text=True)
   self.assertNotEqual(r.returncode,0);self.assertIn('Blender animation disabled',r.stderr);self.assertFalse(out.exists())
if __name__=='__main__':unittest.main()
