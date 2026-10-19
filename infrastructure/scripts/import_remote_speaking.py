"""Validate remote DH_live assets and install them with recoverable backups."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument('archive', type=Path)
args = parser.parse_args()
repo = Path(__file__).resolve().parents[2]
folders = ['assets', 'assets2', 'daniel-fictional']
names = ['01.mp4', 'combined_data.json.gz', 'listening.mp4']
allowed = {'manifest.json', *(f'{folder}/{name}' for folder in folders for name in names)}
payload = {}
with zipfile.ZipFile(args.archive) as archive:
    assert len(archive.infolist()) == len(allowed) and set(archive.namelist()) == allowed
    assert sum(item.file_size for item in archive.infolist()) < 30_000_000
    manifest = json.loads(archive.read('manifest.json'))
    for folder in folders:
        info = manifest[folder]
        assert 190 <= info['frames'] <= 205 and info['fps'] == 25
        assert info['frames'] == info['landmarkFrames']
        for name in names:
            data = archive.read(f'{folder}/{name}')
            checksum = info['files'][name]
            assert len(data) == checksum['bytes'] and hashlib.sha256(data).hexdigest() == checksum['sha256']
            if name.endswith('.mp4'):
                assert data[4:8] == b'ftyp'
            else:
                assert len(data) < 8_000_000
                decoded = gzip.decompress(data)
                assert len(decoded) < 30_000_000
                landmarks = json.loads(decoded)
                assert landmarks['frame_num'] == info['landmarkFrames'] == len(landmarks['json_data'])
            payload[(folder, name)] = data
backup = repo/'artifacts/jury-remote/previous-speaking'
backup.mkdir(parents=True, exist_ok=True)
for (folder, name), data in payload.items():
    target = repo/'frontend/public/vendor/dh-live'/folder/name
    if target.exists():
        previous = backup/f'{folder}-{hashlib.sha256(target.read_bytes()).hexdigest()[:12]}-{name}'
        if not previous.exists():
            shutil.copyfile(target, previous)
    pending = target.with_name(target.name + '.incoming')
    pending.write_bytes(data)
    pending.replace(target)
    print(f'Installed {folder}/{name}: {len(data)} bytes')
