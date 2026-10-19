"""Prepare animated DH_live speech assets in a remote Linux GPU runtime only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument('--workspace', type=Path, default=Path('/content/socratia-speaking'))
args = parser.parse_args()
if os.name == 'nt':
    parser.error('Use Colab; local speaking-asset preparation is disabled.')
import torch
assert torch.cuda.is_available(), 'A remote GPU is required.'
import cv2
import gdown
import gzip

work = args.workspace.resolve()
engine = Path('/content/DH_live')
if not engine.exists():
    subprocess.run(['git','clone','https://github.com/kleinlee/DH_live.git',str(engine)],check=True)
subprocess.run(['git','-C',str(engine),'checkout','4467e97cd97194c2c54762043cf121c6d313db12'],check=True)
checkpoint = engine/'checkpoint'
models = {
    'epoch_40_new.pth': ('DINet_mini/epoch_40_new.pth',25213429),
    'face_landmarker_256x256.pt': ('face_landmarker_256x256.pt',4902205),
    'scrfd_2.5g_kps.onnx': ('scrfd_2.5g_kps.onnx',3291017),
}
if any(not (checkpoint/relative).exists() for relative,_ in models.values()):
    listing = gdown.download_folder('https://drive.google.com/drive/folders/1az5WEWOFmh0_yrF3I9DEyctMyjPolo8V',skip_download=True,use_cookies=False)
    for item in listing:
        name = Path(item.path).name
        if name not in models: continue
        relative, size = models[name]
        target = checkpoint/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():
            gdown.download(id=item.id,output=str(target),use_cookies=False)
        assert target.stat().st_size==size, f'Unexpected checkpoint: {name}'
for relative,size in models.values():
    assert (checkpoint/relative).stat().st_size==size
manifest = {}
for folder in ['daniel-fictional','assets','assets2']:
    source = work/'inputs'/folder/'listening.mp4'
    target = work/'results'/folder
    print('Preparing speaking motion:',folder,flush=True)
    result = subprocess.run([sys.executable,'-u',str(work/'scripts/prepare_jury_avatar.py'),
        '--video','--source',str(source),'--engine-root',str(engine),'--output',str(target)],
        capture_output=True,text=True)
    print(result.stdout[-3500:],result.stderr[-2500:],flush=True)
    result.check_returncode()
    data = json.loads(gzip.decompress((target/'combined_data.json.gz').read_bytes()))
    cap = cv2.VideoCapture(str(target/'01.mp4'))
    frames,fps = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),cap.get(cv2.CAP_PROP_FPS)
    assert frames>=190 and abs(fps-25)<.1
    assert len(data['json_data'])==data['frame_num']==frames
    decoded=0
    while True:
        ok,frame=cap.read()
        if not ok: break
        decoded+=1
    cap.release()
    assert decoded==frames
    # The listening source shares the exact framing and timing of the speech input.
    shutil.copyfile(source,target/'listening.mp4')
    manifest[folder]={'frames':frames,'fps':fps,'landmarkFrames':data['frame_num'],'files':{}}
    for name in ['01.mp4','combined_data.json.gz','listening.mp4']:
        content=(target/name).read_bytes()
        manifest[folder]['files'][name]={'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()}
(work/'results/manifest.json').write_text(json.dumps(manifest,indent=2))
archive_path=work/'socratia-speaking-results.zip'
with zipfile.ZipFile(archive_path,'w',zipfile.ZIP_DEFLATED) as archive:
    for folder in manifest:
        for name in manifest[folder]['files']:
            archive.write(work/'results'/folder/name,f'{folder}/{name}')
    archive.write(work/'results/manifest.json','manifest.json')
print('SPEAKING_READY',archive_path,flush=True)
