"""Embedding-provider contracts and adapters."""

from app.integrations.embeddings.base import (
    EmbeddingDocument,
    EmbeddingError,
    EmbeddingProvider,
)
from app.integrations.embeddings.cohere import CohereEmbeddingProvider
from app.integrations.embeddings.coordinator import EmbeddingCoordinator, FallbackTriggered
from app.integrations.embeddings.gemini import GeminiEmbeddingProvider
from app.integrations.embeddings.huggingface_e5 import HuggingFaceE5Provider
from app.integrations.embeddings.local_e5 import LocalE5Provider

__all__ = [
    "EmbeddingDocument",
    "EmbeddingError",
    "EmbeddingProvider",
    "GeminiEmbeddingProvider",
    "CohereEmbeddingProvider",
    "HuggingFaceE5Provider",
    "LocalE5Provider",
    "EmbeddingCoordinator",
    "FallbackTriggered",
]
