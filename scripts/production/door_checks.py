"""Shared effective door leaves, sweep geometry and independent source-count evidence.

Geometry follows the H5 doorPose conventions. Evidence validation is not image
recognition: a reviewer must actually inspect the hash-bound original drawing.
"""
import hashlib
import math
from pathlib import Path


def effective_openings(state, wall):
    return [(i, {**o, **state.get('doorStyles', {}).get(o.get('id') or wall['id'] + ':' + str(i), {})})
            for i, o in enumerate(wall.get('opens', []))]


def signature(o):
    if o.get('leafRemoved') or o['kind'] == 'open_passage':
        return {'doorModel': 'open_passage', 'leafCount': 0, 'hingeEnds': []}
    if o['kind'] == 'sliding':
        count = o.get('leaves', 2)
        if count not in (1, 2, 3):
            raise ValueError('Sliding door needs one, two or three leaves')
        return {'doorModel': 'sliding', 'leafCount': count, 'hingeEnds': []}
    if o['kind'] != 'door':
        return None
    model = o.get('doorModel', 'single')
    if model not in ('single', 'double', 'hidden'):
        raise ValueError('Unsupported swing door model')
    if model == 'double':
        ratio = o.get('leafRatio', .5)
        if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) or not math.isfinite(ratio) or not .3 <= ratio <= .7:
            raise ValueError('Double door leafRatio must be 0.3–0.7')
        if 'leaves' in o and o['leaves'] != 2:
            raise ValueError('Double door must have exactly two leaves')
    return {'doorModel': model, 'leafCount': 2 if model == 'double' else 1,
            'hingeEnds': ['start', 'end'] if model == 'double' else [o.get('hingeEnd', 'start')]}


def is_closed(state, wall, opening, index):
    key = wall['id'] if index == 0 else wall['id'] + ':' + str(opening.get('id') or index)
    return state.get('doors', {}).get(key) is False


def door_leaves(wall, opening, closed=False):
    spec = signature(opening)
    if not spec or spec['doorModel'] in ('open_passage', 'sliding'):
        return []
    length = math.dist(wall['a'], wall['b'])
    if length <= 0 or opening['width'] <= 50:
        raise ValueError('Invalid door wall/width')
    u = [(wall['b'][k] - wall['a'][k]) / length for k in (0, 1)]
    inward = [-u[1] * opening['swing'], u[0] * opening['swing']]
    portions = [(opening.get('hingeEnd', 'start'), opening['at'], opening['width'])]
    if spec['doorModel'] == 'double':
        first = opening['width'] * opening.get('leafRatio', .5)
        portions = [('start', opening['at'], first), ('end', opening['at'] + first, opening['width'] - first)]
    result = []
    for side, at, width in portions:
        along = at + width if side == 'end' else at
        direction = [v * (-1 if side == 'end' else 1) for v in u]
        offset = wall['t'] / 2 + ( -20 if spec['doorModel'] == 'hidden' else 15)
        hinge = [wall['a'][k] + u[k] * along + inward[k] * offset + direction[k] * 25 for k in (0, 1)]
        a = 0 if closed else math.radians(opening.get('angle', 90))
        vector = [direction[k] * math.cos(a) + inward[k] * math.sin(a) for k in (0, 1)]
        leaf_length = width - (25 if spec['doorModel'] == 'double' else 50)
        result.append({'side': side, 'hinge': hinge, 'closedDirection': direction, 'inward': inward,
                       'widthMm': width, 'lengthMm': leaf_length, 'angleDegrees': math.degrees(a),
                       'tip': [hinge[k] + vector[k] * leaf_length for k in (0, 1)]})
    return result


def segment_in_body(a, b, f, pad=20):
    angle = math.radians(f.get('rot', 0)); c, s = math.cos(angle), math.sin(angle)
    def local(p):
        x, y = p[0] - f['cx'], p[1] - f['cy']
        return [x * c + y * s, -x * s + y * c]
    p, q = local(a), local(b); lo, hi = 0., 1.
    for k, half in enumerate((f['w'] / 2 + pad, f['d'] / 2 + pad)):
        delta = q[k] - p[k]
        if abs(delta) < 1e-9:
            if abs(p[k]) >= half: return False
        else:
            x, y = (-half - p[k]) / delta, (half - p[k]) / delta
            lo, hi = max(lo, min(x, y)), min(hi, max(x, y))
            if hi <= lo: return False
    return True


