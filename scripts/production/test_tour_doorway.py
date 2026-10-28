"""Case-neutral portal composition proposals must preserve the frozen contract."""
import copy
import math
import time
import unittest
from unittest.mock import patch

from tour_doorway import doorway_report, repair_candidates


def fixture(fps=10):
    frames = []
    for i in range(20 * fps + 1):
        u = max(0., min(1., (i - 2 * fps) / (16 * fps)))
        position = -2500 + 5000 * u * u * (3 - 2 * u)
        v = max(0., min(1., (i - 14 * fps) / (4 * fps)))
        yaw = math.radians(45 * (1 - v * v * (3 - 2 * v)))
        frames.append({'frame': i, 'pointMm': [position, 0.],
            'yawRadians': yaw, 'pitchRadians': -.1, 'eyeMm': 1600})
    tour = {'fps': fps, 'seconds': len(frames) / fps, 'frames': frames,
        'visits': [{'name': name, 'frame': frame} for name, frame in
            [('a', 0), ('b', 2 * fps), ('c', 18 * fps), ('d', 20 * fps)]]}
    config = {'chapters': [
        {'name': 'first', 'phase': 'observe', 'from': 'a', 'to': 'b',
         'roomId': 'west', 'singleSweepDegrees': 0},
        {'name': 'connection', 'phase': 'transit', 'from': 'b', 'to': 'c'},
        {'name': 'last', 'phase': 'observe', 'from': 'c', 'to': 'd',
         'roomId': 'east', 'singleSweepDegrees': 0}],
        'tourContract': {'bodyRadiusMm': 180}}
    bundle = {'model': {'footprint': [[-5000, -5000], [5000, -5000],
        [5000, 5000], [-5000, 5000]], 'rooms': []},
        'state': {'furniture': [], 'walls': [{'id': 'partition',
            'a': [0, -5000], 'b': [0, 5000], 't': 120,
            'opens': [{'id': 'real_opening', 'kind': 'door', 'at': 4300,
                       'width': 1400, 'leafRemoved': True}]}]}}
    return bundle, tour, config


def rotated(bundle, tour, config, degrees=73):
    b, t, c = copy.deepcopy((bundle, tour, config))
    angle = math.radians(degrees)
    def point(p):
        return [p[0] * math.cos(angle) - p[1] * math.sin(angle) + 1234,
                p[0] * math.sin(angle) + p[1] * math.cos(angle) - 5678]
    b['model']['footprint'] = [point(p) for p in b['model']['footprint']]
    for wall in b['state']['walls']:
        wall['a'], wall['b'] = point(wall['a']), point(wall['b'])
        wall['id'] = 'renamed_wall'
        for op in wall['opens']:
            op['id'] = 'renamed_portal'
    for frame in t['frames']:
        frame['pointMm'] = point(frame['pointMm'])
        frame['yawRadians'] += angle
    c['chapters'][1]['name'] = 'renamed_connection'
    return b, t, c


