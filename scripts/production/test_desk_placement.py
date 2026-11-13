import unittest,copy
from desk_placement import review_desks
class DeskPlacementTests(unittest.TestCase):
 def case(self):return {'model':{'rooms':[{'id':'r','poly':[[0,0],[4000,0],[4000,4000],[0,4000]]}]},'initialState':{'walls':[{'id':'w','a':[0,0],'b':[4000,0],'t':100,'opens':[{'id':'d','kind':'door','at':1500,'width':900}]}],'furniture':[{'id':'desk','type':'desk','roomId':'r','cx':2000,'cy':2200,'w':900,'d':550,'rot':0}]},'deskPlacementPolicy':{'minimumOpeningDistanceMm':900}}
 def test_near_entry_rejected_far_passes(self):
  c=self.case();self.assertEqual(review_desks(c)['status'],'pass');c['initialState']['furniture'][0]['cy']=500;self.assertEqual(review_desks(c)['status'],'fail')
 def test_policy_not_implicit_and_bad_values_reject(self):
  c=self.case();c.pop('deskPlacementPolicy');self.assertEqual(review_desks(c)['status'],'not_provided')
  for v in [-1,True,float('nan')]:
   c=self.case();c['deskPlacementPolicy']['minimumOpeningDistanceMm']=v
   with self.assertRaises(ValueError):review_desks(c)
 def test_neighbour_room_door_not_misidentified(self):
  c=self.case();c['initialState']['walls'].append({'id':'other','a':[5000,0],'b':[5000,4000],'t':100,'opens':[{'kind':'door','at':1500,'width':900}]});self.assertEqual(len(review_desks(c)['desks'][0]['openingDistances']),1)
 def test_input_unchanged_and_rotated_desk_checked(self):
  c=self.case();c['initialState']['furniture'][0]['rot']=90;before=copy.deepcopy(c);self.assertEqual(review_desks(c)['status'],'pass');self.assertEqual(c,before)
