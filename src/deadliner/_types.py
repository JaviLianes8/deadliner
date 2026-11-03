"""Callable contracts for injected clocks and sleeps."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Protocol


class Clock(Protocol):
    """A callable returning finite, nondecreasing seconds.

    >>> clock: Clock = lambda: 2.0
    >>> clock()
    2.0
    """

    def __call__(self) -> float:
        """Read the clock.

        >>> clock: Clock = lambda: 0.0
        >>> clock()
        0.0
        """
        ...


class Sleep(Protocol):
    """A callable blocking for a number of seconds.

    >>> slept: list[float] = []
    >>> sleep: Sleep = slept.append
    >>> sleep(0.5)
    >>> slept
    [0.5]
    """

    def __call__(self, seconds: float, /) -> None:
        """Block for seconds.

        >>> sleep: Sleep = lambda seconds: None
        >>> sleep(0.0)
        """
        ...


class AsyncSleep(Protocol):
    """A callable returning an awaitable that sleeps for seconds.

    >>> import asyncio
    >>> sleep: AsyncSleep = asyncio.sleep
    >>> asyncio.run(sleep(0.0))
    """

    def __call__(self, seconds: float, /) -> Awaitable[None]:
        """Return a wait for seconds.

        >>> import asyncio
        >>> sleep: AsyncSleep = asyncio.sleep
        >>> asyncio.run(sleep(0.0))
        """
        ...
