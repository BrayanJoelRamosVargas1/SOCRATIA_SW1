import logging
import time

from app.integrations.llm.base import (
    LLMErrorKind,
    QuestionGenerationFailed,
    QuestionGenerationProvider,
    QuestionGenerationProviderError,
    QuestionGenerationRequest,
    QuestionGenerationResult,
    validate_question_bank,
)
from app.integrations.llm.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class QuestionGenerationRouter:
    def __init__(
        self,
        *,
        primary: QuestionGenerationProvider,
        fallback: QuestionGenerationProvider,
        failure_threshold: int,
        recovery_seconds: int,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.primary_circuit = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_seconds=recovery_seconds,
        )
        self.fallback_circuit = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_seconds=recovery_seconds,
        )

    def generate(self, request: QuestionGenerationRequest) -> QuestionGenerationResult:
        started_at = time.monotonic()
        primary_failure_reason: str
        if self.primary_circuit.allow_request():
            try:
                bank = validate_question_bank(self.primary.generate(request), request)
                self.primary_circuit.record_success()
                return QuestionGenerationResult(
                    bank=bank,
                    provider=self.primary.name,
                    model=self.primary.model,
                    fallback_used=False,
                    latency_ms=self._elapsed_ms(started_at),
                    primary_failure_reason=None,
                )
            except QuestionGenerationProviderError as exc:
                self.primary_circuit.record_failure()
                primary_failure_reason = exc.telemetry_reason
                logger.warning("Primary question provider failed: %s", primary_failure_reason)
            except ValueError:
                self.primary_circuit.record_failure()
                primary_failure_reason = (
                    f"{self.primary.name}:{LLMErrorKind.INVALID_OUTPUT.value}"
                )
                logger.warning("Primary question provider returned semantically invalid output")
        else:
            primary_failure_reason = f"{self.primary.name}:{LLMErrorKind.CIRCUIT_OPEN.value}"

        if self.fallback_circuit.allow_request():
            try:
                bank = validate_question_bank(self.fallback.generate(request), request)
                self.fallback_circuit.record_success()
                return QuestionGenerationResult(
                    bank=bank,
                    provider=self.fallback.name,
                    model=self.fallback.model,
                    fallback_used=True,
                    latency_ms=self._elapsed_ms(started_at),
                    primary_failure_reason=primary_failure_reason,
                )
            except QuestionGenerationProviderError as exc:
                self.fallback_circuit.record_failure()
                fallback_failure_reason = exc.telemetry_reason
            except ValueError:
                self.fallback_circuit.record_failure()
                fallback_failure_reason = (
                    f"{self.fallback.name}:{LLMErrorKind.INVALID_OUTPUT.value}"
                )
        else:
            fallback_failure_reason = f"{self.fallback.name}:{LLMErrorKind.CIRCUIT_OPEN.value}"

        logger.error(
            "Question generation providers failed: primary=%s fallback=%s",
            primary_failure_reason,
            fallback_failure_reason,
        )
        raise QuestionGenerationFailed(
            primary_failure_reason=primary_failure_reason,
            fallback_failure_reason=fallback_failure_reason,
            latency_ms=self._elapsed_ms(started_at),
        )

    @staticmethod
    def _elapsed_ms(started_at: float) -> int:
        return max(0, round((time.monotonic() - started_at) * 1000))
