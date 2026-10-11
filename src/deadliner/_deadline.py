"""The monotonic deadline primitive and its expiry error."""

from __future__ import annotations

import time
from collections.abc import Callable

__all__ = ["Deadline", "DeadlineExpired"]


class DeadlineExpired(TimeoutError):
    """Raised when an operation runs past its deadline."""


class Deadline:
    """A monotonic time budget: time remaining, expiry, and bounded sleeping.

    Build one with a number of seconds and pass it down a multi-step operation.
    Each step reads :attr:`remaining`, bounds its own wait with :meth:`sleep`,
    or calls :meth:`raise_if_expired` to stop once the budget is spent. The clock
    is :func:`time.monotonic`, so it is immune to wall-clock jumps.
    """

    def __init__(
        self,
        seconds: float,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._clock = clock
        self._sleep = sleep
        self._deadline = clock() + seconds

    @property
    def remaining(self) -> float:
        """Seconds left before expiry, never below zero."""
        return max(0.0, self._deadline - self._clock())

    @property
    def expired(self) -> bool:
        """True once no time is left."""
        return self._clock() >= self._deadline

    def sleep(self, step: float) -> float:
        """Sleep up to ``step`` seconds, never past the deadline.

        Returns the seconds actually slept, which is zero once expired.
        """
        span = min(max(0.0, step), self.remaining)
        if span > 0.0:
            self._sleep(span)
        return span

    def raise_if_expired(self, exc: type[BaseException] | BaseException = DeadlineExpired) -> None:
        """Raise ``exc`` (a type or an instance) if the deadline has passed."""
        if self.expired:
            raise exc
