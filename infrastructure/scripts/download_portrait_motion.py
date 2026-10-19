"""Provision public FasterLivePortrait ONNX weights for offline clip creation."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse
import urllib.request
import time
import shutil

parser=argparse.ArgumentParser()
parser.add_argument('destination',type=Path)
args=parser.parse_args()
args.destination.mkdir(parents=True,exist_ok=True)
names=['warping_spade-fix.onnx','motion_extractor.onnx','landmark.onnx','retinaface_det_static.onnx','face_2dpose_106_static.onnx','appearance_feature_extractor.onnx','stitching.onnx','stitching_eye.onnx','stitching_lip.onnx']
revision='eb937f4bec7186598df2d1f68e1ddbb488ae1de5'
sizes=dict(zip(names,[421233100,112648514,114666491,16923827,5030884,3355896,182363,580926,150609],strict=True))
def download(name):
    path=args.destination/name
    if path.is_file() and path.stat().st_size==sizes[name]: return
    for attempt in range(3):
        try:
            # Avoid cached redirects with expired signed download URLs.
            url='https://huggingface.co/warmshao/FasterLivePortrait/resolve/'+revision+'/liveportrait_onnx/'+name+'?fresh='+str(time.time_ns())
            partial=path.with_suffix('.part')
            offset=partial.stat().st_size if partial.exists() else 0
            request=urllib.request.Request(url,headers={'Range':f'bytes={offset}-'} if offset else {})
            with urllib.request.urlopen(request, timeout=60) as response, partial.open('ab' if response.status==206 else 'wb') as output:
                shutil.copyfileobj(response, output, length=1024*1024)
            if partial.stat().st_size!=sizes[name]:
                raise RuntimeError('Incomplete model: '+name)
            path.with_suffix('.part').replace(path)
            print(name,path.stat().st_size,flush=True)
            return
        except Exception as error:
            print(name,type(error).__name__,flush=True)
    raise RuntimeError('Download failed: '+name)
with ThreadPoolExecutor(max_workers=3) as pool:
    list(pool.map(download,names))
