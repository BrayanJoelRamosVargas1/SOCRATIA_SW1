"""Download public voice models and compare local Spanish synthesis on this PC."""
import argparse
import concurrent.futures
import hashlib
import json
import time
import urllib.request
from pathlib import Path


def download(pair):
    url, path = pair
    if not path.exists():
        temporary = path.with_suffix(path.suffix + '.part')
        urllib.request.urlretrieve(url, temporary)
        temporary.replace(path)
    return {"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--models', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.models.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)
    base = 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/'
    piper = 'https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium/'
    # Quantized model is substantially smaller for a CPU pilot. Keep a stable
    # deployment filename; the source URL and checksum identify the actual asset.
    files = [('https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx', args.models/'kokoro-v1.0.onnx'), (base+'voices-v1.0.bin',args.models/'voices-v1.0.bin')]
    files += [(piper + name, args.models / name) for name in ['es_ES-sharvard-medium.onnx','es_ES-sharvard-medium.onnx.json']]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        hashes = list(pool.map(download, files))
    import soundfile as sf
    import onnxruntime as ort
    from kokoro_onnx import Kokoro
    from piper import PiperVoice
    import wave
    text = 'Explique qué problema resuelve su investigación. ¿Cómo validó los resultados y cuáles son las principales limitaciones de su propuesta?'
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(args.models / 'kokoro-v1.0.onnx'), sess_options=options, providers=['CPUExecutionProvider'])
    kokoro = Kokoro.from_session(session, str(args.models / 'voices-v1.0.bin'))
    results = []
    for name, voice in [('alex','em_alex'),('elena','ef_dora'),('daniel','em_santa')]:
        for run in range(2):
            started = time.perf_counter()
            samples, rate = kokoro.create(text, voice=voice, lang='es', speed=1.0)
            elapsed = time.perf_counter() - started
            sf.write(str(args.output / f'kokoro-{name}.wav'), samples, rate, subtype='PCM_16')
            results.append(dict(engine='kokoro',voice=voice,run=run,seconds=round(elapsed,3),audio_seconds=round(len(samples)/rate,3)))
            print(json.dumps(results[-1]), flush=True)
    voice = PiperVoice.load(str(args.models / 'es_ES-sharvard-medium.onnx'))
    for run in range(2):
        started = time.perf_counter()
        with wave.open(str(args.output / 'piper-es.wav'), 'wb') as output:
            voice.synthesize_wav(text, output)
        elapsed = time.perf_counter() - started
        with wave.open(str(args.output / 'piper-es.wav'),'rb') as output:
            duration = output.getnframes()/output.getframerate()
        results.append(dict(engine='piper',voice='sharvard',run=run,seconds=round(elapsed,3),audio_seconds=round(duration,3)))
        print(json.dumps(results[-1]), flush=True)
    (args.output/'benchmark.json').write_text(json.dumps(dict(files=hashes,results=results),indent=2),encoding='utf-8')
