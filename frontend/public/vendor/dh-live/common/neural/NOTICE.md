# Spanish speech comparison

2026-10-18: cached Kokoro examples use differentiated pitch/pace profiles:
Alex 1.06/.98, Elena 1.10/1.05, Daniel .88/.90. Original files are backed up
outside the public directory. These are processed versions of the same three
voice identities, not additional models or cloned voices.

Generated locally with Kokoro ONNX 0.6.1 and Piper TTS 1.8.0.
Kokoro model: https://huggingface.co/hexgrad/Kokoro-82M (Apache-2.0).
ONNX implementation: https://github.com/thewh1teagle/kokoro-onnx (MIT).
Model is the INT8 asset from release model-files-v1.0; voice bank is v1.0.

Piper: https://github.com/OHF-Voice/piper1-gpl (GPL-3.0).
Voice: es_ES-sharvard-medium; original Spanish Harvard Corpus dataset,
University of Edinburgh DataShare, https://datashare.ed.ac.uk/handle/10283/574,
CC BY 3.0. Voice card:
https://huggingface.co/rhasspy/piper-voices/blob/main/es/es_ES/sharvard/medium/MODEL_CARD
Audio is synthesized from original Socratia example text; no real person's voice
was cloned. Timings in benchmark.json are this PC's measurements, not AWS capacity.
