from dataclasses import dataclass
from typing import Protocol


class EmbeddingError(Exception):
    """Raised when an embedding provider cannot complete a request."""


@dataclass(frozen=True, slots=True)
class EmbeddingDocument:
    title: str
    text: str


class EmbeddingProvider(Protocol):
    @property
    def model(self) -> str:
        """Return the provider model identifier."""

    @property
    def dimensions(self) -> int:
        """Return the number of values in each generated vector."""

    def embed_documents(self, documents: list[EmbeddingDocument]) -> list[list[float]]:
        """Generate one retrieval embedding per document, preserving input order."""

    def embed_queries(self, queries: list[str]) -> list[list[float]]:
        """Generate one retrieval embedding per search query, preserving input order."""
