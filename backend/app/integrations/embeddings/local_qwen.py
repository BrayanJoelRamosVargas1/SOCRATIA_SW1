"""Private self-hosted Qwen retrieval embeddings."""

import hashlib
import math
from pathlib import Path

import httpx

from app.integrations.embeddings.base import EmbeddingDocument, EmbeddingError

MODEL = "Qwen3-Embedding-0.6B-Q8_0"
MODEL_SHA256 = "06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439"
QUERY_INSTRUCTION = (
    "Instruct: Given a question about an academic project, retrieve relevant passages "
    "that answer the question.\nQuery: "
)
MAX_INPUT_CHARS = 1600


class LocalQwenEmbeddingProvider:
    provider_id = "qwen_local"
    embedding_space_id = "QWEN3_EMBEDDING_0_6B_Q8_1024_V1"
    execution_location = "local"
    model = MODEL
    dimensions = 1024
    batch_size = 2
    compatibility_fingerprint = hashlib.sha256(
        f"{MODEL_SHA256}|last|l2|1024|document_mean_windows1600|{QUERY_INSTRUCTION}".encode()
    ).hexdigest()

    def __init__(self, *, url: str, key_file: str):
        self.url = url.rstrip("/")
        self.key_file = key_file

    @property
    def is_available(self) -> bool:
        return bool(self.url and self.key_file)

    def _embed(self, texts: list[str], *, query: bool) -> list[list[float]]:
        try:
            key = Path(self.key_file).read_text().strip()
            if not key or len(key) > 256 or any(c.isspace() for c in key):
                raise ValueError("Invalid private key")
            vectors = []
            with httpx.Client(
                timeout=httpx.Timeout(45, connect=3), follow_redirects=False
            ) as client:
                for text in texts:
                    content = text[:MAX_INPUT_CHARS]
                    if query:
                        content = QUERY_INSTRUCTION + content
                    response = client.post(
                        self.url + "/embeddings",
                        headers={"Authorization": "Bearer " + key},
                        json={"model": MODEL, "input": [content], "encoding_format": "float"},
                    )
                    response.raise_for_status()
                    if len(response.content) > 100_000:
                        raise ValueError("Oversized embedding response")
                    data = response.json()["data"]
                    if len(data) != 1 or data[0].get("index") != 0:
                        raise ValueError("Invalid embedding order")
                    vector = data[0]["embedding"]
                    if len(vector) != self.dimensions or not all(
                        isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
                        for v in vector
                    ):
                        raise ValueError("Invalid embedding values")
                    norm = math.sqrt(sum(v * v for v in vector))
                    if not math.isfinite(norm) or norm == 0:
                        raise ValueError("Invalid embedding norm")
                    vectors.append([v / norm for v in vector])
            return vectors
        except (OSError, httpx.HTTPError, ValueError, KeyError, TypeError, OverflowError):
            raise EmbeddingError("Local Qwen embedding unavailable") from None

    def embed_documents(self, documents: list[EmbeddingDocument]):
        for offset in range(0, len(documents), self.batch_size):
            batch = []
            for doc in documents[offset : offset + self.batch_size]:
                text = f"{doc.title}\n{doc.text}" if doc.title else doc.text
                # Include the whole chunk, even when it exceeds the bounded sequence size.
                parts = [
                    text[i : i + MAX_INPUT_CHARS] for i in range(0, len(text), MAX_INPUT_CHARS)
                ]
                vectors = self._embed(parts or [" "], query=False)
                vector = [sum(values) / len(vectors) for values in zip(*vectors)]
                norm = math.sqrt(sum(v * v for v in vector))
                if norm == 0:
                    raise EmbeddingError("Local Qwen embedding unavailable")
                batch.append([v / norm for v in vector])
            yield batch

    def embed_queries(self, queries: list[str]) -> list[list[float]]:
        return self._embed(queries, query=True)
