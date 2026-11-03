"""Waiting operations using a shared deadline."""

from __future__ import annotations

import math
from collections.abc import Awaitable, Callable
from typing import TypeVar

from . import _async
from ._core import _Core

_T = TypeVar("_T")


class _Waits(_Core):
    """Waiting methods inherited by Deadline."""

    def sleep(self, step: float) -> float:
        """Sleep up to ``step`` seconds, never past the deadline.

        Returns the seconds asked of the sleep function, zero once expired. When the
        deadline cuts the sleep short, it returns only once :attr:`expired` is true,
        even on a clock coarser than the sleep (Windows before Python 3.13).

        >>> from deadliner import Deadline
        >>> Deadline(0, clock=lambda: 0.0).sleep(5)
        0.0
        """
        span = self._span(step)
        if span > 0.0:
            self._sleep(span)
            while span < step and not self.expired:
                extra = self._settle()
                self._sleep(extra)
                span += extra
        return span

    def sleep_until(self, when: float) -> float:
        """Sleep until absolute time ``when`` on the deadline's clock or the deadline,
        whichever comes first. Returns the seconds slept.

        >>> from deadliner import Deadline
        >>> Deadline(0, clock=lambda: 0.0).sleep_until(5)
        0.0
        """
        if math.isnan(when):
            raise ValueError("when must not be NaN")
        return self.sleep(math.inf if when >= self._when else when - self._clock())

    def wait_until(self, predicate: Callable[[], object], interval: float = 0.05) -> bool:
        """Poll ``predicate`` every ``interval`` seconds until it is truthy or time runs out.

        Returns True as soon as the predicate holds, and False once the deadline has
        passed. The predicate gets one last call at the deadline itself.

        >>> from deadliner import Deadline
        >>> Deadline(0, clock=lambda: 0.0).wait_until(lambda: True)
        True
        """
        if not interval > 0.0:
            raise ValueError("interval must be above zero")
        while not predicate():
            if self.expired:
                return False
            self.sleep(interval)
        return True

    async def sleep_async(self, step: float) -> float:
        """Async :meth:`sleep`: await up to ``step`` seconds, never past the deadline.

        >>> import asyncio
        >>> from deadliner import Deadline
        >>> asyncio.run(Deadline(0, clock=lambda: 0.0).sleep_async(5))
        0.0
        """
        return await _async.sleep_async(self, step)

    async def wait_for(self, awaitable: Awaitable[_T], step: str | None = None) -> _T:
        """Await ``awaitable``; cancel it and raise :class:`DeadlineExceeded` on expiry.

        Errors raised by the awaitable itself propagate unchanged. For a block of
        async code use ``async with asyncio.timeout(deadline.timeout()):`` instead.

        >>> import asyncio
        >>> from deadliner import Deadline
        >>> async def work():
        ...     return 7
        >>> asyncio.run(Deadline.never().wait_for(work()))
        7
        """
        return await _async.wait_for(self, awaitable, step)
