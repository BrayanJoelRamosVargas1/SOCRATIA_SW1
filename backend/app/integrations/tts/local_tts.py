"""Optional CPU speech. Models are provisioned explicitly, never on a request."""
import asyncio
import io
import threading
from collections import OrderedDict
from pathlib import Path

from app.integrations.tts.base import TTSProvider, TTSProviderError, TTSRequest


class LocalTTSProvider(TTSProvider):
    name = "kokoro"
    mime_type = "audio/wav"

    def __init__(self, model_dir: str):
        self.model_dir = Path(model_dir)
        self._model = None
        self._lock = threading.Lock()
        self._cache: OrderedDict[tuple[str, str], bytes] = OrderedDict()

    def _render(self, request: TTSRequest) -> bytes:
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
                return self._cache[key]
            if self._model is None:
                import onnxruntime as ort
                from kokoro_onnx import Kokoro
                options = ort.SessionOptions()
                options.intra_op_num_threads = 2
                options.inter_op_num_threads = 1
                session = ort.InferenceSession(str(self.model_dir / "kokoro-v1.0.onnx"), sess_options=options, providers=["CPUExecutionProvider"])
                self._model = Kokoro.from_session(session, str(self.model_dir / "voices-v1.0.bin"))
            import soundfile as sf
            samples, rate = self._model.create(request.text, voice=voice, lang="es", speed=pace/(pitch/100))
            from scipy.signal import resample_poly
            samples = resample_poly(samples, 100, pitch)
            output = io.BytesIO()
            sf.write(output, samples, rate, format="WAV", subtype="PCM_16")
            data = output.getvalue()
            self._cache[key] = data
            while len(self._cache) > 16 or sum(map(len, self._cache.values())) > 8_000_000:
                self._cache.popitem(last=False)
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
