"""Compare a pre-integration inventory with a fresh, read-only SHA-256 audit."""
import argparse
import hashlib
import json
from pathlib import Path


def inventory(root):
    rows = []
    for path in sorted(root.rglob('*')):
        if path.is_file():
            before = path.stat()
            with path.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            after = path.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise RuntimeError('Source changed during the audit')
            rows.append({'path': str(path.relative_to(root)), 'size': before.st_size,
                         'mtime_ns': before.st_mtime_ns, 'sha256': digest})
    return rows


def fingerprint(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode('utf-8')).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('D:/Paper/passage6'))
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    before = json.loads(args.baseline.read_text(encoding='utf-8'))
    after = inventory(args.root)
    result = {'status': 'PASS' if before == after else 'FAIL',
              'source_root': str(args.root), 'files_before': len(before), 'files_after': len(after),
              'bytes': sum(row['size'] for row in after), 'before_manifest_sha256': fingerprint(before),
              'after_manifest_sha256': fingerprint(after), 'checks': ['relative paths', 'size', 'mtime_ns', 'file SHA-256']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))
    if before != after:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
