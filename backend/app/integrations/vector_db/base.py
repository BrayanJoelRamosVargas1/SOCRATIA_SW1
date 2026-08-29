from dataclasses import dataclass
from typing import Protocol

VectorMetadataValue = str | int | float | bool | list[str]


class VectorStoreError(Exception):
    """Raised when a vector store operation cannot be completed."""


@dataclass(frozen=True, slots=True)
class VectorRecord:
    id: str
    values: list[float]
    metadata: dict[str, VectorMetadataValue]


class VectorStoreProvider(Protocol):
    def upsert(self, *, namespace: str, records: list[VectorRecord]) -> None:
        """Insert or replace vector records in a namespace."""

    def delete(self, *, namespace: str, ids: list[str]) -> None:
        """Delete the specified vector records from a namespace."""
