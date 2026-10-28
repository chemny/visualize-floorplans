"""Soft portal composition diagnostics and bounded, fixed-time repair proposals.

Only real wall openings crossed by the sampled physical path are considered.
The diagnostic is a planar proxy, never an actual-mesh or playback acceptance.
Repairs keep observations, furniture, doors, timing and unselected frames frozen.
The caller must run the normal subject, motion and mesh gates on every proposal.
"""
import copy
import json
import math
import time

from camera_gaze import PROFILE, delta
from design_homeowner_tour import clear_distance, entry_apron, navigation_gaze
from door_checks import effective_openings
from plan_route import Planner
from tour_workflow import edge_limits, markers


DEFAULTS = {
    'enabled': True,
    'approachSeconds': 4.5,
    'recoverySeconds': 2.,
    'afterCrossingSeconds': .6,
    'maximumApproachDistanceMm': 4500.,
    'preferredCenterDegrees': 20.,
    'maximumSideShiftMm': 250.,
    'lookThroughDepthMm': 600.,
    # Fixed observation seams can sit exactly on approved derivative ceilings.
    # A finite larger projection budget resolves them without raising a cap.
    'maximumIterations': 160000,
}


def _policy(config):
    raw = config.get('doorwayCompositionPolicy', {})
    if not isinstance(raw, dict) or set(raw) - set(DEFAULTS):
        raise ValueError('Unknown doorway composition policy field')
    p = {**DEFAULTS, **raw}
    if not isinstance(p['enabled'], bool):
        raise ValueError('Doorway enabled must be boolean')
    bounds = {'approachSeconds': (.25, 10), 'recoverySeconds': (.25, 5),
              'afterCrossingSeconds': (0, 2), 'maximumApproachDistanceMm': (300, 8000),
              'preferredCenterDegrees': (1, 60), 'maximumSideShiftMm': (0, 400),
              'lookThroughDepthMm': (100, 1600), 'maximumIterations': (40, 160000)}
    for key, (low, high) in bounds.items():
        v = p[key]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not low <= v <= high:
            raise ValueError('Invalid bounded doorway policy: ' + key)
    if not isinstance(p['maximumIterations'], int):
        raise ValueError('Doorway maximumIterations must be an integer')
    return p


def _planner(bundle, tour, config):
    contract = config.get('tourContract', {})
    radius = contract.get('bodyRadiusMm', 180)
    if isinstance(radius, bool) or not isinstance(radius, (int, float)) or not math.isfinite(radius) or radius <= 0:
        raise ValueError('Positive physical body radius required')
    access = []
    if contract.get('tourMode') == 'full_tour':
        access, _ = entry_apron(bundle, {'entranceOpeningId': contract['entranceOpeningId'],
            'startPoint': tour['frames'][0]['pointMm'], 'bodyRadiusMm': radius})
    return Planner(bundle, {'bodyRadiusMm': radius, 'accessPolygons': access, 'gridMm': 50})


