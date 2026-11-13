import unittest,copy
from floor_boundaries import normalize_floor_boundaries,signed_area,wall_rects
from lighting_checks import inside

def fixture(poly=None):
 return {'model':{'footprint':[[0,0],[1000,0],[1000,1000],[0,1000]],'rooms':[{'id':'r','poly':poly or [[60,60],[940,60],[940,940],[60,940]]}]},'initialState':{'walls':[{'id':'n','a':[0,0],'b':[1000,0],'t':100,'opens':[]},{'id':'e','a':[1000,0],'b':[1000,1000],'t':100,'opens':[]},{'id':'s','a':[0,1000],'b':[1000,1000],'t':100,'opens':[]},{'id':'w','a':[0,0],'b':[0,1000],'t':100,'opens':[]}],'furniture':[{'id':'fixed','cx':200,'cy':300}],'rooms':{'r':{'mat':'wood','floorStyleMode':'fixed'}}}}
class FloorBoundaries(unittest.TestCase):
 def test_small_gap_and_idempotence(self):
  c=fixture();n,r=normalize_floor_boundaries(c);self.assertEqual(abs(signed_area(n['model']['rooms'][0]['poly'])),810000);self.assertGreater(r['gapFilledMm2'],0);self.assertEqual(n,normalize_floor_boundaries(n)[0]);self.assertEqual(c['initialState'],n['initialState'])
 def test_clip_wall_and_outside(self):
  n,r=normalize_floor_boundaries(fixture([[-10,-10],[1010,-10],[1010,1010],[-10,1010]]));self.assertGreater(r['wallOverlapRemovedMm2'],0);self.assertGreater(r['outsideRemovedMm2'],0);self.assertEqual(abs(signed_area(n['model']['rooms'][0]['poly'])),810000)
 def test_large_gap_not_invented(self):
  with self.assertRaisesRegex(ValueError,'Unassigned floor') as hit:normalize_floor_boundaries(fixture([[200,200],[800,200],[800,800],[200,800]]))
  self.assertGreater(hit.exception.report['unresolvedGapMm2'],0);self.assertTrue(hit.exception.report['unresolvedRegions'])
 def test_free_overlap_rejected(self):
  c=fixture();c['model']['rooms'].append({'id':'other','poly':c['model']['rooms'][0]['poly']})
  with self.assertRaisesRegex(ValueError,'Ambiguous'):normalize_floor_boundaries(c)
 def test_doors_remain_passable(self):
  c=fixture([[50,50],[450,50],[450,950],[50,950]]);c['model']['rooms'].append({'id':'right','poly':[[550,50],[950,50],[950,950],[550,950]]});c['initialState']['walls'].append({'id':'divider','a':[500,0],'b':[500,1000],'t':100,'opens':[{'kind':'door','at':400,'width':200}]});c['model']['floorConnections']=[{'id':'dl','materialRoomId':'r','poly':[[450,400],[500,400],[500,600],[450,600]]},{'id':'dr','materialRoomId':'right','poly':[[500,400],[550,400],[550,600],[500,600]]}];n,r=normalize_floor_boundaries(c);self.assertTrue(any(inside([490,500],x['poly']) for x in n['model']['rooms']));self.assertTrue(any(inside([510,500],x['poly']) for x in n['model']['rooms']));self.assertEqual(n['initialState'],c['initialState'])
 def test_compatibility_exception(self):
  c=fixture();c['floorBoundaryPolicy']={'enabled':False};n,r=normalize_floor_boundaries(c);self.assertEqual(n,c);self.assertEqual(r['status'],'disabled')
 def test_zero_sill_is_open_at_floor(self):
  c=fixture();c['initialState']['walls'][0]['opens']=[{'kind':'window','at':400,'width':200,'sillHeight':0}];rects=wall_rects(c['initialState']['walls']);self.assertFalse(any(a<500<b and y<0<z for a,y,b,z in rects))
 def test_unequal_junction_matches_rendered_wall_caps(self):
  walls=[{'id':'v','a':[3220,7000],'b':[3220,9580],'t':220,'opens':[]},{'id':'h','a':[3220,9580],'b':[4660,9580],'t':240,'opens':[]}]
  from floor_connection_checks import solid_wall_rects
  self.assertEqual(wall_rects(walls),solid_wall_rects(walls));self.assertFalse(any(a<3105<b and y<9600<z for a,y,b,z in wall_rects(walls)))
 def retained_fixture(self):
  c=fixture([[50,50],[850,50],[850,950],[50,950]])
  c['model']['footprint']=[[0,0],[960,0],[960,1000],[0,1000]]
  c['initialState']['walls'][1]={'id':'divider','a':[900,0],'b':[900,1000],'t':100,'opens':[]}
  c['model']['floorConnections']=[{'id':'edge','materialRoomId':'r','poly':[[950,50],[960,50],[960,950],[950,950]]}]
  c['floorBoundaryPolicy']={'retainConnections':[{'id':'edge','maximumWidthMm':10,'reason':'Source-defined exterior finish strip, separate from usable floor'}]}
  return c
 def test_explicit_finish_strip_is_not_usable_room(self):
  c=self.retained_fixture();n,r=normalize_floor_boundaries(c)
  self.assertEqual(c['initialState'],n['initialState']);self.assertEqual(c['model']['footprint'],n['model']['footprint'])
  self.assertEqual(n['model']['floorConnections'],c['model']['floorConnections']);self.assertFalse(inside([955,500],n['model']['rooms'][0]['poly']))
  self.assertEqual(r['retainedConnections'][0]['areaMm2'],9000);self.assertEqual(n,normalize_floor_boundaries(n)[0])
 def test_retained_strip_cannot_hide_wall_overlap(self):
  c=self.retained_fixture();c['model']['floorConnections'][0]['poly']=[[945,50],[955,50],[955,950],[945,950]]
  with self.assertRaisesRegex(ValueError,'Retained finish connection overlaps'):normalize_floor_boundaries(c)
 def test_retained_strip_requires_identity_reason_and_width(self):
  for patch in [{'id':'missing'},{'reason':''},{'maximumWidthMm':5},{'maximumWidthMm':float('nan')}]:
   c=self.retained_fixture();c['floorBoundaryPolicy']['retainConnections'][0].update(patch)
   with self.assertRaises(ValueError):normalize_floor_boundaries(c)
 def test_retained_strip_does_not_waive_unassigned_floor(self):
  c=self.retained_fixture();c['model']['rooms'][0]['poly']=[[200,200],[700,200],[700,800],[200,800]]
  with self.assertRaisesRegex(ValueError,'Unassigned floor'):normalize_floor_boundaries(c)
if __name__=='__main__':unittest.main()
