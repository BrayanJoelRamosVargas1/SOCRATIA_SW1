import time
from collections import deque
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class RateBudget:
    available_rpm: int
    available_tpm: int
    wait_ms: float
    is_allowed: bool

class TokenRateLimiter:
    """
    In-memory Sliding Window Token-Aware Rate Limiter.
    
    WARNING:
    This implementation assumes a single worker (EMBEDDING_WORKER_CONCURRENCY=1).
    Until distributed coordination (e.g. via PostgreSQL or Redis) is implemented, 
    running multiple workers will cause rate limits to be exceeded.
    """

    def __init__(
        self, 
        max_rpm: int, 
        max_tpm: int, 
        safe_tpm_ratio: float = 0.75,
        window_seconds: float = 60.0
    ) -> None:
        self.max_rpm = max_rpm
        self.max_tpm = max_tpm
        self.safe_tpm = int(max_tpm * safe_tpm_ratio)
        self.window_seconds = window_seconds
        
        # deques store tuples of (timestamp_seconds, tokens_used)
        self._requests: deque[tuple[float, int]] = deque()

    def _cleanup(self, now: float) -> None:
        threshold = now - self.window_seconds
        while self._requests and self._requests[0][0] <= threshold:
            self._requests.popleft()

    def estimate_tokens(self, text: str) -> int:
        """
        Conservative estimate for Gemini tokens.
        1 token ~ 3 characters.
        """
        return (len(text) // 3) + 1

    def calculate_budget(self, requested_tokens: int) -> RateBudget:
        now = time.monotonic()
        self._cleanup(now)

        current_rpm = len(self._requests)
        current_tpm = sum(tokens for _, tokens in self._requests)

        available_rpm = max(0, self.max_rpm - current_rpm)
        available_tpm = max(0, self.safe_tpm - current_tpm)

        is_allowed = available_rpm > 0 and available_tpm >= requested_tokens

        wait_ms = 0.0
        if not is_allowed:
            # Calculate how long we have to wait to free up enough budget
            if current_rpm >= self.max_rpm and self._requests:
                wait_for_rpm = (self._requests[0][0] + self.window_seconds) - now
            else:
                wait_for_rpm = 0.0
            
            wait_for_tpm = 0.0
            if current_tpm + requested_tokens > self.safe_tpm:
                freed_tpm = 0
                needed_tpm = (current_tpm + requested_tokens) - self.safe_tpm
                for timestamp, tokens in self._requests:
                    freed_tpm += tokens
                    if freed_tpm >= needed_tpm:
                        wait_for_tpm = (timestamp + self.window_seconds) - now
                        break
            
            wait_ms = max(wait_for_rpm, wait_for_tpm, 0.0) * 1000.0

        return RateBudget(
            available_rpm=available_rpm,
            available_tpm=available_tpm,
            wait_ms=wait_ms,
            is_allowed=is_allowed
        )

    def consume(self, tokens: int) -> None:
        """Record a successful request."""
        self._requests.append((time.monotonic(), tokens))

