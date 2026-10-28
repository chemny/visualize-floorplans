import copy, math, unittest
from types import SimpleNamespace
from tour_forward_motion import inspect
from tour_contract import inspect as contract_inspect
from tour_pipeline import JointPlanner


class ForwardMotionTests(unittest.TestCase):
    def fixture(self, yaw=0, speed=1., count=25, fps=24):
        t = {'fps': fps, 'frames': [
            {'pointMm': [i*speed*1000/fps, 0], 'yawRadians': math.radians(yaw)} for i in range(count)],
            'visits': [{'name': 'a', 'frame': 0}, {'name': 'b', 'frame': count-1}]}
        return t, {'chapters': [{'name': 'walk', 'from': 'a', 'to': 'b', 'phase': 'transit'}]}

    def test_forward_and_side_glance(self):
        for yaw in (0, 60, 85):
            t, c = self.fixture(yaw)
            self.assertEqual(inspect(t, c)['status'], 'pass')

    def test_backwards_fails_including_observe_label(self):
        t, c = self.fixture(180)
        c['chapters'][0]['phase'] = 'observe'
        r = inspect(t, c)
        self.assertEqual(r['issues'][0]['code'], 'sustained_backward_walking')
        self.assertEqual(r['issues'][0]['seconds'], 1)

    def test_stationary_and_low_speed_not_backward_walking(self):
        for speed in (0, .1, .2):
            t, c = self.fixture(180, speed)
            self.assertFalse(inspect(t, c)['issues'])

    def test_exact_half_second_and_brief_glance(self):
        t, c = self.fixture(180, count=13)
        self.assertFalse(inspect(t, c)['issues'])
        t, c = self.fixture(180, count=14)
        self.assertTrue(inspect(t, c)['issues'])

    def test_wraparound_uses_shortest_midpoint(self):
        t, c = self.fixture()
        for i, f in enumerate(t['frames']):
            f['yawRadians'] = math.radians(359 if i%2 else 1)
        self.assertEqual(inspect(t, c)['status'], 'pass')

    def test_splitting_chapters_does_not_hide_continuous_reverse(self):
        t, c = self.fixture(180)
        t['visits'].insert(1, {'name': 'mid', 'frame': 12})
        c['chapters'] = [{'name': 'one', 'from': 'a', 'to': 'mid'}, {'name': 'two', 'from': 'mid', 'to': 'b'}]
        r = inspect(t, c)
        self.assertEqual(r['issues'][0]['chapters'], ['one', 'two'])

    def test_returning_along_path_is_fine_when_facing_return_direction(self):
        t, c = self.fixture(180)
        for f in t['frames']: f['pointMm'][0] *= -1
        self.assertEqual(inspect(t, c)['status'], 'pass')

    def test_contract_catches_final_backwards_frames(self):
        from test_tour_contract import ContractTests
        x = ContractTests(); x.setUp()
        t = copy.deepcopy(x.t)
        for f in t['frames']: f['yawRadians'] += math.pi
        r = contract_inspect(x.b, t, x.c)
        self.assertEqual(r['checks']['forwardMotion']['status'], 'needs_revision')
        self.assertIn('sustained_backward_walking', [i['code'] for i in r['issues']])

    def test_closing_pose_faces_from_gate_toward_outside_endpoint(self):
        for endpoint in ([200, 500], [-200, 500]):
            p = SimpleNamespace(t={'frames': [{'pointMm': endpoint}]},
                c={'tourContract': {'tourMode': 'full_tour', 'entranceOpeningId': 'door'}},
                b={'state': {'walls': [{'a': [0, 0], 'b': [0, 1000], 'opens': [{'id': 'door', 'at': 300, 'width': 400}]}]}})
            frame = JointPlanner.closing_pose(p)
            self.assertAlmostEqual(math.cos(frame['yawRadians']), 1 if endpoint[0]>0 else -1)

    def test_navigation_does_not_trade_forward_heading_for_clearer_back_wall(self):
        from unittest.mock import patch
        from design_homeowner_tour import navigation_gaze
        dense = [[i*50, 0] for i in range(31)]
        with patch('design_homeowner_tour.clear_distance', side_effect=lambda p, pos, yaw: 2000 if math.cos(yaw)<0 else 1000):
            gaze = navigation_gaze(None, dense, [i*50 for i in range(31)], 0, 0)
        self.assertTrue(all(math.cos(v)>=-1e-9 for v in gaze))


if __name__ == '__main__': unittest.main()