class DoorwayTests(unittest.TestCase):
    def test_reports_real_crossing_and_wrong_wall_center(self):
        b, t, c = fixture()
        report = doorway_report(b, t, c)
        self.assertTrue(report['softDiagnostic'])
        self.assertEqual(report['status'], 'needs_review')
        self.assertEqual(report['policy']['maximumIterations'], 160000)
        self.assertEqual(len(report['chapters']), 1)
        row = report['chapters'][0]
        self.assertEqual(row['gate']['openingId'], 'real_opening')
        self.assertAlmostEqual(row['crossFrame'], 100.)
        self.assertGreater(row['offOpeningSeconds'], 1)
        self.assertGreater(row['score'], 1)
        self.assertTrue(any(not s['centerRayThroughOpening'] for s in row['samples']))

    def test_window_or_uncrossed_opening_is_not_a_doorway(self):
        b, t, c = fixture()
        b['state']['walls'][0]['opens'][0]['kind'] = 'window'
        self.assertEqual(doorway_report(b, t, c)['chapters'], [])
        b, t, c = fixture()
        b['state']['walls'][0]['opens'][0]['at'] = 6000
        self.assertEqual(doorway_report(b, t, c)['chapters'], [])

    def test_touching_or_following_portal_plane_then_returning_is_not_crossing(self):
        b, t, c = fixture()
        for i, frame in enumerate(t['frames']):
            frame['pointMm'][0] = -abs(frame['pointMm'][0])
            if 95 <= i <= 105:
                frame['pointMm'][0] = 0.
        self.assertEqual(doorway_report(b, t, c)['chapters'], [])

    def test_expired_or_invalid_deadline_stops_before_generation(self):
        b, t, c = fixture()
        with self.assertRaises(TimeoutError):
            repair_candidates(b, t, c, deadline=time.monotonic() - 1)
        for value in (True, float('nan'), 'tomorrow'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                repair_candidates(b, t, c, deadline=value)

    def test_repairs_misframed_actual_gate_without_editing_observations(self):
        b, t, c = fixture()
        original = copy.deepcopy((b, t, c))
        proposals = repair_candidates(b, t, c, ['connection'])
        self.assertTrue(proposals)
        self.assertLessEqual(len(proposals), 3)
        for p in proposals:
            e, out = p['evidence'], p['tour']
            self.assertLess(e['scoreAfter'], e['scoreBefore'] - .02)
            self.assertTrue(e['observationsFrozen'])
            self.assertTrue(e['outsideFramesFrozen'])
            self.assertTrue(e['timingFrozen'])
            self.assertEqual(out['frames'][:21], t['frames'][:21])
            self.assertEqual(out['frames'][180:], t['frames'][180:])
            self.assertEqual(out['visits'], t['visits'])
            self.assertEqual(p['config'], c)
            self.assertEqual([f['pitchRadians'] for f in out['frames']],
                             [f['pitchRadians'] for f in t['frames']])
            self.assertIn('mesh', e['status'])
        self.assertEqual((b, t, c), original)

    def test_rotation_translation_and_renaming_do_not_change_diagnostic(self):
        b, t, c = fixture()
        transformed = rotated(b, t, c)
        one, two = doorway_report(b, t, c), doorway_report(*transformed)
        self.assertAlmostEqual(one['score'], two['score'], places=8)
        self.assertAlmostEqual(one['chapters'][0]['crossFrame'],
                               two['chapters'][0]['crossFrame'], places=8)
        p = repair_candidates(*transformed, chapters=['renamed_connection'])
        self.assertTrue(p)
        self.assertLess(p[0]['evidence']['scoreAfter'], two['score'])
        self.assertEqual(p[0]['evidence']['openingId'], 'renamed_portal')

    def test_physically_infeasible_gate_is_rejected(self):
        b, t, c = fixture()
        # This real obstacle blocks the complete aperture. A composition score
        # must never buy traversal through it, even if the seed already does.
        b['state']['furniture'] = [{'id': 'obstruction', 'type': 'wardrobe',
            'cx': 0, 'cy': 0, 'w': 1000, 'd': 2000, 'h': 2000, 'rot': 0}]
        self.assertEqual(repair_candidates(b, t, c), [])

    def test_new_contract_failure_is_not_sent_for_mesh(self):
        b, t, c = fixture()
        c['tourContract']['schema'] = 'homeowner-tour-contract/1'
        source_issue = {'code': 'source_failure', 'chapter': 'unselected'}
        count = 0
        def contract(*args):
            nonlocal count
            count += 1
            issues = [source_issue]
            if count > 1:
                issues.append({'code': 'excessive_transit_turn', 'chapter': 'connection'})
            return {'status': 'needs_revision', 'issues': issues}
        with patch('tour_contract.inspect', side_effect=contract):
            self.assertEqual(repair_candidates(b, t, c), [])
        with patch('tour_contract.inspect', return_value={'status': 'needs_revision', 'issues': [source_issue]}):
            proposals = repair_candidates(b, t, c)
        self.assertTrue(proposals)
        self.assertEqual(proposals[0]['evidence']['numericContractIssues'], [source_issue])

    def test_unselected_chapters_and_disabled_policy_do_nothing(self):
        b, t, c = fixture()
        self.assertEqual(repair_candidates(b, t, c, ['not_this_connection']), [])
        c['doorwayCompositionPolicy'] = {'enabled': False}
        self.assertEqual(doorway_report(b, t, c)['status'], 'disabled')
        self.assertEqual(repair_candidates(b, t, c), [])

    def test_bounds_and_unknown_policy_are_rejected(self):
        b, t, c = fixture()
        for n in (-1, 4, True, 1.5):
            with self.subTest(n=n), self.assertRaises(ValueError):
                repair_candidates(b, t, c, maximum_candidates=n)
        for policy in ({'unknown': 1}, {'maximumSideShiftMm': 500},
                       {'maximumIterations': 8000.5}, {'maximumIterations': 160001},
                       {'maximumIterations': 39}, {'enabled': 1},
                       {'approachSeconds': float('nan')}):
            c['doorwayCompositionPolicy'] = policy
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                doorway_report(b, t, c)

    def test_lateral_candidate_reuses_public_position_projector(self):
        from tour_connection_motion import repair_positions_numpy
        b, t, c = fixture(fps=24)
        # A normal walking-speed fixture makes the aperture-relative side
        # correction compatible with the unchanged 12-degree heading limit.
        # The slower, coarsely sampled case below is deliberately rejected.
        for frame in t['frames']:
            frame['pointMm'][0] *= 1.6
        deadline = time.monotonic() + 10
        with patch('tour_connection_motion.repair_positions_numpy', wraps=repair_positions_numpy) as spy:
            proposals = repair_candidates(b, t, c, deadline=deadline)
        self.assertEqual(spy.call_count, 1)
        self.assertEqual(spy.call_args.args[2].radius, 180)
        self.assertEqual(spy.call_args.kwargs['deadline'], deadline)
        lateral = [p for p in proposals if p['evidence']['mode'] == 'connection_lateral']
        self.assertTrue(lateral)
        self.assertTrue(lateral[0]['evidence']['position']['accepted'])
        self.assertGreater(lateral[0]['evidence']['position']['maximumNetDisplacementMm'], 0)
        self.assertFalse(lateral[0]['evidence']['solverBudget']['motionLimitsChanged'])

    def test_coarse_sampling_does_not_waive_heading_step_limit(self):
        from tour_rules import trajectory
        b, t, c = fixture(fps=10)
        inspected = []
        def check(*args):
            result = trajectory(*args)
            inspected.extend(result['issues'])
            return result
        with patch('tour_rules.trajectory', side_effect=check):
            proposals = repair_candidates(b, t, c)
        self.assertNotIn('connection_lateral', [p['evidence']['mode'] for p in proposals])
        turns = [x for x in inspected if x['code'] == 'path_tangent_discontinuity']
        self.assertTrue(turns)
        self.assertTrue(all(x['maximumDegrees'] == 12 for x in turns))


if __name__ == '__main__':
    unittest.main()
