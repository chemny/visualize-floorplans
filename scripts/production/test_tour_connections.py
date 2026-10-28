import math, unittest
from refine_tour_connections import refine,wall_risk
from design_homeowner_tour import design
from tour_workflow import markers

class ConnectionTests(unittest.TestCase):
 def test_wall_risk_counts_duration_and_longest_run(self):
  class Wall:
   walls=[([500,-3000],[500,3000],50)]
   leaves=[]
  frames=[{'pointMm':[0,0],'yawRadians':0} for _ in range(5)]
  r=wall_risk(frames,Wall(),10)
  self.assertEqual(r['nearWallSeconds'],.5);self.assertEqual(r['longestNearWallSeconds'],.5)
 def test_only_selected_transit_can_change_and_room_frames_are_preserved(self):
  bundle={'schemeSha256':'test','model':{'footprint':[[0,0],[4000,0],[4000,4000],[0,4000]],'rooms':[{'id':'room','poly':[[100,100],[3900,100],[3900,3900],[100,3900]]}]},'state':{'walls':[{'id':'w','a':[4000,0],'b':[4000,4000],'t':100,'opens':[{'id':'entry','kind':'door','at':1500,'width':1000,'swing':-1,'angle':90,'hingeEnd':'start'}]}],'furniture':[{'id':'sofa','type':'sofa','cx':1200,'cy':2000,'w':1000,'d':600,'rot':0}]}}
  brief={'schema':'homeowner-design-brief/1','coveragePolicy':{'enabled':False},'tourMode':'full_tour','entranceOpeningId':'entry','startPoint':[4500,2000],'maximumSeconds':60,'rooms':[{'roomId':'room','name':'Room','subjectId':'sofa','targetMm':[1200,2000,1000],'candidatePoints':[[2800,2000]],'viewSeconds':2,'viewPurpose':'View room','tourRole':'public','observationPanDegrees':10}],'choreographyPolicy':{'maximumTransitFraction':1}}
  tour,config,_=design(bundle,brief);ch=config['chapters'][-1]
  new,report=refine(bundle,tour,config,{'entranceOpeningId':'entry','chapters':[ch['name']]},{'excessTurnPerStepWeight':30})
  self.assertTrue(report['observationFramesPreserved']);self.assertEqual(tour['frames'][0]['pointMm'],new['frames'][-1]['pointMm'])
  a,b=markers(tour),markers(new)
  observe=config['chapters'][1]
  self.assertEqual(a[observe['to']]-a[observe['from']],b[observe['to']]-b[observe['from']])
  with self.assertRaisesRegex(ValueError,'Only pure transit'):
   refine(bundle,tour,config,{'entranceOpeningId':'entry','chapters':[observe['name']]},{})
if __name__=='__main__':unittest.main()
