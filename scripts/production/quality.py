"""Hash-bound H5 review gates. File checks never grant visual or user approval.

Records are created in case folders. No OCR, image provider or identity inference.
"""
import hashlib
import json
import math
from pathlib import Path

SCHEMA = 'floor-visualization-quality-review/1.0'
STAGES = ('source', 'images', 'tour')
IMAGE_CHECKS = ('room_shape', 'openings', 'object_identity', 'placement',
                'orientation', 'proportions', 'materials', 'lighting', 'perspective')

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def require(value, message):
    if not value:
        raise ValueError(message)

def finite(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)

def text(value):
    return isinstance(value, str) and bool(value.strip())

def evidence(value):
    return isinstance(value, list) and bool(value) and all(text(x) for x in value)

def reviewed(record, name):
    require(isinstance(record, dict) and record.get('status') == 'pass', name + ': review is not pass')
    require(text(record.get('reviewer')) and evidence(record.get('evidence')), name + ': reviewer/evidence missing')

def artifacts(stage, base):
    records = stage.get('artifacts', {})
    require(isinstance(records, dict) and bool(records), 'Hash-bound artifacts missing')
    files = {}
    for key, item in records.items():
        require(text(key) and isinstance(item, dict), 'Invalid artifact record')
        require(text(item.get('path')), key + ': artifact path missing')
        path = (base / item['path']).resolve()
        require(path.is_file(), key + ': artifact file missing')
        require(item.get('sha256') == sha(path), key + ': artifact bytes changed')
        require(item.get('role') in ('input', 'output', 'evidence'), key + ': role must be input/output/evidence')
        files[key] = path
    require(any(v['role'] == 'output' for v in records.values()), 'Displayed output artifact missing')
    return files

def at(files, key):
    require(key in files, 'Referenced artifact missing: ' + str(key))
    return files[key]

def source_check(bundle, stage, files):
    expected = bundle.get('confirmations', {}).get('structure', {}).get('sha256')
    require(expected and stage.get('scopeSha256') == expected, 'Source structure scope changed')
    calibration = stage.get('calibration', {})
    require(calibration.get('method') in ('manual_dimension_reading', 'assisted_extraction_reviewed'),
            'Declare manual or assisted-and-reviewed source extraction')
    dimensions = stage.get('dimensions', [])
    require(isinstance(dimensions, list) and dimensions, 'Dimension provenance missing')
    ids = [d.get('id') for d in dimensions]
    require(all(text(i) for i in ids) and len(ids) == len(set(ids)), 'Dimension IDs must be unique')
    dim_by_id = dict(zip(ids, dimensions))
    for d in dimensions:
        require(finite(d.get('valueMm')) and d['valueMm'] > 0, 'Dimension must be positive mm')
        p = d.get('provenance')
        require(p in ('source_dimension', 'derived', 'design_assumption'), 'Dimension provenance invalid')
        require(evidence(d.get('evidence')), 'Dimension evidence missing: ' + d['id'])
        if p == 'source_dimension':
            at(files, d.get('sourceArtifact'))
        elif p == 'derived':
            require(d.get('basisIds') and all(i in dim_by_id and i != d['id'] for i in d['basisIds']),
                    'Derived dimension needs independent basis IDs')
    for key in ('width', 'depth', 'height'):
        ds = [d for d in dimensions if d.get('target') == 'model.' + key]
        require(len(ds) == 1 and abs(ds[0]['valueMm'] - bundle['model'][key]) < .1,
                'Model dimension lacks matching provenance: ' + key)
    for axis in ('x', 'y'):
        spec = calibration.get(axis, {})
        scale = spec.get('mmPerPixel')
        require(finite(scale) and scale > 0 and spec.get('anchors'), 'Both image axes need calibration anchors')
        source_path = at(files, spec.get('sourceArtifact'))
        from PIL import Image
        with Image.open(source_path) as image:
            pixel_limit = image.width if axis == 'x' else image.height
        tolerance = spec.get('toleranceFraction', .02)
        require(finite(tolerance) and 0 <= tolerance <= .05, 'Calibration tolerance must be explicit and <= 5%')
        for anchor in spec['anchors']:
            pixels = anchor.get('pixels')
            require(isinstance(pixels, list) and len(pixels) == 2 and all(map(finite, pixels)) and pixels[0] != pixels[1],
                    'Anchor needs two distinct pixel coordinates along its axis')
            dim = dim_by_id.get(anchor.get('dimensionId'), {})
            require(dim.get('provenance') == 'source_dimension', 'Calibration must use a readable source dimension')
            require(dim.get('sourceArtifact') == spec.get('sourceArtifact') and all(0 <= p <= pixel_limit for p in pixels),
                    'Calibration anchor is outside its source image or uses a different source')
            require(abs(abs(pixels[1] - pixels[0]) * scale - dim['valueMm']) / dim['valueMm'] <= tolerance,
                    'Calibration span disagrees with readable dimension')
    expected_ids = {'room:' + r['id'] for r in bundle['model']['rooms']}
    for wall in bundle['state']['walls']:
        expected_ids.add('wall:' + wall['id'])
        expected_ids.update('opening:' + o['id'] for o in wall.get('opens', []))
    geometry = stage.get('geometryItems', [])
    require(len(geometry) == len(expected_ids) and {i.get('id') for i in geometry} == expected_ids,
            'Every current room, wall and opening needs source/derived/assumed provenance')
    for item in geometry:
        require(item.get('provenance') in ('source_geometry', 'derived', 'design_assumption') and evidence(item.get('evidence')),
                'Geometry evidence/provenance missing: ' + item['id'])
        at(files, item.get('sourceArtifact'))
    unresolved = stage.get('unresolved', [])
    require(isinstance(unresolved, list), 'Unresolved items must be a list')
    require(not any(u.get('consequential', True) and u.get('status') != 'resolved' for u in unresolved),
            'Consequential source ambiguity remains unresolved')
    require(text(stage.get('interpretationLimits')), 'State unlabelled/inferred geometry limits')

