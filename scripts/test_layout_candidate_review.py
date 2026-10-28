import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from design_contract import digest
from layout_review import artifact
from layout_candidate_review import compare_candidates,DIMENSIONS,HARD_CHECKS

class CandidateReviewTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name)
  self.state={'walls':[],'doorStyles':{},'rooms':{'R':{}},'style':'test','furniture':[{'id':'storage','w':1400},{'id':'other','w':500}]}
  self.old=copy.deepcopy(self.state);self.old['furniture'][0]['w']=1000
  self.write('intent.txt','Synthetic comparison scope');self.write('evidence.txt','Synthetic observations, not an actual apartment');self.write('delivery.txt','Close door before taking items')
  cs=[]
  for name,state in [('old',self.old),('current',self.state)]:
   self.write(name+'.json',{'scheme':state})
   cs.append({'id':name,'snapshot':self.ref(name+'.json'),'stateSha256':digest(state),'hardChecks':{k:{'status':'pass','finding':'Checked declared function/use/access','evidence':[self.ref('evidence.txt')]} for k in HARD_CHECKS},'dimensions':{k:{'status':'assessed','benefit':'Specific observed advantage','limitation':'Specific cost or unchanged condition','evidence':[self.ref('evidence.txt')]}for k in DIMENSIONS}})
  self.record={'stateSha256':digest(self.state),'candidateComparison':{'contextStateSha256':digest(self.state),'mode':'retrospective_validation','scope':'synthetic storage assembly only','intentEvidence':self.ref('intent.txt'),'allowedChangedIds':['storage'],'preservedFields':['walls','doorStyles','rooms','style'],'candidates':cs,'selection':{'candidateId':'current','reason':'Function complete; choose usable storage with an acknowledged cost','alternatives':[{'candidateId':'old','reason':'Less storage but simpler access','preferredDimensions':['convenience']}],'tradeoffs':[{'dimension':'convenience','cost':'Door must close first','response':'Restrict use and disclose'}],'conditions':[{'text':'Close door before taking items','artifact':self.ref('delivery.txt')}]}}}
 def write(self,p,x):(self.base/p).write_text(x if isinstance(x,str)else json.dumps(x))
 def ref(self,p):return {'path':p,'sha256':hashlib.sha256((self.base/p).read_bytes()).hexdigest()}
 def run_check(self):return compare_candidates(self.state,self.record,self.base,artifact)
 def test_valid(self):self.assertEqual(self.run_check()['status'],'reviewed_with_tradeoffs')
 def test_legacy_missing(self):self.assertEqual(compare_candidates(self.state,{},self.base,artifact)['status'],'not_provided')
 def test_only_collision_evidence_not_six_dimensions(self):
  self.record['candidateComparison']['candidates'][1]['dimensions']={}
  with self.assertRaisesRegex(ValueError,'six'):self.run_check()
 def test_duplicate_layouts_not_two_options(self):
  c=self.record['candidateComparison']['candidates'][0];c['snapshot']=self.ref('current.json');c['stateSha256']=digest(self.state)
  with self.assertRaisesRegex(ValueError,'Duplicate layouts'):self.run_check()
 def test_missing_alternative(self):
  self.record['candidateComparison']['candidates'].pop(0)
  with self.assertRaisesRegex(ValueError,'At least two'):self.run_check()
 def test_aesthetic_gain_cannot_offset_hard_failure(self):
  self.record['candidateComparison']['candidates'][1]['hardChecks']['required_access']['status']='fail'
  with self.assertRaisesRegex(ValueError,'cannot offset'):self.run_check()
 def test_unverified_hard_check_cannot_be_called_pass(self):
  self.record['candidateComparison']['candidates'][1]['hardChecks']['safe_operation']['status']='unverified'
  with self.assertRaisesRegex(ValueError,'cannot offset'):self.run_check()
 def test_design_mode_needs_two_viable_candidates(self):
  b=self.record['candidateComparison'];b['mode']='design_comparison';b['candidates'][0]['hardChecks']['required_functions']['status']='fail'
  with self.assertRaisesRegex(ValueError,'two viable'):self.run_check()
 def test_missing_tradeoff(self):
  self.record['candidateComparison']['selection']['tradeoffs']=[]
  with self.assertRaisesRegex(ValueError,'trade-offs'):self.run_check()
 def test_missing_rejection_reason(self):
  self.record['candidateComparison']['selection']['alternatives']=[{'candidateId':'old','reason':'','preferredDimensions':['maintenance']}]
  with self.assertRaisesRegex(ValueError,'reasoning'):self.run_check()
 def test_scope_change_rejected(self):
  self.old['furniture'][1]['w']=600;self.write('old.json',self.old);c=self.record['candidateComparison']['candidates'][0];c['snapshot']=self.ref('old.json');c['stateSha256']=digest(self.old)
  with self.assertRaisesRegex(ValueError,'outside comparison scope'):self.run_check()
 def test_stale_context(self):
  self.record['candidateComparison']['contextStateSha256']='old'
  with self.assertRaisesRegex(ValueError,'stale'):self.run_check()
 def test_selected_is_not_current(self):
  self.record['candidateComparison']['selection']['candidateId']='old'
  with self.assertRaisesRegex(ValueError,'not the reviewed'):self.run_check()
 def test_condition_omitted_in_delivery(self):
  self.write('delivery.txt','Everything usable');self.record['candidateComparison']['selection']['conditions'][0]['artifact']=self.ref('delivery.txt')
  with self.assertRaisesRegex(ValueError,'absent'):self.run_check()
 def test_only_good_sides_rejected(self):
  self.record['candidateComparison']['candidates'][1]['dimensions']['space_use']['limitation']=''
  with self.assertRaisesRegex(ValueError,'benefits and limitations'):self.run_check()
 def test_restricted_state_ignored_in_selection(self):
  self.record['operationMatrix']={'scenarios':[{'id':'open-door','expected':'blocked'}]}
  with self.assertRaisesRegex(ValueError,'restricted'):self.run_check()

if __name__=='__main__':unittest.main()
