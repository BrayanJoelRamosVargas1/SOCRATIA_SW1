"""Validate and install remote videos, without running local inference."""
import argparse
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
allowed = {'manifest.json', *(f'{folder}/listening.mp4' for folder in folders)}
with zipfile.ZipFile(args.archive) as archive:
    assert set(archive.namelist()) == allowed and len(archive.infolist()) == 4, 'Unexpected archive contents'
    assert sum(item.file_size for item in archive.infolist()) < 30_000_000, 'Archive exceeds video budget'
    manifest = json.loads(archive.read('manifest.json'))
    videos = {}
    for folder in folders:
        data = archive.read(f'{folder}/listening.mp4')
        info = manifest[folder]
        assert info['frames'] == 120 and info['fps'] == 15, 'Unexpected clip timing'
        assert len(data) == info['bytes'] and hashlib.sha256(data).hexdigest() == info['sha256'], 'Checksum mismatch'
        assert data[4:8] == b'ftyp', 'Not an MP4 file'
        videos[folder] = data
backup = repo/'artifacts/jury-remote/previous-clips'
backup.mkdir(parents=True, exist_ok=True)
for folder, data in videos.items():
    target = repo/'frontend/public/vendor/dh-live'/folder/'listening.mp4'
    if target.exists():
        previous = backup/f'{folder}-{hashlib.sha256(target.read_bytes()).hexdigest()[:12]}.mp4'
        if not previous.exists(): shutil.copyfile(target, previous)
    pending = target.with_suffix('.incoming.mp4')
    pending.write_bytes(data)
    pending.replace(target)
    print(f'Installed {folder}: {len(data)} bytes')
