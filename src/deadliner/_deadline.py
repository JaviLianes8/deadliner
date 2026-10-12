"""The monotonic deadline primitive."""

from __future__ import annotations

import math
import time
from collections.abc import Awaitable, Callable, Iterator, Sequence
from typing import Any, TypeVar

from . import _async, _split
from ._core import AsyncSleep, Clock, Sleep, _Core

__all__ = ["Deadline"]

_T = TypeVar("_T")


class Deadline(_Core):
    """A monotonic time budget you create once and pass down a call stack.

    ``Deadline(5.0)`` (or ``Deadline.after(5.0)``) expires five seconds from now on
    :func:`time.monotonic`, a clock that never goes backwards and ignores wall-clock
    changes. Each step reads :attr:`remaining`, calls :meth:`check` to stop once the
    budget is spent, hands stdlib calls :meth:`timeout`, and derives tighter budgets
    with :meth:`child` and :meth:`split`. Instances are immutable.

    ``clock``, ``sleep`` and ``async_sleep`` are injectable so tests run without real
    waiting; every derived deadline shares them. ``async_sleep`` defaults to
    :func:`asyncio.sleep`.
    """

    __slots__ = ()

    @classmethod
    def after(
        cls,
        seconds: float,
        *,
        clock: Clock = time.monotonic,
        sleep: Sleep = time.sleep,
        async_sleep: AsyncSleep | None = None,
    ) -> Deadline:
        """A deadline ``seconds`` from now (Go's ``WithTimeout``). Same as the constructor."""
        return cls(seconds, clock=clock, sleep=sleep, async_sleep=async_sleep)

    @classmethod
    def at(
        cls,
        when: float,
        *,
        clock: Clock = time.monotonic,
        sleep: Sleep = time.sleep,
        async_sleep: AsyncSleep | None = None,
    ) -> Deadline:
        """A deadline at absolute time ``when`` on ``clock`` (Go's ``WithDeadline``).

        ``when`` must come from the same clock, for example ``time.monotonic() + 3``.
        """
        return cls(0.0, clock=clock, sleep=sleep, async_sleep=async_sleep)._spawn(when)

    @classmethod
    def never(
        cls,
        *,
        clock: Clock = time.monotonic,
        sleep: Sleep = time.sleep,
        async_sleep: AsyncSleep | None = None,
    ) -> Deadline:
        """A deadline that never expires, for callers that set no limit."""
        return cls(math.inf, clock=clock, sleep=sleep, async_sleep=async_sleep)

    def child(self, seconds: float) -> Deadline:
        """A deadline ``seconds`` from now, but never later than this one.

        Follows Go's ``WithDeadline``: if the parent expires first, the child is
        equivalent to the parent.
        """
        if math.isnan(seconds):
            raise ValueError("seconds must not be NaN")
        return self._spawn(min(self._when, self._clock() + seconds))

    def split(self, parts: int | Sequence[float]) -> Iterator[Deadline]:
        """Iterate over per-step deadlines that share this budget.

        ``parts`` is a step count (equal shares) or a sequence of positive weights.
        Each step's deadline is computed when the iterator reaches it, from the time
        then left, so time an early step does not use rolls over to the later ones.
        The last step always ends exactly at this deadline.
        """
        return _split.split(self, parts)

    def sleep(self, step: float) -> float:
        """Sleep up to ``step`` seconds, never past the deadline.

        Returns the seconds actually slept, which is zero once expired.
        """
        span = min(max(0.0, step), self.remaining)
        if span > 0.0:
            self._sleep(span)
        return span

    def sleep_until(self, when: float) -> float:
        """Sleep until absolute time ``when`` on the deadline's clock or the deadline,
        whichever comes first. Returns the seconds slept."""
        return self.sleep(min(when, self._when) - self._clock())

    def wait_until(self, predicate: Callable[[], object], interval: float = 0.05) -> bool:
        """Poll ``predicate`` every ``interval`` seconds until it is truthy or time runs out.

        Returns True as soon as the predicate holds, and False once the deadline has
        passed. The predicate gets one last call at the deadline itself.
        """
        if not interval > 0.0:
            raise ValueError("interval must be above zero")
        while not predicate():
            if self.expired:
                return False
            self.sleep(interval)
        return True

    async def sleep_async(self, step: float) -> float:
        """Async :meth:`sleep`: await up to ``step`` seconds, never past the deadline."""
        return await _async.sleep_async(self, step)

    async def wait_for(self, awaitable: Awaitable[_T], step: str | None = None) -> _T:
        """Await ``awaitable``; cancel it and raise :class:`DeadlineExceeded` on expiry.

        Errors raised by the awaitable itself propagate unchanged. For a block of
        async code use ``async with asyncio.timeout(deadline.timeout()):`` instead.
        """
        return await _async.wait_for(self, awaitable, step)

    def __repr__(self) -> str:
        if self.infinite:
            return "Deadline(never)"
        left = self._when - self._clock()
        if left > 0.0:
            return f"Deadline(remaining={left:.3f}s)"
        return f"Deadline(expired, overrun={-left:.3f}s)"

    def __reduce__(self) -> tuple[Any, ...]:
        # A monotonic reading means nothing in another process, so store the time
        # left and rebase it on load, as gRPC does when it propagates a deadline.
        args = (self._when - self._clock(), self._clock, self._sleep, self._async_sleep)
        return (_restore, args)

    def __copy__(self) -> Deadline:
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> Deadline:
        return self

    def _spawn(self, when: float) -> Deadline:
        if math.isnan(when):
            raise ValueError("when must not be NaN")
        new = Deadline(0.0, clock=self._clock, sleep=self._sleep, async_sleep=self._async_sleep)
        new._when = when
        return new


def _restore(left: float, clock: Clock, sleep: Sleep, async_sleep: AsyncSleep | None) -> Deadline:
    return Deadline(left, clock=clock, sleep=sleep, async_sleep=async_sleep)
