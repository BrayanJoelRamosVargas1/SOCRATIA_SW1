"""Vector-store contracts and adapters."""

from app.integrations.vector_db.base import VectorRecord, VectorStoreError, VectorStoreProvider
from app.integrations.vector_db.pinecone import PineconeVectorStoreProvider

__all__ = [
    "PineconeVectorStoreProvider",
    "VectorRecord",
    "VectorStoreError",
    "VectorStoreProvider",
]
