import logging

from app.integrations.embeddings import EmbeddingCoordinator, EmbeddingError
from app.integrations.retrieval.base import FallbackReason, RetrievalMode, RetrievalResult
from app.integrations.retrieval.lexical import PostgresLexicalFallbackRetriever
from app.integrations.vector_db.base import VectorStoreError
from app.integrations.vector_db.router import VectorStoreRouter
from app.modules.p2_gestion_documentos_preparacion.models.document import Document
from app.modules.p2_gestion_documentos_preparacion.models.vector_store import (
    EmbeddingProfileStoreSync,
)

logger = logging.getLogger(__name__)


class RetrievalRouter:
    """
    Coordinates vector retrieval and lexical fallback (Graceful Degradation).
    Ensures that if all vector stores or embedding providers are down, the user still gets results via FTS.
    """

    def __init__(
        self,
        embeddings: EmbeddingCoordinator,
        vector_router: VectorStoreRouter,
        lexical_retriever: PostgresLexicalFallbackRetriever,
    ):
        self.embeddings = embeddings
        self.vector_router = vector_router
        self.lexical_retriever = lexical_retriever

    def retrieve_for_document(
        self, document: Document, user_id: str, query_text: str, top_k: int
    ) -> tuple[list[RetrievalResult], FallbackReason]:

        if str(document.user_id) != str(user_id):
            # Enforce tenant isolation at the retrieval core
            return [], FallbackReason.NONE

        active_profile = next(
            (
                p
                for p in document.embedding_profiles
                if p.id == document.active_embedding_profile_id
            ),
            None,
        )

        fallback_reason = FallbackReason.NONE

        if active_profile and active_profile.chunk_set_id:
            # 1. Check if we have ANY vector route available for this profile before even embedding.
            # If both stores are unavailable or have no SYNCED sync status, we can short-circuit.
            has_vector_route = self._has_any_vector_route(active_profile.id)

            if has_vector_route:
                try:
                    # 2. Embed the query respecting the document's embedding space
                    query_vectors = self.embeddings.embed_queries_for_document(
                        document, [query_text]
                    )
                    if not query_vectors:
                        raise EmbeddingError("Empty embeddings returned")

                    query_vector = query_vectors[0]

                    filters = {
                        "$and": [
                            {"user_id": {"$eq": str(user_id)}},
                            {"document_id": {"$eq": document.id}},
                        ]
                    }

                    # 3. Query vector stores using the VectorStoreRouter
                    matches = self.vector_router.query(
                        profile_id=active_profile.id,
                        namespace=active_profile.vector_namespace,
                        vector=query_vector,
                        top_k=top_k,
                        filters=filters,
                        index_name=active_profile.vector_index,
                        dimensions=active_profile.dimension,
                    )

                    # If we got here, vector search worked.
                    results = []
                    for i, match in enumerate(matches, start=1):
                        primary_name = getattr(self.vector_router.primary, "provider_name", "pinecone")
                        mode = (
                            RetrievalMode.VECTOR_PRIMARY
                            if match.source_store == primary_name
                            else RetrievalMode.VECTOR_SECONDARY
                        )

                        results.append(
                            RetrievalResult(
                                chunk_id=match.chunk_id,
                                content=match.metadata.get("text", ""),
                                rank=i,
                                raw_score=match.score,
                                retrieval_mode=mode,
                                source=match.source_store,
                                metadata=match.metadata,
                            )
                        )
                    return results, FallbackReason.NONE

                except ValueError as e:
                    logger.error("Programming or validation error in vector retrieval. Aborting: %s", str(e))
                    raise
                except EmbeddingError as e:
                    logger.warning(
                        "Embedding providers unavailable, falling back to FTS. Reason: %s", str(e)
                    )
                    fallback_reason = FallbackReason.EMBEDDING_PROVIDERS_UNAVAILABLE
                except VectorStoreError as e:
                    logger.warning(
                        "Vector retrieval failed, falling back to FTS. Reason: %s", str(e)
                    )
                    fallback_reason = FallbackReason.VECTOR_RETRIEVAL_FAILED
                except Exception as e:
                    logger.warning(
                        "Unexpected error in vector retrieval, falling back to FTS. Reason: %s",
                        str(e),
                    )
                    fallback_reason = FallbackReason.VECTOR_RETRIEVAL_FAILED
            else:
                fallback_reason = FallbackReason.NO_SYNCED_VECTOR_STORE
        else:
            fallback_reason = FallbackReason.NO_SYNCED_VECTOR_STORE

        # 4. Fallback to FTS if vector retrieval failed or no stores were available
        if active_profile and active_profile.chunk_set_id:
            logger.info("Executing FTS fallback for document %s", document.id)
            fts_results = self.lexical_retriever.search(
                document_id=document.id,
                user_id=user_id,
                chunk_set_id=active_profile.chunk_set_id,
                query_text=query_text,
                top_k=top_k,
            )
            return fts_results, fallback_reason

        return [], fallback_reason

    def _has_any_vector_route(self, profile_id: str) -> bool:
        """
        Check if any store is SYNCED for this profile.
        If circuit breaker is open, it will still try the secondary.
        If both are PENDING/FAILED, returns False.
        """
        syncs = (
            self.vector_router.db.query(EmbeddingProfileStoreSync)
            .filter(
                EmbeddingProfileStoreSync.profile_id == profile_id,
                EmbeddingProfileStoreSync.status == "SYNCED",
            )
            .all()
        )
        return len(syncs) > 0
