"""Package public avatar frames and a Colab notebook; never runs inference."""
import ast
import json
from pathlib import Path
import tempfile
import zipfile

repo = Path(__file__).resolve().parents[2]
destination = repo / 'artifacts/jury-remote'
destination.mkdir(parents=True, exist_ok=True)
bundle = destination / 'socratia-jury-inputs.zip'
with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in ['render_jury_listening.py', 'download_portrait_motion.py']:
        source = Path(__file__).with_name(name)
        ast.parse(source.read_text(encoding='utf-8'))
        archive.write(source, 'scripts/' + name)
    for name in ['alex', 'elena', 'daniel']:
        source = Path(tempfile.gettempdir()) / f'socratia-{name}-neutral.png'
        if not source.exists():
            raise FileNotFoundError(f'Missing authorized avatar frame: {source}')
        archive.write(source, 'inputs/' + name + '.png')

cells = []
def markdown(source):
    cells.append(dict(cell_type='markdown', metadata={}, source=source))
def code(source):
    ast.parse(source)
    cells.append(dict(cell_type='code', metadata={}, source=source, outputs=[], execution_count=None))

markdown('''# Socratia · generación remota del jurado

Este notebook procesa únicamente los tres personajes del ZIP. No incluye cuentas,
claves, cámara del estudiante ni base de datos. Los modelos y el render se ejecutan
en la máquina de Google Colab. No seleccionar «Conectar a entorno local».

1. En **Entorno de ejecución → Cambiar tipo de entorno**, seleccionar una GPU gratuita.
2. Ejecutar las celdas en orden y subir `socratia-jury-inputs.zip` cuando lo solicite.
3. Descargar `socratia-jury-results.zip` y devolver ese archivo a Codex para integrarlo.

Si no hay GPU gratuita disponible, detenerse y probar más tarde. No contratar un
plan ni montar Google Drive. Se procesan los personajes uno por uno; se conserva
el progreso de fotogramas mientras siga vivo el entorno. Código del motor MIT;
los pesos y personajes conservan sus condiciones. Uso de prototipo académico.
''')
code('''import os, subprocess, sys
assert not sys.platform.startswith('win'), 'Este notebook debe ejecutarse en Colab, no en tu laptop.'
import torch
assert torch.cuda.is_available(), 'No hay GPU remota. Detén la ejecución; no usar CPU ni entorno local.'
print('GPU remota:', torch.cuda.get_device_name(0))
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'onnxruntime-gpu>=1.20,<2', 'onnx>=1.16', 'omegaconf>=2.3', 'torchgeometry==0.1.2', 'ffmpeg-python==0.2.0', 'imageio-ffmpeg>=0.6', 'opencv-python-headless>=4.10', 'tqdm', 'pillow'], check=True)
''')
code('''from google.colab import files
from pathlib import Path
import zipfile
if not Path('/content/socratia-jury-inputs.zip').exists():
    uploaded = files.upload()
    assert set(uploaded) == {'socratia-jury-inputs.zip'}, 'Sube solo socratia-jury-inputs.zip.'
work = Path('/content/socratia-jury')
work.mkdir(exist_ok=True)
allowed = {'scripts/render_jury_listening.py', 'scripts/download_portrait_motion.py', 'inputs/alex.png', 'inputs/elena.png', 'inputs/daniel.png'}
with zipfile.ZipFile('socratia-jury-inputs.zip') as archive:
    assert set(archive.namelist()) == allowed, 'Contenido inesperado en el paquete.'
    assert sum(item.file_size for item in archive.infolist()) < 10_000_000, 'Paquete demasiado grande.'
    archive.extractall(work)
engine = Path('/content/FasterLivePortrait')
if not engine.exists():
    subprocess.run(['git', 'clone', 'https://github.com/warmshao/FasterLivePortrait.git', str(engine)], check=True)
subprocess.run(['git', '-C', str(engine), 'checkout', '8aad3602177547aaa5e4beec0c3ef5b7944e7a1f'], check=True)
subprocess.run([sys.executable, str(work/'scripts/download_portrait_motion.py'), str(engine/'checkpoints/liveportrait_onnx')], check=True)
''')
code('''import onnxruntime as ort
assert 'CUDAExecutionProvider' in ort.get_available_providers(), 'Falta CUDA; detenerse.'
output = work/'results'
for name, folder, phase in [('alex','assets',.2), ('elena','assets2',1.3), ('daniel','daniel-fictional',2.7)]:
    target = output/folder/'listening.mp4'
    result = subprocess.run([sys.executable, '-u', str(work/'scripts/render_jury_listening.py'), '--engine-root', str(engine), '--source', str(work/'inputs'/f'{name}.png'), '--output', str(target), '--provider', 'cuda', '--threads', '2', '--frames', '120', '--fps', '15', '--phase', str(phase)], capture_output=True, text=True)
    print(name, result.stdout[-4000:], result.stderr[-2000:], flush=True)
    result.check_returncode()
print('Tres clips generados. Falta validar y descargar.')
''')
code('''import cv2, hashlib, json
manifest = {}
for folder in ['assets','assets2','daniel-fictional']:
    clip = output/folder/'listening.mp4'
    video = cv2.VideoCapture(str(clip))
    assert int(video.get(cv2.CAP_PROP_FRAME_COUNT)) == 120, f'Clip incompleto: {folder}'
    assert abs(video.get(cv2.CAP_PROP_FPS)-15) < .01
    decoded = 0
    while True:
        ok, frame = video.read()
        if not ok: break
        assert frame.mean() > 5, f'Fotograma vacío: {folder}'
        decoded += 1
    video.release()
    assert decoded == 120
    manifest[folder] = {'frames':decoded,'fps':15,'bytes':clip.stat().st_size,'sha256':hashlib.sha256(clip.read_bytes()).hexdigest()}
(output/'manifest.json').write_text(json.dumps(manifest,indent=2))
result = Path('/content/socratia-jury-results.zip')
with zipfile.ZipFile(result,'w',zipfile.ZIP_DEFLATED) as archive:
    for clip in output.rglob('*.mp4'): archive.write(clip,clip.relative_to(output))
    archive.write(output/'manifest.json','manifest.json')
files.download(str(result))
''')
for index, cell in enumerate(cells): cell['id'] = f'socratia-{index}'
notebook = dict(cells=cells, metadata=dict(colab=dict(name='Socratia-jurado-remoto.ipynb'),
    kernelspec=dict(display_name='Python 3', language='python', name='python3'), accelerator='GPU'), nbformat=4, nbformat_minor=5)
(destination/'Socratia-jurado-remoto.ipynb').write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Notebook and input bundle: {destination}')
print(f'Input bundle: {bundle.stat().st_size} bytes; public avatar frames only.')
