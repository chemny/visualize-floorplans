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
MAXIMUM_BACKWARD_SECONDS = .5
MINIMUM_WALKING_SPEED_MPS = .2


def inspect(tour, config):
    frames, fps = tour['frames'], tour['fps']
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError('Positive finite fps required')
    marks = markers(tour)
    chapters = [(marks[ch['from']], marks[ch['to']], ch['name'])
                for ch in config.get('chapters', [])]
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
    issues = [{'code': 'sustained_backward_walking', 'chapter': s['chapters'][0] if s['chapters'] else '',
               **s} for s in spans if s['seconds'] > MAXIMUM_BACKWARD_SECONDS + 1e-9]
    return {'schema': SCHEMA, 'status': 'needs_revision' if issues else 'pass',
            'thresholds': {'preferredMaximumDegrees': PREFERRED_DEGREES,
                           'backwardAngleDegrees': BACKWARD_DEGREES,
                           'maximumBackwardSeconds': MAXIMUM_BACKWARD_SECONDS,
                           'minimumWalkingSpeedMps': MINIMUM_WALKING_SPEED_MPS},
            'walkingSeconds': walking / fps, 'outsidePreferredSeconds': preferred / fps,
            'maximumWalkingDeviationDegrees': maximum, 'backwardSpans': spans, 'issues': issues}