def _gates(bundle):
    for wall in bundle['state']['walls']:
        if wall.get('demolished'):
            continue
        length = math.dist(wall['a'], wall['b'])
        if length <= 0:
            continue
        along = [(wall['b'][k] - wall['a'][k]) / length for k in (0, 1)]
        normal = [-along[1], along[0]]
        for index, op in effective_openings(bundle['state'], wall):
            if op['kind'] not in ('door', 'sliding', 'open_passage'):
                continue
            yield {'wallId': wall['id'], 'openingId': op.get('id', wall['id'] + ':' + str(index)),
                'kind': op['kind'], 'wallOriginMm': wall['a'][:], 'along': along,
                'normal': normal, 'startAlongMm': op['at'], 'endAlongMm': op['at'] + op['width'],
                'widthMm': op['width'], 'wallThicknessMm': wall['t'],
                'centerMm': [wall['a'][k] + along[k] * (op['at'] + op['width'] / 2) for k in (0, 1)]}


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _crossings(gate, frames, first, last):
    origin, normal, along = gate['wallOriginMm'], gate['normal'], gate['along']
    previous = -math.inf
    for i in range(first, last):
        a, z = frames[i]['pointMm'], frames[i + 1]['pointMm']
        one, two = (_dot([p[k] - origin[k] for k in (0, 1)], normal) for p in (a, z))
        one = 0. if abs(one) < 1e-8 else one
        two = 0. if abs(two) < 1e-8 else two
        # Count arriving at the plane once; do not count a tangent touch or
        # duplicate the following chord that begins on the same plane.
        if one == 0 or one * two > 0 or abs(one - two) < 1e-9:
            continue
        if two == 0:
            after = next((_dot([frames[j]['pointMm'][k] - origin[k] for k in (0, 1)], normal)
                for j in range(i + 2, last + 1)
                if abs(_dot([frames[j]['pointMm'][k] - origin[k] for k in (0, 1)], normal)) > 1e-8), None)
            if after is None or one * after >= 0:
                continue
        u = one / (one - two)
        q = [a[k] + (z[k] - a[k]) * u for k in (0, 1)]
        projection = _dot([q[k] - origin[k] for k in (0, 1)], along)
        if not gate['startAlongMm'] <= projection <= gate['endAlongMm']:
            continue
        cross = i + u
        if cross - previous < 1e-6:
            continue
        previous = cross
        yield cross, -1 if one > 0 else 1


def _measurement(frame, gate, planner):
    point, yaw = frame['pointMm'], frame['yawRadians']
    center = gate['centerMm']
    distance = math.dist(point, center)
    error = math.degrees(delta(yaw, math.atan2(center[1] - point[1], center[0] - point[0])))
    ray = [math.cos(yaw), math.sin(yaw)]
    normal = gate['normal']
    denominator = _dot(ray, normal)
    signed = _dot([point[k] - gate['wallOriginMm'][k] for k in (0, 1)], normal)
    intercept = None
    if abs(denominator) > 1e-9:
        depth = -signed / denominator
        if depth > 0:
            q = [point[k] + ray[k] * depth - gate['wallOriginMm'][k] for k in (0, 1)]
            intercept = _dot(q, gate['along'])
    in_aperture = intercept is not None and gate['startAlongMm'] <= intercept <= gate['endAlongMm']
    bearing = math.atan2(center[1] - point[1], center[0] - point[0])
    visible = clear_distance(planner, point, bearing, distance) >= distance - 60
    return {'distanceMm': distance, 'centerErrorDegrees': error,
        'rayAlongMm': intercept, 'centerRayThroughOpening': in_aperture,
        'gateCenterLineClear': visible, 'centerRayClearanceMm': clear_distance(planner, point, yaw, 4500)}


