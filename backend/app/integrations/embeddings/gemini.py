import time
from collections.abc import Iterable

import httpx

from app.integrations.embeddings.base import EmbeddingDocument, EmbeddingError

GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class GeminiEmbeddingProvider:
    """Gemini Embedding 2 adapter using the official REST API."""

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        dimensions: int,
        batch_size: int,
        timeout_seconds: int,
    ) -> None:
        self.api_key = api_key
        self._model = model
        self._dimensions = dimensions
        self.batch_size = batch_size
        self.timeout_seconds = timeout_seconds

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_documents(self, documents: list[EmbeddingDocument]) -> list[list[float]]:
        if not documents:
            return []
        if not self.api_key:
            raise EmbeddingError("Gemini is not configured")

        embeddings: list[list[float]] = []
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }
        with httpx.Client(headers=headers, timeout=self.timeout_seconds) as client:
            for batch in self._batches(documents):
                embeddings.extend(self._embed_batch(client, batch))
        return embeddings

    def _embed_batch(
        self,
        client: httpx.Client,
        documents: list[EmbeddingDocument],
    ) -> list[list[float]]:
        model_name = f"models/{self.model}"
        payload = {
            "requests": [
                {
                    "model": model_name,
                    "content": {
                        "parts": [
                            {"text": f"title: {document.title} | text: {document.text}"}
                        ]
                    },
                    "outputDimensionality": self.dimensions,
                }
                for document in documents
            ]
        }
        response = self._post_with_retry(
            client,
            f"{GEMINI_API_BASE_URL}/{model_name}:batchEmbedContents",
            payload,
        )
        raw_embeddings = response.get("embeddings")
        if not isinstance(raw_embeddings, list) or len(raw_embeddings) != len(documents):
            raise EmbeddingError("Gemini returned an unexpected embedding count")

        embeddings: list[list[float]] = []
        for raw_embedding in raw_embeddings:
            values = raw_embedding.get("values") if isinstance(raw_embedding, dict) else None
            if not isinstance(values, list) or len(values) != self.dimensions:
                raise EmbeddingError("Gemini returned an invalid embedding")
            try:
                embeddings.append([float(value) for value in values])
            except (TypeError, ValueError) as exc:
                raise EmbeddingError("Gemini returned non-numeric embedding values") from exc
        return embeddings

    @staticmethod
    def _post_with_retry(
        client: httpx.Client,
        url: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        for attempt in range(3):
            try:
                response = client.post(url, json=payload)
            except httpx.HTTPError as exc:
                if attempt == 2:
                    raise EmbeddingError("Gemini could not be reached") from exc
                time.sleep(2**attempt)
                continue

            if response.status_code in RETRYABLE_STATUS_CODES and attempt < 2:
                retry_after = response.headers.get("retry-after")
                delay = float(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
                time.sleep(delay)
                continue
            if response.is_error:
                raise EmbeddingError(f"Gemini rejected the request ({response.status_code})")
            try:
                body = response.json()
            except ValueError as exc:
                raise EmbeddingError("Gemini returned invalid JSON") from exc
            if not isinstance(body, dict):
                raise EmbeddingError("Gemini returned an invalid response")
            return body
        raise EmbeddingError("Gemini could not complete the request")

    def _batches(
        self,
        documents: list[EmbeddingDocument],
    ) -> Iterable[list[EmbeddingDocument]]:
        for start in range(0, len(documents), self.batch_size):
            yield documents[start : start + self.batch_size]
