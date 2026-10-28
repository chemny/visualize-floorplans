import copy, hashlib, json, tempfile, unittest
from pathlib import Path
from door_checks import door_leaves, signature, sweep_conflicts, audit_source_doors, is_closed
from plan_route import Planner

class DoorChecks(unittest.TestCase):
 def setUp(self):
  self.w={'id':'W','a':[0,0],'b':[0,2000],'t':120,'opens':[{'id':'D','kind':'door','at':200,'width':1200,'swing':-1,'angle':90}]}
  self.s={'walls':[self.w],'furniture':[],'doorStyles':{'D':{'doorModel':'double','leaves':2}}}
 def opening(self):return {**self.w['opens'][0],**self.s['doorStyles']['D']}
 def test_two_independent_hinges(self):
  a,b=door_leaves(self.w,self.opening());self.assertEqual([a['side'],b['side']],['start','end']);self.assertEqual(a['lengthMm'],575);self.assertEqual(b['lengthMm'],575);self.assertEqual(a['hinge'],[75,225]);self.assertEqual(b['hinge'],[75,1375])
 def test_unequal_and_reversed(self):
  o={**self.opening(),'leafRatio':.3};a,b=door_leaves(self.w,o);self.assertEqual([a['lengthMm'],b['lengthMm']],[335,815]);w={**self.w,'a':[0,2000],'b':[0,0]};self.assertLess(door_leaves(w,o)[0]['tip'][0],0)
 def test_second_leaf_collision(self):
  self.s['furniture']=[{'id':'f','type':'cabinet','cx':500,'cy':1350,'w':200,'d':100}];r=sweep_conflicts(self.s);self.assertEqual({c['leafSide'] for c in r['conflicts']},{'end'})
 def test_removed_and_sliding(self):
  self.assertEqual(door_leaves(self.w,{**self.opening(),'leafRemoved':True}),[]);self.assertEqual(door_leaves(self.w,{**self.opening(),'kind':'sliding'}),[])
 def test_closed(self):
  a,b=door_leaves(self.w,self.opening(),True);self.assertAlmostEqual(a['tip'][0],75);self.assertAlmostEqual(b['tip'][0],75);self.assertTrue(is_closed({'doors':{'W:D':False}},self.w,self.opening(),1))
 def test_planner(self):
  b={'state':self.s,'model':{'rooms':[],'footprint':[[-100,-100],[2000,-100],[2000,2200],[-100,2200]]}};p=Planner(b,{});self.assertEqual(len(p.vision_leaves),2);self.assertEqual(len(p.leaves),6);self.assertTrue(p.blocked([500,1375]));self.s['doorStyles']['D']['leafRemoved']=True;self.assertEqual(len(Planner(b,{}).leaves),0)
 def test_hidden(self):self.assertEqual(door_leaves(self.w,{**self.opening(),'doorModel':'hidden','leaves':1})[0]['hinge'][0],40)
 def test_source_evidence(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'source.bin';p.write_bytes(b'original');r={'openingId':'D',**signature(self.opening()),'reviewedBy':'tester','observation':'two opposing leaves seen','sourceArtifact':{'path':'source.bin','sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'crop':[0,0,50,50]}}
   self.assertEqual(audit_source_doors(self.s,[r],d)['status'],'pass')
   for field,value in [('leafCount',1),('hingeEnds',['start']),('doorModel','single')]:
    bad=copy.deepcopy(r);bad[field]=value
    with self.assertRaises(ValueError):audit_source_doors(self.s,[bad],d)
   with self.assertRaises(ValueError):audit_source_doors(self.s,[],d)
   p.write_bytes(b'changed')
   with self.assertRaises(ValueError):audit_source_doors(self.s,[r],d)
 def test_build_rejects_source_mismatch(self):
  from h5 import build
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'case.json';p.write_text('{}')
   with patch('floor_boundaries.normalize_floor_boundaries',return_value=({'model':{'rooms':[]},'initialState':self.s}, {'status':'isolated_fixture'})), patch('h5.validate_case',return_value={'model':{'rooms':[]},'initialState':self.s,'doorSourceReview':[]}):
    with self.assertRaisesRegex(ValueError,'cover each opening'):build(p,Path(d)/'out.html')
   self.assertFalse((Path(d)/'out.html').exists())
 def test_recognition_count_is_required(self):
  import sys
  sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
  from validate_recognition import validate_recognition, RecognitionError
  sample=Path(__file__).resolve().parents[2]/'assets/sample-recognition.json'
  data=json.loads(sample.read_text());validate_recognition(data)
  door=next(e for e in data['elements'] if e['kind']=='entrance_door')
  door['leaf_count']=2
  with self.assertRaises(RecognitionError):validate_recognition(data)
  door['door_model']='double';door['hinge_ends']=['start','end'];validate_recognition(data)
  del door['source_observation']
  with self.assertRaises(RecognitionError):validate_recognition(data)
 def test_invalid_ratio(self):
  with self.assertRaises(ValueError):door_leaves(self.w,{**self.opening(),'leafRatio':.9})
if __name__=='__main__':unittest.main()
