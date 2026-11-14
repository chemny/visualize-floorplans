import copy
import math
import unittest
from rotate_case import rotate_case, turn_once


def sample():
    return {
        'caseId': 'demo', 'model': {'width': 4000, 'depth': 3000, 'footprint': [[0, 0], [4000, 0], [4000, 3000], [0, 3000]],
            'rooms': [{'id': 'a', 'poly': [[0, 0], [2000, 0], [2000, 3000], [0, 3000]], 'at': [500, 500]},
                      {'id': 'b', 'poly': [[2000, 0], [4000, 0], [4000, 3000], [2000, 3000]], 'at': [3500, 1000]}],
            'floorConnections': [{'id': 'f', 'poly': [[1950, 100], [2050, 100], [2050, 900], [1950, 900]]}]},
        'initialState': {'caseId': 'demo', 'ceilings': [], 'measures': [],
            'walls': [{'id': 'w', 'a': [0, 0], 'b': [4000, 0], 't': 200, 'opens': [{'id': 'D', 'kind': 'door', 'at': 500, 'width': 900}]},
                      {'id': 'e', 'a': [4000, 0], 'b': [4000, 3000], 't': 200, 'opens': []}],
            'furniture': [{'id': 'bed', 'type': 'bed', 'cx': 3500, 'cy': 1000, 'rot': 0, 'w': 1500, 'd': 2000},
                          {'id': 'sink', 'type': 'ksink', 'cx': 500, 'cy': 500, 'rot': 180, 'supportId': 'bed',
                           'supportPose': [3500, 1000, 0, 1500, 2000, 500, 0], 'wallAnchor': {'wallId': 'w', 'side': 'south'}}]},
        'walkStart': {'point': [3900, 100], 'lookAt': [100, 100]},
        'dimensionChains': {'top': [1000, 3000], 'bottom': [2000, 2000], 'left': [3000], 'right': [1000, 2000]},
        'dimensionChainStarts': {'top': 0, 'bottom': 0, 'left': 0, 'right': 0}}


def area(poly):
    return abs(sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(poly, poly[1:] + poly[:1]))) / 2


class RotateCase(unittest.TestCase):
    def test_right_goes_to_top_and_left_to_bottom(self):
        r = turn_once(sample())
        self.assertEqual((r['model']['width'], r['model']['depth']), (3000, 4000))
        bed = next(f for f in r['initialState']['furniture'] if f['id'] == 'bed')
        self.assertEqual([bed['cx'], bed['cy']], [1000, 500])  # was at the right edge, now at the top
        sink = next(f for f in r['initialState']['furniture'] if f['id'] == 'sink')
        self.assertEqual([sink['cx'], sink['cy']], [500, 3500])  # was at the left edge, now at the bottom

    def test_headings_turn_with_the_plan(self):
        r = turn_once(sample())
        rot = {f['id']: f['rot'] for f in r['initialState']['furniture']}
        self.assertEqual(rot['bed'], -90)
        self.assertEqual(rot['sink'], 90)
        pose = next(f for f in r['initialState']['furniture'] if f['id'] == 'sink')['supportPose']
        self.assertEqual(pose, [1000, 500, -90, 1500, 2000, 500, 0])

    def test_four_turns_restore_geometry(self):
        base = sample()
        r = base
        for _ in range(4):
            r = turn_once(r)
        for key in ('footprint',):
            self.assertEqual(r['model'][key], base['model'][key])
        self.assertEqual(r['initialState']['walls'], base['initialState']['walls'])
        self.assertEqual(r['dimensionChains'], base['dimensionChains'])
        for a, b in zip(r['initialState']['furniture'], base['initialState']['furniture']):
            self.assertEqual((a['cx'], a['cy'], a['rot']), (b['cx'], b['cy'], b['rot']))
        self.assertEqual(r['walkStart'], base['walkStart'])

    def test_areas_and_lengths_do_not_change(self):
        base, r = sample(), turn_once(sample())
        for a, b in zip(base['model']['rooms'], r['model']['rooms']):
            self.assertAlmostEqual(area(a['poly']), area(b['poly']))
        for a, b in zip(base['initialState']['walls'], r['initialState']['walls']):
            self.assertAlmostEqual(math.dist(a['a'], a['b']), math.dist(b['a'], b['b']))
            self.assertEqual(a['opens'], b['opens'])

    def test_chains_move_to_the_new_sides_and_keep_their_order_along_the_edge(self):
        r = turn_once(sample())
        self.assertEqual(r['dimensionChains'], {'top': [1000, 2000], 'left': [3000, 1000], 'bottom': [3000], 'right': [2000, 2000]})
        for side in ('top', 'bottom'):
            self.assertEqual(sum(r['dimensionChains'][side]), r['model']['width'])
        for side in ('left', 'right'):
            self.assertEqual(sum(r['dimensionChains'][side]), r['model']['depth'])

    def test_side_words_and_walk_start_follow(self):
        r = turn_once(sample())
        self.assertEqual(next(f for f in r['initialState']['furniture'] if f['id'] == 'sink')['wallAnchor']['side'], 'east')
        self.assertEqual(r['walkStart'], {'point': [100, 100], 'lookAt': [100, 3900]})

    def test_refuses_what_it_cannot_turn(self):
        for key, value in (('ceilings', [{'id': 'c'}]), ('measures', [{'id': 'm'}])):
            case = sample()
            case['initialState'][key] = value
            with self.assertRaises(ValueError):
                turn_once(case)
        case = sample()
        case['dimensionChainStarts']['top'] = 5
        with self.assertRaises(ValueError):
            turn_once(case)
        case = sample()
        case['initialState']['walls'][0]['b'] = [4500, 0]
        with self.assertRaises(ValueError):
            turn_once(case)

    def test_rotate_case_records_the_reason_and_gives_a_new_case_id(self):
        r = rotate_case(sample(), 1, '用户：飘窗朝南', '-north-up')
        self.assertEqual(r['caseId'], 'demo-north-up')
        self.assertEqual(r['initialState']['caseId'], 'demo-north-up')
        self.assertTrue(r['orientation']['northIsUp'])
        self.assertEqual(r['orientation']['rotations'][0]['reason'], '用户：飘窗朝南')
        with self.assertRaises(ValueError):
            rotate_case(sample(), 4)


if __name__ == '__main__':
    unittest.main()
