import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'production'))
from h5 import validate_case
from synthetic_cases import fixture_cases
from floor_connection_checks import check_floor_connections

class FloorConnectionTests(unittest.TestCase):
    def setUp(self):
        self.case=fixture_cases()[0]
        self.case['model']['rooms'][0]['poly']=[[300,120],[2940,120],[2940,3880],[300,3880]]
        self.case['model']['floorConnections']=[{'id':'band','poly':[[120,120],[300,120],[300,3880],[120,3880]],'materialRoomId':'left'}]
    def test_explicit_band_preserves_room_partition(self):
        before=copy.deepcopy(self.case['model']['rooms']);validate_case(self.case)
        self.assertEqual(self.case['model']['rooms'],before)
    def test_room_overlap_rejected(self):
        self.case['model']['floorConnections'][0]['poly'][1][0]=400
        self.case['model']['floorConnections'][0]['poly'][2][0]=400
        with self.assertRaisesRegex(ValueError,'overlaps room'):validate_case(self.case)
    def test_overlapping_patches_rejected(self):
        extra=copy.deepcopy(self.case['model']['floorConnections'][0]);extra['id']='second';self.case['model']['floorConnections'].append(extra)
        with self.assertRaisesRegex(ValueError,'connections overlap'):validate_case(self.case)
    def test_outside_footprint_rejected(self):
        self.case['model']['floorConnections'][0]['poly']=[[-500,100],[-300,100],[-300,300],[-500,300]]
        with self.assertRaisesRegex(ValueError,'outside footprint'):validate_case(self.case)
    def test_wall_overlap_rejected(self):
        self.case['model']['floorConnections'][0]['poly']=[[0,120],[40,120],[40,500],[0,500]]
        with self.assertRaisesRegex(ValueError,'overlaps wall'):validate_case(self.case)
    def test_unknown_material_owner_rejected(self):
        self.case['model']['floorConnections'][0]['materialRoomId']='missing'
        with self.assertRaisesRegex(ValueError,'existing material room'):validate_case(self.case)
    def doorway(self,kind='door',vertical=False,reverse=False):
        model={'footprint':[[0,0],[2000,0],[2000,2000],[0,2000]],'rooms':[],
               'floorConnections':[{'id':'threshold','poly':[[700,950],[1300,950],[1300,1050],[700,1050]]}]}
        wall={'a':[0,1000],'b':[2000,1000],'t':100,
              'opens':[{'at':700,'width':600,'kind':kind}]}
        if vertical:
            wall['a']=wall['a'][::-1];wall['b']=wall['b'][::-1]
            model['floorConnections'][0]['poly']=[p[::-1] for p in model['floorConnections'][0]['poly']]
        if reverse:wall['a'],wall['b']=wall['b'],wall['a']
        return model,wall
    def test_door_and_slider_thresholds_allowed_both_axes(self):
        for kind in ('door','sliding'):
            for vertical in (False,True):
                for reverse in (False,True):
                    m,w=self.doorway(kind,vertical,reverse);check_floor_connections(m,[w])
    def test_window_does_not_remove_wall_at_floor(self):
        m,w=self.doorway('window')
        with self.assertRaisesRegex(ValueError,'overlaps wall'):check_floor_connections(m,[w])
    def test_patch_crossing_door_jamb_rejected(self):
        m,w=self.doorway();m['floorConnections'][0]['poly'][0][0]=690
        m['floorConnections'][0]['poly'][3][0]=690
        with self.assertRaisesRegex(ValueError,'overlaps wall'):check_floor_connections(m,[w])
    def test_crossing_wall_still_blocks_door_threshold(self):
        m,w=self.doorway();other={'a':[1000,0],'b':[1000,2000],'t':100,'opens':[]}
        with self.assertRaisesRegex(ValueError,'overlaps wall'):check_floor_connections(m,[w,other])
if __name__=='__main__':unittest.main()
