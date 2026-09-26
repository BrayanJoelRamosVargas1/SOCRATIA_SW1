from collections.abc import Sequence

from app.integrations.llm.base import DocumentContextChunk
from app.integrations.retrieval.base import FallbackReason, RetrievalMode
from app.integrations.retrieval.router import RetrievalRouter
from app.modules.p2_gestion_documentos_preparacion.models.document import Document


class DocumentContextUnavailableError(Exception):
    """Raised when no safe, document-scoped context can be built."""


class DocumentRetrievalService:
    def __init__(
        self,
        *,
        router: RetrievalRouter,
        top_k: int,
        max_context_chars: int,
    ) -> None:
        self.router = router
        self.top_k = top_k
        self.max_context_chars = max_context_chars

    def retrieve(
        self,
        *,
        user_id: str,
        document: Document,
        intents: Sequence[str],
    ) -> tuple[tuple[DocumentContextChunk, ...], RetrievalMode, FallbackReason]:
        deduplicated: dict[str, DocumentContextChunk] = {}

        overall_retrieval_mode = RetrievalMode.VECTOR_PRIMARY
        overall_fallback_reason = FallbackReason.NONE

        for intent in intents:
            matches, fallback_reason = self.router.retrieve_for_document(
                document=document, user_id=user_id, query_text=intent, top_k=self.top_k
            )

            if fallback_reason != FallbackReason.NONE:
                overall_fallback_reason = fallback_reason

            for match in matches:
                # Track the most degraded mode encountered
                if match.retrieval_mode == RetrievalMode.LEXICAL_FALLBACK:
                    overall_retrieval_mode = RetrievalMode.LEXICAL_FALLBACK
                elif (
                    match.retrieval_mode == RetrievalMode.VECTOR_SECONDARY
                    and overall_retrieval_mode == RetrievalMode.VECTOR_PRIMARY
                ):
                    overall_retrieval_mode = RetrievalMode.VECTOR_SECONDARY

                candidate = DocumentContextChunk(
                    id=match.chunk_id,
                    text=match.content,
                    score=match.raw_score,
                )

                current = deduplicated.get(match.chunk_id)
                # For FTS, a lower rank (1, 2, 3) is better. For vector, higher score is better.
                # Since we don't mix them usually, we just take the first we see or max score if vector
                if current is None:
                    deduplicated[match.chunk_id] = candidate
                elif (
                    match.retrieval_mode != RetrievalMode.LEXICAL_FALLBACK
                    and candidate.score > current.score
                ):
                    deduplicated[match.chunk_id] = candidate

        packed: list[DocumentContextChunk] = []
        used_chars = 0
        for chunk in deduplicated.values():
            if packed and used_chars + len(chunk.text) > self.max_context_chars:
                continue
            packed.append(chunk)
            used_chars += len(chunk.text)

        if not packed:
            raise DocumentContextUnavailableError

        return tuple(packed), overall_retrieval_mode, overall_fallback_reason
