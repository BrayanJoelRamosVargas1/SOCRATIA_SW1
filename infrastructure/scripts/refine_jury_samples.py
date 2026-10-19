"""Restore Alex's recorded expressions and distinguish cached sample voices.

No model inference: file copies and three short audio filters, two threads.
"""
import argparse
from pathlib import Path
import shutil
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--ffmpeg', type=Path, required=True)
args = parser.parse_args()
repo = Path(__file__).resolve().parents[2]
vendor = repo/'frontend/public/vendor/dh-live'
backup = repo/'artifacts/jury-remote/expression-voice-backup'
backup.mkdir(parents=True, exist_ok=True)
for name in ['01.mp4', 'combined_data.json.gz', 'listening.mp4']:
    target = vendor/'assets'/name
    saved = backup/('alex-'+name)
    if not saved.exists(): shutil.copyfile(target,saved)
original = repo/'artifacts/jury-remote/previous-speaking'
shutil.copyfile(original/'assets-b70c76468c33-01.mp4',vendor/'assets/01.mp4')
shutil.copyfile(original/'assets-6c12fbd0ac5b-combined_data.json.gz',vendor/'assets/combined_data.json.gz')
# Native clip already contains natural eyes/head motion and neutral lips.
shutil.copyfile(vendor/'assets/01.mp4',vendor/'assets/listening.mp4')
for name,pitch,pace in [('alex',1.06,.98),('elena',1.10,1.05),('daniel',.88,.90)]:
    target = vendor/f'common/neural/kokoro-{name}.wav'
    saved = backup/target.name
    if not saved.exists(): shutil.copyfile(target,saved)
    subprocess.run([str(args.ffmpeg),'-v','error','-y','-i',str(saved),
        '-af',f'asetrate=24000*{pitch},aresample=24000,atempo={pace/pitch}',
        '-threads','2','-c:a','pcm_s16le',str(target)],check=True)
    print(f'{name}: pitch {pitch}, pace {pace}')
