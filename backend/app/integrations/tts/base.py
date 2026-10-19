import dataclasses
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


@dataclasses.dataclass(frozen=True)
class TTSRequest:
    text: str
    voice_id: str | None = None
    speaker_index: int = 0


class TTSProviderError(Exception):
    def __init__(self, message: str, provider: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable


class TTSProvider(ABC):
    mime_type = "audio/mpeg"
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def synthesize(self, request: TTSRequest) -> AsyncIterator[bytes]: ...
