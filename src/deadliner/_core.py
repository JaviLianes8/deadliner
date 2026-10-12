"""The state and read-only queries every deadline answers."""

from __future__ import annotations

import math
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, overload

from ._errors import DeadlineExpired, exceeded

__all__ = ["AsyncSleep", "Clock", "Sleep"]

_T = TypeVar("_T")
#: A zero-argument callable returning seconds on a monotonic scale.
Clock = Callable[[], float]
#: A callable that blocks for the given number of seconds.
Sleep = Callable[[float], None]
#: An async callable that waits for the given number of seconds.
AsyncSleep = Callable[[float], Awaitable[None]]


class _Core:
    """Holds the clock and the expiry time; answers how much is left."""

    def __init__(
        self,
        seconds: float,
        *,
        clock: Clock = time.monotonic,
        sleep: Sleep = time.sleep,
        async_sleep: AsyncSleep | None = None,
    ) -> None:
        if math.isnan(seconds):
            raise ValueError("seconds must not be NaN")
        self._clock = clock
        self._sleep = sleep
        self._async_sleep = async_sleep
        self._start = clock()
        self._when = self._start + seconds

    @property
    def when(self) -> float:
        """The absolute expiry time on the deadline's clock (``inf`` for :meth:`never`)."""
        return self._when

    @property
    def infinite(self) -> bool:
        """True when the deadline never expires."""
        return self._when == math.inf

    @property
    def elapsed(self) -> float:
        """Seconds since this deadline object was created."""
        return self._clock() - self._start

    @property
    def remaining(self) -> float:
        """Seconds left before expiry, never below zero (``inf`` when infinite)."""
        return max(0.0, self._when - self._clock())

    @property
    def expired(self) -> bool:
        """True once no time is left."""
        return self._clock() >= self._when

    def check(self, step: str | None = None) -> float:
        """Return the seconds left, or raise :class:`DeadlineExceeded` once expired.

        ``step`` names the work about to start; it goes into the message and the
        error's ``step`` attribute. The error's ``overrun`` holds how late it is.
        """
        left = self._when - self._clock()
        if left > 0.0:
            return left
        raise exceeded(step, max(0.0, -left))

    def raise_if_expired(self, exc: type[BaseException] | BaseException = DeadlineExpired) -> None:
        """Raise ``exc`` (a type or an instance) if the deadline has passed."""
        if self.expired:
            raise exc

    @overload
    def timeout(self, cap: float | None = None) -> float | None: ...
    @overload
    def timeout(self, cap: float | None = None, *, unbounded: _T) -> float | _T: ...
    def timeout(self, cap: float | None = None, *, unbounded: Any = None) -> Any:
        """The ``timeout=`` value to hand a blocking stdlib call. Never negative.

        Returns the seconds left, at most ``cap`` when given, and ``0.0`` once
        expired. An infinite deadline with no cap returns ``unbounded``: the default
        ``None`` suits ``queue.Queue.get``, ``subprocess.run`` and
        ``socket.settimeout``; pass ``unbounded=-1`` for ``threading.Lock.acquire``.
        Note that ``socket.settimeout(0.0)`` switches to non-blocking mode, so call
        :meth:`check` first when a zero would change the meaning of the call.
        """
        if cap is not None and math.isnan(cap):
            raise ValueError("cap must not be NaN")
        left = self.remaining
        if cap is not None:
            left = min(left, max(0.0, cap))
        return unbounded if left == math.inf else left

    def _span(self, step: float) -> float:
        if math.isnan(step):
            raise ValueError("step must not be NaN")
        return min(max(0.0, step), self.remaining)

    def _settle(self) -> float:
        # A cut sleep can wake before a coarse clock shows the deadline as passed.
        return max(self.remaining, 0.001)

    def _exceeded(self, step: str | None) -> DeadlineExpired:
        return exceeded(step, max(0.0, self._clock() - self._when))
