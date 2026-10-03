from functools import lru_cache

from app.core.config import get_settings
from app.integrations.embeddings.cohere import CohereEmbeddingProvider
from app.integrations.embeddings.coordinator import EmbeddingCoordinator
from app.integrations.embeddings.gemini import GeminiEmbeddingProvider
from app.integrations.embeddings.huggingface_e5 import HuggingFaceE5Provider
from app.integrations.embeddings.local_e5 import LocalE5Provider


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

    hf_remote_provider = HuggingFaceE5Provider(
        api_key=(
            settings.huggingface_api_key.get_secret_value()
            if settings.huggingface_api_key
            else None
        ),
        model=settings.e5_embedding_model,
        dimensions=768,
        batch_size=10,
        timeout_seconds=settings.embedding_timeout_seconds,
    )

    hf_local_provider = LocalE5Provider(
        model_name=settings.e5_embedding_model,
        dimensions=768,
        batch_size=10,
    )

    providers = [gemini_provider, cohere_provider, hf_remote_provider, hf_local_provider]
    return EmbeddingCoordinator(providers=providers)
