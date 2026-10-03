import logging
import time
from collections.abc import Iterable

from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError

from app.integrations.embeddings.base import EmbeddingDocument, EmbeddingError
from app.integrations.embeddings.rate_limiter import TokenRateLimiter

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class HuggingFaceE5Provider:
    def __init__(
        self,
        api_key: str,
        model: str = "intfloat/multilingual-e5-base",
        dimensions: int = 768,
        batch_size: int = 10,
        timeout_seconds: int = 60,
    ) -> None:
        # api_key is optional — if None, is_available returns False and the provider
        # is gracefully skipped during fallback chain traversal.
        self.api_key = api_key or ""
        self._model = model
        self._dimensions = dimensions
        self.batch_size = batch_size
        self.timeout_seconds = timeout_seconds

        # Hugging Face Free tier is usually very low, but Pro can be higher.
        self.rate_limiter = TokenRateLimiter(max_rpm=300, max_tpm=50000, safe_tpm_ratio=0.7)

        # Patch huggingface_hub to allow feature-extraction on sentence-similarity models
        import huggingface_hub.inference._providers.hf_inference

        original_check = huggingface_hub.inference._providers.hf_inference._check_supported_task

        def _mock_check(model_id, task):
            if task == "feature-extraction" and model_id == model:
                return
            return original_check(model_id, task)

        huggingface_hub.inference._providers.hf_inference._check_supported_task = _mock_check

        # API actual de Inference Providers (no hardcodea api-inference)
        self.client = InferenceClient(
            provider="hf-inference", api_key=self.api_key, timeout=self.timeout_seconds
        )

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def provider_id(self) -> str:
        return "huggingface"

    @property
    def embedding_space_id(self) -> str:
        # FASE D: Unificamos el espacio con Local E5 porque el Golden Test demostró
        # compatibilidad perfecta matemática.
        return "E5_BASE_768_V1"

    @property
    def compatibility_fingerprint(self) -> str:
        import hashlib

        # sha256(model_repo + revision + tokenizer_revision + pooling + normalize + max_length + query_prefix + passage_prefix)
        # Note: HF remote doesn't strictly let us pin tokenizers/models by revision unless we specify it in the API call
        # but for E5 we assume the default revision is the one we tested.
        fingerprint_data = "intfloat/multilingual-e5-base|d128750597153bb5987e10b1c3493a34e5a4502a|d128750597153bb5987e10b1c3493a34e5a4502a|mean|l2|512|query: |passage: "
        return hashlib.sha256(fingerprint_data.encode("utf-8")).hexdigest()

    @property
    def is_available(self) -> bool:
        if not self.api_key:
            return False

        try:
            from huggingface_hub import whoami

            user_info = whoami(token=self.api_key)
            # The token must be valid. Inference Providers permission could be checked here.
        except Exception as e:
            logger.warning("HuggingFace provider unavailable (invalid token): %s", str(e))
            return False

        try:
            # Health/preflight real del provider usando InferenceClient
            # Intentamos vectorizar un texto mínimo. Si HF Remote no está disponible, esto falla y devolvemos False
            self.client.feature_extraction(
                "test",
                model=self._model,
                normalize=True,
                truncate=True,
                truncation_direction="Right",
            )
            return True
        except Exception as e:
            # Clasificamos indisponibilidad remota como provider unavailable, no como bug interno
            logger.warning("HuggingFace provider unavailable (inference error): %s", str(e))
            return False

    @property
    def execution_location(self) -> str:
        return "remote"

    def embed_documents(self, documents: list[EmbeddingDocument]) -> Iterable[list[list[float]]]:
        if not documents:
            return

        for batch in self._batches(documents):
            texts = [
                f"passage: {doc.title}\n{doc.text}" if doc.title else f"passage: {doc.text}"
                for doc in batch
            ]
            estimated_tokens = sum(len(text) for text in texts) // 4

            budget = self.rate_limiter.calculate_budget(estimated_tokens)
            if not budget.is_allowed:
                logger.info(
                    "HuggingFace Rate limiter active. Waiting %.2f ms for %s tokens",
                    budget.wait_ms,
                    estimated_tokens,
                )
                time.sleep(budget.wait_ms / 1000.0)

            yield self._embed_batch(texts, estimated_tokens)
            self.rate_limiter.consume(estimated_tokens)

    def embed_queries(self, queries: list[str]) -> list[list[float]]:
        if not queries:
            return []

        texts = [f"query: {query}" for query in queries]
        estimated_tokens = sum(len(text) for text in texts) // 4
        return self._embed_batch(texts, estimated_tokens)

    def _embed_batch(self, texts: list[str], estimated_tokens: int) -> list[list[float]]:
        import numpy as np

        for attempt in range(6):
            start_time = time.monotonic()
            try:
                # Usar InferenceClient y feature_extraction.
                # InferenceClient maneja batch nativamente si acepta lista.
                # Mantenemos normalize=True, truncate=True consistentes con LocalE5.
                response = self.client.feature_extraction(
                    texts,  # The backend parses inputs=[...] automatically
                    model=self._model,
                    normalize=True,
                    truncate=True,
                    truncation_direction="Right",
                )

                import numpy as np

                if isinstance(response, np.ndarray):
                    response = response.tolist()

                latency_ms = (time.monotonic() - start_time) * 1000.0
                logger.info(
                    "Telemetry: provider=huggingface model=%s batch_chunks=%s est_tokens=%s attempt=%s latency_ms=%.2f",
                    self._model,
                    len(texts),
                    estimated_tokens,
                    attempt,
                    latency_ms,
                )

                embeddings: list[list[float]] = []
                for values in response:
                    if not isinstance(values, list):
                        raise EmbeddingError("HuggingFace returned an invalid format")

                    if len(values) > 0 and isinstance(values[0], list):
                        seq_len = len(values)
                        dim = len(values[0])
                        if dim != self.dimensions:
                            raise EmbeddingError(
                                f"HuggingFace returned an invalid dimension {dim} vs {self.dimensions}"
                            )
                        pooled = [sum(col) / seq_len for col in zip(*values)]
                        embeddings.append(pooled)
                    else:
                        if len(values) != self.dimensions:
                            raise EmbeddingError(
                                f"HuggingFace returned an invalid embedding dimension {len(values)} vs {self.dimensions}"
                            )
                        embeddings.append([float(value) for value in values])

                return embeddings

            except Exception as exc:
                latency_ms = (time.monotonic() - start_time) * 1000.0

                logger.error(
                    "Telemetry: provider=huggingface model=%s batch_chunks=%s est_tokens=%s attempt=%s latency_ms=%.2f error=%s",
                    self._model,
                    len(texts),
                    estimated_tokens,
                    attempt,
                    latency_ms,
                    str(exc),
                )

                if isinstance(exc, HfHubHTTPError):
                    status_code = getattr(exc.response, "status_code", None)
                    if status_code in (401, 403):
                        raise EmbeddingError(
                            f"HuggingFace API unauthorized or token missing 'Inference Providers' permission: {exc}"
                        ) from exc

                if attempt == 5:
                    raise EmbeddingError("HuggingFace could not be reached or failed") from exc

                time.sleep(2**attempt)
                continue

        raise EmbeddingError("HuggingFace could not complete the request")

    def _batches(
        self,
        documents: list[EmbeddingDocument],
    ) -> Iterable[list[EmbeddingDocument]]:
        for start in range(0, len(documents), self.batch_size):
            yield documents[start : start + self.batch_size]