def sweep_conflicts(state, furniture=None, angle_step=2):
    if not isinstance(angle_step, (int, float)) or isinstance(angle_step, bool) or not 0 < angle_step <= 5:
        raise ValueError('Sweep sampling step must be positive and at most5 degrees')
    ignored = {'threshold', 'doortrim', 'windowtrim', 'skirting', 'floordrain', 'transition'}
    objects = state['furniture'] if furniture is None else furniture
    conflicts = []; leaf_count = 0
    for wall in state['walls']:
        if wall.get('demolished'): continue
        for _, o in effective_openings(state, wall):
            leaves = door_leaves(wall, o); leaf_count += len(leaves)
            for leaf in leaves:
                for f in objects:
                    if f['type'] in ignored or f.get('planPoint') or f.get('elevation', 0) >= o.get('height', 2100): continue
                    n = max(1, math.ceil(abs(leaf['angleDegrees']) / angle_step))
                    for i in range(n + 1):
                        a = math.radians(leaf['angleDegrees'] * i / n)
                        v = [leaf['closedDirection'][k] * math.cos(a) + leaf['inward'][k] * math.sin(a) for k in (0, 1)]
                        tip = [leaf['hinge'][k] + v[k] * leaf['lengthMm'] for k in (0, 1)]
                        if segment_in_body(leaf['hinge'], tip, f):
                            conflicts.append({'openingId': o.get('id', wall['id']), 'wallId': wall['id'],
                                              'leafSide': leaf['side'], 'objectId': f['id'], 'angleDegrees': round(math.degrees(a), 3)})
                            break
    return {'status': 'fail' if conflicts else 'pass', 'leafCount': leaf_count, 'conflicts': conflicts,
            'basis': 'Independent leaves, actual H5 hinge offsets/lengths,2-degree-or-finer angular sampling with20mm leaf thickness allowance; not certified continuous clearance'}


def audit_source_doors(state, reviews, base):
    """Require independent pixel observations for every effective door/passage."""
    actual = {o.get('id') or w['id'] + ':' + str(i): signature(o)
              for w in state['walls'] if not w.get('demolished') for i, o in effective_openings(state, w)
              if o['kind'] in ('door', 'sliding', 'open_passage')}
    if not isinstance(reviews, list) or len(reviews) != len(actual) or {r.get('openingId') for r in reviews} != set(actual):
        raise ValueError('Source door review must cover each opening exactly once')
    for r in reviews:
        if not isinstance(r.get('reviewedBy'), str) or not r['reviewedBy'].strip() or not str(r.get('observation', '')).strip():
            raise ValueError('Actual source door observation/reviewer required')
        ref = r.get('sourceArtifact', {}); p = Path(base) / ref.get('path', '')
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != ref.get('sha256'):
            raise ValueError('Source door evidence missing or changed')
        crop = ref.get('crop')
        if not isinstance(crop, list) or len(crop) != 4 or not all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in crop) or not (0 <= crop[0] < crop[2] and 0 <= crop[1] < crop[3]):
            raise ValueError('Source door observation needs an exact positive crop rectangle')
        expected = {k: r.get(k) for k in ('doorModel', 'leafCount', 'hingeEnds')}
        if expected != actual[r['openingId']]:
            raise ValueError('Source/model door leaf count or hinges mismatch: ' + r['openingId'])
    return {'status': 'pass', 'openingCount': len(actual), 'leaves': sum(x['leafCount'] for x in actual.values()),
            'scope': 'Hash-bound source observation vs effective model; does not independently recognize pixels or grant user approval'}


