#!/usr/bin/env python3
"""Local project persistence and version-bound confirmation, using Python stdlib."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
import threading
import time


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def atomic_json(path, value):
    raw = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.scheme-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def validate_scheme(scheme, case_id):
    if not isinstance(scheme, dict) or scheme.get('caseId') != case_id:
        raise ValueError('方案不属于当前项目')
    digest(scheme)  # Reject NaN and unsupported JSON values.
    for key in ('furniture', 'walls'):
        if not isinstance(scheme.get(key), list):
            raise ValueError('缺少完整方案：' + key)
        ids = set()
        for item in scheme[key]:
            if not isinstance(item, dict) or not isinstance(item.get('id'), str) or item['id'] in ids:
                raise ValueError('无效或重复对象 ID：' + key)
            ids.add(item['id'])
    if not isinstance(scheme.get('rooms'), dict) or not isinstance(scheme.get('doors'), dict):
        raise ValueError('缺少房间或门数据')
    # Full engine geometry/type checks still run on the client and before production.


class Conflict(Exception):
    pass


class Store:
    def __init__(self, directory, seed, stage):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / 'scheme-current.json'
        self.backup = self.directory / 'scheme-previous.json'
        self.lock = threading.RLock()
        self.stage = stage
        self.case_id = seed['caseId']
        validate_scheme(seed, self.case_id)
        if self.path.exists():
            self.current()  # Corrupt data must stop startup, not reset to defaults.
        else:
            atomic_json(self.path, {'schema': 'project-scheme/1', 'caseId': self.case_id,
                'revision': 1, 'schemeHash': digest(seed), 'savedAt': stamp(),
                'scheme': seed, 'confirmation': None})

    def current(self):
        with self.lock:
            value = json.loads(self.path.read_text(encoding='utf-8'))
            validate_scheme(value['scheme'], self.case_id)
            if value['caseId'] != self.case_id or value['schemeHash'] != digest(value['scheme']):
                raise ValueError('项目文件校验失败；请检查备份')
            return value

    def save(self, scheme, expected_revision):
        with self.lock:
            old = self.current()
            if expected_revision != old['revision']:
                raise Conflict('方案已被另一页面修改；请先保留当前编辑，再重新加载项目')
            validate_scheme(scheme, self.case_id)
            if digest(scheme) == old['schemeHash']:
                return old
            new = {**old, 'revision': old['revision'] + 1, 'scheme': copy.deepcopy(scheme),
                   'schemeHash': digest(scheme), 'savedAt': stamp(), 'confirmation': None}
            atomic_json(self.backup, old)
            atomic_json(self.path, new)
            return self.current()

    def confirm(self, expected_revision, expected_hash):
        with self.lock:
            old = self.current()
            if expected_revision != old['revision'] or expected_hash != old['schemeHash']:
                raise Conflict('确认版本不是当前保存版本')
            event = {'id': secrets.token_hex(12), 'stage': self.stage,
                     'revision': old['revision'], 'schemeHash': old['schemeHash'],
                     'confirmedAt': stamp(), 'source': 'explicit_workbench_button'}
            atomic_json(self.backup, old)
            atomic_json(self.path, {**old, 'confirmation': event})
            return self.current()


def make_server(store, html, port=0):
    token = secrets.token_urlsafe(32)
    raw_html = Path(html).read_text(encoding='utf-8')
    # Require a generated current-engine workbench, not an arbitrary proxy target.
    for element in ('caseData', 'projectSeed'):
        if not re.search(r'<script\b[^>]*id=["\']' + element + r'["\'][^>]*>', raw_html):
            raise ValueError('工作台缺少 ' + element)
    case_match = re.search(r'<script\b[^>]*id=["\']caseData["\'][^>]*>(.*?)</script>', raw_html, re.S)
    if json.loads(case_match[1]).get('caseId') != store.case_id:
        raise ValueError('工作台与项目不是同一户型')
    if 'project-service-client/1' not in raw_html:
        raise ValueError('请先使用新版引擎构建工作台')

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Never log session token or scheme contents.

        def response(self, status, value, mime='application/json; charset=utf-8'):
            body = value.encode() if isinstance(value, str) else json.dumps(value, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def trusted(self, write=False):
            host = '127.0.0.1:' + str(self.server.server_port)
            if self.headers.get('Host') != host:
                return False
            origin = self.headers.get('Origin')
            if origin and origin != 'http://' + host:
                return False
            if write or self.path.startswith('/api/'):
                return secrets.compare_digest(self.headers.get('X-Project-Token', ''), token)
            return True

        def do_GET(self):
            if not self.trusted():
                return self.response(403, {'error': '访问被拒绝'})
            if self.path in ('/', '/workbench'):
                with store.lock:
                    current = store.current()
                    config = {'token': token, 'revision': current['revision'], 'stage': store.stage,
                              'savedAt': current['savedAt'], 'confirmation': current['confirmation']}
                    seed = json.dumps(current['scheme'], ensure_ascii=False).replace('<', '\\u003c')
                    page = re.sub(r'(<script\b[^>]*id=["\']projectSeed["\'][^>]*>).*?(</script>)',
                                  lambda m: m[1] + seed + m[2], raw_html, flags=re.S)
                    config_script = '<script id="projectServiceConfig">window.PROJECT_IO=' + json.dumps(config).replace('<', '\\u003c') + ';</script>'
                    page = page.replace('<head>', '<head>' + config_script, 1)
                return self.response(200, page, 'text/html; charset=utf-8')
            if self.path == '/api/scheme':
                return self.response(200, store.current())
            return self.response(404, {'error': '不存在'})

        def do_POST(self):
            if not self.trusted(write=True):
                return self.response(403, {'error': '访问被拒绝'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 8 * 1024 * 1024:
                    return self.response(413, {'error': '请求大小超出范围'})
                if self.headers.get_content_type() != 'application/json':
                    return self.response(415, {'error': '需要 JSON'})
                body = json.loads(self.rfile.read(length))
                if self.path == '/api/save':
                    value = store.save(body['scheme'], body['expectedRevision'])
                elif self.path == '/api/confirm':
                    value = store.confirm(body['expectedRevision'], body['schemeHash'])
                else:
                    return self.response(404, {'error': '不存在'})
                return self.response(200, value)
            except Conflict as exc:
                return self.response(409, {'error': str(exc)})
            except (ValueError, TypeError, KeyError) as exc:
                return self.response(400, {'error': str(exc)})
            except OSError:
                return self.response(500, {'error': '项目写入失败；当前编辑仍在页面，请检查磁盘及备份'})
    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    serve = sub.add_parser('serve')
    serve.add_argument('--html', required=True, type=Path)
    serve.add_argument('--seed', required=True, type=Path)
    serve.add_argument('--project', required=True, type=Path)
    serve.add_argument('--stage', required=True, choices=['structure', 'layout', 'style', 'final-output'])
    serve.add_argument('--port', type=int, default=0)
    wait = sub.add_parser('wait')
    wait.add_argument('--project', required=True, type=Path)
    wait.add_argument('--stage', required=True)
    wait.add_argument('--after', default='', help='Last confirmation ID already handled')
    wait.add_argument('--timeout', type=float, default=30)
    args = parser.parse_args()
    if args.command == 'wait':
        deadline = time.monotonic() + min(60, max(0, args.timeout))
        while True:
            value = json.loads((args.project / 'scheme-current.json').read_text(encoding='utf-8'))
            event = value.get('confirmation')
            if event and event['stage'] == args.stage and event['id'] != args.after and event['revision'] == value['revision'] and event['schemeHash'] == digest(value['scheme']):
                print(json.dumps({'status': 'confirmed', 'record': value}, ensure_ascii=False))
                return 0
            if time.monotonic() >= deadline:
                print(json.dumps({'status': 'pending'}))
                return 2
            time.sleep(.2)
    seed = json.loads(args.seed.read_text(encoding='utf-8'))
    args.project.mkdir(parents=True, exist_ok=True)
    lock = args.project / 'project-service.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise SystemExit('该项目已有服务或未清理的锁；先停止旧服务，核实进程后处理锁文件')
    with os.fdopen(fd, 'w') as f:
        f.write(str(os.getpid()))
    server = None
    try:
        store = Store(args.project, seed, args.stage)
        server = make_server(store, args.html, args.port)
        print(json.dumps({'url': f'http://127.0.0.1:{server.server_port}/workbench',
                          'projectFile': str(store.path), 'stage': args.stage}), flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if server:
            server.server_close()
        lock.unlink()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
