"""Optional CPU speech. Models are provisioned explicitly, never on a request."""
import asyncio
import io
import threading
import time
from collections import OrderedDict
from pathlib import Path

from app.integrations.tts.base import TTSProvider, TTSProviderError, TTSRequest


def speech_segments(text: str, limit: int = 120) -> list[str]:
    """Short word-aligned audio batches keep first playback bounded on CPU."""
    chunks: list[str] = []
    current = ""
    for word in text.split():
        # First audio can begin after fewer words. Following batches retain the
        # original size for throughput; no words are removed or rewritten.
        batch_limit = min(limit, 64) if not chunks else limit
        if current and len(current) + len(word) + 1 > batch_limit:
            chunks.append(current)
            current = ""
        current = f"{current} {word}".strip()
    if current:
        chunks.append(current)
    return chunks


class LocalTTSProvider(TTSProvider):
    name = "kokoro"
    mime_type = "audio/wav"

    def __init__(self, model_dir: str):
        self.model_dir = Path(model_dir)
        self._model = None
        self._lock = threading.Lock()
        self._cache: OrderedDict[tuple[str, str], bytes] = OrderedDict()
        self.last_metrics: dict = {}

    def _render(self, request: TTSRequest) -> bytes:
        started = time.perf_counter()
        if not request.text.strip() or len(request.text) > 3000:
            raise TTSProviderError("Invalid speech length", provider=self.name)
        # Distinct voice identities plus restrained pitch/rhythm differences.
        voice, pitch, pace = (("em_alex", 106, .98), ("ef_dora", 110, 1.05), ("em_santa", 88, .90))[request.speaker_index % 3]
        key = (voice, request.text)
        # Bound CPU work rather than allowing an unbounded inference queue.
        if not self._lock.acquire(blocking=False):
            raise TTSProviderError("Local speech is busy", provider=self.name, retryable=True)
        try:
            if key in self._cache:
                self._cache.move_to_end(key)
                self.last_metrics = {"cache_hit": True, "load_s": 0.0, "inference_s": 0.0,
                    "postprocess_s": 0.0, "total_s": time.perf_counter() - started,
                    "input_chars": len(request.text)}
                return self._cache[key]
            load_started = time.perf_counter()
            if self._model is None:
                import onnxruntime as ort
                from kokoro_onnx import Kokoro
                options = ort.SessionOptions()
                options.intra_op_num_threads = 2
                options.inter_op_num_threads = 1
                session = ort.InferenceSession(str(self.model_dir / "kokoro-v1.0.onnx"), sess_options=options, providers=["CPUExecutionProvider"])
                self._model = Kokoro.from_session(session, str(self.model_dir / "voices-v1.0.bin"))
            import soundfile as sf
            from scipy.signal import resample_poly
            load_seconds = time.perf_counter() - load_started
            inference_started = time.perf_counter()
            samples, rate = self._model.create(request.text, voice=voice, lang="es", speed=pace/(pitch/100))
            inference_seconds = time.perf_counter() - inference_started
            postprocess_started = time.perf_counter()
            samples = resample_poly(samples, 100, pitch)
            output = io.BytesIO()
            sf.write(output, samples, rate, format="WAV", subtype="PCM_16")
            data = output.getvalue()
            self._cache[key] = data
            while len(self._cache) > 16 or sum(map(len, self._cache.values())) > 8_000_000:
                self._cache.popitem(last=False)
            self.last_metrics = {"cache_hit": False, "load_s": load_seconds,
                "inference_s": inference_seconds, "postprocess_s": time.perf_counter() - postprocess_started,
                "total_s": time.perf_counter() - started, "input_chars": len(request.text)}
            return data
        except TTSProviderError:
            raise
        except Exception as exc:
            raise TTSProviderError("Local speech unavailable", provider=self.name) from exc
        finally:
            self._lock.release()

    async def synthesize(self, request: TTSRequest):
        # Cancellation drops playback; the bounded CPU job finishes in its thread.
        yield await asyncio.to_thread(self._render, request)
