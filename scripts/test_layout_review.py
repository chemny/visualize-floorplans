import copy,hashlib,json,tempfile,unittest,sys
from pathlib import Path
from design_contract import digest
from layout_review import review

class LayoutReviewTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name)
  self.state={'walls':[],'doorStyles':{},'furniture':[
   dict(id='bed',type='bed',roomId='room',cx=3000,cy=3000,w=1600,d=2200,h=1000,rot=0),
   dict(id='wardrobe',type='wardrobe',roomId='room',cx=500,cy=3000,w=2400,d=600,h=2300,rot=90),
   dict(id='sofa',type='sofa',roomId='room',cx=5000,cy=5000,w=2200,d=800,h=800,rot=0),
   dict(id='table',type='coffeetable',roomId='room',cx=5000,cy=6500,w=1000,d=500,h=400,rot=0),
   *[dict(id='c'+str(i),type='chair',roomId='room',cx=7000+i*500,cy=8000,w=400,d=400,h=800,rot=0) for i in range(4)]]}
  self.case={'model':{'rooms':[{'id':'room'}]},'initialState':self.state}
  (self.base/'evidence.txt').write_text('Synthetic observation evidence; not an actual apartment')
  self.ref=lambda p:{'path':p,'sha256':hashlib.sha256((self.base/p).read_bytes()).hexdigest()}
  obs={'status':'observed_clear','observation':'Synthetic fixture observed, function and usable relationships reviewed','evidence':[self.ref('evidence.txt')]}
  (self.base/'baseline.json').write_text(json.dumps(self.state))
  self.record={'schema':'layout-review/1','stateSha256':digest(self.state),'rooms':[{'id':'room','purpose':'synthetic multipurpose room','requirements':[{'types':['bed'],'minimum':1},{'types':['chair'],'minimum':4},{'types':['desk'],'minimum':0,'maximum':0}],'reasonableness':copy.deepcopy(obs)}],
   'groups':[{'id':'living','roomId':'room','members':['sofa','table'],'composition':copy.deepcopy(obs),'useStates':[{'name':'seated and passing',**copy.deepcopy(obs)}],'relations':[{'kind':'aligned','ids':['sofa','table'],'axis':'x','toleranceMm':2},{'kind':'gap','ids':['sofa','table'],'axis':'y','minimumMm':500,'maximumMm':1000}]}],
   'revision':{'baseline':self.ref('baseline.json'),'intentEvidence':self.ref('evidence.txt'),'allowedChangedIds':['wardrobe','split','sofa','table','bed','c0','c1','c2','c3','desk'],'requirements':[{'kind':'inventory','roomId':'room','types':['wardrobe'],'expected':1,'d':600},{'kind':'pose','ids':['wardrobe'],'values':{'w':2400,'rot':90}}]}}
 def run_review(self):
  self.record['stateSha256']=digest(self.state);return review(self.case,self.record,self.base)
 def test_valid(self):self.assertEqual(self.run_review()['status'],'pass')
 def test_split_cabinet_rejected(self):
  f=copy.deepcopy(self.state['furniture'][1]);f.update(id='split',d=350);self.state['furniture'].append(f)
  with self.assertRaisesRegex(ValueError,'inventory'):self.run_review()
 def test_uniform_depth_relation(self):
  self.record['revision']['requirements']=[{'kind':'uniform_depth','ids':['wardrobe','table'],'toleranceMm':0}]
  with self.assertRaisesRegex(ValueError,'Depth'):self.run_review()
 def test_missing_real_bed(self):
  self.state['furniture'][0]['type']='sofabed'
  with self.assertRaisesRegex(ValueError,'function'):self.run_review()
 def test_two_chairs_for_four_places(self):
  self.state['furniture']=self.state['furniture'][:-2]
  with self.assertRaisesRegex(ValueError,'function'):self.run_review()
 def test_unrequested_desk(self):
  f=copy.deepcopy(self.state['furniture'][0]);f.update(id='desk',type='desk');self.state['furniture'].append(f)
  with self.assertRaisesRegex(ValueError,'surplus'):self.run_review()
 def test_group_axis(self):
  self.state['furniture'][3]['cx']+=250
  with self.assertRaisesRegex(ValueError,'misaligned'):self.run_review()
 def test_wrong_table_size(self):
  self.record['revision']['requirements'].append({'kind':'pose','ids':['table'],'values':{'w':1200,'d':700}})
  with self.assertRaisesRegex(ValueError,'field'):self.run_review()
 def test_blocked_fridge_or_cabinet_use_zone(self):
  self.record['groups'][0]['relations'].append({'kind':'operating_zone','ids':['wardrobe'],'rect':[0,2500,1000,3500],'heightLimitMm':1200})
  with self.assertRaisesRegex(ValueError,'blocked'):self.run_review()
 def test_static_clearance_does_not_pass_pending_use(self):
  self.record['groups'][0]['useStates'][0]['status']='unverified'
  with self.assertRaisesRegex(ValueError,'unresolved'):self.run_review()
 def test_unrequested_bed_change(self):
  self.record['revision']['allowedChangedIds']=['wardrobe'];self.state['furniture'][0]['cx']+=100
  with self.assertRaisesRegex(ValueError,'Unrequested'):self.run_review()
 def test_wrong_rotation(self):
  self.state['furniture'][1]['rot']=0
  with self.assertRaisesRegex(ValueError,'field'):self.run_review()
 def test_stale_state(self):
  self.state['furniture'][0]['cx']+=100
  with self.assertRaisesRegex(ValueError,'stale'):review(self.case,self.record,self.base)
 def test_stale_evidence(self):
  (self.base/'evidence.txt').write_text('modified')
  with self.assertRaisesRegex(ValueError,'changed'):self.run_review()
 def test_missing_group_or_room(self):
  self.record['groups']=[]
  with self.assertRaisesRegex(ValueError,'missing group'):self.run_review()
 def test_mismatch_blocks_real_build_before_write(self):
  sys.path.insert(0,str(Path(__file__).parent/'production'));import h5
  from unittest.mock import patch
  self.record['revision']['requirements'][0]['expected']=2
  (self.base/'review.json').write_text(json.dumps(self.record));case={**self.case,'layoutReview':self.ref('review.json')}
  (self.base/'case.json').write_text('{}')
  with patch('floor_boundaries.normalize_floor_boundaries',return_value=(case, {'status':'isolated_fixture'})), patch.object(h5,'validate_case',return_value=case):
   with self.assertRaisesRegex(ValueError,'inventory'):h5.build(self.base/'case.json',self.base/'out.html')
  self.assertFalse((self.base/'out.html').exists())
 def test_required_candidate_comparison_cannot_be_skipped(self):
  self.record['requiredChecks']=['candidateComparisonCheck']
  with self.assertRaisesRegex(ValueError,'Required candidate'):self.run_review()
 def test_candidate_failure_blocks_existing_build(self):
  sys.path.insert(0,str(Path(__file__).parent/'production'));import h5
  from unittest.mock import patch
  self.record['candidateComparison']={'contextStateSha256':digest(self.state),'mode':'design_comparison','intentEvidence':self.ref('evidence.txt'),'scope':'synthetic group','candidates':[]}
  (self.base/'review.json').write_text(json.dumps(self.record));case={**self.case,'layoutReview':self.ref('review.json')};(self.base/'case.json').write_text('{}')
  with patch('floor_boundaries.normalize_floor_boundaries',return_value=(case, {'status':'isolated_fixture'})), patch.object(h5,'validate_case',return_value=case):
   with self.assertRaisesRegex(ValueError,'two actual'):h5.build(self.base/'case.json',self.base/'out.html')
  self.assertFalse((self.base/'out.html').exists())
if __name__=='__main__':unittest.main()
