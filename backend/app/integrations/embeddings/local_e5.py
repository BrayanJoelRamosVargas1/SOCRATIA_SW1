import logging
import os
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor

from app.integrations.embeddings.base import EmbeddingDocument, EmbeddingError

logger = logging.getLogger(__name__)

# Global executor for Local E5 to strictly control CPU concurrency and avoid starving FastAPI
MAX_CONCURRENCY = int(os.getenv("LOCAL_E5_MAX_CONCURRENCY", "1"))
_e5_executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENCY, thread_name_prefix="LocalE5")


class LocalE5Provider:
    def __init__(
        self,
        model_name: str = "intfloat/multilingual-e5-base",
        dimensions: int = 768,
        batch_size: int = 16,
    ) -> None:
        # Default fallback if E5_MODEL_NAME is not set, though it should be set in production
        self._model_name = os.getenv("E5_MODEL_NAME", model_name)
        # Pinned revision to guarantee exact mathematical equivalence
        self._model_revision = os.getenv(
            "E5_MODEL_REVISION", "d128750597153bb5987e10b1c3493a34e5a4502a"
        )

        self._dimensions = dimensions
        self.batch_size = batch_size
        self._model_instance = None

    @property
    def model(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def provider_id(self) -> str:
        return "local_e5"

    @property
    def embedding_space_id(self) -> str:
        return "E5_BASE_768_V1"

    @property
    def compatibility_fingerprint(self) -> str:
        import hashlib

        # sha256(model_repo + revision + tokenizer_revision + pooling + normalize + max_length + query_prefix + passage_prefix)
        # Dynamic based on actual configured revision
        fingerprint_data = f"{self._model_name}|{self._model_revision}|{self._model_revision}|mean|l2|512|query: |passage: "
        return hashlib.sha256(fingerprint_data.encode("utf-8")).hexdigest()

    @property
    def is_available(self) -> bool:
        try:
            from huggingface_hub import snapshot_download

            # Use snapshot_download with local_files_only=True to check if cached
            snapshot_download(
                repo_id=self._model_name, revision=self._model_revision, local_files_only=True
            )
            return True
        except Exception:
            return False

    @property
    def execution_location(self) -> str:
        return "local"

    def _get_model(self):
        """Lazy load the sentence-transformer model."""
        if self._model_instance is None:
            try:
                from sentence_transformers import SentenceTransformer

                # local_files_only=True guarantees we don't attempt to download at runtime
                logger.info(
                    "Loading Local E5 model %s (rev: %s) from cache...",
                    self._model_name,
                    self._model_revision,
                )
                self._model_instance = SentenceTransformer(
                    self._model_name, revision=self._model_revision, local_files_only=True
                )
                dim = self._model_instance.get_sentence_embedding_dimension()
                if dim != self._dimensions:
                    raise EmbeddingError(
                        f"Model dimension {dim} does not match expected {self._dimensions}"
                    )

            except ImportError as exc:
                raise EmbeddingError(
                    "sentence-transformers is not installed. Please install requirements-local-embeddings.txt"
                ) from exc
            except Exception as exc:
                raise EmbeddingError(
                    f"Failed to load local model '{self._model_name}'. Did you run preload_embedding_model.py?"
                ) from exc
        return self._model_instance

    def _encode_in_thread(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        try:
            future = _e5_executor.submit(
                model.encode,
                texts,
                batch_size=self.batch_size,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
            embeddings = future.result()

            result = []
            for vec in embeddings:
                if len(vec) != self._dimensions:
                    raise EmbeddingError(f"Local E5 returned unexpected dimension: {len(vec)}")
                result.append(vec.tolist())
            return result

        except Exception as exc:
            raise EmbeddingError("Local E5 model failed to encode texts") from exc

    def embed_documents(self, documents: list[EmbeddingDocument]) -> Iterable[list[list[float]]]:
        if not documents:
            return

        for start in range(0, len(documents), self.batch_size):
            batch = documents[start : start + self.batch_size]
            texts = [
                f"passage: {doc.title}\n{doc.text}" if doc.title else f"passage: {doc.text}"
                for doc in batch
            ]
            yield self._encode_in_thread(texts)

    def embed_queries(self, queries: list[str]) -> list[list[float]]:
        if not queries:
            return []

        texts = [f"query: {query}" for query in queries]
        return self._encode_in_thread(texts)
