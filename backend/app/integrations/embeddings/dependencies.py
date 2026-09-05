from functools import lru_cache

from app.core.config import get_settings
from app.integrations.embeddings.base import EmbeddingProvider
from app.integrations.embeddings.gemini import GeminiEmbeddingProvider

from app.integrations.embeddings.cohere import CohereEmbeddingProvider
from app.integrations.embeddings.coordinator import EmbeddingCoordinator

@lru_cache
def get_embedding_provider() -> EmbeddingCoordinator:
    settings = get_settings()
    gemini_provider = GeminiEmbeddingProvider(
        api_key=(settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else None),
        model=settings.gemini_embedding_model,
        dimensions=settings.embedding_dimensions,
        batch_size=settings.embedding_batch_size,
        timeout_seconds=settings.embedding_timeout_seconds,
    )
    cohere_provider = CohereEmbeddingProvider(
        api_key=(settings.cohere_api_key.get_secret_value() if settings.cohere_api_key else None),
        model=settings.cohere_embedding_model,
        dimensions=settings.cohere_embedding_dimensions,
        batch_size=settings.embedding_batch_size,
        timeout_seconds=settings.embedding_timeout_seconds,
    )
    return EmbeddingCoordinator(primary_provider=gemini_provider, secondary_provider=cohere_provider)
