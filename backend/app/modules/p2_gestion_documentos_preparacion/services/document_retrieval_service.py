from collections.abc import Sequence

from app.integrations.embeddings import EmbeddingCoordinator, EmbeddingError
from app.integrations.llm.base import DocumentContextChunk
from app.integrations.vector_db import VectorStoreProvider
from app.modules.p2_gestion_documentos_preparacion.models.document import Document


class DocumentContextUnavailableError(Exception):
    """Raised when no safe, document-scoped context can be built."""


class DocumentRetrievalService:
    def __init__(
        self,
        *,
        embeddings: EmbeddingCoordinator,
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
        document: Document,
        intents: Sequence[str],
    ) -> tuple[DocumentContextChunk, ...]:
        query_vectors = self.embeddings.embed_queries_for_document(document, list(intents))
        if len(query_vectors) != len(intents):
            raise EmbeddingError("Embedding count does not match retrieval intent count")

        active_profile = next(
            (
                p
                for p in document.embedding_profiles
                if p.id == document.active_embedding_profile_id
            ),
            None,
        )
        if not active_profile:
            # Fallback for old tests/mock data without profiles
            namespace = f"{self.namespace_prefix}-{user_id}"
            index_name = None
            dimension = None
        else:
            namespace = active_profile.vector_namespace
            index_name = active_profile.vector_index
            dimension = active_profile.dimension
        filters = {
            "$and": [
                {"user_id": {"$eq": user_id}},
                {"document_id": {"$eq": document.id}},
            ]
        }
        deduplicated: dict[str, DocumentContextChunk] = {}
        for query_vector in query_vectors:
            matches = self.vectors.query(
                namespace=namespace,
                vector=query_vector,
                top_k=self.top_k,
                filters=filters,
                index_name=index_name,
                dimensions=dimension,
            )
            for match in matches:
                metadata = match.metadata
                if metadata.get("user_id") != user_id or metadata.get("document_id") != document.id:
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