def doorway_report(bundle, tour, config):
    """Return soft portal composition evidence from actual openings and frames.

    ``score`` is a lower-is-better candidate cost, not a quality-gate verdict.
    Every row identifies the actual opening, crossing and sampled approach.
    """
    policy = _policy(config)
    if not policy['enabled']:
        return {'schema': 'homeowner-doorway-composition/1', 'status': 'disabled',
                'score': 0., 'chapters': [], 'softDiagnostic': True}
    fps, frames, marks = tour['fps'], tour['frames'], markers(tour)
    planner = _planner(bundle, tour, config)
    rows = []
    for ch in config.get('chapters', []):
        if ch.get('phase') != 'transit':
            continue
        first, last = marks[ch['from']], marks[ch['to']]
        for gate in _gates(bundle):
            for cross, direction in _crossings(gate, frames, first, last):
                start = max(first, int(math.floor(cross - policy['approachSeconds'] * fps)))
                end = min(last, int(math.ceil(cross + policy['afterCrossingSeconds'] * fps)))
                samples = []
                for i in range(start, min(last, math.ceil(cross))):
                    value = _measurement(frames[i], gate, planner)
                    if gate['wallThicknessMm'] / 2 + 80 <= value['distanceMm'] <= policy['maximumApproachDistanceMm']:
                        samples.append({'frame': i, **value})
                errors = [abs(v['centerErrorDegrees']) for v in samples]
                misses = sum(not v['centerRayThroughOpening'] for v in samples)
                near = sum(not v['centerRayThroughOpening'] and v['centerRayClearanceMm'] < 1100 for v in samples)
                count = max(1, len(samples))
                score = (sum(min(90, e) / 90 for e in errors) + misses * 2 + near) / count
                rows.append({'chapter': ch['name'], 'chapterStartFrame': first,
                    'chapterEndFrame': last, 'gate': gate, 'crossFrame': cross,
                    'crossingDirection': direction, 'approachWindow': {'startFrame': start, 'endFrame': end},
                    'sampleCount': len(samples), 'meanCenterErrorDegrees': sum(errors) / count,
                    'maximumCenterErrorDegrees': max(errors, default=0),
                    'offOpeningSeconds': misses / fps, 'nearWallSeconds': near / fps,
                    'score': score, 'samples': samples})
    total = sum(r['score'] for r in rows)
    return {'schema': 'homeowner-doorway-composition/1', 'status': 'needs_review' if any(
        r['meanCenterErrorDegrees'] > policy['preferredCenterDegrees'] or r['nearWallSeconds'] > .25 for r in rows) else 'clear',
        'score': total, 'chapters': rows, 'softDiagnostic': True, 'policy': policy,
        'limitations': 'Planar aperture and wall/opaque-door proxy only; actual mesh, subjects and playback remain required.'}


def _ease(u):
    u = max(0., min(1., u))
    return u * u * (3 - 2 * u)


def _look_through(gate, direction, endpoint, depth):
    """Bias the virtual portal view toward the real outgoing station.

    Absolute gate-centre fixation can manufacture a second pan while the
    viewer is already approaching the next room. A bounded aperture-relative
    offset lets the portal and the existing room intent cooperate.
    """
    inward = [v * direction for v in gate['normal']]
    vector = [endpoint[k] - gate['centerMm'][k] for k in (0, 1)]
    ahead = _dot(vector, inward)
    offset = _dot(vector, gate['along']) * depth / ahead if ahead > 180 else 0.
    offset = max(-gate['widthMm'] * .4, min(gate['widthMm'] * .4, offset))
    return [gate['centerMm'][k] + inward[k] * depth + gate['along'][k] * offset for k in (0, 1)]


def _check_deadline(deadline):
    if deadline is not None:
        if isinstance(deadline, bool) or not isinstance(deadline, (int, float)) or not math.isfinite(deadline):
            raise ValueError('Finite monotonic doorway deadline required')
        if time.monotonic() >= deadline:
            raise TimeoutError('Doorway candidate deadline reached')


def _position_projection(tour, config, planner, start, end, peak, side_shift, gate, maximum_iterations, deadline=None):
    """Scope the public projector with frozen two-frame boundary context."""
    from tour_connection_motion import repair_positions_numpy
    frames = tour['frames']
    lo, hi = max(0, start - 2), min(len(frames) - 1, end + 2)
    sub = {'fps': tour['fps'], 'frames': copy.deepcopy(frames[lo:hi + 1]),
        'visits': [{'name': 'context_start', 'frame': 0}, {'name': 'local_start', 'frame': start - lo},
                   {'name': 'local_end', 'frame': end - lo}, {'name': 'context_end', 'frame': hi - lo}]}
    for i in range(start + 1, end):
        bump = ((i - start) / (peak - start)) ** 2 if i <= peak else (end - i) / (end - peak)
        sub['frames'][i - lo]['pointMm'] = [frames[i]['pointMm'][k] + gate['along'][k] * side_shift * bump for k in (0, 1)]
    c = {'chapters': [{'phase': 'observe', 'from': 'context_start', 'to': 'local_start'},
            {'phase': 'transit', 'from': 'local_start', 'to': 'local_end'},
            {'phase': 'observe', 'from': 'local_end', 'to': 'context_end'}],
        'motionReviewLimits': copy.deepcopy(config.get('motionReviewLimits', {})),
        'trajectoryPolicy': copy.deepcopy(config.get('trajectoryPolicy', {}))}
    projected, evidence = repair_positions_numpy(sub, c, planner,
        maximum_iterations=maximum_iterations, speed_headroom_fraction=0,
        acceleration_headroom_fraction=0, projection_tolerance_mm=1e-7,
        **({'deadline': deadline} if deadline is not None else {}))
    if not evidence['accepted']:
        raise ValueError('Doorway position projection did not converge safely')
    out = copy.deepcopy(tour)
    for i in range(start + 1, end):
        out['frames'][i]['pointMm'] = projected['frames'][i - lo]['pointMm']
    evidence['maximumNetDisplacementMm'] = max(math.dist(a['pointMm'], z['pointMm'])
        for a, z in zip(tour['frames'][start:end + 1], out['frames'][start:end + 1]))
    return out, evidence


