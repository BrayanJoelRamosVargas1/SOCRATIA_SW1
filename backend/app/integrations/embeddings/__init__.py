"""Embedding-provider contracts and adapters."""

from app.integrations.embeddings.base import (
    EmbeddingDocument,
    EmbeddingError,
    EmbeddingProvider,
)
from app.integrations.embeddings.gemini import GeminiEmbeddingProvider

__all__ = [
    "EmbeddingDocument",
    "EmbeddingError",
    "EmbeddingProvider",
    "GeminiEmbeddingProvider",
]
