"""The state and read-only queries every deadline answers."""

from __future__ import annotations

import math
import time
from typing import TypeVar, overload

from ._errors import DeadlineExpired, exceeded
from ._types import AsyncSleep, Clock, Sleep

__all__ = ["AsyncSleep", "Clock", "Sleep"]

_T = TypeVar("_T")


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
        """The absolute expiry time on the deadline's clock (``inf`` for :meth:`never`).

        >>> from deadliner import Deadline
        >>> Deadline(5, clock=lambda: 2.0).when
        7.0
        """
        return self._when

    @property
    def infinite(self) -> bool:
        """True when the deadline never expires.

        >>> from deadliner import Deadline
        >>> Deadline.never().infinite
        True
        """
        return self._when == math.inf

    @property
    def elapsed(self) -> float:
        """Seconds since this deadline object was created.

        >>> from deadliner import Deadline
        >>> Deadline(5, clock=lambda: 2.0).elapsed
        0.0
        """
        return self._clock() - self._start

    @property
    def remaining(self) -> float:
        """Seconds left before expiry, never below zero (``inf`` when infinite).

        >>> from deadliner import Deadline
        >>> Deadline(-1, clock=lambda: 0.0).remaining
        0.0
        """
        return max(0.0, self._when - self._clock())

    @property
    def expired(self) -> bool:
        """True once no time is left.

        >>> from deadliner import Deadline
        >>> Deadline(0, clock=lambda: 0.0).expired
        True
        """
        return self._clock() >= self._when

    def check(self, step: str | None = None) -> float:
        """Return the seconds left, or raise :class:`DeadlineExceeded` once expired.

        ``step`` names the work about to start; it is kept only in the
        error's ``step`` attribute. The error's ``overrun`` holds how late it is.

        >>> from deadliner import Deadline
        >>> Deadline(3, clock=lambda: 0.0).check()
        3.0
        """
        left = self._when - self._clock()
        if left > 0.0:
            return left
        raise exceeded(step, max(0.0, -left))

    def raise_if_expired(self, exc: type[BaseException] | BaseException = DeadlineExpired) -> None:
        """Raise ``exc`` (a type or an instance) if the deadline has passed.

        >>> from deadliner import Deadline
        >>> Deadline.never().raise_if_expired()
        """
        if self.expired:
            raise exc

    @overload
    def timeout(self, cap: float | None = None) -> float | None: ...
    @overload
    def timeout(self, cap: float | None = None, *, unbounded: _T) -> float | _T: ...
    def timeout(self, cap: float | None = None, *, unbounded: object = None) -> object:
        """The ``timeout=`` value to hand a blocking stdlib call. Never negative.

        Returns the seconds left, at most ``cap`` when given, and ``0.0`` once
        expired. An infinite deadline with no cap returns ``unbounded``: the default
        ``None`` suits ``queue.Queue.get``, ``subprocess.run`` and
        ``socket.settimeout``; pass ``unbounded=-1`` for ``threading.Lock.acquire``.
        Note that ``socket.settimeout(0.0)`` switches to non-blocking mode, so call
        :meth:`check` first when a zero would change the meaning of the call.

        >>> from deadliner import Deadline
        >>> Deadline(3, clock=lambda: 0.0).timeout(cap=1)
        1
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
