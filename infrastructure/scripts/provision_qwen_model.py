"""Run on the AWS host, not on the developer laptop. Never prints the API key."""
import hashlib
import os
import secrets
import urllib.request
from pathlib import Path

MODEL_REVISION = "370f27d7550e0def9b39c1f16d3fbaa13aa67728"
MODEL_SHA256 = "06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439"
MODEL_SIZE = 639150592
MODEL_NAME = "Qwen3-Embedding-0.6B-Q8_0.gguf"
MODEL_URL = f"https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF/resolve/{MODEL_REVISION}/{MODEL_NAME}"


def main():
    os.umask(0o077)
    directory = Path("/opt/socratia-qwen/models")
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / MODEL_NAME
    if not destination.exists():
        temporary = directory / (MODEL_NAME + ".partial")
        request = urllib.request.Request(MODEL_URL, headers={"User-Agent": "socratia-model-provisioner"})
        with urllib.request.urlopen(request, timeout=90) as source, temporary.open("wb") as target:
            total = 0
            while block := source.read(1024 * 1024):
                total += len(block)
                if total > MODEL_SIZE:
                    raise ValueError("Unexpected model size")
                target.write(block)
        assert total == MODEL_SIZE, "Incomplete model download"
        with temporary.open("rb") as downloaded:
            assert hashlib.file_digest(downloaded, "sha256").hexdigest() == MODEL_SHA256
        temporary.replace(destination)
    with destination.open("rb") as model:
        assert hashlib.file_digest(model, "sha256").hexdigest() == MODEL_SHA256
    destination.chmod(0o644)
    secret_dir = Path("/opt/socratia-secrets")
    secret_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    key = secret_dir / "qwen-api-key"
    if not key.exists():
        key.write_text(secrets.token_urlsafe(48) + "\n")
    key.chmod(0o600)
    print(f"QWEN_MODEL_VERIFIED bytes={MODEL_SIZE} sha256={MODEL_SHA256}", flush=True)
    print("QWEN_PRIVATE_KEY_READY", flush=True)


if __name__ == "__main__":
    main()
