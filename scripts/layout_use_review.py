"""Optional extensions of layout-review/1, with explicit legacy coverage.

Validate declared numeric snapshots and hash-bound capture receipts, not vision,
semantic inference, product certification, or proof the producer measured honestly.
"""
import json
import math
from layout_access_checks import overlap
from production.door_checks import segment_in_body


def need(ok, message):
    if not ok: raise ValueError(message)


def finite(v):
    return type(v) in (int, float) and math.isfinite(v)


def rect(v):
    need(isinstance(v, list) and len(v) == 4 and all(map(finite, v))
         and v[0] < v[2] and v[1] < v[3], 'Invalid use-state rectangle')
    return v


def point(v):
    need(isinstance(v, list) and len(v) == 2 and all(map(finite, v)), 'Invalid use-state point')
    return v


def segment_clear(a, b, box, pad):
    point(a); point(b); rect(box)
    need(finite(pad) and pad >= 0, 'Invalid motion/handle padding')
    f = {'cx': (box[0]+box[2])/2, 'cy': (box[1]+box[3])/2,
         'w': box[2]-box[0], 'd': box[3]-box[1], 'rot': 0}
    return not segment_in_body(a, b, f, pad)


def numeric_check(c):
    kind = c['kind']
    if kind == 'rect_clear': return not overlap(rect(c['a']), rect(c['b']))
    if kind == 'segment_clear': return segment_clear(c['a'], c['b'], c['rect'], c['padMm'])
    if kind == 'path_clear':
        pts = c['points']; need(isinstance(pts, list) and len(pts) >= 2, 'A route needs actual continuous points')
        for p in pts: point(p)
        need(finite(c['radiusMm']) and c['radiusMm'] >= 0, 'Invalid route radius')
        need(isinstance(c['obstacles'], list), 'Route obstacle inventory required')
        return all(segment_clear(a, b, obstacle, c['radiusMm'])
                   for a, b in zip(pts, pts[1:]) for obstacle in c['obstacles'])
    raise ValueError('Unsupported operating-state numeric check: '+str(kind))


