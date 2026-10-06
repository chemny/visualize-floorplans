import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'production'))
from h5 import validate_case
from synthetic_cases import fixture_cases

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
if __name__=='__main__':unittest.main()