def image_check(bundle, stage, files):
    require(stage.get('schemeSha256') == bundle['schemeSha256'], 'Image review belongs to another scheme')
    camera_data = read(at(files, stage.get('viewsArtifact')))
    views = camera_data if isinstance(camera_data, list) else camera_data.get('views', [])
    require(views and len({v['name'] for v in views}) == len(views), 'Camera authority must have unique names')
    view_by_name = {v['name']: v for v in views}
    images = stage.get('images', [])
    require(images and len({i['id'] for i in images}) == len(images), 'Image set must have unique IDs')
    require(set(stage.get('expectedImageIds', [])) == {i['id'] for i in images}, 'Agreed image set is incomplete')
    from PIL import Image
    policy = stage.get('aspectPolicy', {})
    ratio = policy.get('width', 16) / policy.get('height', 9)
    tolerance = policy.get('relativeTolerance', .001)
    require(finite(ratio) and ratio > 0 and finite(tolerance) and 0 <= tolerance <= .01, 'Invalid aspect policy')
    for item in images:
        view = view_by_name.get(item.get('viewName'))
        require(view is not None, 'Image camera is not in frozen camera authority')
        metadata = read(at(files, item.get('captureArtifact')))
        require(metadata.get('schemeSha256') == bundle['schemeSha256'] and metadata.get('camera') == view,
                'H5 capture camera/scheme changed: ' + item['id'])
        require(view.get('mustShow'), 'Declare major subjects for each planned image')
        reference_path = at(files, item.get('referenceArtifact'))
        require(metadata.get('imageSha256') == sha(reference_path), 'Capture reference bytes are unbound or changed')
        with Image.open(at(files, item.get('outputArtifact'))) as im:
            require(abs(im.width / im.height / ratio - 1) <= tolerance, 'Image aspect is outside agreed tolerance')
        checks = item.get('checks', {})
        for key in IMAGE_CHECKS:
            reviewed(checks.get(key), item['id'] + '/' + key)
        require(isinstance(item.get('allowedDifferences'), list), 'Record allowed conceptual differences explicitly')
    reviewed(stage.get('setConsistency'), 'Cross-view image consistency')

