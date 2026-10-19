from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.integrations.vector_db.base import VectorStoreProvider
from app.integrations.vector_db.pgvector_provider import PgVectorStoreProvider
from app.integrations.vector_db.pinecone import PineconeVectorStoreProvider
from app.integrations.vector_db.router import VectorStoreRouter


def get_vector_store_provider(db: Session = Depends(get_db)) -> VectorStoreProvider:
    settings = get_settings()

    if settings.vector_primary_provider == "pgvector":
        return PgVectorStoreProvider(db=db)

    # We use get_secret_value() if it's a SecretStr, else the raw string
    api_key = (
        settings.pinecone_api_key.get_secret_value()
        if hasattr(settings.pinecone_api_key, "get_secret_value")
        else settings.pinecone_api_key
    )

    pinecone = PineconeVectorStoreProvider(
        api_key=api_key,
        index_name=settings.pinecone_index_name,
        dimensions=settings.embedding_dimensions,
        cloud=settings.pinecone_cloud,
        region=settings.pinecone_region,
        timeout_seconds=settings.pinecone_timeout_seconds,
    )

    pgvector = PgVectorStoreProvider(db=db)

    return VectorStoreRouter(
        primary=pinecone, secondary=pgvector, db=db, circuit_breaker_timeout_sec=30
    )
