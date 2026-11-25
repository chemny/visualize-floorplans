"""Final-frame walking/facing check, independent of chapter labels.

These are product review thresholds, not a walking or accessibility standard.
Stationary turns and very slow composition adjustments are excluded. Ordinary
revisits are allowed; sustained backwards walking is not.
"""
import math
from camera_gaze import delta
from tour_workflow import markers

SCHEMA = 'homeowner-forward-motion/1'
PREFERRED_DEGREES = 60
BACKWARD_DEGREES = 90
MAXIMUM_BACKWARD_SECONDS = 1.0  # was .5; user decision 2026-11-02 after plan 1 measured .58 and .83 s
MINIMUM_WALKING_SPEED_MPS = .2
# Case-enabled exception (config.smallRoomBackOut): leaving a small single-exit room by
# stepping back while still facing it. Product limits, not a standard; a config can only tighten them.
SMALL_ROOM_AREA_M2 = 15.  # was 12; user decision 2026-11-15: small rooms (under 15 m2, single exit) back out instead of circling
BACK_OUT_METERS = 1.2
BACK_OUT_SECONDS = 2.5


def polygon_area_m2(poly):
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))) / 2e6


def verify_policy(bundle, config):
    """The exception only stands for rooms that really are small in the confirmed scheme."""
    policy = config.get('smallRoomBackOut')
    if not policy:
        return {'status': 'not_requested', 'issues': []}
    rooms = {r['id']: r for r in bundle['model']['rooms']}
    issues = []
    for row in policy.get('rooms', []):
        room = rooms.get(row.get('roomId'))
        area = polygon_area_m2(room['poly']) if room else None
        if room is None or abs(area - row.get('areaM2', -1)) > .2:
            issues.append({'code': 'small_room_back_out_invalid', 'roomId': row.get('roomId'), 'message': 'Declared area does not match the confirmed scheme'})
        elif area > SMALL_ROOM_AREA_M2:
            issues.append({'code': 'small_room_back_out_invalid', 'roomId': row['roomId'], 'message': 'Room is larger than %g m2' % SMALL_ROOM_AREA_M2})
    return {'status': 'pass' if not issues else 'needs_revision', 'issues': issues, 'limits': {
        'maximumAreaM2': SMALL_ROOM_AREA_M2, 'maximumMeters': BACK_OUT_METERS, 'maximumSeconds': BACK_OUT_SECONDS}}


def inspect(tour, config):
    frames, fps = tour['frames'], tour['fps']
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError('Positive finite fps required')
    marks = markers(tour)
    chapters = [(marks[ch['from']], marks[ch['to']], ch['name'])
                for ch in config.get('chapters', [])]
    policy = config.get('smallRoomBackOut') or {}
    allowed_rows = {row.get('chapter'): row for row in policy.get('rooms', [])}
    meters = min(policy.get('maximumMeters', BACK_OUT_METERS), BACK_OUT_METERS)
    seconds_limit = min(policy.get('maximumSeconds', BACK_OUT_SECONDS), BACK_OUT_SECONDS)
    starts = {name: start for start, end, name in chapters}
    spans, active = [], None
    walking = preferred = 0
    maximum = 0.
    for i, (a, b) in enumerate(zip(frames, frames[1:])):
        dx, dy = (b['pointMm'][k] - a['pointMm'][k] for k in (0, 1))
        speed = math.hypot(dx, dy) * fps / 1000
        yaw = a['yawRadians'] + delta(a['yawRadians'], b['yawRadians']) / 2
        off = abs(math.degrees(delta(math.atan2(dy, dx), yaw)))
        moving = speed > MINIMUM_WALKING_SPEED_MPS
        if moving:
            walking += 1
            maximum = max(maximum, off)
            preferred += off > PREFERRED_DEGREES
        backward = moving and off > BACKWARD_DEGREES
        if backward:
            if active is None:
                active = {'startFrame': i, 'endFrame': i + 1,
                          'maximumDeviationDegrees': off, 'chapters': []}
            active['endFrame'] = i + 1
            active['maximumDeviationDegrees'] = max(active['maximumDeviationDegrees'], off)
            for start, end, name in chapters:
                if start <= i < end and name not in active['chapters']:
                    active['chapters'].append(name)
        if active is not None and (not backward or i == len(frames) - 2):
            active['seconds'] = (active['endFrame'] - active['startFrame']) / fps
            spans.append(active)
            active = None
    def back_out(span):
        names = span['chapters']
        row = allowed_rows.get(names[0]) if len(names) == 1 else None
        if not row or row.get('areaM2', 1e9) > SMALL_ROOM_AREA_M2 or span['startFrame'] > starts[names[0]] + round(fps * .75):
            return False
        travelled = sum(math.dist(frames[i]['pointMm'], frames[i + 1]['pointMm']) for i in range(span['startFrame'], span['endFrame'])) / 1000
        return travelled <= meters + 1e-6 and span['seconds'] <= seconds_limit + 1e-9
    for span in spans:
        if span['seconds'] > MAXIMUM_BACKWARD_SECONDS + 1e-9 and back_out(span):
            span['allowance'] = 'small_room_back_out'
    issues = [{'code': 'sustained_backward_walking', 'chapter': s['chapters'][0] if s['chapters'] else '',
               **s} for s in spans if s['seconds'] > MAXIMUM_BACKWARD_SECONDS + 1e-9 and not s.get('allowance')]
    return {'schema': SCHEMA, 'status': 'needs_revision' if issues else 'pass',
            'thresholds': {'preferredMaximumDegrees': PREFERRED_DEGREES,
                           'backwardAngleDegrees': BACKWARD_DEGREES,
                           'maximumBackwardSeconds': MAXIMUM_BACKWARD_SECONDS,
                           'minimumWalkingSpeedMps': MINIMUM_WALKING_SPEED_MPS},
            'walkingSeconds': walking / fps, 'outsidePreferredSeconds': preferred / fps,
            'maximumWalkingDeviationDegrees': maximum, 'backwardSpans': spans, 'issues': issues}
