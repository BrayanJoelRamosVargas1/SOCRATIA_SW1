from typing import BinaryIO, Protocol


class StorageError(Exception):
    """Raised when an object cannot be persisted or removed."""


class StorageProvider(Protocol):
    def save(self, key: str, source: BinaryIO) -> int:
        """Persist source under key and return the number of bytes written."""

    def delete(self, key: str) -> None:
        """Delete key if it exists."""

    def exists(self, key: str) -> bool:
        """Return whether key exists."""
