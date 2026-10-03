from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol


class EmbeddingError(Exception):
    """Raised when an embedding provider cannot complete a request."""


@dataclass(frozen=True, slots=True)
class EmbeddingDocument:
    title: str | None
    text: str


class EmbeddingProvider(Protocol):
    @property
    def provider_id(self) -> str:
        """Return the unique provider identifier."""

    @property
    def embedding_space_id(self) -> str:
        """Return the mathematical embedding space ID this provider operates in."""

    @property
    def compatibility_fingerprint(self) -> str:
        """Return the strict mathematical fingerprint required for safe EXECUTOR_CHANGE."""

    @property
    def is_available(self) -> bool:
        """Return True if the provider is configured and available for use."""

    @property
    def execution_location(self) -> str:
        """Return 'remote' or 'local'."""

    @property
    def model(self) -> str:
        """Return the provider model identifier."""

    @property
    def dimensions(self) -> int:
        """Return the number of values in each generated vector."""

    def embed_documents(self, documents: list[EmbeddingDocument]) -> Iterable[list[list[float]]]:
        """Generate one retrieval embedding per document, preserving input order."""

    def embed_queries(self, queries: list[str]) -> list[list[float]]:
        """Generate one retrieval embedding per search query, preserving input order."""
