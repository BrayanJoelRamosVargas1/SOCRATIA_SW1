"""Vector-store contracts and adapters."""

from app.integrations.vector_db.base import (
    VectorFilter,
    VectorMatch,
    VectorRecord,
    VectorStoreError,
    VectorStoreProvider,
)
from app.integrations.vector_db.pinecone import PineconeVectorStoreProvider

__all__ = [
    "PineconeVectorStoreProvider",
    "VectorFilter",
    "VectorMatch",
    "VectorRecord",
    "VectorStoreError",
    "VectorStoreProvider",
]
