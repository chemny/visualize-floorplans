"""Check the shipped H5 bundle against its installed source; no compiler needed."""
import argparse
import hashlib
import json
from pathlib import Path

SCHEMA = 'h5-engine-provenance/1'
MANIFEST = 'engine.provenance.json'


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_inputs(root):
    root = Path(root).resolve()
    source = root / 'assets/h5/source'
    paths = [p for p in source.rglob('*') if p.is_file()
             and not any(part.startswith('.') or part == 'node_modules'
                         for part in p.relative_to(source).parts)
             and p.suffix in {'.js', '.mjs', '.css', '.json'}]
    paths.append(root / 'assets/h5/version.json')
    if not (source / 'app.js').is_file():
        raise ValueError('H5 source/app.js is missing')
    return [{'path': p.relative_to(root).as_posix(), 'sha256': file_sha(p)}
            for p in sorted(paths, key=lambda p: p.relative_to(root).as_posix())]


def source_fingerprint(inputs):
    lines = ''.join(row['path'] + '\0' + row['sha256'] + '\n' for row in inputs)
    return hashlib.sha256(lines.encode('utf-8')).hexdigest()


def require_current_engine(root):
    """Fail closed on missing/stale provenance; never stamp an existing bundle."""
    root = Path(root).resolve()
    assets = root / 'assets/h5'
    path = assets / MANIFEST
    remedy = 'Rebuild with scripts/production/rebuild_h5.mjs using existing dependencies.'
    try:
        evidence = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise ValueError('Missing or invalid H5 engine provenance. ' + remedy) from error
    if evidence.get('schema') != SCHEMA:
        raise ValueError('Unsupported H5 engine provenance. ' + remedy)
    inputs = source_inputs(root)
    if evidence.get('inputs') != inputs or evidence.get('sourceSha256') != source_fingerprint(inputs):
        raise ValueError('H5 source changed since the last engine build. ' + remedy)
    for name, key in [('engine.js', 'engineSha256'), ('component-types.json', 'registrySha256')]:
        if not (assets / name).is_file() or evidence.get(key) != file_sha(assets / name):
            raise ValueError('H5 bundled ' + name + ' differs from its provenance. ' + remedy)
    return {'status': 'pass', 'schema': SCHEMA,
            'sourceSha256': evidence['sourceSha256'],
            'engineSha256': evidence['engineSha256'],
            'registrySha256': evidence['registrySha256'],
            'manifestSha256': file_sha(path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check'])
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    try:
        print(json.dumps(require_current_engine(args.root)))
    except (ValueError, OSError) as error:
        print(json.dumps({'status': 'failed', 'error': str(error)}))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