def tour_check(bundle, stage, files):
    require(stage.get('schemeSha256') == bundle['schemeSha256'], 'Tour review belongs to another scheme')
    tour_path = at(files, stage.get('tourArtifact'))
    tour = read(tour_path)
    require(tour.get('schemeSha256') == bundle['schemeSha256'], 'Tour source is stale')
    subject = read(at(files, stage.get('subjectAuditArtifact')))
    require(subject.get('schema') == 'floor-visualization-subject-audit/1.0', 'Subject window audit missing')
    require(subject.get('schemeSha256') == bundle['schemeSha256'] and subject.get('tourSha256') == sha(tour_path),
            'Subject audit is stale for this route')
    require(subject.get('status') == 'pass' and subject.get('chapters') and all(c.get('pass') for c in subject['chapters']),
            'Subject visibility/composition time windows failed')
    plan_path = at(files, stage.get('subjectPlanArtifact'))
    require(subject.get('planSha256') == sha(plan_path), 'Subject intent plan changed')
    plan = read(plan_path)
    require(len(subject['chapters']) == len(plan.get('chapters', [])), 'Subject chapters were skipped')
    require({c.get('id') for c in subject['chapters']} == {c.get('id') for c in plan['chapters']}, 'Subject chapter identity changed')
    plan_by_id = {c['id']: c for c in plan['chapters']}
    minimum = plan.get('policy', {}).get('minContinuousSeconds', 2)
    for chapter in subject['chapters']:
        metrics = chapter.get('subjects', {})
        expected = set(plan_by_id[chapter['id']].get('subjects', []))
        require(expected and set(metrics) == expected, 'Measured subjects differ from planned objects')
        require(all(m.get('pass') and finite(m.get('longestContinuousSeconds')) and m['longestContinuousSeconds'] >= minimum
                    for m in metrics.values()), 'Subject pass label contradicts measured viewing duration')
    mesh = read(at(files, stage.get('meshAuditArtifact')))
    require(mesh.get('schemeSha256') == bundle['schemeSha256'] and mesh.get('tourSha256') == sha(tour_path),
            'Mesh audit belongs to another route')
    require(mesh.get('meshAudit') is not None and not mesh['meshAudit'].get('hits'), 'Actual mesh path audit failed')
    require(mesh['meshAudit'].get('bodyRadiusMm') == tour.get('audit', {}).get('bodyRadiusMm'), 'Physical audit used a different camera envelope')
    require(mesh.get('lighting', {}).get('allFixturesOn') and mesh.get('lighting', {}).get('allPrimaryFacesVisible'),
            'Light emission/face visibility failed')
    reviewed(stage.get('walkingClearance'), 'Human passage and shallow-entry review')
    require(text(stage.get('purpose')) and text(stage.get('paceRationale')), 'Purpose and duration rationale missing')
    watched = stage.get('playback', {})
    reviewed(watched, 'Actual playback continuity and motion review')
    video_path = at(files, stage.get('videoArtifact'))
    require(watched.get('videoSha256') == sha(video_path), 'Playback review is bound to another video')
    probe = read(at(files, stage.get('videoProbeArtifact')))['streams'][0]
    require(int(probe['nb_read_frames']) == len(tour['frames']) and abs(float(probe['duration']) - tour['seconds']) <= .1,
            'Encoded video duration/frame count mismatch')

def acceptance(stage):
    approval = stage.get('acceptance', {})
    if approval.get('status') != 'accepted':
        return False
    require(approval.get('source') == 'explicit_user_confirmation' and text(approval.get('by')) and text(approval.get('recordedAt'))
            and evidence(approval.get('evidence')), 'Human acceptance needs explicit user provenance')
    outputs = {k: v['sha256'] for k, v in stage['artifacts'].items() if v['role'] == 'output'}
    require(approval.get('artifactHashes') == outputs, 'Human acceptance does not match displayed output bytes')
    return True

def evaluate(review_path, bundle, stages=None):
    path = Path(review_path).resolve()
    review = read(path)
    require(review.get('schema') == SCHEMA and review.get('caseId') == bundle.get('caseId'), 'Review schema/case mismatch')
    requested = stages or review.get('requiredStages')
    require(isinstance(requested, list) and requested and len(set(requested)) == len(requested)
            and set(requested) <= set(STAGES), 'Declare nonempty unique requiredStages')
    result = {'schema': 'floor-visualization-quality-result/1.0', 'caseId': bundle.get('caseId'),
              'reviewSha256': sha(path), 'schemeSha256': bundle['schemeSha256'], 'stages': {},
              'humanAcceptanceInferred': False}
    for name in requested:
        stage = review.get('stages', {}).get(name, {})
        errors = []
        try:
            files = artifacts(stage, path.parent)
            {'source': source_check, 'images': image_check, 'tour': tour_check}[name](bundle, stage, files)
        except (ValueError, KeyError, TypeError, ZeroDivisionError, OSError) as e:
            errors.append(str(e))
        status = {'technical': 'fail' if errors else 'pass', 'geometry': stage.get('geometry', {}).get('status', 'pending'),
                  'visual': stage.get('visual', {}).get('status', 'pending'), 'acceptance': stage.get('acceptance', {}).get('status', 'pending'), 'errors': errors}
        if status['acceptance'] not in ('pending', 'accepted', 'rejected'):
            status['acceptance']='fail';errors.append('Invalid human acceptance state')
        for scope in ('geometry', 'visual'):
            if status[scope] == 'pass':
                try:
                    reviewed(stage[scope], name + '/' + scope)
                except ValueError as e:
                    status[scope] = 'fail'; errors.append(str(e))
            elif status[scope] not in ('pending', 'fail'):
                status[scope] = 'fail'; errors.append('Invalid ' + scope + ' review state')
        try:
            if acceptance(stage):
                status['acceptance'] = 'accepted'
        except (ValueError, KeyError, TypeError) as e:
            status['acceptance'] = 'fail'; errors.append(str(e))
        status['readyForAcceptedDelivery'] = not errors and status['geometry'] == status['visual'] == 'pass' and status['acceptance'] == 'accepted'
        result['stages'][name] = status
    result['readyForAcceptedDelivery'] = all(s['readyForAcceptedDelivery'] for s in result['stages'].values())
    result['status'] = 'failed' if any(s['errors'] or 'fail' in (s['geometry'], s['visual']) or s['acceptance']=='rejected' for s in result['stages'].values()) else 'ready' if result['readyForAcceptedDelivery'] else 'awaiting_review'
    return result

