import unittest
from tour_observation_points import validate,inspect

class ObservationPointTests(unittest.TestCase):
 def test_real_room_count_and_second_reason(self):
  r={'roomId':'room','viewSeconds':2}
  with self.assertRaisesRegex(ValueError,'Second observation'):validate([r,r])
  second={**r,'secondPointReason':'First station cannot show the screened work area'}
  validate([r,second])
  with self.assertRaisesRegex(ValueError,'At most two'):validate([r,second,second])
  with self.assertRaisesRegex(ValueError,'time exceeds'):validate([{**r,'viewSeconds':3.1}])
 def test_final_duration_and_stillness_are_rechecked(self):
  policy=validate([{'roomId':'r','viewSeconds':2}])
  tour={'fps':10,'frames':[{'pointMm':[0,0],'yawRadians':0} for i in range(41)],'visits':[{'name':'a','frame':0},{'name':'b','frame':40}]}
  config={'observationPointPolicy':policy,'chapters':[{'phase':'observe','roomId':'r','from':'a','to':'b'}]}
  codes={i['code'] for i in inspect(tour,config)['issues']}
  self.assertEqual(codes,{'observation_point_over_budget','stationary_camera_hold'})
  for i,f in enumerate(tour['frames']):f['yawRadians']=i*.01
  config['chapters'][0]['to']='c';tour['visits'].append({'name':'c','frame':20})
  self.assertFalse(inspect(tour,config)['issues'])
 def test_navigation_vertices_do_not_count_as_stations(self):
  policy=validate([{'roomId':'r','viewSeconds':2}])
  t={'fps':1,'frames':[{'pointMm':[i,0],'yawRadians':i*.1} for i in range(4)],'visits':[{'name':'a','frame':0},{'name':'b','frame':1},{'name':'c','frame':3}]}
  c={'observationPointPolicy':policy,'chapters':[{'phase':'transit','from':'a','to':'b'},{'phase':'observe','movingView':True,'from':'b','to':'c','roomId':'r'}]}
  self.assertEqual(inspect(t,c)['countsByRoom'],{})
if __name__=='__main__':unittest.main()
