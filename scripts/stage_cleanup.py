"""Conservative project cleanup: inventory -> scan -> approved backup/quarantine -> restore.

No scheduler or permanent deletion. Uses only the Python standard library.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
from html import unescape
import json
import os
from pathlib import Path, PurePosixPath
import re
import uuid
from urllib.parse import unquote
import zipfile

TEXT = {'.json', '.html', '.htm', '.md', '.txt', '.svg', '.css', '.js', '.mjs', '.py', '.csv', '.yaml', '.yml'}
MEDIA = {'.png', '.jpg', '.jpeg', '.webp', '.mp4', '.webm', '.mov', '.exr', '.tmp', '.part'}
ROLES = {'source', 'reference', 'current', 'final', 'evidence', 'dependency', 'obsolete', 'temporary'}


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    path = Path(path)
    tmp = path.with_name(path.name + '.new')
    with tmp.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(tmp, path)


def project(path):
    p = Path(path).absolute()
    if any(x.is_symlink() for x in (p, *p.parents)):
        raise ValueError('Project path must not traverse symlinks')
    if not p.is_dir():
        raise ValueError('Project directory required')
    return p.resolve()


def local(root, name):
    if not isinstance(name, str) or '\\' in name or ':' in name:
        raise ValueError('Use project-relative POSIX paths')
    rel = PurePosixPath(name)
    if rel.is_absolute() or not rel.parts or any(x in {'.', '..', '.cleanup', '.git'} for x in rel.parts):
        raise ValueError('Unsafe or reserved project path')
    p = root.joinpath(*rel.parts)
    if any(x.is_symlink() for x in (p, *p.parents)) or not p.resolve().is_relative_to(root):
        raise ValueError('Symlink or project escape')
    return p


def files(root):
    result = {}
    texts = {}
    def fail_walk(error):
        raise error
    for parent, dirs, names in os.walk(root, followlinks=False, onerror=fail_walk):
        dirs[:] = sorted(d for d in dirs if d not in {'.git', '.cleanup'} and not (Path(parent) / d).is_symlink())
        for name in sorted(names):
            p = Path(parent) / name
            if p.is_symlink() or not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            before = p.stat()
            result[rel] = {'sha256': sha(p), 'bytes': before.st_size, 'mtimeNs': before.st_mtime_ns}
            if p.suffix.lower() in TEXT:
                limit = 256 if p.suffix.lower() == '.json' else 16
                if before.st_size > limit * 1024 * 1024:
                    raise ValueError('Reference text exceeds inspection budget: ' + rel)
                texts[rel] = p
            after = p.stat()
            if (after.st_size, after.st_mtime_ns) != (before.st_size, before.st_mtime_ns):
                raise ValueError('File changed during scan: ' + rel)
    return result, texts


def reference_index(root, texts, snapshot, names, inventory_path):
    """Parse one JSON at a time; index all candidate names in one text pass.

    JSON strings and keys are decoded by the standard parser, not regex-extracted.
    Oversized, malformed, changing or unreadable documents still fail closed.
    """
    refs = {name: set() for name in names}
    pattern = re.compile(r'(?<![\w.-])(?:' + '|'.join(re.escape(n) for n in sorted(names, key=len, reverse=True)) + r')(?![\w.-])') if names else None
    def inspect(text, src):
        if pattern:
            for match in pattern.finditer(unquote(unescape(text))):
                refs[match.group()].add(src)
    def strings(value, src):
        stack = [value]
        while stack:
            current = stack.pop()
            if isinstance(current, str):
                inspect(current, src)
            elif isinstance(current, dict):
                for key, child in current.items():
                    inspect(key, src)
                    if isinstance(child, (str, dict, list)):
                        stack.append(child)
            elif isinstance(current, list):
                # Numeric geometry arrays need validation, not string copies.
                stack.extend(v for v in current if isinstance(v, (str, dict, list)))
    def unique_object(pairs):
        result = {}
        for key, child in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key in reference document: ' + key)
            result[key] = child
        return result
    def invalid_constant(value):
        raise ValueError('Nonstandard JSON constant: ' + value)
    for src, p in texts.items():
        if p.resolve() == inventory_path:
            continue
        if p.suffix.lower() == '.json':
            with p.open(encoding='utf-8', errors='strict') as f:
                value = json.load(f, object_pairs_hook=unique_object, parse_constant=invalid_constant)
            strings(value, src)
            del value
        else:
            inspect(p.read_text(encoding='utf-8', errors='strict'), src)
        if sha(p) != snapshot[src]['sha256'] or p.stat().st_mtime_ns != snapshot[src]['mtimeNs']:
            raise ValueError('Reference changed during inspection: ' + src)
    return refs


def scan(root, inventory):
    root = project(root)
    inv = read(inventory)
    if inv.get('stage') not in {'stage-confirmed', 'video-verified', 'delivery-confirmed'}:
        raise ValueError('A confirmed stage trigger is required')
    if not str(inv.get('stageEvidence', '')).strip():
        raise ValueError('Record genuine stage confirmation/verification evidence')
    snapshot, texts = files(root)
    inventory_path = Path(inventory).resolve()
    entries = inv.get('items', [])
    seen = set()
    candidates, protected = [], []
    index = reference_index(root, texts, snapshot, {Path(item['path']).name for item in entries}, inventory_path)
    for item in entries:
        name, role = item['path'], item['role']
        p = local(root, name)
        if name in seen or role not in ROLES or name not in snapshot:
            raise ValueError('Invalid, duplicate or missing inventory item: ' + name)
        seen.add(name)
        reason = str(item.get('reason', '')).strip()
        refs = sorted(src for src in index[p.name] if src != name)
        reserved = any(x.lower() in {'source', 'sources', 'input', 'inputs', 'originals', 'reference', 'references', 'final', 'delivery', 'runtime'} for x in p.relative_to(root).parts[:-1])
        if role not in {'obsolete', 'temporary'} or refs or reserved or p.suffix.lower() not in MEDIA:
            protected.append({'path': name, 'role': role, 'references': refs, 'reason': 'protected role/path/type or referenced by current project'})
        elif not reason or not str(item.get('evidence', '')).strip():
            protected.append({'path': name, 'role': role, 'reason': 'Missing obsolescence/dependency review evidence'})
        else:
            candidates.append({'path': name, **snapshot[name], 'reason': reason, 'evidence': item['evidence']})
    body = {'schemaVersion': 1, 'referencePolicy': 'decoded-json-single-document-v2; conservative-basename-index', 'project': str(root), 'stage': inv['stage'], 'stageEvidence': inv['stageEvidence'], 'inventorySha256': sha(Path(inventory)), 'snapshot': snapshot, 'candidates': candidates, 'protected': protected, 'unclassified': sorted(set(snapshot) - seen), 'candidateBytes': sum(x['bytes'] for x in candidates), 'minimumRetentionDays': 7, 'permanentDeletion': False}
    return {**body, 'planSha256': digest(body)}


@contextmanager
def lock(root):
    store = root / '.cleanup'
    if store.is_symlink():
        raise ValueError('Cleanup store must not be a symlink')
    store.mkdir(exist_ok=True)
    p = store / 'lock'
    with p.open('x') as f:
        f.write(str(os.getpid()))
    try:
        yield store
    finally:
        p.unlink()


def apply(root, inventory, plan_path, approval, backup_dir):
    root = project(root)
    plan = read(plan_path)
    body = {k: v for k, v in plan.items() if k != 'planSha256'}
    if digest(body) != approval or plan.get('planSha256') != approval:
        raise ValueError('Exact reviewed plan SHA256 approval required')
    if scan(root, inventory) != plan:
        raise ValueError('Stale plan: rescan and obtain new batch approval')
    if not plan['candidates']:
        raise ValueError('No eligible files')
    backup = Path(backup_dir).absolute()
    if any(x.is_symlink() for x in (backup, *backup.parents)):
        raise ValueError('Backup path must not traverse symlinks')
    if backup.resolve().is_relative_to(root) or root.is_relative_to(backup.resolve()):
        raise ValueError('Use a separate backup directory outside the project')
    backup.mkdir(parents=True, exist_ok=True)
    with lock(root) as store:
        if scan(root, inventory) != plan:
            raise ValueError('Project changed before backup')
        batch = uuid.uuid4().hex
        archive = backup / (batch + '.zip')
        with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_STORED) as z:
            for item in plan['candidates']:
                z.write(local(root, item['path']), item['path'])
            z.writestr('cleanup-backup-manifest.json', json.dumps(plan, ensure_ascii=False))
        with archive.open('rb') as f:
            os.fsync(f.fileno())
        with zipfile.ZipFile(archive) as z:
            if z.testzip() is not None:
                raise ValueError('Backup CRC failed')
            for item in plan['candidates']:
                h = hashlib.sha256()
                with z.open(item['path']) as f:
                    for b in iter(lambda: f.read(1024 * 1024), b''):
                        h.update(b)
                if h.hexdigest() != item['sha256']:
                    raise ValueError('Backup hash failed')
        if scan(root, inventory) != plan:
            raise ValueError('Project changed during backup; nothing quarantined')
        target = store / batch
        target.mkdir()
        record = {'batch': batch, 'createdAt': datetime.now(timezone.utc).isoformat(), 'project': str(root), 'backup': str(archive), 'backupSha256': sha(archive), 'planSha256': approval, 'minimumRetentionDays': 7, 'status': 'quarantining', 'items': plan['candidates']}
        journal = target / 'journal.json'
        write(journal, record)
        for item in plan['candidates']:
            src = local(root, item['path'])
            if sha(src) != item['sha256']:
                raise ValueError('File changed; use journal to restore partial batch')
            dst = target / 'files' / item['path']
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)
        record['status'] = 'quarantined'
        write(journal, record)
        return record


def restore(root, batch):
    root = project(root)
    if not re.fullmatch(r'[0-9a-f]{32}', batch):
        raise ValueError('Invalid batch')
    with lock(root) as store:
        target = store / batch
        if target.is_symlink():
            raise ValueError('Symlink batch')
        journal = target / 'journal.json'
        if journal.is_symlink():
            raise ValueError('Symlink journal')
        record = read(journal)
        if record['project'] != str(root):
            raise ValueError('Wrong project')
        pending = []
        for item in record['items']:
            dst = local(root, item['path'])
            src = target / 'files' / item['path']
            if any(x.is_symlink() for x in (src, *src.parents)):
                raise ValueError('Symlink quarantine')
            if src.exists():
                if dst.exists() or sha(src) != item['sha256']:
                    raise ValueError('Restore collision or changed quarantine: ' + item['path'])
                pending.append((src, dst))
            elif not dst.is_file() or sha(dst) != item['sha256']:
                raise ValueError('Missing or modified restore data: ' + item['path'])
        for src, dst in pending:
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)
        record['status'] = 'restored'
        write(journal, record)
        return record


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    for command in ('scan', 'apply', 'restore'):
        p = sub.add_parser(command)
        p.add_argument('--project', required=True)
        if command != 'restore':
            p.add_argument('--inventory', required=True)
        if command == 'scan':
            p.add_argument('--out', required=True)
        elif command == 'apply':
            p.add_argument('--plan', required=True)
            p.add_argument('--approved-plan-sha256', required=True)
            p.add_argument('--backup-dir', required=True)
        else:
            p.add_argument('--batch', required=True)
    a = ap.parse_args()
    if a.command == 'scan':
        out = Path(a.out).absolute()
        # Reports must not become self-references or alter the approved snapshot.
        if out.resolve().is_relative_to(project(a.project)):
            raise ValueError('Write scan reports outside the project')
        result = scan(a.project, a.inventory)
        if out.exists():
            raise ValueError('Use a new report name')
        write(out, result)
        print(json.dumps({k: result[k] for k in ('planSha256', 'candidateBytes', 'candidates', 'protected', 'unclassified')}, ensure_ascii=False))
    elif a.command == 'apply':
        print(json.dumps(apply(a.project, a.inventory, a.plan, a.approved_plan_sha256, a.backup_dir), ensure_ascii=False))
    else:
        print(json.dumps(restore(a.project, a.batch), ensure_ascii=False))


if __name__ == '__main__':
    main()
