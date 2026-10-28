import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent/'production'))
from tour_revision_review import artifact_sha256, build_revision_review, closeout_assessment


class RevisionReviewTests(unittest.TestCase):
    def setUp(self):
        self.tour = {'fps': 4, 'seconds': 3, 'schemeSha256': 'frozen',
                     'frames': [{'frame': i, 'pointMm': [i, 0], 'yawRadians': 0, 'pitchRadians': -.1} for i in range(12)],
                     'visits': [{'name': 'start', 'frame': 0}, {'name': 'arrive', 'frame': 6}, {'name': 'done', 'frame': 9}]}
        self.config = {'maximumSeconds': 3, 'chapters': [{'name': 'watch', 'from': 'arrive', 'to': 'done', 'phase': 'observe'}]}
        self.contract = {'status': 'numeric_pass_visual_pending', 'issues': [], 'checks': {
            k: {'issues': []} for k in ('coreTargets', 'choreography', 'cameraEvidence', 'trajectory', 'forwardMotion')}}
        self.mesh = {'status': 'pass', 'issues': [], 'coreTargets': {'status': 'pass', 'issues': []},
                     'screenQuality': {'status': 'pass', 'issues': []}}
        self.scope = {'allowedChanges': {'yawRadians': [[2, 5]]}, 'preserveViewingWindows': True,
                      'baselineConfig': copy.deepcopy(self.config)}

    def assess(self, candidate=None, scope=True, contract=None, mesh=None, playback=None):
        return closeout_assessment(self.tour, candidate or self.tour, self.config,
                                    self.contract if contract is None else contract,
                                    self.mesh if mesh is None else mesh,
                                    self.scope if scope else None, playback)

    def test_legal_local_change_passes_engineering_without_claiming_human_acceptance(self):
        candidate = copy.deepcopy(self.tour)
        candidate['frames'][3]['yawRadians'] = .1
        r = self.assess(candidate)
        self.assertEqual(r['engineeringStatus'], 'pass')
        self.assertEqual(r['reviewStatus'], 'ready_for_review')
        self.assertEqual(r['actualPlayback']['status'], 'not_evaluated')
        self.assertEqual(r['humanAcceptance']['status'], 'not_evaluated')
        self.assertFalse(r['humanAcceptance']['accepted'])
        self.assertFalse(r['videoGenerated'])

    def test_outside_frame_change_fails(self):
        c = copy.deepcopy(self.tour); c['frames'][1]['yawRadians'] = .1
        self.assertEqual(self.assess(c)['checks']['scopeFreeze']['status'], 'failed')
        self.assertEqual(self.assess(c)['engineeringStatus'], 'failed')

    def test_observation_boundary_is_frozen_even_if_allowed_range_includes_it(self):
        c = copy.deepcopy(self.tour); c['frames'][6]['yawRadians'] = .1
        self.scope['allowedChanges']['yawRadians'] = [[2, 7]]
        self.assertEqual(self.assess(c)['checks']['viewingWindows']['status'], 'failed')

    def test_time_change_fails_scoped_revision(self):
        c = copy.deepcopy(self.tour); c['fps'] = 8; c['seconds'] = 1.5
        self.assertEqual(self.assess(c)['checks']['timePreserved']['status'], 'failed')

    def test_ordinary_replanning_can_change_view_and_timing_within_budget(self):
        c = copy.deepcopy(self.tour); c['frames'][6]['yawRadians'] = .1; c['fps'] = 8; c['seconds'] = 1.5
        self.assertEqual(self.assess(c, scope=False)['engineeringStatus'], 'pass')

    def test_mesh_failure_is_never_downgraded_or_exempted_as_exterior(self):
        self.mesh['screenQuality']['issues'] = [{'code': 'screen_blank_segment', 'region': 'exterior'}]
        r = self.assess()
        self.assertEqual(r['engineeringStatus'], 'failed')
        self.assertEqual(r['closeoutChecklist']['noSustainedObstruction']['status'], 'failed')

    def test_contract_failure_is_not_masked_by_status(self):
        self.contract['issues'] = [{'code': 'collision'}]
        self.assertEqual(self.assess()['engineeringStatus'], 'failed')

    def test_nonpassing_or_unknown_report_status_never_passes(self):
        for status in ('needs_revision', 'unavailable', 'unexpected_terminal'):
            mesh = copy.deepcopy(self.mesh); mesh['status'] = status
            with self.subTest(status=status):
                self.assertNotEqual(self.assess(mesh=mesh)['engineeringStatus'], 'pass')

    def test_unrecognized_nested_check_is_not_accepted(self):
        self.contract['checks']['trajectory']['status'] = 'unknown'
        self.assertEqual(self.assess()['engineeringStatus'], 'action_required')

    def test_missing_audit_requires_action(self):
        self.assertEqual(self.assess(mesh={})['engineeringStatus'], 'action_required')

    def test_playback_without_matching_both_hashes_does_not_count(self):
        p = {'performed': True, 'result': 'pass', 'method': 'UI playback', 'reviewedSeconds': [0, 1]}
        self.assertEqual(self.assess(playback=p)['actualPlayback']['status'], 'not_evaluated')
        p.update(candidateTourSha256=artifact_sha256(self.tour), candidateConfigSha256=artifact_sha256(self.config))
        r = self.assess(playback=p)
        self.assertEqual(r['actualPlayback']['status'], 'pass')
        self.assertEqual(r['humanAcceptance']['status'], 'not_evaluated')
        p['candidateTourSha256'] = 'old'
        self.assertEqual(self.assess(playback=p)['actualPlayback']['status'], 'not_evaluated')

    def test_failed_bound_playback_blocks_ready_for_review(self):
        p = {'performed': True, 'result': 'failed', 'method': 'UI playback', 'reviewedSeconds': [1],
             'candidateTourSha256': artifact_sha256(self.tour), 'candidateConfigSha256': artifact_sha256(self.config)}
        r = self.assess(playback=p)
        self.assertEqual(r['engineeringStatus'], 'pass')
        self.assertEqual(r['reviewStatus'], 'action_required')

    def test_stale_mesh_hash_fails(self):
        self.mesh['tourSha256'] = 'stale'
        self.assertEqual(self.assess()['checks']['meshBinding']['status'], 'failed')

    def test_missing_baseline_config_does_not_claim_config_was_preserved(self):
        del self.scope['baselineConfig']
        r = self.assess()
        self.assertEqual(r['checks']['configPreserved']['status'], 'not_evaluated')
        self.assertEqual(r['engineeringStatus'], 'action_required')

    def test_out_of_range_playback_timestamps_do_not_count(self):
        p = {'performed': True, 'result': 'pass', 'method': 'UI playback', 'reviewedSeconds': [99],
             'candidateTourSha256': artifact_sha256(self.tour), 'candidateConfigSha256': artifact_sha256(self.config)}
        self.assertEqual(self.assess(playback=p)['actualPlayback']['status'], 'not_evaluated')

    def test_config_or_layout_mutation_fails(self):
        self.config['maximumSeconds'] = 4
        self.assertEqual(self.assess()['checks']['configPreserved']['status'], 'failed')
        c = copy.deepcopy(self.tour); c['schemeSha256'] = 'other'
        self.assertEqual(self.assess(c)['checks']['layoutPreserved']['status'], 'failed')

    def test_build_uses_same_runtime_absolute_time_and_no_video(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); runtime = root/'runtime'; runtime.mkdir()
            for name in ('scene.json', 'geometry.bin', 'three.module.js', 'three.core.js', 'THREE-LICENSE.txt'):
                (runtime/name).write_text('{}')
            (runtime/'renderer.html').write_text('<style></style><script>window.renderFrame=async f=>{camera.position.set(0,0,0);renderer.render(scene,camera);\n};</script>')
            files = []
            for name, value in [('a.json', self.tour), ('b.json', self.tour), ('ac.json', self.config), ('bc.json', self.config)]:
                path = root/name; path.write_text(json.dumps(value)); files.append(path)
            manifest = build_revision_review(root/'review', *files, runtime,
                                             candidate_report={'contract': self.contract, 'mesh': self.mesh, 'scope': self.scope},
                                             limits={'reviewSeconds': [1, 2], 'maximumSeconds': 3})
            self.assertTrue(manifest['sameAbsoluteTime'])
            self.assertEqual(manifest['engineeringStatus'], 'pass')
            self.assertFalse(manifest['videoGenerated'])
            html = (root/'review/index.html').read_text()
            self.assertEqual(html.count('src="runtime/renderer.html"'), 2)
            self.assertNotIn('<video', html)
            self.assertEqual((root/'review/runtime/geometry.bin').read_bytes(), (runtime/'geometry.bin').read_bytes())
            self.assertIn('samplePose(tours[i],at)', (root/'review/revision-review.js').read_text())
            with self.assertRaisesRegex(ValueError, 'Fresh'):
                build_revision_review(root/'review', *files, runtime)
            (runtime/'scene.json').write_text(json.dumps({'schemeSha256': 'stale'}))
            with self.assertRaisesRegex(ValueError, 'runtime does not match'):
                build_revision_review(root/'stale-review', *files, runtime)
            self.assertFalse((root/'stale-review').exists())
            (runtime/'scene.json').write_text('{}')
            (runtime/'geometry.bin').unlink()
            with self.assertRaisesRegex(ValueError, 'Missing comparison runtime source'):
                build_revision_review(root/'missing-review', *files, runtime)
            self.assertFalse((root/'missing-review').exists())


if __name__ == '__main__':
    unittest.main()