def sliding_geometry(wall, opening):
    """Same mm panel model as source/sliding-door.js; projected largest clear gap.

    Does not deduct handles/installation tolerances or certify body reachability.
    """
    if opening.get('leaves') == 1:
        width = opening['width']; opened = opening.get('slideOpen', 0); direction = opening.get('slideDirection', 1)
        side = opening.get('slideSide', -1); overlap = opening.get('slideOverlap', 20)
        dx, dy = [wall['b'][k] - wall['a'][k] for k in (0, 1)]; length = math.hypot(dx, dy)
        if (not length or opening.get('slideMount') != 'wall' or width < 300 or not math.isfinite(width)
                or not math.isfinite(opened) or not 0 <= opened <= 1 or direction not in (-1, 1)
                or side not in (-1, 1) or not math.isfinite(overlap) or not 0 <= overlap <= 100):
            raise ValueError('Invalid single wall-sliding door')
        u = [dx / length, dy / length]; normal = [-u[1], u[0]]; pw = width + overlap * 2; thickness = 35
        along = width / 2 + direction * pw * opened; track = side * (wall.get('t', 0) / 2 + thickness / 2 + 12)
        centre = [wall['a'][k] + u[k] * (opening['at'] + along) + normal[k] * track for k in (0, 1)]
        interval = [max(0, min(width, along - pw / 2)), max(0, min(width, along + pw / 2))]
        panels = [] if opening.get('leafRemoved') else [dict(cx=centre[0], cy=centre[1], pw=pw, thickness=thickness, along=along, track=track,
            v=abs(u[1]) > abs(u[0]), w=abs(u[0])*pw+abs(normal[0])*thickness, d=abs(u[1])*pw+abs(normal[1])*thickness, interval=interval)]
        occupied = [interval] if panels and interval[1] > interval[0] else []
        gaps = []; end = 0
        for a, b in occupied:
            if a > end: gaps.append([end, a])
            end = max(end, b)
        if end < width: gaps.append([end, width])
        return dict(panels=panels, occupied=occupied, gaps=gaps, netOpeningMm=max([0]+[b-a for a,b in gaps]), totalClearMm=sum(b-a for a,b in gaps), apertureWidthMm=width)
    dx, dy = [wall['b'][k] - wall['a'][k] for k in (0, 1)]
    length = math.hypot(dx, dy)
    width = opening['width']; n = opening.get('leaves', 2)
    opened = opening.get('slideOpen', 0); direction = opening.get('slideDirection', 1)
    if (not length or not math.isfinite(width) or n not in (2, 3) or width < n * 300
            or not math.isfinite(opened) or not 0 <= opened <= 1 or direction not in (-1, 1)):
        raise ValueError('Invalid sliding door parameters')
    u = [dx / length, dy / length]; normal = [-u[1], u[0]]
    pw = width / n + min(30, width * .02); panels = []
    for i in range(0 if opening.get('leafRemoved') else n):
        closed = -width / 2 + width * (i + .5) / n
        target = direction * (width / 2 - pw / 2)
        along = width / 2 + closed + (target - closed) * opened
        track = (i - (n - 1) / 2) * 35
        centre = [wall['a'][k] + u[k] * (opening['at'] + along) + normal[k] * track for k in (0, 1)]
        panels.append({'cx': centre[0], 'cy': centre[1], 'pw': pw, 'thickness': 35,
                       'along': along, 'track': track, 'v': abs(u[1]) > abs(u[0]),
                       'w': abs(u[0]) * pw + abs(normal[0]) * 35,
                       'd': abs(u[1]) * pw + abs(normal[1]) * 35,
                       'interval': [max(0, along - pw / 2), min(width, along + pw / 2)]})
    occupied = []
    for a, b in sorted(p['interval'] for p in panels):
        if occupied and a <= occupied[-1][1]: occupied[-1][1] = max(b, occupied[-1][1])
        else: occupied.append([a, b])
    gaps = []; end = 0
    for a, b in occupied:
        if a > end: gaps.append([end, a])
        end = max(end, b)
    if end < width: gaps.append([end, width])
    return {'panels': panels, 'occupied': occupied, 'gaps': gaps,
            'netOpeningMm': max([0] + [b - a for a, b in gaps]),
            'totalClearMm': sum(b - a for a, b in gaps), 'apertureWidthMm': width}


def leaf_segments(leaf,degree):
    a=math.radians(degree);v=[leaf['closedDirection'][k]*math.cos(a)+leaf['inward'][k]*math.sin(a) for k in (0,1)];n=[-v[1],v[0]];h=leaf['hinge'];L=leaf['lengthMm']
    yield 'leaf',h,[h[k]+v[k]*L for k in (0,1)],20
    for side in (-1,1):
        yield 'handle',[h[k]+v[k]*(L-120)+n[k]*32*side for k in (0,1)],[h[k]+v[k]*(L-55)+n[k]*32*side for k in (0,1)],9