def require_ready(review_path, bundle, stages=None):
    result = evaluate(review_path, bundle, stages)
    require(result['readyForAcceptedDelivery'], 'Quality review is not ready: ' + json.dumps(result['stages'], ensure_ascii=False))
    return result

def accepted_outputs(review_path, stages):
    review = read(review_path)
    base = Path(review_path).resolve().parent
    return {(base / item['path']).resolve(): item['sha256']
            for name in stages for item in review['stages'][name]['artifacts'].values() if item['role'] == 'output'}

def template(bundle):
    """Populate only identifiers/known model values, never infer source or approval."""
    def pending():
        return {'status': 'pending', 'reviewer': '', 'evidence': []}
    def asset(role):
        return {'path': '', 'sha256': '', 'role': role}
    def stage():
        return {'artifacts': {}, 'geometry': pending(), 'visual': pending(),
                'acceptance': {'status': 'pending', 'source': '', 'by': '', 'recordedAt': '', 'evidence': [], 'artifactHashes': {}}}
    source = stage()
    source.update(scopeSha256=bundle['confirmations']['structure']['sha256'],
                  artifacts={'original': asset('input'), 'drawing': asset('output')},
                  calibration={'method': 'manual_dimension_reading', 'x': {'sourceArtifact': 'original', 'mmPerPixel': None, 'anchors': []},
                               'y': {'sourceArtifact': 'original', 'mmPerPixel': None, 'anchors': []}},
                  dimensions=[{'id': key, 'target': 'model.' + key, 'valueMm': bundle['model'][key],
                               'provenance': 'unreviewed', 'sourceArtifact': 'original', 'evidence': []} for key in ('width', 'depth', 'height')],
                  geometryItems=[], unresolved=[{'id': 'source-review-required', 'consequential': True, 'status': 'open', 'note': 'Complete comparison against the dimensioned original before resolving'}],
                  interpretationLimits='')
    keys = ['room:' + r['id'] for r in bundle['model']['rooms']]
    for w in bundle['state']['walls']:
        keys += ['wall:' + w['id']] + ['opening:' + o['id'] for o in w.get('opens', [])]
    source['geometryItems'] = [{'id': key, 'provenance': 'unreviewed', 'sourceArtifact': 'original', 'evidence': []} for key in keys]
    images = stage()
    images.update(schemeSha256=bundle['schemeSha256'], viewsArtifact='views', expectedImageIds=[], images=[],
                  aspectPolicy={'width': 16, 'height': 9, 'relativeTolerance': .001}, setConsistency=pending())
    tour = stage()
    tour.update(schemeSha256=bundle['schemeSha256'], purpose='', paceRationale='',
                tourArtifact='tour', subjectPlanArtifact='subject-plan', subjectAuditArtifact='subjects', meshAuditArtifact='mesh-audit',
                videoArtifact='video', videoProbeArtifact='probe', walkingClearance=pending(), playback={**pending(), 'videoSha256': ''})
    return {'schema': SCHEMA, 'caseId': bundle['caseId'], 'requiredStages': ['source'],
            'instructions': 'Case-local record. Add images/tour to requiredStages only when requested. Pending placeholders intentionally block final delivery.',
            'stages': {'source': source, 'images': images, 'tour': tour}}