def _motion_legal(tour, config, planner, start, end):
    """Certify changed physical chords and derivatives at both frozen seams."""
    from tour_camera_evidence import DEFAULTS as CAMERA_DEFAULTS
    from tour_forward_motion import inspect as forward
    from tour_rules import trajectory
    frames, fps = tour['frames'], tour['fps']
    limits = {**json.loads(PROFILE.read_text())['reviewLimits'], **config.get('motionReviewLimits', {})}
    a, z = max(0, start - 2), min(len(frames) - 1, end + 2)
    for i in range(a, z):
        one, two = frames[i:i + 2]
        if planner.blocked(one['pointMm']) or not planner.line_free(one['pointMm'], two['pointMm']):
            return False
        if math.dist(one['pointMm'], two['pointMm']) * fps / 1000 > limits['maximumSpeedMps'] + 1e-6:
            return False
    camera_limits = {**CAMERA_DEFAULTS, **config.get('cameraEvidencePolicy', {})}
    for axis, speed, acceleration in (
        ('yawRadians', 'maxYawDegreesPerSecond', 'maximumYawAccelerationDegreesPerSecondSquared'),
        ('pitchRadians', 'maxPitchDegreesPerSecond', 'maximumPitchAccelerationDegreesPerSecondSquared')):
        caps = edge_limits(tour, config, speed, limits)
        values = [math.degrees(f[axis]) for f in frames]
        if any(abs(values[i + 1] - values[i]) * fps > caps[i] + 1e-6 for i in range(a, z)):
            return False
        if any(abs(values[i + 2] - 2 * values[i + 1] + values[i]) * fps ** 2 > camera_limits[acceleration] + 1e-5 for i in range(a, z - 1)):
            return False
    # These are existing public physical/forward checks, not new allowances.
    if any(a <= x.get('frame', -1) <= z for x in trajectory(tour, config)['issues']):
        return False
    if any(x['startFrame'] < end and x['endFrame'] > start for x in forward(tour, config)['issues']):
        return False
    return True


def _issue_key(issue):
    # Measurements/messages vary during a repair. Identity retains the exact
    # rule and semantic scope; an unrelated source failure is not a new one.
    return tuple((key, json.dumps(issue.get(key), sort_keys=True)) for key in
        ('code', 'chapter', 'subjectId', 'roomId', 'axis', 'metric', 'field'))