def matching(a, b, tolerance):
    if finite(a) and finite(b): return abs(a-b) <= tolerance
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(matching(x, y, tolerance) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(matching(a[k], b[k], tolerance) for k in a)
    return type(a) is type(b) and a == b


def extensions(state, record, groups, base, artifact, observation, relation):
    objects = {f['id']: f for f in state['furniture'] if not f.get('assemblyOwner')}
    group_map = {g['id']: g for g in groups}; result = {}
    intents = record.get('assemblyIntents')
    if intents is None: result['assemblyIntentCheck'] = {'status': 'not_provided'}
    else:
        need(isinstance(intents, list) and bool(intents), 'Assembly intent list must not be empty')
        seen = set()
        for intent in intents:
            gid = intent['groupId']; need(gid in group_map and gid not in seen, 'Missing/duplicate assembly group'); seen.add(gid)
            functions = intent['functions']; need(isinstance(functions, list) and bool(functions), 'Assembly functions required')
            names = set()
            for function in functions:
                need(function.get('name') and function['name'] not in names, 'Missing/duplicate assembly function'); names.add(function['name'])
                ids = function['memberIds']
                need(ids and len(ids) == len(set(ids)) and set(ids) <= set(group_map[gid]['members']), 'Assembly function has missing members')
            need(bool(intent['requirements']), 'Assembly intent needs computed semantic requirements')
            for rule in intent['requirements']: relation(rule, objects)
        result['assemblyIntentCheck'] = {'status': 'pass', 'groups': len(intents)}
    matrix = record.get('operationMatrix')
    if matrix is None: result['operationMatrixCheck'] = {'status': 'not_provided'}
    else:
        actors = matrix['actors']; need(actors and all(v and len(v)==len(set(v)) for v in actors.values()), 'Named actor states required')
        need(matrix.get('motionIncludesHandles') is True, 'Door/cabinet motion must include handles or remain unverified')
        need(matrix['scenarios'], 'Operating-state scenarios required'); seen = set(); usable = 0; blocked = 0
        for scenario in matrix['scenarios']:
            need(scenario['id'] not in seen, 'Duplicate use scenario'); seen.add(scenario['id'])
            states = scenario['states']; need(states.keys() == actors.keys() and all(states[k] in actors[k] for k in actors), 'Scenario omits/changes actor state')
            p = artifact(scenario['snapshot'], base); snap = json.loads(p.read_text(encoding='utf-8'))
            need(snap['stateSha256'] == record['stateSha256'] and snap['states'] == states, 'Operating snapshot stale or wrong state')
            checks = snap['checks']; need(set(checks) == {'body', 'motion', 'use'} and all(checks.values()), 'Separate body, motion and human-use checks required')
            clear = all([numeric_check(c) for domain in checks.values() for c in domain])
            expected = scenario['expected']; need(expected in ('usable', 'blocked'), 'Unknown use-state expectation')
            need(clear == (expected == 'usable'), 'Operating state contradicts declared usability')
            if expected == 'blocked':
                blocked += 1; need(bool(scenario.get('reason')), 'Blocked scenario needs reason')
                disclosure = scenario['disclosure']; text = disclosure['text']; need(bool(text), 'Operating condition must be disclosed')
                p = artifact(disclosure['artifact'], base)
                need(text in p.read_text(encoding='utf-8'), 'Operating condition absent from delivery artifact')
            else: usable += 1
        need(usable > 0, 'No usable operating state was verified')
        # Every advertised state must actually be exercised; unsupported/irrelevant states stay outside this matrix.
        for actor, states in actors.items():
            need(set(states) == {s['states'][actor] for s in matrix['scenarios']}, 'Actor state left unchecked')
        result['operationMatrixCheck'] = {'status': 'pass_with_conditions' if blocked else 'pass', 'usable': usable, 'expectedBlocked': blocked}
    final = record.get('finalRepresentations')
    if final is None: result['finalRepresentationCheck'] = {'status': 'not_provided'}
    else:
        captures = {}
        for kind in ('plan', 'mesh', 'screenshot'):
            receipt = final[kind]; p = artifact(receipt['receipt'], base); data = json.loads(p.read_text(encoding='utf-8'))
            need(data['stateSha256'] == record['stateSha256'], 'Final representation receipt is stale')
            artifact(data['artifact'], p.parent); observation(receipt['observation'], base); captures[kind] = data
        pairs = final['comparisons']; need(bool(pairs), 'Final geometry comparisons required')
        for pair in pairs:
            tol = pair['tolerance']; need(finite(tol) and tol >= 0, 'Invalid representation tolerance')
            key = pair['measurement']
            need(key in captures['plan']['measurements'] and key in captures['mesh']['measurements'], 'Missing final geometry measurement')
            need(matching(captures['plan']['measurements'][key], captures['mesh']['measurements'][key], tol), 'Final 2D/3D geometry differs: '+key)
        screenshot = captures['screenshot']
        need(screenshot['renderedStates'] == final['expectedScreenshotStates'] and bool(final['expectedScreenshotStates']), 'Screenshot shows wrong operating state')
        need(screenshot.get('animationSamples'), 'Actual animation/pose samples required')
        for sample in screenshot['animationSamples']:
            need(all(finite(sample[k]) for k in ('actual', 'target', 'tolerance')) and sample['tolerance'] >= 0
                 and abs(sample['actual']-sample['target']) <= sample['tolerance'], 'Screenshot captured before pose settled')
        result['finalRepresentationCheck'] = {'status': 'pass', 'comparisons': len(pairs), 'scope': 'Hash-bound receipts, declared measurements and observations; not automatic image understanding'}
    for name in record.get('requiredChecks', []):
        if name == 'candidateComparisonCheck': continue  # Existing review entry validates this independent scope.
        need(name in result and result[name]['status'] != 'not_provided', 'Required extended layout check missing: '+str(name))
    return result
