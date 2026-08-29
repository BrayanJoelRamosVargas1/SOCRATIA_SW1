from functools import lru_cache

from app.core.config import get_settings
from app.integrations.embeddings.base import EmbeddingProvider
from app.integrations.embeddings.gemini import GeminiEmbeddingProvider


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    if settings.embedding_provider.lower() != "gemini":
        raise RuntimeError(f"Unsupported embedding provider: {settings.embedding_provider}")
    return GeminiEmbeddingProvider(
        api_key=(
            settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else None
        ),
        model=settings.gemini_embedding_model,
        dimensions=settings.embedding_dimensions,
        batch_size=settings.embedding_batch_size,
        timeout_seconds=settings.embedding_timeout_seconds,
    )