def repair_candidates(bundle, tour, config, chapters=None, maximum_candidates=3, deadline=None):
    """Return at most three safe, improved portal proposals; no approval side effects.

    A local candidate is followed by a bounded whole-connection alternative and
    a position/gaze alternative. The latter two can remove a redundant earlier
    turn in the same connection; an infeasible frozen context yields no proposal.
    ``chapters`` selects exact chapter names, never case-specific defaults.
    """
    if isinstance(maximum_candidates, bool) or not isinstance(maximum_candidates, int) or not 0 <= maximum_candidates <= 3:
        raise ValueError('Use zero to three bounded doorway candidates')
    if chapters is not None and (not isinstance(chapters, (list, tuple, set)) or any(not isinstance(x, str) for x in chapters)):
        raise ValueError('Doorway chapters must be explicit names')
    if not maximum_candidates:
        return []
    _check_deadline(deadline)
    policy = _policy(config)
    before = doorway_report(bundle, tour, config)
    if not policy['enabled']:
        return []
    allowed = set(chapters) if chapters is not None else None
    rows = [r for r in before['chapters'] if (allowed is None or r['chapter'] in allowed)
        and r['sampleCount'] and (r['meanCenterErrorDegrees'] > policy['preferredCenterDegrees'] or r['nearWallSeconds'] > .25)]
    if not rows:
        return []
    row = max(rows, key=lambda r: r['score'])
    chapter = next(c for c in config['chapters'] if c['name'] == row['chapter'])
    planner = _planner(bundle, tour, config)
    first, last = row['chapterStartFrame'], row['chapterEndFrame']
    if last - first < 6:
        return []
    from tour_gaze_repair import revise
    from tour_camera_evidence import inspect as camera_inspect
    baseline_camera = camera_inspect(bundle, tour, config, planner)
    baseline_issues = {json.dumps(x, sort_keys=True) for x in baseline_camera['issues']}
    contracted = config.get('tourContract', {}).get('schema') == 'homeowner-tour-contract/1'
    if contracted:
        from tour_contract import inspect as numeric_contract
        baseline_contract_issues = {_issue_key(x) for x in numeric_contract(bundle, tour, config)['issues']}
    _check_deadline(deadline)
    proposals = []
    gate, fps = row['gate'], tour['fps']
    desired = [s['rayAlongMm'] - (gate['startAlongMm'] + gate['endAlongMm']) / 2
        for s in row['samples'] if s['rayAlongMm'] is not None and not s['centerRayThroughOpening']]
    sign = -1 if sum(desired) >= 0 else 1
    for mode in ('local', 'connection', 'connection_lateral')[:maximum_candidates]:
        if deadline is not None and time.monotonic() >= deadline and proposals:
            break
        _check_deadline(deadline)
        start = row['approachWindow']['startFrame'] if mode == 'local' else first
        end = min(last, row['approachWindow']['endFrame']) if mode == 'local' else last
        if end - start < 6:
            continue
        candidate = copy.deepcopy(tour)
        position_evidence = None
        try:
            if mode == 'connection_lateral' and policy['maximumSideShiftMm']:
                # Late entry correction, before crossing, with frozen endpoints.
                shift_start = max(start, math.floor(row['crossFrame'] - 3.5 * fps))
                peak = min(end - 1, max(shift_start + 1, row['crossFrame'] - .4 * fps))
                candidate, position_evidence = _position_projection(candidate, config, planner,
                    shift_start, end, peak, sign * policy['maximumSideShiftMm'], gate,
                    policy['maximumIterations'], deadline)
            segment = candidate['frames'][start:end + 1]
            base = [f['yawRadians'] for f in segment]
            if mode != 'local':
                path = [f['pointMm'] for f in segment]
                distances = [0.]
                for a, z in zip(path, path[1:]):
                    distances.append(distances[-1] + math.dist(a, z))
                base = navigation_gaze(planner, path, distances, base[0], base[-1], {
                    'avoidBroadWallViews': True, 'broadWallPenalty': 150,
                    'forwardWeight': 8, 'excessTurnPerStepWeight': 60})
            target = _look_through(gate, row['crossingDirection'],
                candidate['frames'][last]['pointMm'], policy['lookThroughDepthMm'])
            keys = []
            # The transit endpoints may also be the last/first observation
            # frames. Leave them outside the public gaze patch, not merely as
            # soft keys that a projection could move.
            for offset, frame in enumerate(segment[1:-1], 1):
                i = start + offset
                yaw = base[offset]
                if i < row['crossFrame']:
                    toward = math.atan2(target[1] - frame['pointMm'][1], target[0] - frame['pointMm'][0])
                    elapsed = (i - row['approachWindow']['startFrame']) / fps
                    recovery = (end - i) / fps / policy['recoverySeconds']
                    # A portal is a composition target, not an instantaneous
                    # look-at command. Fade in on the same connection and fade
                    # out continuously before crossing, so the observation's
                    # frozen outgoing intent has time to recover naturally.
                    enter = _ease(elapsed / min(2., policy['approachSeconds'] / 2))
                    leave = _ease((row['crossFrame'] - i) / fps / .75)
                    weight = enter * _ease(recovery) * leave
                    yaw += delta(yaw, toward) * weight
                # Always keep endpoint values as soft targets to minimize seams;
                # the neighbouring unpatched samples are strict frozen context.
                keys.append({'offsetFrame': offset - 1, 'yawDegrees': math.degrees(yaw)})
            candidate, gaze = revise(candidate, config, [{'chapter': chapter['name'],
                'axes': ['yawRadians'], 'startOffsetFrame': start + 1 - first,
                'endOffsetFrame': end - 1 - first, 'keys': keys}],
                maximum_iterations=policy['maximumIterations'], projection_tolerance=1e-9,
                **({'deadline': deadline} if deadline is not None else {}))
            _check_deadline(deadline)
            if not _motion_legal(candidate, config, planner, start, end):
                continue
            after_camera = camera_inspect(bundle, candidate, config, planner)
            if {json.dumps(x, sort_keys=True) for x in after_camera['issues']} - baseline_issues:
                continue
            numeric = numeric_contract(bundle, candidate, config) if contracted else None
            if numeric and {_issue_key(x) for x in numeric['issues']} - baseline_contract_issues:
                continue
            after = doorway_report(bundle, candidate, config)
            match = next((r for r in after['chapters'] if r['chapter'] == row['chapter']
                and r['gate']['openingId'] == gate['openingId'] and abs(r['crossFrame'] - row['crossFrame']) < fps), None)
            if match is None or match['score'] >= row['score'] - .02:
                continue
            frozen = all(a == z for i, (a, z) in enumerate(zip(tour['frames'], candidate['frames'])) if not start <= i <= end)
            observation = all(tour['frames'][i] == candidate['frames'][i]
                for ch in config['chapters'] if ch['phase'] == 'observe'
                for i in range(markers(tour)[ch['from']], markers(tour)[ch['to']] + 1))
            if not frozen or not observation:
                continue
            proposals.append({'tour': candidate, 'config': copy.deepcopy(config), 'evidence': {
                'schema': 'homeowner-doorway-repair/1', 'mode': mode, 'chapter': chapter['name'],
                'openingId': gate['openingId'], 'changedWindow': {'startFrame': start, 'endFrame': end},
                'lookThroughPointMm': target,
                'solverBudget': {'maximumCandidates': maximum_candidates,
                    'maximumIterationsPerProjection': policy['maximumIterations'],
                    'gazeProjectionToleranceDegrees': 1e-9,
                    'positionProjectionToleranceMm': 1e-7,
                    'motionLimitsChanged': False},
                'scoreBefore': row['score'], 'scoreAfter': match['score'], 'doorwayBefore': row,
                'doorwayAfter': match, 'position': position_evidence, 'gaze': gaze,
                'outsideFramesFrozen': frozen, 'observationsFrozen': observation,
                'timingFrozen': tour['fps'] == candidate['fps'] and len(tour['frames']) == len(candidate['frames'])
                    and tour.get('seconds') == candidate.get('seconds') and tour.get('visits') == candidate.get('visits'),
                'layoutAndDoorsFrozen': True, 'hardGates': 'existing checks remain authoritative; actual mesh and playback pending',
                'numericContractStatus': numeric['status'] if numeric else 'legacy_not_contracted',
                'numericContractIssues': numeric['issues'] if numeric else [],
                'status': 'proposal_needs_mesh_and_playback'}})
        except TimeoutError:
            if proposals:
                break
            raise
        except (ValueError, KeyError, StopIteration):
            # A fixed boundary or real obstacle can make a bounded proposal
            # infeasible. Do not widen motion caps or edit another chapter.
            continue
    return proposals
