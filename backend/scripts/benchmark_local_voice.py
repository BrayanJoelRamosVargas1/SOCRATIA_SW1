"""Explicit controlled benchmark; no downloads, no model changes, no API keys.

Run on a test host with provisioned models, not on the student's laptop.
The report distinguishes create() (phonemization + inference) from postprocessing.
"""

import argparse
import hashlib
import io
import json
import platform
import sys
import time
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.integrations.tts.base import TTSRequest
from app.integrations.tts.local_tts import LocalTTSProvider, speech_segments


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", default="/opt/socratia-voice/models")
    parser.add_argument("--confirm-controlled-inference", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if not args.confirm_controlled_inference:
        parser.error(
            "Confirma una ventana de medición controlada; no se ejecuta inferencia automáticamente."
        )
    directory = Path(args.model_dir)
    paths = [directory / filename for filename in ("kokoro-v1.0.onnx", "voices-v1.0.bin")]
    if not all(path.is_file() for path in paths):
        parser.error("Faltan pesos provisionados; no se descargarán modelos.")
    hashes = {}
    for path in paths:
        with path.open("rb") as model:
            hashes[path.name] = hashlib.file_digest(model, "sha256").hexdigest()
    provider = LocalTTSProvider(str(directory))
    phrases = [
        "Explique cómo validó los resultados de su investigación y cuáles fueron sus principales limitaciones.",
        "Describa los componentes del sistema y cómo se protegen los documentos de cada estudiante.",
    ]
    observations = []
    for speaker in range(3):
        for phrase in phrases:
            segment = speech_segments(phrase)[0]
            for repetition in range(2):
                started = time.perf_counter()
                audio = provider._render(TTSRequest(text=segment, speaker_index=speaker))
                with wave.open(io.BytesIO(audio)) as wav:
                    duration = wav.getnframes() / wav.getframerate()
                observations.append(
                    {
                        "speaker": speaker,
                        "repetition": repetition,
                        "wall_s": time.perf_counter() - started,
                        "audio_s": duration,
                        "bytes": len(audio),
                        **provider.last_metrics,
                    }
                )
    report = {
        "platform": platform.platform(),
        "model_hashes": hashes,
        "cache_initially_empty": True,
        "network_inference": False,
        "observations": observations,
        "measurement_note": "inference_s includes phonemization; wall_s excludes HTTP delivery. Compare identical host, model hashes, phrases and CPU limits.",
    }
    Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
