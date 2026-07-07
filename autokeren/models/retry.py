"""Retry policy + circuit breaker."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, TypeVar


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    failure_threshold: int
    open_seconds: float
    _failures: int = 0
    _last_failure: float | None = None
    _state: CircuitState = CircuitState.CLOSED

    def record_success(self):
        self._failures = 0
        self._state = CircuitState.CLOSED

    def record_failure(self):
        self._failures += 1
        self._last_failure = time.monotonic()
        if self._failures >= self.failure_threshold:
            self._state = CircuitState.OPEN

    def allow(self) -> bool:
        if self._state == CircuitState.CLOSED:
            return True
        if self._last_failure and time.monotonic() - self._last_failure > self.open_seconds:
            self._state = CircuitState.HALF_OPEN
            return True
        return False

    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN and self.allow():
            return CircuitState.HALF_OPEN
        return self._state


@dataclass
class RetryPolicy:
    max_retries: int = 5
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on: frozenset[int] = frozenset({408, 429, 500, 502, 503, 504})

    def should_retry(self, exc: Exception, status: int | None, attempt: int) -> bool:
        if attempt >= self.max_retries:
            return False
        if status is None:
            return True  # network-level failure (timeout, connection error)
        if status in self.retry_on:
            return True
        return False

    def sleep_for(self, attempt: int, exc: Exception | None = None) -> float:
        if exc is not None:
            retry_after = getattr(exc, "retry_after", None)
            if retry_after and retry_after > 0:
                return min(retry_after, self.max_delay)
        delay = self.base_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        return delay


T = TypeVar("T")


def retry_call(
    fn: Callable[[], T],
    policy: RetryPolicy,
    breaker: CircuitBreaker | None = None,
    on_retry: Callable[[int, float, Exception], None] | None = None,
) -> T:
    """Call fn with retries. fn must raise and supply status via exception attribute 'status'."""
    if breaker and not breaker.allow():
        raise RuntimeError("circuit breaker open")
    last_exc: Exception | None = None
    for attempt in range(policy.max_retries + 1):
        try:
            result = fn()
            if breaker:
                breaker.record_success()
            return result
        except Exception as e:
            last_exc = e
            status = getattr(e, "status", None)
            if not policy.should_retry(e, status, attempt):
                break
            delay = policy.sleep_for(attempt, e)
            if on_retry:
                on_retry(attempt + 1, delay, e)
            time.sleep(delay)
    if breaker and last_exc:
        breaker.record_failure()
    raise last_exc or RuntimeError("retry_call failed")
