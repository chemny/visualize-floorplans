import copy,json,tempfile,unittest
from pathlib import Path
from tour_room_fragments import clip,inspect_fragment,groups,prepare,summarize
from tour_pipeline import JointPlanner
from tour_workflow import markers
from test_tour_contract import ContractTests

class RoomFragmentTests(unittest.TestCase):
 def fixture(self):
  x=ContractTests();x.setUp();return x.b,x.t,x.c
 def test_fragment_preserves_each_view_count_and_does_not_change_source(self):
  b,t,c=self.fixture();before=copy.deepcopy(t);e=JointPlanner(b,t,c,{})
  group=groups(c)[0];choices={ch['name']:e.baseline(ch) for ch in group}
  ft,fc=clip(e,group,choices);m=markers(ft)
  for ch in group:self.assertEqual(m[ch['to']]-m[ch['from']],e.m[ch['to']]-e.m[ch['from']])
  self.assertEqual(t,before);self.assertTrue(ft['fragmentOnly']);self.assertEqual(ft['schemeSha256'],t['schemeSha256'])
  result=inspect_fragment(e,ft,fc,[group[0]['roomId']]);self.assertEqual(result['completeFirstVisitCoverage'],'pending_connections')
 def test_room_first_preparation_only_writes_data_and_cannot_claim_missing_mesh_pass(self):
  b,t,c=self.fixture();observe=next(ch for ch in c['chapters'] if ch['phase']=='observe');observe['candidatePoses']=[{'point':t['frames'][markers(t)[observe['from']]]['pointMm'],'yawDegrees':0,'panDegrees':10,'pitchDegrees':-10}]
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)
   for name,value in [('bundle',b),('seedTour',t),('seedConfig',c)]: (p/(name+'.json')).write_text(json.dumps(value))
   job={name:str(p/(name+'.json')) for name in ('bundle','seedTour','seedConfig')};job['roomFirst']={'maximumMeshCandidatesPerRoom':2}
   prepare(job,p/'out');report=summarize(p/'out')
   self.assertFalse(any((p/'out').rglob('*.html')));self.assertFalse(any((p/'out').rglob('*.mp4')))
   self.assertFalse(report[0]['qualifiedObservationFragments']);self.assertEqual(report[0]['meshValidation'],'incomplete')
   with self.assertRaisesRegex(ValueError,'Fresh'):prepare(job,p/'out')

if __name__=='__main__':unittest.main()

class FragmentConnectionTests(unittest.TestCase):
 def test_frozen_window_rejects_any_changed_viewing_frame_count(self):
  x=ContractTests();x.setUp();e=JointPlanner(x.b,x.t,x.c,{})
  choices={ch['name']:e.baseline(ch) for _,ch in e.obs};ch=e.obs[0][1]
  fs=copy.deepcopy(x.t['frames'][e.m[ch['from']]:e.m[ch['to']]+1])
  with self.assertRaisesRegex(ValueError,'locked viewing frames'):e.rebuild(choices,{'closingView':'seed'},{ch['from']:fs[:-1]})
 def test_missing_qualified_room_stops_before_assembling_a_timeline(self):
  from tour_fragment_connections import connect
  x=ContractTests();x.setUp()
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)
   for name,value in [('bundle',x.b),('seedTour',x.t),('seedConfig',x.c)]: (p/(name+'.json')).write_text(json.dumps(value))
   (p/'qualification.json').write_text(json.dumps({'rooms':[{'roomId':'room','candidates':[]}]}))
   result=connect({name:str(p/(name+'.json')) for name in ('bundle','seedTour','seedConfig')},p/'qualification.json',p/'out')
   self.assertEqual(result['status'],'room_qualification_blocked');self.assertFalse((p/'out/tour.json').exists());self.assertFalse(any((p/'out').rglob('*.html')))
 def test_endpoint_diversity_precedes_minor_pitch_variants(self):
  from tour_fragment_connections import pick_nodes
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);candidates=[]
   for i in range(5):
    d=p/str(i);d.mkdir();f={'pointMm':[0 if i<4 else 1000,0],'yawRadians':0,'pitchRadians':i*.1}
    (d/'tour.json').write_text(json.dumps({'frames':[f,f]}));(d/'config.json').write_text('{}');candidates.append({'qualifiedObservationFragment':True,'directory':str(d)})
   nodes=pick_nodes({'rooms':[{'roomId':'room','candidates':candidates}]},2)[0][1]
   self.assertEqual([n['start']['pointMm'][0] for n in nodes],[0,1000])
