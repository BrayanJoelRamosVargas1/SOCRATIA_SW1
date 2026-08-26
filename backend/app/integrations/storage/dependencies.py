from functools import lru_cache

from app.core.config import get_settings
from app.integrations.storage.base import StorageProvider
from app.integrations.storage.local import LocalStorageProvider


@lru_cache
def get_storage_provider() -> StorageProvider:
    return LocalStorageProvider(get_settings().local_storage_path)
