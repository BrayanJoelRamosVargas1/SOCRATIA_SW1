import logging
import random
import time
from collections.abc import Iterable

import httpx

from app.integrations.embeddings.base import EmbeddingDocument, EmbeddingError
from app.integrations.embeddings.rate_limiter import TokenRateLimiter

logger = logging.getLogger(__name__)

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

        # RPM 1500 and TPM 30k for Gemini Embedding 2 is the free tier. We use a safe ratio of 0.5.
        self.rate_limiter = TokenRateLimiter(max_rpm=1500, max_tpm=30000, safe_tpm_ratio=0.5)

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def provider_id(self) -> str:
        return "gemini"

    @property
    def embedding_space_id(self) -> str:
        return "GEMINI_EMBEDDING_2_768_V1"

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    @property
    def execution_location(self) -> str:
        return "remote"

    def embed_documents(self, documents: list[EmbeddingDocument]) -> Iterable[list[list[float]]]:
        yield from self._embed_documents(documents)

    def embed_queries(self, queries: list[str]) -> list[list[float]]:
        query_documents = [
            EmbeddingDocument(title="consulta de recuperacion", text=query) for query in queries
        ]
        # Query is usually just one or a few, we can just consume the generator
        all_embeddings = []
        for batch_embeddings in self._embed_documents(query_documents, is_query=True):
            all_embeddings.extend(batch_embeddings)
        return all_embeddings

    def _embed_documents(
        self,
        documents: list[EmbeddingDocument],
        *,
        is_query: bool = False,
    ) -> Iterable[list[list[float]]]:
        if not documents:
            return
        if not self.api_key:
            raise EmbeddingError("Gemini is not configured")

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }
        with httpx.Client(headers=headers, timeout=self.timeout_seconds) as client:
            # We process documents. But we adaptive-batch them to fit rate limits.
            remaining = documents.copy()
            while remaining:
                batch = remaining[: self.batch_size]

                # Estimate tokens for the maximum allowed batch
                estimated_tokens = sum(self.rate_limiter.estimate_tokens(doc.text) for doc in batch)

                # If even a single document is larger than safe TPM, we must fail or force it
                if len(batch) == 1 and estimated_tokens > self.rate_limiter.safe_tpm:
                    logger.warning("Single chunk exceeds safe TPM budget: %s", estimated_tokens)
                    # We send it anyway and hope the real token count is smaller, but cap it to 1.
                else:
                    # Adaptive batch split: if the batch is too large, halve it
                    budget = self.rate_limiter.calculate_budget(estimated_tokens)
                    if not budget.is_allowed and budget.available_tpm > 0:
                        # Find how many chunks we can fit
                        fit_count = 0
                        acc_tokens = 0
                        for doc in batch:
                            tks = self.rate_limiter.estimate_tokens(doc.text)
                            if acc_tokens + tks <= budget.available_tpm:
                                acc_tokens += tks
                                fit_count += 1
                            else:
                                break
                        if fit_count > 0:
                            batch = batch[:fit_count]
                            estimated_tokens = acc_tokens
                        # If we can't even fit 1, we will wait.

                budget = self.rate_limiter.calculate_budget(estimated_tokens)
                if not budget.is_allowed:
                    logger.info(
                        "Rate limiter active. Waiting %.2f ms for %s tokens",
                        budget.wait_ms,
                        estimated_tokens,
                    )
                    time.sleep(budget.wait_ms / 1000.0)
                    continue  # Re-evaluate budget

                # Try sending
                batch_embeddings = self._embed_batch(
                    client, batch, estimated_tokens=estimated_tokens, is_query=is_query
                )
                self.rate_limiter.consume(estimated_tokens)

                yield batch_embeddings

                # Remove processed from remaining
                remaining = remaining[len(batch) :]

    def _embed_batch(
        self,
        client: httpx.Client,
        documents: list[EmbeddingDocument],
        *,
        estimated_tokens: int,
        is_query: bool = False,
    ) -> list[list[float]]:
        model_name = f"models/{self.model}"
        payload = {
            "requests": [
                {
                    "model": model_name,
                    "content": {
                        "parts": [
                            {
                                "text": (
                                    f"task: question answering | query: {document.text}"
                                    if is_query
                                    else f"title: {document.title} | text: {document.text}"
                                )
                            }
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
            batch_chunks=len(documents),
            estimated_tokens=estimated_tokens,
            model_name=self.model,
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
                response = client.post(url, json=payload)
                http_status = response.status_code
            except httpx.HTTPError as exc:
                latency_ms = (time.monotonic() - start_time) * 1000.0
                logger.error(
                    "Telemetry: provider=gemini model=%s batch_chunks=%s est_tokens=%s attempt=%s latency_ms=%.2f error=%s",
                    model_name,
                    batch_chunks,
                    estimated_tokens,
                    attempt,
                    latency_ms,
                    str(exc),
                )
                if attempt == 5:
                    raise EmbeddingError("Gemini could not be reached") from exc
                wait_ms = (2**attempt) * 1000.0
                time.sleep(wait_ms / 1000.0)
                continue

            latency_ms = (time.monotonic() - start_time) * 1000.0

            if response.status_code in RETRYABLE_STATUS_CODES and attempt < 5:
                retry_after = response.headers.get("retry-after")
                if retry_after and retry_after.isdigit():
                    delay = float(retry_after)
                    retry_after_ms = delay * 1000.0
                else:
                    # Exponential backoff: 10s, 20s, 40s, 80s
                    base_delay = 10.0 * (2**attempt)
                    delay = random.uniform(base_delay * 0.5, base_delay)

                wait_ms = delay * 1000.0
                logger.warning(
                    "Telemetry: provider=gemini model=%s batch_chunks=%s est_tokens=%s attempt=%s http_status=%s latency_ms=%.2f retry_after_ms=%.2f wait_ms=%.2f",
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
                "Telemetry: provider=gemini model=%s batch_chunks=%s est_tokens=%s attempt=%s http_status=%s latency_ms=%.2f wait_ms=0.0",
                model_name,
                batch_chunks,
                estimated_tokens,
                attempt,
                http_status,
                latency_ms,
            )

            if response.is_error:
                # E.g. 401/403 or 400 Bad Request fail immediately
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
