import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image
sys.path.insert(0, str(Path(__file__).parent / 'production'))
import quality
import h5

class QualityGates(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bundle = {'caseId': 'synthetic-test', 'schemeSha256': 'a' * 64,
            'confirmations': {'structure': {'sha256': 'b' * 64}},
            'model': {'width': 1000, 'depth': 1000, 'height': 2750, 'rooms': [{'id': 'room'}]},
            'state': {'walls': [{'id': 'wall', 'opens': [{'id': 'door'}]}], 'furniture': []}}
        Image.new('RGB', (500, 500), 'white').save(self.root / 'source.png')
        Image.new('RGB', (16, 9), 'white').save(self.root / 'drawing.png')
        self.record = quality.template(self.bundle)
        s = self.record['stages']['source']
        s['artifacts'] = {'original': self.asset('source.png', 'input'), 'drawing': self.asset('drawing.png', 'output')}
        for d in s['dimensions']:
            d.update(provenance='source_dimension', evidence=['Synthetic visible dimension'])
        for axis, dimension in [('x', 'width'), ('y', 'depth')]:
            s['calibration'][axis].update(mmPerPixel=10, anchors=[{'pixels': [0, 100], 'dimensionId': dimension}])
        for g in s['geometryItems']:
            g.update(provenance='source_geometry', evidence=['Synthetic original comparison'])
        s['unresolved'] = []
        s['interpretationLimits'] = 'Synthetic only; source comparison is a recorded human observation.'
        s['geometry'] = self.pass_review()
        s['visual'] = self.pass_review()
        self.path = self.root / 'review.json'

    def pass_review(self):
        return {'status': 'pass', 'reviewer': 'synthetic reviewer', 'evidence': ['Synthetic test evidence, not a real approval']}

    def asset(self, name, role):
        return {'path': name, 'sha256': quality.sha(self.root / name), 'role': role}

    def save(self):
        self.path.write_text(json.dumps(self.record))
        return quality.evaluate(self.path, self.bundle)

    def accept(self, stage):
        s = self.record['stages'][stage]
        s['acceptance'] = {'status': 'accepted', 'source': 'explicit_user_confirmation', 'by': 'synthetic test user',
            'recordedAt': 'test timestamp', 'evidence': ['SYNTHETIC ONLY'],
            'artifactHashes': {k: a['sha256'] for k, a in s['artifacts'].items() if a['role'] == 'output'}}

    def image_stage(self):
        self.record['requiredStages'] = ['images']
        Image.new('RGB', (16, 9), '#dddddd').save(self.root / 'reference.png')
        Image.new('RGB', (16, 9), '#eeeeee').save(self.root / 'image.png')
        view = {'name': 'synthetic angle', 'point': [100, 100], 'target': [700, 700], 'mustShow': ['object']}
        (self.root / 'views.json').write_text(json.dumps({'views': [view]}))
        (self.root / 'capture.json').write_text(json.dumps({'schemeSha256': self.bundle['schemeSha256'], 'camera': view,
                                                          'imageSha256': quality.sha(self.root / 'reference.png')}))
        s = self.record['stages']['images']
        s['artifacts'] = {n: self.asset(n + ext, 'output' if n == 'image' else 'input') for n, ext in
                          [('views', '.json'), ('capture', '.json'), ('reference', '.png'), ('image', '.png')]}
        s['expectedImageIds'] = ['one']
        s['images'] = [{'id': 'one', 'viewName': view['name'], 'captureArtifact': 'capture', 'referenceArtifact': 'reference',
            'outputArtifact': 'image', 'checks': {key: self.pass_review() for key in quality.IMAGE_CHECKS}, 'allowedDifferences': []}]
        s['setConsistency'] = s['geometry'] = s['visual'] = self.pass_review()
        return s

    def test_valid_technical_review_stays_pending_without_user_acceptance(self):
        r = self.save(); self.assertEqual(r['stages']['source']['technical'], 'pass')
        self.assertEqual(r['status'], 'awaiting_review'); self.assertFalse(r['readyForAcceptedDelivery'])

    def test_exact_explicit_acceptance_permits_delivery(self):
        self.accept('source'); self.assertTrue(self.save()['readyForAcceptedDelivery'])

    def test_changed_output_invalidates_acceptance(self):
        self.accept('source'); (self.root / 'drawing.png').write_bytes(b'changed')
        self.assertEqual(self.save()['status'], 'failed')

    def test_source_scope_change_invalidates_review(self):
        self.bundle['confirmations']['structure']['sha256'] = 'c' * 64
        self.assertEqual(self.save()['status'], 'failed')

    def test_material_change_does_not_reopen_source_scope(self):
        self.accept('source'); self.bundle['schemeSha256'] = 'd' * 64
        self.assertTrue(self.save()['readyForAcceptedDelivery'])

    def test_unresolved_structural_ambiguity_blocks(self):
        self.record['stages']['source']['unresolved'] = [{'id': 'opening', 'consequential': True, 'status': 'open'}]
        self.assertEqual(self.save()['status'], 'failed')

    def test_missing_geometry_provenance_blocks(self):
        self.record['stages']['source']['geometryItems'].pop()
        self.assertEqual(self.save()['status'], 'failed')

    def test_wrong_calibration_or_outside_anchor_blocks(self):
        self.record['stages']['source']['calibration']['x']['mmPerPixel'] = 15
        self.assertEqual(self.save()['status'], 'failed')
        self.record['stages']['source']['calibration']['x'].update(mmPerPixel=10, anchors=[{'pixels': [500, 600], 'dimensionId': 'width'}])
        self.assertEqual(self.save()['status'], 'failed')

    def test_internal_review_cannot_be_user_acceptance(self):
        self.accept('source'); self.record['stages']['source']['acceptance']['source'] = 'internal_review'
        self.assertFalse(self.save()['readyForAcceptedDelivery'])

    def test_acceptance_hashes_must_match_all_shown_outputs(self):
        self.accept('source'); self.record['stages']['source']['acceptance']['artifactHashes'] = {}
        self.assertFalse(self.save()['readyForAcceptedDelivery'])

    def test_good_image_set_is_still_pending(self):
        self.image_stage(); self.assertEqual(self.save()['status'], 'awaiting_review')

    def test_failed_image_drift_check_blocks(self):
        s = self.image_stage(); s['images'][0]['checks']['openings']['status'] = 'fail'
        self.assertEqual(self.save()['status'], 'failed')

    def test_reference_swap_blocks_despite_updated_artifact_hash(self):
        s = self.image_stage(); Image.new('RGB', (16, 9), 'red').save(self.root / 'reference.png')
        s['artifacts']['reference'] = self.asset('reference.png', 'input')
        self.assertEqual(self.save()['status'], 'failed')

    def test_changed_camera_authority_blocks(self):
        s = self.image_stage(); v=json.loads((self.root / 'views.json').read_text());v['views'][0]['point']=[200,200]
        (self.root / 'views.json').write_text(json.dumps(v));s['artifacts']['views']=self.asset('views.json','input')
        self.assertEqual(self.save()['status'], 'failed')

    def test_portrait_output_blocks(self):
        s = self.image_stage(); Image.new('RGB', (9, 16), 'white').save(self.root / 'image.png');s['artifacts']['image']=self.asset('image.png','output')
        self.assertEqual(self.save()['status'], 'failed')

    def test_missing_agreed_view_blocks(self):
        s = self.image_stage();s['expectedImageIds'].append('missing')
        self.assertEqual(self.save()['status'], 'failed')

    def test_pending_template_cannot_pass(self):
        self.record=quality.template(self.bundle);self.assertEqual(self.save()['status'],'failed')

    def test_plain_handoff_cannot_promote_manifest_boolean(self):
        manifest=self.root/'handoff-input.json';manifest.write_text(json.dumps({'items':[{'path':'drawing.png','accepted':True,'acceptanceEvidence':'claimed'}]}))
        h5.handoff(self.root,manifest)
        self.assertIn('待查看',(self.root/'index.html').read_text());self.assertNotIn('已确认',(self.root/'index.html').read_text())

    def tour_stage(self):
        self.record['requiredStages']=['tour']
        tour={'schemeSha256':self.bundle['schemeSha256'],'fps':24,'seconds':2,'frames':[{}]*48,'audit':{'bodyRadiusMm':180}}
        (self.root/'tour.json').write_text(json.dumps(tour))
        plan={'chapters':[{'id':'one','subjects':['object']}]};(self.root/'plan.json').write_text(json.dumps(plan))
        subject={'schema':'floor-visualization-subject-audit/1.0','schemeSha256':self.bundle['schemeSha256'],
          'tourSha256':quality.sha(self.root/'tour.json'),'planSha256':quality.sha(self.root/'plan.json'),
          'status':'pass','chapters':[{'id':'one','pass':True,'subjects':{'object':{'pass':True,'longestContinuousSeconds':2}}}]}
        (self.root/'subject.json').write_text(json.dumps(subject))
        mesh={'schemeSha256':self.bundle['schemeSha256'],'tourSha256':quality.sha(self.root/'tour.json'),
          'meshAudit':{'hits':[],'bodyRadiusMm':180},'lighting':{'allFixturesOn':True,'allPrimaryFacesVisible':True}}
        (self.root/'mesh.json').write_text(json.dumps(mesh))
        (self.root/'video.mp4').write_bytes(b'SYNTHETIC VIDEO FIXTURE, NOT REAL PLAYBACK')
        (self.root/'probe.json').write_text(json.dumps({'streams':[{'nb_read_frames':'48','duration':'2'}]}))
        s=self.record['stages']['tour'];s.update(purpose='Synthetic homeowner function',paceRationale='Synthetic pace review',
          tourArtifact='tour',subjectPlanArtifact='plan',subjectAuditArtifact='subject',meshAuditArtifact='mesh',videoArtifact='video',videoProbeArtifact='probe',
          walkingClearance=self.pass_review(),playback={**self.pass_review(),'videoSha256':quality.sha(self.root/'video.mp4')},geometry=self.pass_review(),visual=self.pass_review())
        s['artifacts']={n:self.asset(n+ext,'output' if n=='video' else 'evidence') for n,ext in
          [('tour','.json'),('plan','.json'),('subject','.json'),('mesh','.json'),('video','.mp4'),('probe','.json')]}
        return s

    def test_tour_technical_pass_does_not_grant_acceptance(self):
        self.tour_stage();self.assertEqual(self.save()['status'],'awaiting_review')

    def test_failed_subject_window_blocks_tour(self):
        s=self.tour_stage();v=json.loads((self.root/'subject.json').read_text());v['status']='fail';v['chapters'][0]['pass']=False
        (self.root/'subject.json').write_text(json.dumps(v));s['artifacts']['subject']=self.asset('subject.json','evidence')
        self.assertEqual(self.save()['status'],'failed')

    def test_changed_subject_plan_blocks_even_with_new_artifact_hash(self):
        s=self.tour_stage();(self.root/'plan.json').write_text(json.dumps({'chapters':[{'id':'changed'}]}));s['artifacts']['plan']=self.asset('plan.json','evidence')
        self.assertEqual(self.save()['status'],'failed')

    def test_mesh_audit_envelope_must_match_route(self):
        s=self.tour_stage();m=json.loads((self.root/'mesh.json').read_text());m['meshAudit']['bodyRadiusMm']=80
        (self.root/'mesh.json').write_text(json.dumps(m));s['artifacts']['mesh']=self.asset('mesh.json','evidence')
        self.assertEqual(self.save()['status'],'failed')

    def test_playback_review_cannot_bind_another_video(self):
        s=self.tour_stage();s['playback']['videoSha256']='f'*64
        self.assertEqual(self.save()['status'],'failed')

    def test_subject_pass_label_cannot_override_failed_measurement(self):
        s=self.tour_stage();v=json.loads((self.root/'subject.json').read_text());v['chapters'][0]['subjects']['object']['longestContinuousSeconds']=.1
        (self.root/'subject.json').write_text(json.dumps(v));s['artifacts']['subject']=self.asset('subject.json','evidence')
        self.assertEqual(self.save()['status'],'failed')

if __name__ == '__main__': unittest.main()
