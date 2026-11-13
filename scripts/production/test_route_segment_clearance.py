import unittest
from plan_route import Planner


class RouteSegmentClearanceTests(unittest.TestCase):
    def planner(self, furniture=None):
        poly = [[-100, -100], [100, -100], [100, 100], [-100, 100]]
        return Planner({'model': {'footprint': poly, 'rooms': [{'id': 'room', 'poly': poly}]},
                        'state': {'walls': [], 'furniture': furniture or []}},
                       {'bodyRadiusMm': 0})

    def test_furniture_corner_between_old_sample_positions_is_not_clear(self):
        f = dict(id='cabinet', type='cabinet', cx=12.5, cy=3, w=8, d=8, h=800, rot=0)
        p = self.planner([f])
        self.assertTrue(all(not p.blocked(q) for q in [[0, 0], [25, 0], [50, 0]]))
        self.assertFalse(p.line_free([0, 0], [50, 0]))
        self.assertTrue(p.line_free([0, 7], [50, 7]))

    def test_thin_handle_between_samples_is_not_clear(self):
        p = self.planner()
        p.leaves = [([12.5, -1], [12.5, 1], 1)]
        self.assertFalse(p.line_free([0, 0], [50, 0]))
        self.assertTrue(p.line_free([0, 4], [50, 4]))

    def test_body_radius_is_preserved_for_complete_edge(self):
        p = self.planner()
        p.radius = 3
        p.walls = [([12.5, 5], [12.5, 10], 3)]
        self.assertFalse(p.line_free([0, 0], [50, 0]))
        self.assertTrue(p.line_free([0, -2], [50, -2]))

    def test_domain_and_stationary_position_still_checked(self):
        p = self.planner()
        self.assertTrue(p.line_free([0, 0], [0, 0]))
        self.assertFalse(p.line_free([0, 0], [150, 0]))

    def test_rounding_replans_with_space_without_shrinking_body_or_moving_endpoints(self):
        from compact_tour_visits import safe_path
        poly = [[0, 0], [3000, 0], [3000, 3000], [0, 3000]]
        bundle = {'model': {'footprint': poly, 'rooms': [{'id': 'r', 'poly': poly}]},
                  'state': {'walls': [], 'furniture': [dict(id='cab', type='cabinet',
                            cx=1300, cy=1300, w=620, d=620, h=1000, rot=0)]}}
        p = Planner(bundle, {'bodyRadiusMm': 180, 'gridMm': 50})
        start, end = [400, 1800], [1800, 400]
        raw = [start] + p.astar(start, end) + [end]
        with self.assertRaises(ValueError):
            p.round(p.simplify(raw))
        path = safe_path(p, start, end)
        self.assertEqual((path[0], path[-1]), (start, end))
        self.assertEqual(p.radius, 180)
        self.assertTrue(all(p.line_free(a, b) for a, b in zip(path, path[1:])))
        with self.assertRaises(ValueError):
            safe_path(p, [1300, 1300], end)


if __name__ == '__main__':
    unittest.main()
