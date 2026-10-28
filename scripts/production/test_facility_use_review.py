import copy,unittest
from facility_use_review import review_facilities,rect_overlap

def fixture():
 f={'id':'S','type':'shower','cx':2000,'cy':1500,'w':900,'d':900,'h':2100,'rot':0,'showerDoor':{'type':'hinged','hinge':'left','angle':85,'open':0}}
 return {'model':{'rooms':[{'id':'r','poly':[[0,0],[5000,0],[5000,5000],[0,5000]]}]},'initialState':{'walls':[],'furniture':[f]},'facilityUsePolicy':{'required':True,'scope':['S'],'facilities':[{'id':'S','from':[3500,3200],'operator':[2900,2300],'usePoint':[2000,1500],'bodyRadiusMm':250}]}}
class FacilityTests(unittest.TestCase):
 def test_complete_shower(self):
  r=review_facilities(fixture());self.assertEqual(r['status'],'pass');self.assertEqual(set(r['facilities'][0]['paths']),{'approach','enter','use_closed','exit','leave'})
 def test_legacy_shape_not_accepted(self):
  c=fixture();c['initialState']['furniture'][0].pop('showerDoor');self.assertEqual(review_facilities(c)['status'],'fail')
 def test_missing_declaration(self):
  c=fixture();c['facilityUsePolicy']['scope'].append('unreviewed');self.assertEqual(review_facilities(c)['status'],'fail')
 def test_motion_conflict(self):
  c=fixture();c['initialState']['furniture'].append({'id':'cab','type':'wardrobe','cx':1600,'cy':2400,'w':200,'d':200});self.assertEqual(review_facilities(c)['status'],'fail')
 def test_operator_in_sweep(self):
  c=fixture();c['facilityUsePolicy']['facilities'][0]['operator']=[2000,2200];self.assertEqual(review_facilities(c)['status'],'fail')
 def test_closed_entry_not_passed_as_exit(self):
  c=fixture();c['initialState']['furniture'][0]['showerDoor']['angle']=25;self.assertEqual(review_facilities(c)['status'],'fail')
 def test_invalid_extension(self):
  c=fixture();c['initialState']['furniture'][0]['type']='vanity';c['facilityUsePolicy']['facilities'][0]['motion']={'type':'front_extension','extensionMm':-10}
  self.assertEqual(review_facilities(c)['status'],'fail')
 def test_invalid_radius(self):
  c=fixture();c['facilityUsePolicy']['facilities'][0]['bodyRadiusMm']=-1;self.assertEqual(review_facilities(c)['status'],'fail')
 def test_missing_policy_pending(self):
  c=fixture();del c['facilityUsePolicy'];self.assertEqual(review_facilities(c)['status'],'not_provided')
 def test_room_slider_privacy_sequence(self):
  c=fixture();c['initialState']['walls']=[{'id':'W','a':[0,3000],'b':[5000,3000],'t':120,'opens':[{'id':'D','kind':'sliding','at':2500,'width':1000,'leaves':1,'slideMount':'wall','slideSide':1,'slideDirection':1,'slideOverlap':20,'slideOpen':1}]}]
  spec=c['facilityUsePolicy']['facilities'][0];spec.update(closeRoomDoor='D',roomDoorOperator=[3000,2400],**{'from':[3500,3600]})
  r=review_facilities(c);self.assertEqual(r['status'],'pass');self.assertIn('enter_room',r['facilities'][0]['paths']);self.assertIn('leave_room',r['facilities'][0]['paths'])
  spec['roomDoorOperator']=[4500,3090];self.assertEqual(review_facilities(c)['status'],'fail')
 def test_rotation_intersection(self):
  a={'cx':0,'cy':0,'w':1000,'d':20,'rot':45};self.assertTrue(rect_overlap(a,{'cx':100,'cy':100,'w':10,'d':10,'rot':0}));self.assertFalse(rect_overlap(a,{'cx':100,'cy':-100,'w':10,'d':10,'rot':0}))
class BuildGateTests(unittest.TestCase):
 def test_required_failure_blocks_html(self):
  import tempfile
  from pathlib import Path
  from unittest.mock import patch
  import h5
  c=fixture();c['initialState']['furniture'][0].pop('showerDoor')
  # The gate fixture deliberately omits floor geometry; that has its own tests.
  with tempfile.TemporaryDirectory() as d,patch.object(h5,'read_snapshot',return_value=(c,'test-input')),patch.object(h5,'validate_case',return_value=c),patch('floor_boundaries.normalize_floor_boundaries',return_value=(c,{'status':'isolated_test'})):
   out=Path(d)/'blocked.html'
   with self.assertRaisesRegex(ValueError,'Facility use review failed'):h5.build('fixture',out)
   self.assertFalse(out.exists());self.assertTrue(out.with_suffix('.facilities.json').exists())
if __name__=='__main__':unittest.main()
