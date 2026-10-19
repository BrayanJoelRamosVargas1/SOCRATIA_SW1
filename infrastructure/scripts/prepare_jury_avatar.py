"""Convert a portrait or animated clip into DH_live assets with official tools.

Requires an explicitly provisioned DH_live checkout and model checkpoints.
The source remains intact. Run preparation remotely; Windows requires an explicit override.
"""
import argparse
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--engine-root',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--video',action='store_true',help='Use an animated source clip instead of looping a portrait')
parser.add_argument('--allow-local-render',action='store_true')
args=parser.parse_args()
if os.name=='nt' and not args.allow_local_render:
    parser.error('Local avatar preparation is disabled. Use the remote Colab runtime.')
root=args.engine_root.resolve()
work=(root/'video_data'/'socratia-daniel-fictional').resolve()
# Upstream removes work/frames recursively. Verify the absolute path before it runs.
assert work.parent == (root/'video_data').resolve()
assert (work/'frames').resolve().is_relative_to(work)
work.mkdir(parents=True,exist_ok=True)
import imageio_ffmpeg
bin_dir=root/'.socratia-bin'
bin_dir.mkdir(exist_ok=True)
ffmpeg=bin_dir/('ffmpeg.exe' if os.name=='nt' else 'ffmpeg')
if not ffmpeg.exists(): shutil.copyfile(imageio_ffmpeg.get_ffmpeg_exe(),ffmpeg)
if os.name != 'nt': ffmpeg.chmod(0o755)
environment=os.environ.copy()
environment['PATH']=str(bin_dir)+os.pathsep+environment.get('PATH','')
environment['OMP_NUM_THREADS']='2'
environment['MKL_NUM_THREADS']='2'
environment['PYTHONUTF8']='1'
environment['PYTHONIOENCODING']='utf-8'
video=work/'portrait.mp4'
inputs=['-i',str(args.source.resolve())] if args.video else ['-loop','1','-i',str(args.source.resolve())]
duration=[] if args.video else ['-t','2']
scale='scale=trunc(iw/2)*2:trunc(ih/2)*2' if args.video else 'scale=576:768'
subprocess.run([str(ffmpeg),'-y',*inputs,'-vf',scale,*duration,'-an','-r','25','-c:v','libx264','-pix_fmt','yuv420p',str(video)],check=True,env=environment,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
for script,arguments in [('data_preparation_mini.py',[str(video),str(work)]),('data_preparation_web.py',[str(work)])]:
    code="import runpy,sys,torch; torch.set_num_threads(2); sys.argv="+repr([script,*arguments])+"; runpy.run_path("+repr(script)+",run_name='__main__')"
    if args.video and script == 'data_preparation_mini.py':
        code = "import runpy,torch; torch.set_num_threads(2); module=runpy.run_path('data_preparation_mini.py'); module['data_preparation_mini'](" + repr(str(video)) + "," + repr(str(work)) + ",reverse_option=False)"
    if os.name != 'nt': code = 'import subprocess; subprocess.CREATE_NO_WINDOW=0; ' + code
    subprocess.run([sys.executable,'-c',code],cwd=root,env=environment,check=True)
args.output.mkdir(parents=True,exist_ok=True)
for name in ['01.mp4','combined_data.json.gz']:
    source=work/'assets'/name
    if not source.is_file(): raise RuntimeError(f'Missing avatar output: {name}')
    if args.video and name == '01.mp4':
        frames = json.loads(gzip.decompress((work/'assets/combined_data.json.gz').read_bytes()))['frame_num']
        # Upstream leaves the last original PNG beside its numbered outputs.
        subprocess.run([str(ffmpeg),'-y','-i',str(source),'-frames:v',str(frames),
            '-an','-c:v','libx264','-crf','16','-threads','2','-pix_fmt','yuv420p',
            '-movflags','+faststart',str(args.output/name)],check=True,env=environment,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    else:
        shutil.copyfile(source,args.output/name)
print('Prepared fictional avatar at',args.output.resolve())
