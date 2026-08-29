from functools import lru_cache

from app.core.config import get_settings
from app.integrations.vector_db.base import VectorStoreProvider
from app.integrations.vector_db.pinecone import PineconeVectorStoreProvider


@lru_cache
def get_vector_store_provider() -> VectorStoreProvider:
    settings = get_settings()
    if settings.vector_primary_provider.lower() != "pinecone":
        raise RuntimeError(
            f"Unsupported vector store provider: {settings.vector_primary_provider}"
        )
    return PineconeVectorStoreProvider(
        api_key=(
            settings.pinecone_api_key.get_secret_value() if settings.pinecone_api_key else None
        ),
        index_name=settings.pinecone_index_name,
        dimensions=settings.embedding_dimensions,
        cloud=settings.pinecone_cloud,
        region=settings.pinecone_region,
        timeout_seconds=settings.pinecone_timeout_seconds,
    )
