import logging
import random
import time
from collections.abc import Iterable

import httpx

from app.integrations.embeddings.base import EmbeddingDocument, EmbeddingError
from app.integrations.embeddings.rate_limiter import TokenRateLimiter

logger = logging.getLogger(__name__)

COHERE_API_BASE_URL = "https://api.cohere.com/v1"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class CohereEmbeddingProvider:
    def __init__(
        self,
        api_key: str,
        model: str = "embed-v4.0",
        dimensions: int = 1024,
        batch_size: int = 20,
        timeout_seconds: int = 60,
    ) -> None:
        # api_key is optional — if None/empty, is_available returns False and the provider
        # is gracefully skipped during fallback chain traversal.
        self.api_key = api_key or ""
        self._model = model
        self._dimensions = dimensions
        self.batch_size = batch_size
        self.timeout_seconds = timeout_seconds

        # Cohere limits can be higher, but let's use a safe pacing
        self.rate_limiter = TokenRateLimiter(max_rpm=1000, max_tpm=100000, safe_tpm_ratio=0.7)

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def provider_id(self) -> str:
        return "cohere"

    @property
    def embedding_space_id(self) -> str:
        return "COHERE_EMBED-V4.0_1024_V1"

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    @property
    def execution_location(self) -> str:
        return "remote"

    def embed_documents(self, documents: list[EmbeddingDocument]) -> Iterable[list[list[float]]]:
        if not documents:
            return

        with httpx.Client(timeout=self.timeout_seconds) as client:
            for batch in self._batches(documents):
                texts = [f"{doc.title}\n{doc.text}" if doc.title else doc.text for doc in batch]

                # We roughly estimate tokens using 1 token ≈ 4 chars
                estimated_tokens = sum(len(text) for text in texts) // 4
                budget = self.rate_limiter.calculate_budget(estimated_tokens)
                if not budget.is_allowed:
                    logger.info(
                        "Cohere Rate limiter active. Waiting %.2f ms for %s tokens",
                        budget.wait_ms,
                        estimated_tokens,
                    )
                    time.sleep(budget.wait_ms / 1000.0)

                yield self._embed_batch(client, texts, "search_document", estimated_tokens)
                self.rate_limiter.consume(estimated_tokens)

    def embed_queries(self, queries: list[str]) -> list[list[float]]:
        if not queries:
            return []

        # For queries, we do it in one go (assuming they are few)
        estimated_tokens = sum(len(q) for q in queries) // 4
        with httpx.Client(timeout=self.timeout_seconds) as client:
            return self._embed_batch(client, queries, "search_query", estimated_tokens)

    def _embed_batch(
        self, client: httpx.Client, texts: list[str], input_type: str, estimated_tokens: int
    ) -> list[list[float]]:
        payload = {
            "model": self._model,
            "texts": texts,
            "input_type": input_type,
            "embedding_types": ["float"],
        }

        # embed-v4.0 allows truncating
        payload["truncate"] = "END"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        response = self._post_with_retry(
            client,
            f"{COHERE_API_BASE_URL}/embed",
            headers,
            payload,
            batch_chunks=len(texts),
            estimated_tokens=estimated_tokens,
            model_name=self._model,
        )

        raw_embeddings = response.get("embeddings", {}).get("float")
        if not isinstance(raw_embeddings, list) or len(raw_embeddings) != len(texts):
            raise EmbeddingError("Cohere returned an unexpected embedding count")

        embeddings: list[list[float]] = []
        for values in raw_embeddings:
            if not isinstance(values, list) or len(values) != self.dimensions:
                raise EmbeddingError("Cohere returned an invalid embedding dimension")
            try:
                embeddings.append([float(value) for value in values])
            except (TypeError, ValueError) as exc:
                raise EmbeddingError("Cohere returned non-numeric embedding values") from exc
        return embeddings

    @staticmethod
    def _post_with_retry(
        client: httpx.Client,
        url: str,
        headers: dict[str, str],
        payload: dict[str, object],
        batch_chunks: int,
        estimated_tokens: int,
        model_name: str,
    ) -> dict[str, object]:
        for attempt in range(6):
            start_time = time.monotonic()
            http_status = None
            retry_after_ms = 0.0
            wait_ms = 0.0

            try:
                response = client.post(url, headers=headers, json=payload)
                http_status = response.status_code
            except httpx.HTTPError as exc:
                latency_ms = (time.monotonic() - start_time) * 1000.0
                logger.error(
                    "Telemetry: provider=cohere model=%s batch_chunks=%s est_tokens=%s attempt=%s latency_ms=%.2f error=%s",
                    model_name,
                    batch_chunks,
                    estimated_tokens,
                    attempt,
                    latency_ms,
                    str(exc),
                )
                if attempt == 5:
                    raise EmbeddingError("Cohere could not be reached") from exc
                wait_ms = (2**attempt) * 1000.0
                time.sleep(wait_ms / 1000.0)
                continue

            latency_ms = (time.monotonic() - start_time) * 1000.0

            if response.status_code in RETRYABLE_STATUS_CODES and attempt < 5:
                retry_after = response.headers.get(
                    "x-ratelimit-reset"
                )  # Cohere uses x-ratelimit-reset for absolute timestamp or retry-after
                if (
                    response.headers.get("retry-after")
                    and response.headers.get("retry-after").isdigit()
                ):
                    delay = float(response.headers.get("retry-after"))
                    retry_after_ms = delay * 1000.0
                else:
                    base_delay = 10.0 * (2**attempt)
                    delay = random.uniform(base_delay * 0.5, base_delay)

                wait_ms = delay * 1000.0
                logger.warning(
                    "Telemetry: provider=cohere model=%s batch_chunks=%s est_tokens=%s attempt=%s http_status=%s latency_ms=%.2f retry_after_ms=%.2f wait_ms=%.2f",
                    model_name,
                    batch_chunks,
                    estimated_tokens,
                    attempt,
                    http_status,
                    latency_ms,
                    retry_after_ms,
                    wait_ms,
                )
                time.sleep(delay)
                continue

            logger.info(
                "Telemetry: provider=cohere model=%s batch_chunks=%s est_tokens=%s attempt=%s http_status=%s latency_ms=%.2f wait_ms=0.0",
                model_name,
                batch_chunks,
                estimated_tokens,
                attempt,
                http_status,
                latency_ms,
            )

            if response.is_error:
                raise EmbeddingError(
                    f"Cohere rejected the request ({response.status_code}): {response.text}"
                )
            try:
                body = response.json()
            except ValueError as exc:
                raise EmbeddingError("Cohere returned invalid JSON") from exc
            if not isinstance(body, dict):
                raise EmbeddingError("Cohere returned an invalid response")
            return body

        raise EmbeddingError("Cohere could not complete the request")

    def _batches(
        self,
        documents: list[EmbeddingDocument],
    ) -> Iterable[list[EmbeddingDocument]]:
        for start in range(0, len(documents), self.batch_size):
            yield documents[start : start + self.batch_size]
