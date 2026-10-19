"""Create/resume the three local listening clips without provider APIs."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile
import os

parser = argparse.ArgumentParser()
parser.add_argument('--engine-root', type=Path, required=True)
parser.add_argument('--directml-runtime', type=Path)
parser.add_argument('--device-id', type=int, default=0)
parser.add_argument('--allow-local-render', action='store_true')
args = parser.parse_args()
if os.name == 'nt' and not args.allow_local_render:
    parser.error('Local rendering is disabled to protect this laptop. Use the remote notebook.')
import cv2
repo = Path(__file__).resolve().parents[2]
assets = repo / 'frontend/public/vendor/dh-live'
renderer = Path(__file__).with_name('render_jury_listening.py')
for folder, name, position, phase in [
    ('assets2', 'elena', 1.2, 1.3),
    ('daniel-fictional', 'daniel', .5, 2.7),
    ('assets', 'alex', .5, .2),
]:
    output = assets / folder / 'listening.mp4'
    existing = cv2.VideoCapture(str(output)) if output.exists() else None
    if existing:
        complete = existing.get(cv2.CAP_PROP_FRAME_COUNT) == 120
        existing.release()
        if complete:
            print(f'{name}: complete', flush=True)
            continue
    capture = cv2.VideoCapture(str(assets / folder / '01.mp4'))
    capture.set(cv2.CAP_PROP_POS_MSEC, position * 1000)
    ok, image = capture.read()
    capture.release()
    if not ok:
        raise RuntimeError(f'Cannot read neutral frame: {name}')
    source = Path(tempfile.gettempdir()) / f'socratia-{name}-neutral.png'
    if not cv2.imwrite(str(source), image):
        raise RuntimeError(f'Cannot save neutral frame: {name}')
    command = [sys.executable, '-u', str(renderer), '--engine-root', str(args.engine_root.resolve()),
               '--source', str(source), '--output', str(output), '--frames', '120', '--phase', str(phase)]
    if args.directml_runtime:
        command += ['--directml-runtime', str(args.directml_runtime.resolve()), '--device-id', str(args.device_id)]
    if args.allow_local_render:
        command += ['--allow-local-render']
    subprocess.run(command, check=True)
