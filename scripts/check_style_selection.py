#!/usr/bin/env python3
"""Evidence checkpoint for both host and legacy style-selection workflows."""
import argparse
import hashlib
import json
from pathlib import Path


def check(record, base, production=False):
    errors = []
    def need(ok, message):
        if not ok:
            errors.append(message)
    def nonempty(value):
        return isinstance(value, str) and bool(value.strip())
    def image_file(item, label):
        if not isinstance(item, dict) or not nonempty(item.get('path')):
            errors.append(label + ': missing image path')
            return
        path = base / item['path']
        try:
            data = path.read_bytes()
        except OSError:
            errors.append(label + ': image unavailable')
            return
        need(path.suffix.lower() in {'.png', '.jpg', '.jpeg'} and
             (data.startswith(b'\x89PNG\r\n\x1a\n') or data.startswith(b'\xff\xd8\xff')),
             label + ': expected actual PNG/JPG evidence')
        need(hashlib.sha256(data).hexdigest() == item.get('sha256'),
             label + ': image hash mismatch')
    mode = record.get('mode', 'visual')
    need(mode in {'visual', 'direct_choice', 'text_fallback'}, 'unknown mode')
    options = record.get('options', [])
    valid_options = isinstance(options, list) and all(nonempty(x) for x in options)
    need(valid_options, 'options must be style IDs')
    if not valid_options:
        options = []
    need(len(set(options)) == len(options), 'duplicate style IDs')
    if mode == 'visual':
        need(len(options) >= 2, 'visual selection requires multiple styles')
        image_file(record.get('layout'), 'layout')
        boards = record.get('boards', [])
        need(isinstance(boards, list) and bool(boards), 'comparison board missing')
        covered = set()
        for board in boards if isinstance(boards, list) else []:
            image_file(board, 'board')
            if not isinstance(board, dict):
                continue
            need(board.get('shown_to_user') is True, 'board not shown to user')
            ids = board.get('style_ids', [])
            need(isinstance(ids, list) and all(nonempty(x) for x in ids),
                 'board style IDs invalid')
            if isinstance(ids, list) and all(nonempty(x) for x in ids):
                covered.update(ids)
        need(covered == set(options), 'board styles do not match options')
        review = record.get('comparison_review', {})
        need(isinstance(review, dict) and
             review.get('fixed_layout_camera_light') is True and
             review.get('visually_distinct_styles') is True and
             nonempty(review.get('evidence')), 'visual comparison review missing')
    elif mode in {'direct_choice', 'text_fallback'}:
        need(nonempty(record.get('user_evidence')), 'explicit user evidence missing')
        if mode == 'text_fallback':
            need(nonempty(record.get('blocker')), 'fallback blocker missing')
    if mode in {'visual', 'text_fallback'}:
        tool = record.get('tool_check', {})
        need(isinstance(tool, dict) and tool.get('checked') is True and
             nonempty(tool.get('evidence')), 'actual tool check missing')
    if production:
        selection = record.get('selection', {})
        need(isinstance(selection, dict) and selection.get('style_id') in options and
             nonempty(selection.get('user_evidence')), 'explicit selected style missing')
    return {'passed': not errors, 'purpose': 'production' if production else 'selection',
            'errors': errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('review', type=Path)
    parser.add_argument('--production', action='store_true')
    args = parser.parse_args()
    try:
        record = json.loads(args.review.read_text(encoding='utf-8'))
        if not isinstance(record, dict):
            raise ValueError('review must be a JSON object')
        result = check(record, args.review.resolve().parent, args.production)
    except (OSError, ValueError) as exc:
        result = {'passed': False, 'errors': [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
