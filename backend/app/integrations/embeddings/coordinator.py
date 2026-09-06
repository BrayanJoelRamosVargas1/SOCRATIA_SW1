import logging
from collections.abc import Iterable

from app.core.config import get_settings
from app.integrations.embeddings.base import EmbeddingDocument, EmbeddingError
from app.modules.p2_gestion_documentos_preparacion.models.document import Document

logger = logging.getLogger(__name__)

class FallbackTriggered(Exception):
    """Raised when the primary provider fails due to a persistent external error (e.g., 429 quota, 500s)."""
    pass

class EmbeddingCoordinator:
    def __init__(self, primary_provider, secondary_provider) -> None:
        """
        Orchestrates fallback between providers.
        """
        self.primary_provider = primary_provider
        self.secondary_provider = secondary_provider
        
        # Map spaces to providers for query routing
        self.providers_by_space = {
            "GEMINI_EMBEDDING_2_768_V1": self.primary_provider,
            "COHERE_EMBED-V4.0_1024_V1": self.secondary_provider,
        }

    def embed_documents_with_fallback(
        self, documents: list[EmbeddingDocument], use_fallback: bool = False
    ) -> Iterable[list[list[float]]]:
        """
        Embeds a batch of documents using the primary provider.
        If use_fallback is True, it forces the secondary provider.
        If the primary provider throws an EmbeddingError, it raises FallbackTriggered
        so the service can switch spaces and restart.
        """
        active_provider = self.secondary_provider if use_fallback else self.primary_provider
        
        try:
            settings = get_settings()
            if not use_fallback and settings.embedding_force_provider_failure in ("gemini", "both") and settings.app_env != "production":
                raise EmbeddingError("Simulated Gemini failure triggered by configuration")
            elif use_fallback and settings.embedding_force_provider_failure in ("cohere", "both") and settings.app_env != "production":
                raise EmbeddingError("Simulated Cohere failure triggered by configuration")

            # Yield from the underlying provider
            # Note: Since it's a generator, the error might happen during iteration.
            for batch in active_provider.embed_documents(documents):
                yield batch
        except EmbeddingError as exc:
            # Internal/code bugs will raise standard Exceptions and crash (no fallback).
            # EmbeddingError indicates an external API failure (429, 500, quota exhausted).
            if not use_fallback:
                logger.warning("Primary provider failed with external error: %s. Triggering fallback.", str(exc))
                raise FallbackTriggered(str(exc)) from exc
            else:
                logger.error("Secondary provider also failed: %s", str(exc))
                raise

    def embed_queries_for_document(self, document: Document, texts: list[str]) -> list[list[float]]:
        """
        Routes the queries to the correct provider based on the document's active embedding profile.
        Ensures that 768d profiles use Gemini and 1024d profiles use Cohere.
        """
        if not document.active_embedding_profile_id:
            raise ValueError(f"Document {document.id} has no active embedding profile.")
            
        active_profile = next(
            (p for p in document.embedding_profiles if p.id == document.active_embedding_profile_id), None
        )
        if not active_profile:
            raise ValueError(f"Active embedding profile {document.active_embedding_profile_id} not found in document relationships.")
            
        space_id = active_profile.embedding_space_id
        provider = self.providers_by_space.get(space_id)
        
        if not provider:
            raise ValueError(f"No provider configured for embedding space: {space_id}")
            
        return provider.embed_queries(texts)

    def get_space_id_for_primary(self) -> str:
        return "GEMINI_EMBEDDING_2_768_V1"

    def get_space_id_for_fallback(self) -> str:
        return "COHERE_EMBED-V4.0_1024_V1"
