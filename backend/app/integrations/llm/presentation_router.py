import logging
import time

from app.integrations.llm.base import LLMErrorKind, QuestionGenerationProviderError
from app.integrations.llm.circuit_breaker import CircuitBreaker
from app.integrations.llm.presentation import (
    PresentationGenerationFailed,
    PresentationGenerationProvider,
    PresentationGenerationRequest,
    PresentationGenerationResult,
    validate_presentation,
)

logger = logging.getLogger(__name__)


class PresentationGenerationRouter:
    def __init__(
        self,
        *,
        primary: PresentationGenerationProvider,
        fallback: PresentationGenerationProvider,
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

    def generate(self, request: PresentationGenerationRequest) -> PresentationGenerationResult:
        started_at = time.monotonic()
        primary_reason = self._circuit_reason(self.primary.name)
        if self.primary_circuit.allow_request():
            try:
                material = validate_presentation(self.primary.generate(request), request)
                self.primary_circuit.record_success()
                return self._result(material, self.primary, False, started_at, None)
            except QuestionGenerationProviderError as exc:
                self.primary_circuit.record_failure()
                primary_reason = exc.telemetry_reason
            except ValueError:
                self.primary_circuit.record_failure()
                primary_reason = f"{self.primary.name}:{LLMErrorKind.INVALID_OUTPUT.value}"
            logger.warning("Primary presentation provider failed: %s", primary_reason)

        fallback_reason = self._circuit_reason(self.fallback.name)
        if self.fallback_circuit.allow_request():
            try:
                material = validate_presentation(self.fallback.generate(request), request)
                self.fallback_circuit.record_success()
                return self._result(material, self.fallback, True, started_at, primary_reason)
            except QuestionGenerationProviderError as exc:
                self.fallback_circuit.record_failure()
                fallback_reason = exc.telemetry_reason
            except ValueError:
                self.fallback_circuit.record_failure()
                fallback_reason = f"{self.fallback.name}:{LLMErrorKind.INVALID_OUTPUT.value}"

        logger.error(
            "Presentation providers failed: primary=%s fallback=%s",
            primary_reason,
            fallback_reason,
        )
        raise PresentationGenerationFailed(
            primary_failure_reason=primary_reason,
            fallback_failure_reason=fallback_reason,
            latency_ms=self._elapsed_ms(started_at),
        )

    def _result(self, material, provider, fallback, started_at, primary_reason):
        return PresentationGenerationResult(
            presentation=material,
            provider=provider.name,
            model=provider.model,
            fallback_used=fallback,
            latency_ms=self._elapsed_ms(started_at),
            primary_failure_reason=primary_reason,
        )

    @staticmethod
    def _circuit_reason(provider: str) -> str:
        return f"{provider}:{LLMErrorKind.CIRCUIT_OPEN.value}"

    @staticmethod
    def _elapsed_ms(started_at: float) -> int:
        return max(0, round((time.monotonic() - started_at) * 1000))
