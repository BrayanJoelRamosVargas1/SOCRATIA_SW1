import dataclasses
from abc import ABC, abstractmethod
from typing import AsyncIterator


@dataclasses.dataclass(frozen=True)
class TTSRequest:
    text: str
    voice_id: str | None = None


class TTSProviderError(Exception):
    def __init__(self, message: str, provider: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable


class TTSProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def synthesize(self, request: TTSRequest) -> AsyncIterator[bytes]:
        ...
