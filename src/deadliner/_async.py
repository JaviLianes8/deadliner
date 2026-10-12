"""Async helpers behind :meth:`Deadline.sleep_async` and :meth:`Deadline.wait_for`."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from ._core import _Core as Deadline

__all__ = ["sleep_async", "wait_for"]

_T = TypeVar("_T")


async def sleep_async(deadline: Deadline, step: float) -> float:
    """Await up to ``step`` seconds, never past ``deadline``; return the span slept."""
    span = min(max(0.0, step), deadline.remaining)
    if span > 0.0:
        await (deadline._async_sleep or asyncio.sleep)(span)
    return span


async def wait_for(deadline: Deadline, awaitable: Awaitable[_T], step: str | None) -> _T:
    """Await ``awaitable`` until the deadline; cancel it and raise once it passes.

    Errors raised by the awaitable itself, including its own ``TimeoutError``,
    propagate unchanged: only the deadline running out becomes
    :class:`DeadlineExceeded`. Cancelling the caller cancels the awaitable too.
    """
    task = asyncio.ensure_future(awaitable)
    try:
        done, _ = await asyncio.wait({task}, timeout=deadline.timeout())
    except BaseException:
        task.cancel()
        raise
    if done:
        return task.result()
    task.cancel()
    await asyncio.wait({task})
    if not task.cancelled():
        task.exception()  # mark it retrieved; the deadline error wins
    raise deadline._exceeded(step)
