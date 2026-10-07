import logging
from collections.abc import Iterable
from enum import StrEnum

from app.core.config import get_settings
from app.integrations.embeddings.base import EmbeddingDocument, EmbeddingError, EmbeddingProvider
from app.modules.p2_gestion_documentos_preparacion.models.document import Document

logger = logging.getLogger(__name__)


class FallbackType(StrEnum):
    EXECUTOR_CHANGE = "EXECUTOR_CHANGE"
    SPACE_CHANGE = "SPACE_CHANGE"


class FallbackTriggered(Exception):
    """Raised when a provider fails and triggers a fallback to the next provider."""

    def __init__(self, message: str, fallback_type: FallbackType, next_provider: EmbeddingProvider):
        super().__init__(message)
        self.fallback_type = fallback_type
        self.next_provider = next_provider


class EmbeddingCoordinator:
    def __init__(self, providers: list[EmbeddingProvider]) -> None:
        """
        Orchestrates fallback between providers.
        The providers list represents the priority order for fallback.
        """
        if not providers:
            raise ValueError("EmbeddingCoordinator requires at least one provider")
        self.providers = providers

        # Map spaces to providers for query routing (only keeps the first available provider per space)
        self.providers_by_space = {}
        for p in self.providers:
            if p.embedding_space_id not in self.providers_by_space:
                self.providers_by_space[p.embedding_space_id] = p

    def embed_documents_with_fallback(
        self, documents: list[EmbeddingDocument], active_provider: EmbeddingProvider
    ) -> Iterable[list[list[float]]]:
        """
        Embeds a batch of documents using the active_provider.
        If the provider throws an EmbeddingError, it finds the next provider in the chain
        and raises FallbackTriggered so the service can adapt.
        """
        # Simulated failure for testing.
        # EMBEDDING_FORCE_PROVIDER_FAILURE accepts a CSV of provider IDs to forcibly fail,
        # e.g. "gemini,cohere,huggingface" or "all" to fail every remote provider.
        settings = get_settings()
        if settings.app_env != "production" and settings.embedding_force_provider_failure:
            forced_failures = {
                p.strip().lower() for p in settings.embedding_force_provider_failure.split(",")
            }
            if (
                active_provider.provider_id.lower() in forced_failures
                or "all" in forced_failures
                # Legacy single-string alias kept for backwards compatibility
                or settings.embedding_force_provider_failure == "both"
            ):
                self._trigger_fallback(
                    active_provider,
                    f"Simulated {active_provider.provider_id} failure triggered by configuration",
                )

        try:
            for batch in active_provider.embed_documents(documents):
                yield batch
        except EmbeddingError as exc:
            logger.warning(
                "Provider %s failed with error: %s. Attempting fallback.",
                active_provider.provider_id,
                str(exc),
            )
            self._trigger_fallback(active_provider, str(exc))

    def _trigger_fallback(self, current_provider: EmbeddingProvider, error_message: str):
        try:
            current_index = self.providers.index(current_provider)
        except ValueError:
            raise EmbeddingError(
                f"Current provider {current_provider.provider_id} is not in the coordinator's chain"
            )

        next_provider = None
        for i in range(current_index + 1, len(self.providers)):
            p = self.providers[i]
            if p.is_available:
                next_provider = p
                break

        if not next_provider:
            logger.error(
                "No fallback providers available after %s failed.", current_provider.provider_id
            )
            raise EmbeddingError(f"All providers exhausted. Last failure: {error_message}")

        fallback_type = (
            FallbackType.EXECUTOR_CHANGE
            if (
                next_provider.embedding_space_id == current_provider.embedding_space_id
                and getattr(next_provider, "compatibility_fingerprint", None)
                == getattr(current_provider, "compatibility_fingerprint", None)
            )
            else FallbackType.SPACE_CHANGE
        )

        logger.info(
            "Triggering fallback: %s -> %s (%s)",
            current_provider.provider_id,
            next_provider.provider_id,
            fallback_type,
        )
        raise FallbackTriggered(error_message, fallback_type, next_provider)

    def embed_queries_for_document(self, document: Document, texts: list[str]) -> list[list[float]]:
        """
        Routes the queries to the correct provider based on the document's active embedding profile.
        """
        if not document.active_embedding_profile_id:
            raise ValueError(f"Document {document.id} has no active embedding profile.")

        active_profile = next(
            (
                p
                for p in document.embedding_profiles
                if p.id == document.active_embedding_profile_id
            ),
            None,
        )
        if not active_profile:
            raise ValueError(
                f"Active embedding profile {document.active_embedding_profile_id} not found in document relationships."
            )

        space_id = active_profile.embedding_space_id

        candidates = [p for p in self.providers if p.embedding_space_id == space_id]
        if not candidates:
            raise ValueError(f"No provider configured for embedding space: {space_id}")

        for provider in candidates:
            if provider.is_available:
                return provider.embed_queries(texts)

        raise EmbeddingError(
            f"All providers for space {space_id} are unavailable for query embedding."
        )

    def get_initial_provider(self) -> EmbeddingProvider:
        """Returns the first available provider in the chain."""
        for p in self.providers:
            if p.is_available:
                return p
        raise RuntimeError("No embedding providers are available.")
