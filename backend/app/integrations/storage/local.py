import os
import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

from app.integrations.storage.base import StorageError


class LocalStorageProvider:
    """Filesystem adapter used locally; S3 will implement the same contract later."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def path_for(self, key: str) -> Path:
        target = (self.root / key).resolve()
        if not target.is_relative_to(self.root):
            raise StorageError("Invalid storage key")
        return target

    def save(self, key: str, source: BinaryIO) -> int:
        target = self.path_for(key)
        temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.uploading")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            source.seek(0)
            with temporary.open("wb") as destination:
                shutil.copyfileobj(source, destination, length=1024 * 1024)
                destination.flush()
                os.fsync(destination.fileno())
            size = temporary.stat().st_size
            os.replace(temporary, target)
            return size
        except OSError as exc:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise StorageError("Could not persist document") from exc

    def delete(self, key: str) -> None:
        target = self.path_for(key)
        try:
            target.unlink(missing_ok=True)
            self._remove_empty_parents(target.parent)
        except OSError as exc:
            raise StorageError("Could not delete document") from exc

    def exists(self, key: str) -> bool:
        return self.path_for(key).is_file()

    def _remove_empty_parents(self, directory: Path) -> None:
        while directory != self.root and directory.is_relative_to(self.root):
            try:
                directory.rmdir()
            except OSError:
                break
            directory = directory.parent

