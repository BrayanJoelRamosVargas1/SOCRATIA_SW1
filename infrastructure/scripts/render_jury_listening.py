"""Render actual head/eye motion offline with FasterLivePortrait ONNX on CPU.

Uses procedural pose/eye targets, not another person's recorded expressions.
Heavy weights remain outside the deployed application.
"""
import argparse
import copy
import os
from pathlib import Path
import sys
import time
import subprocess
import hashlib
import tempfile

parser=argparse.ArgumentParser()
parser.add_argument('--engine-root',type=Path,required=True)
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--frames',type=int,default=120)
parser.add_argument('--fps',type=int,default=15)
parser.add_argument('--phase',type=float,default=0)
parser.add_argument('--eye-mode',choices=['preserve','synthetic'],default='preserve')
parser.add_argument('--threads',type=int,default=4)
parser.add_argument('--directml-runtime',type=Path,help='Optional isolated onnxruntime-directml installation')
parser.add_argument('--device-id',type=int,default=0)
parser.add_argument('--provider',choices=['cpu','cuda'],default='cpu')
parser.add_argument('--allow-local-render',action='store_true')
args=parser.parse_args()
if os.name=='nt' and not args.allow_local_render:
    parser.error('Local rendering is disabled to protect this laptop. Use the remote notebook.')
source=args.source.resolve(); output=args.output.resolve(); root=args.engine_root.resolve()
os.chdir(root); sys.path.insert(0,str(root))
os.environ['SOCRATIA_PORTRAIT_THREADS']=str(max(1,args.threads))
os.environ['SOCRATIA_PORTRAIT_DML']='1' if args.directml_runtime else '0'
os.environ['SOCRATIA_PORTRAIT_DEVICE']=str(args.device_id)
os.environ['SOCRATIA_PORTRAIT_CUDA']='1' if args.provider=='cuda' else '0'
if args.directml_runtime: sys.path.insert(0,str(args.directml_runtime.resolve()))

# The upstream ORT path still initializes CUDA unconditionally in two wrappers.
# Adapt the external checkout for CPU, preserving the model math and ONNX files.
for relative in ['src/models/base_model.py','src/models/face_analysis_model.py']:
    path=root/relative
    text=path.read_text(encoding='utf-8')
    text=text.replace('self.device = torch.cuda.current_device()', 'self.device = torch.device("cpu")')
    text=text.replace('self.cudaStream = torch.cuda.current_stream().cuda_stream','self.cudaStream = None')
    if relative.endswith('face_analysis_model.py'):
        text=text.replace('from insightface.app.common import Face', 'class Face(dict):\n    def __getattr__(self, name):\n        return self[name]')
    path.write_text(text,encoding='utf-8')
path=root/'src/models/__init__.py'
text=path.read_text(encoding='utf-8').replace('from .mediapipe_face_model import MediaPipeFaceModel','')
path.write_text(text,encoding='utf-8')
path=root/'src/models/predictor.py'
text=path.read_text(encoding='utf-8').replace("providers = ['CUDAExecutionProvider', 'CoreMLExecutionProvider', 'CPUExecutionProvider']","providers = ['CPUExecutionProvider']")
text=text.replace('# opts.inter_op_num_threads = kwargs.get("num_threads", 4)','opts.inter_op_num_threads = 1')
text=text.replace('# opts.intra_op_num_threads = kwargs.get("num_threads", 4)','opts.intra_op_num_threads = 2')
text=text.replace('opts.intra_op_num_threads = 2','opts.intra_op_num_threads = int(os.environ.get("SOCRATIA_PORTRAIT_THREADS", "2"))')
text=text.replace("providers = ['CPUExecutionProvider']", "providers = [('DmlExecutionProvider', {'device_id': int(os.environ.get('SOCRATIA_PORTRAIT_DEVICE', '0'))}), 'CPUExecutionProvider'] if os.environ.get('SOCRATIA_PORTRAIT_DML') == '1' else ['CPUExecutionProvider']")
text=text.replace('opts = onnxruntime.SessionOptions()\n','opts = onnxruntime.SessionOptions(); opts.enable_mem_pattern = False; opts.log_severity_level = 3\n')
text=text.replace("providers = [('DmlExecutionProvider'", "providers = [('CUDAExecutionProvider', {'cudnn_conv_algo_search': 'DEFAULT', 'use_tf32': '0'}), 'CPUExecutionProvider'] if os.environ.get('SOCRATIA_PORTRAIT_CUDA') == '1' else [('DmlExecutionProvider'")
path.write_text(text,encoding='utf-8')

import cv2
import numpy as np
import torch
import onnx
import imageio_ffmpeg
import onnxruntime
if args.provider=='cuda' and 'CUDAExecutionProvider' not in onnxruntime.get_available_providers():
    raise RuntimeError('Remote CUDA provider unavailable; refusing CPU rendering')
