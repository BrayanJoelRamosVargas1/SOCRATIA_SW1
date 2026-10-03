from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RetrievalMode(StrEnum):
    VECTOR_PRIMARY = "VECTOR_PRIMARY"
    VECTOR_SECONDARY = "VECTOR_SECONDARY"
    LEXICAL_FALLBACK = "LEXICAL_FALLBACK"


class FallbackReason(StrEnum):
    NONE = "NONE"
    PRIMARY_VECTOR_STORE_FAILED = "PRIMARY_VECTOR_STORE_FAILED"
    NO_SYNCED_VECTOR_STORE = "NO_SYNCED_VECTOR_STORE"
    EMBEDDING_PROVIDERS_UNAVAILABLE = "EMBEDDING_PROVIDERS_UNAVAILABLE"
    VECTOR_RETRIEVAL_FAILED = "VECTOR_RETRIEVAL_FAILED"


@dataclass
class RetrievalResult:
    chunk_id: str
    content: str
    rank: int
    raw_score: float
    retrieval_mode: RetrievalMode
    source: str
    degraded: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
