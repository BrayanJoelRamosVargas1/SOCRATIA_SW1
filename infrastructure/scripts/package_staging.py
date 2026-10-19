"""Package current deployment sources, excluding credentials and local runtime data."""
import argparse
import hashlib
from pathlib import Path
import tarfile

parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
excluded = {'.git', 'node_modules', '.next', '.venv', '.test-deps', '__pycache__',
            '.pytest_cache', '.ruff_cache', 'uploads', 'tests', '.mypy_cache'}

def deploy_filter(info):
    path = Path(info.name)
    if any(part in excluded for part in path.parts):
        return None
    if any(part.startswith('.env') for part in path.parts):
        return None
    if info.issym() or info.islnk():
        return None
    if path.suffix.lower() in {'.pem', '.key', '.log', '.db', '.sqlite', '.pyc', '.tsbuildinfo'}:
        return None
    info.uid = info.gid = 0
    info.uname = info.gname = ''
    return info

args.output.parent.mkdir(parents=True, exist_ok=True)
with tarfile.open(args.output, 'x:gz') as archive:
    for relative in ('backend', 'frontend', 'infrastructure', 'compose.staging.yaml'):
        archive.add(root / relative, arcname=relative, filter=deploy_filter)
with tarfile.open(args.output) as archive:
    names = archive.getnames()
    assert not any(Path(name).name.startswith('.env') for name in names)
digest = hashlib.file_digest(args.output.open('rb'), 'sha256').hexdigest()
print(f'Archive: {args.output}\nBytes: {args.output.stat().st_size}\nSHA256: {digest}\nEntries: {len(names)}')
