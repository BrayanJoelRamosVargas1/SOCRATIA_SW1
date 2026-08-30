from collections.abc import Sequence

from app.integrations.embeddings import EmbeddingError, EmbeddingProvider
from app.integrations.llm.base import DocumentContextChunk
from app.integrations.vector_db import VectorStoreProvider


class DocumentContextUnavailableError(Exception):
    """Raised when no safe, document-scoped context can be built."""


class DocumentRetrievalService:
    def __init__(
        self,
        *,
        embeddings: EmbeddingProvider,
        vectors: VectorStoreProvider,
        namespace_prefix: str,
        top_k: int,
        max_context_chars: int,
    ) -> None:
        self.embeddings = embeddings
        self.vectors = vectors
        self.namespace_prefix = namespace_prefix
        self.top_k = top_k
        self.max_context_chars = max_context_chars

    def retrieve(
        self,
        *,
        user_id: str,
        document_id: str,
        intents: Sequence[str],
    ) -> tuple[DocumentContextChunk, ...]:
        query_vectors = self.embeddings.embed_queries(list(intents))
        if len(query_vectors) != len(intents):
            raise EmbeddingError("Embedding count does not match retrieval intent count")

        namespace = f"{self.namespace_prefix}-{user_id}"
        filters = {
            "$and": [
                {"user_id": {"$eq": user_id}},
                {"document_id": {"$eq": document_id}},
            ]
        }
        deduplicated: dict[str, DocumentContextChunk] = {}
        for query_vector in query_vectors:
            matches = self.vectors.query(
                namespace=namespace,
                vector=query_vector,
                top_k=self.top_k,
                filters=filters,
            )
            for match in matches:
                metadata = match.metadata
                if metadata.get("user_id") != user_id or metadata.get("document_id") != document_id:
                    continue
                text = metadata.get("text")
                if not isinstance(text, str) or not text.strip():
                    continue
                candidate = DocumentContextChunk(
                    id=match.id,
                    text=text.strip(),
                    score=match.score,
                )
                current = deduplicated.get(match.id)
                if current is None or candidate.score > current.score:
                    deduplicated[match.id] = candidate

        packed: list[DocumentContextChunk] = []
        used_chars = 0
        for chunk in deduplicated.values():
            if packed and used_chars + len(chunk.text) > self.max_context_chars:
                continue
            packed.append(chunk)
            used_chars += len(chunk.text)
        if not packed:
            raise DocumentContextUnavailableError
        return tuple(packed)
