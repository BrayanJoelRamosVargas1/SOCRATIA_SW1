import dataclasses
from abc import ABC, abstractmethod


@dataclasses.dataclass(frozen=True)
class STTRequest:
    audio_bytes: bytes
    mime_type: str
    prompt: str | None = None


@dataclasses.dataclass(frozen=True)
class STTResult:
    text: str
    latency_ms: int
    provider: str
    model: str


class STTProviderError(Exception):
    def __init__(self, message: str, provider: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable


class STTProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def transcribe(self, request: STTRequest) -> STTResult:
        ...
