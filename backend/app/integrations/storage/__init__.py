"""Object-storage interfaces and adapters."""

from app.integrations.storage.base import StorageError, StorageProvider
from app.integrations.storage.local import LocalStorageProvider

__all__ = ["LocalStorageProvider", "StorageError", "StorageProvider"]
