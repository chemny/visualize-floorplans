#!/usr/bin/env python3
"""Rotate a whole H5 case by quarter turns so that north is up in every drawing.

The workbench draws the plan with the model's +y axis pointing down and has no compass, so "north"
is whatever the author drew at the top. When the real orientation is known (for example the bay
window and balcony face south, the study and secondary bedroom face north), the case is rotated
instead of annotated: every coordinate, furniture heading, dimension chain and wall-relative side
word turns together, so plan, 3D, exports and tours all agree.

Only counter-clockwise quarter turns as seen on screen are applied (default one turn); the
transform is a pure rotation, so handedness, door swings, areas and lengths are unchanged.
Fields the tool cannot turn safely (ceiling zones, measures, non-zero chain starts) stop it with
an error instead of producing a half-rotated case.

Usage: rotate_case.py CASE.json OUT.json [--turns 1] [--reason TEXT] [--case-id-suffix TEXT]
"""
import argparse
import copy
import json
import sys
from pathlib import Path

# Plan sides turn with the drawing: top->left, left->bottom, bottom->right, right->top.
SIDE_AFTER_CCW = {'north': 'west', 'west': 'south', 'south': 'east', 'east': 'north',
                  'top': 'left', 'left': 'bottom', 'bottom': 'right', 'right': 'top'}


def normal_angle(value):
    value = (value + 180.0) % 360.0 - 180.0
    return 180.0 if value == -180.0 else round(value, 9)


class Turn:
    """One counter-clockwise quarter turn about the plan's own frame [0,W]x[0,H]."""

    def __init__(self, width):
        self.width = width

    def point(self, p):
        # Round to 6 decimals so that edges that coincide in the input still coincide after W - x.
        return [round(p[1], 6), round(self.width - p[0], 6)] + list(p[2:])

    def polygon(self, poly):
        return [self.point(p) for p in poly]


def turn_once(case):
    out = copy.deepcopy(case)
    model, state = out['model'], out['initialState']
    width, depth = model['width'], model['depth']
    if state.get('ceilings'):
        raise ValueError('ceiling zones are not rotated automatically; rotate them by hand or remove them first')
    if state.get('measures'):
        raise ValueError('measures are not rotated automatically')
    if any(out.get('dimensionChainStarts', {}).values()):
        raise ValueError('non-zero dimensionChainStarts are not supported')
    t = Turn(width)
    xs = [p[0] for p in model['footprint']] + [v for w in state['walls'] for v in (w['a'][0], w['b'][0])]
    ys = [p[1] for p in model['footprint']] + [v for w in state['walls'] for v in (w['a'][1], w['b'][1])]
    if min(xs) < -1 or max(xs) > width + 1 or min(ys) < -1 or max(ys) > depth + 1:
        raise ValueError('geometry lies outside [0,width]x[0,depth]; set model.width/depth to the real extent first')
    model['width'], model['depth'] = depth, width
    model['footprint'] = t.polygon(model['footprint'])
    for room in model['rooms']:
        room['poly'] = t.polygon(room['poly'])
        if room.get('at'):
            room['at'] = t.point(room['at'])
    for patch in model.get('floorConnections', []):
        patch['poly'] = t.polygon(patch['poly'])
    for wall in state['walls']:
        wall['a'], wall['b'] = t.point(wall['a']), t.point(wall['b'])
    for item in state['furniture']:
        item['cx'], item['cy'] = t.point([item['cx'], item['cy']])
        item['rot'] = normal_angle(item.get('rot', 0) - 90)
        pose = item.get('supportPose')
        if pose:
            item['supportPose'] = t.point(pose[:2]) + [normal_angle(pose[2] - 90)] + list(pose[3:])
        anchor = item.get('wallAnchor')
        if anchor and anchor.get('side') in SIDE_AFTER_CCW:
            anchor['side'] = SIDE_AFTER_CCW[anchor['side']]
    walk = out.get('walkStart')
    if walk:
        for key in ('point', 'lookAt'):
            if walk.get(key):
                walk[key] = t.point(walk[key])
    chains = out.get('dimensionChains')
    if chains:
        out['dimensionChains'] = {'top': list(chains['right']), 'left': list(reversed(chains['top'])),
                                  'bottom': list(chains['left']), 'right': list(reversed(chains['bottom']))}
    return out


def rotate_case(case, turns=1, reason='', suffix=None):
    if turns % 4 == 0:
        raise ValueError('turns must not be a multiple of 4')
    out = case
    for _ in range(turns % 4):
        out = turn_once(out)
    out = copy.deepcopy(out)
    if suffix:
        out['caseId'] = case['caseId'] + suffix
        out['initialState']['caseId'] = out['caseId']
    history = list(out.get('orientation', {}).get('rotations', []))
    history.append({'turnsCounterClockwise': turns % 4, 'reason': reason or 'orientation correction'})
    out['orientation'] = {'northIsUp': True, 'rotations': history,
                          'note': '整套案例按逆时针旋转，使北朝上；坐标、家具朝向、尺寸链同步旋转，面积和长度不变。'}
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('case')
    parser.add_argument('out')
    parser.add_argument('--turns', type=int, default=1, help='counter-clockwise quarter turns as seen on screen')
    parser.add_argument('--reason', default='')
    parser.add_argument('--case-id-suffix', default='-north-up')
    args = parser.parse_args(argv)
    out_path = Path(args.out)
    if out_path.exists():
        raise SystemExit('Use a new output path; existing files are preserved')
    case = json.loads(Path(args.case).read_text(encoding='utf-8'))
    result = rotate_case(case, args.turns, args.reason, args.case_id_suffix)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({'status': 'rotated', 'turns': args.turns % 4, 'caseId': result['caseId'],
                      'width': result['model']['width'], 'depth': result['model']['depth'], 'output': str(out_path)},
                     ensure_ascii=False))


if __name__ == '__main__':
    sys.exit(main())
