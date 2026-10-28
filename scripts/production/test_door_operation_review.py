import copy,unittest
from door_operation_review import review_doors

def case():
 return {'initialState':{'walls':[{'id':'W','a':[0,0],'b':[4000,0],'t':120,'opens':[{'id':'D','kind':'door','at':1000,'width':900,'height':2100,'hingeEnd':'start','swing':1,'angle':90}]}],'furniture':[]},'model':{'rooms':[]}}
class DoorOperationTest(unittest.TestCase):
 def test_empty_and_missing_paths(self):
  r=review_doors(case());self.assertEqual(r['status'],'pass');self.assertEqual(r['pathStatus'],'not_provided')
 def test_handle_wall_distinct_from_leaf(self):
  c=case();c['initialState']['walls'].append({'id':'receiver','a':[1080,200],'b':[1080,1100],'t':30,'opens':[]});r=review_doors(c)
  self.assertTrue(any(h['part']=='handle' and h.get('wallId')=='receiver' for h in r['doors'][0]['conflicts']))
 def test_furniture_sweep(self):
  c=case();c['initialState']['furniture']=[{'id':'cab','type':'wardrobe','cx':1500,'cy':600,'w':300,'d':300}];self.assertEqual(review_doors(c)['status'],'fail')
 def test_slide_parking(self):
  c=case();c['initialState']['walls'][0]['opens'][0].update(kind='sliding',leaves=1,slideMount='wall',slideSide=1,slideDirection=1,slideOpen=0,slideOverlap=20)
  c['initialState']['furniture']=[{'id':'parking-cab','type':'wardrobe','cx':2300,'cy':90,'w':300,'d':100}]
  r=review_doors(c);self.assertEqual(r['status'],'fail');self.assertTrue(r['doors'][0]['parkingChecked']);self.assertTrue(any(h.get('objectId')=='parking-cab' and h.get('slideOpen',0)>0 for h in r['doors'][0]['conflicts']))
 def test_passage(self):
  c=case();c['initialState']['walls'][0]['opens'][0]['leafRemoved']=True;self.assertEqual(review_doors(c)['doors'][0]['mechanism'],'passage')
 def test_other_door(self):
  c=case();c['initialState']['walls'].append({'id':'W2','a':[0,600],'b':[4000,600],'t':100,'opens':[{'id':'D2','kind':'door','at':1400,'width':900,'swing':-1,'angle':90}]});r=review_doors(c);self.assertTrue(any(h['kind']=='other_door' for row in r['doors'] for h in row['conflicts']))
 def test_required_gate_rejects_missing_path_or_conflict(self):
  import tempfile
  from pathlib import Path
  from unittest.mock import patch
  import h5
  for conflict in (False,True):
   c=case();c['doorLayoutPolicy']={'required':True}
   if conflict:c['initialState']['furniture']=[{'id':'cab','type':'wardrobe','cx':1500,'cy':600,'w':300,'d':300}]
   # This minimal fixture isolates the door gate, not floor reconstruction.
   with tempfile.TemporaryDirectory() as d,patch.object(h5,'read_snapshot',return_value=(c,'test-input')),patch.object(h5,'validate_case',return_value=c),patch('floor_boundaries.normalize_floor_boundaries',return_value=(c,{'status':'isolated_test'})):
    target=Path(d)/'blocked.html'
    with self.assertRaisesRegex(ValueError,'Door operation review failed'):h5.build('fixture.json',target)
    self.assertFalse(target.exists());self.assertTrue(target.with_suffix('.doors.json').exists())
if __name__=='__main__':unittest.main()