from omegaconf import OmegaConf
from src.pipelines.faster_live_portrait_pipeline import FasterLivePortraitPipeline
from src.utils.utils import get_rotation_matrix, calc_eye_close_ratio, calc_lip_close_ratio
torch.set_num_threads(max(1,args.threads))
cfg=OmegaConf.load(root/'configs/onnx_infer.yaml')
cpu_model=root/'checkpoints/liveportrait_onnx/warping_spade-cpu.onnx'
if not cpu_model.exists():
    model=onnx.load(root/'checkpoints/liveportrait_onnx/warping_spade-fix.onnx')
    # The TensorRT export uses a custom GridSample3D; standard ONNX opset 20
    # supports volumetric GridSample directly on ORT CPU.
    for node in model.graph.node:
        if node.op_type=='GridSample3D': node.op_type='GridSample'
    model=onnx.version_converter.convert_version(model,20)
    onnx.checker.check_model(model)
    onnx.save(model,cpu_model)
cfg.models.warping_spade.model_path=str(cpu_model)
cfg.infer_params.animation_region='pose'
cfg.infer_params.flag_eye_retargeting=args.eye_mode=='synthetic'
cfg.infer_params.flag_relative_motion=False
cfg.infer_params.flag_pasteback=True
cfg.infer_params.source_max_dim=768
pipeline=FasterLivePortraitPipeline(cfg)
pipeline.device=torch.device('cpu')
if not pipeline.prepare_source(str(source)): raise RuntimeError('No source face')
info=pipeline.src_infos[0]
base=copy.deepcopy(info[0][0])
landmarks=info[0][1]
base['R']=get_rotation_matrix(base['pitch'],base['yaw'],base['roll'])
eyes=calc_eye_close_ratio(landmarks[None]); lips=calc_lip_close_ratio(landmarks[None])
output.parent.mkdir(parents=True,exist_ok=True)
height,width=pipeline.src_imgs[0].shape[:2]
working=output.with_name(output.stem+'.render.mp4')
writer=cv2.VideoWriter(str(working),cv2.VideoWriter_fourcc(*'mp4v'),args.fps,(width,height))
if not writer.isOpened(): raise RuntimeError('Cannot open output video')
started=time.monotonic()
cache_key=hashlib.sha256(source.read_bytes()+repr(('pose-eye-v3',args.eye_mode,args.frames,args.fps,args.phase)).encode()).hexdigest()[:24]
frame_cache=Path(tempfile.gettempdir())/'socratia-portrait-frames'/cache_key
frame_cache.mkdir(parents=True,exist_ok=True)
try:
    for frame in range(args.frames):
        cached=frame_cache/f'{frame:04d}.png'
        saved=cv2.imread(str(cached)) if cached.exists() else None
        if saved is not None:
            writer.write(saved)
            if frame%10==0: print(f'{frame+1}/{args.frames} cached',flush=True)
            continue
        t=frame/args.fps
        motion=copy.deepcopy(base)
        # Starts/ends neutral for crossfades; small actual rotations, not image shifts.
        envelope=np.sin(np.pi*frame/max(1,args.frames-1))**2
        motion['yaw']=base['yaw']+np.float32(3.4*(.75*np.sin(t*.65+args.phase)+.25*np.sin(t*1.4+args.phase*.6))*envelope)
        motion['pitch']=base['pitch']+np.float32(2.0*(np.sin(t*1.1)+.2*np.sin(t*.4+args.phase))*envelope)
        motion['roll']=base['roll']+np.float32(.9*np.sin(t*.55+args.phase)*envelope)
        motion['R']=get_rotation_matrix(motion['pitch'],motion['yaw'],motion['roll'])
        blink_centers=[1.5+(args.phase%1)*.7,4.7+(args.phase%1)*.5,7.15]
        blink=max(max(0,1-abs(t-center)/.13) for center in blink_centers)
        eye_target=np.array([[eyes.mean()*(1-blink*.94)]],dtype=np.float32)
        _,result=pipeline.run_with_pkl([motion,eye_target,lips],pipeline.src_imgs[0],info,first_frame=frame==0)
        if isinstance(result,torch.Tensor):result=result.cpu().numpy()
        rendered=cv2.cvtColor(np.asarray(result,dtype=np.uint8),cv2.COLOR_RGB2BGR)
        pending=cached.with_suffix('.tmp.png')
        if not cv2.imwrite(str(pending),rendered): raise RuntimeError('Cannot checkpoint rendered frame')
        pending.replace(cached)
        writer.write(rendered)
        if frame%10==0: print(f'{frame+1}/{args.frames} {time.monotonic()-started:.1f}s',flush=True)
finally:
    writer.release()
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-i',str(working),'-an',
                '-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p',
                '-movflags','+faststart',str(output)],check=True,
               stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
working.unlink()
print('Rendered',output,flush=True)
