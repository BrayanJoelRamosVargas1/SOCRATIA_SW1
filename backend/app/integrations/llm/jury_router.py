import time

from app.integrations.llm.circuit_breaker import CircuitBreaker
from app.integrations.llm.jury_base import (
    JuryRoutingFailed,
    JuryRoutingProvider,
    JuryRoutingProviderError,
    JuryRoutingRequest,
    JuryRoutingResult,
)


class JuryRoutingRouter:
    def __init__(
        self,
        *,
        primary: JuryRoutingProvider,
        fallback: JuryRoutingProvider,
        failure_threshold: int,
        recovery_seconds: int,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_seconds=recovery_seconds,
        )

    async def route(self, request: JuryRoutingRequest) -> JuryRoutingResult:
        start_time = time.monotonic()
        primary_failure_reason: str | None = None

        if self.breaker.allow_request():
            try:
                decision = await self.primary.route(request)
                self.breaker.record_success()
                return JuryRoutingResult(
                    decision=decision,
                    provider=self.primary.name,
                    model=self.primary.model,
                    fallback_used=False,
                    latency_ms=self._latency_ms(start_time),
                    primary_failure_reason=None,
                )
            except JuryRoutingProviderError as exc:
                self.breaker.record_failure()
                primary_failure_reason = exc.telemetry_reason
        else:
            primary_failure_reason = f"{self.primary.name}:circuit_open"

        try:
            decision = await self.fallback.route(request)
            return JuryRoutingResult(
                decision=decision,
                provider=self.fallback.name,
                model=self.fallback.model,
                fallback_used=True,
                latency_ms=self._latency_ms(start_time),
                primary_failure_reason=primary_failure_reason,
            )
        except JuryRoutingProviderError as exc:
            raise JuryRoutingFailed(
                "All jury routing providers failed",
            ) from exc

    @staticmethod
    def _latency_ms(start_time: float) -> int:
        return int((time.monotonic() - start_time) * 1000)
