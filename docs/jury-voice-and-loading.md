# Jury voice and loading — staging

The video room uses three small native alpha loops while listening. Only the
active speaker mounts DH_live/WebAssembly; it is released after the turn.
Hidden tabs pause video and inference. Lip-sync waits for a renderer-specific
ready message and receives decoded PCM16 at 16 kHz. Source playback is 25 FPS;
inference is capped at 15 FPS. Browser voices cannot supply PCM and remain an
emergency fallback; they cannot promise synchronized human lips.

Staging enables Kokoro ONNX CPU voices em_alex, ef_dora and em_santa. This uses
the existing EC2 CPU, no external speech API or API tokens. Quantized model
assets live outside Git, mounted read-only at /data/voice-models. Before enabling
on a new host, provision these official release assets:

- https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx
  as /opt/socratia-voice/models/kokoro-v1.0.onnx; SHA256
  6e742170d309016e5891a994e1ce1559c702a2ccd0075e67ef7157974f6406cb
- https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
  as /opt/socratia-voice/models/voices-v1.0.bin; SHA256
  bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d

Model provenance/licenses: https://github.com/thewh1teagle/kokoro-onnx
(MIT wrapper, Apache-2.0 Kokoro model; preserve upstream notices).
Docker installs optional requirements only with INSTALL_LOCAL_VOICE=true.
Staging bounds the backend to 1.5 CPUs/900 MB. Voice admits one synthesis job
at a time and caches up to 16 batches/8 MB. Active-question ownership and text
allowlist apply before segmentation; the client only requests numbered batches
of that same question. It prepares at most one next batch while playing.
Question-bank prewarming never makes speculative LLM calls.

A one-CPU staging benchmark of a fixed 55-character sentence took 9.77 seconds
cold and 6.08–6.64 seconds for the next identities, with peak RSS 378 MB.
This is not an instant-voice guarantee: short word-aligned batches bound the
first playback wait, but CPU contention may cause gaps or browser fallback.
Quota and balance evidence belongs in ignored artifacts, never in public Git.
