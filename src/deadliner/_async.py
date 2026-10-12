"""Async helpers behind :meth:`Deadline.sleep_async` and :meth:`Deadline.wait_for`."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from ._core import _Core as Deadline

__all__ = ["sleep_async", "wait_for"]

_T = TypeVar("_T")


async def sleep_async(deadline: Deadline, step: float) -> float:
    """Await up to ``step`` seconds, never past ``deadline``; return the span slept."""
    nap = deadline._async_sleep or asyncio.sleep
    span = deadline._span(step)
    if span > 0.0:
        await nap(span)
        while span < step and not deadline.expired:
            extra = deadline._settle()
            await nap(extra)
            span += extra
    return span


async def wait_for(deadline: Deadline, awaitable: Awaitable[_T], step: str | None) -> _T:
    """Await ``awaitable`` until the deadline; cancel it and raise once it passes.

    Errors raised by the awaitable itself, including its own ``TimeoutError``,
    propagate unchanged: only the deadline running out becomes
    :class:`DeadlineExceeded`, chained to any error the awaitable raised while it
    was being cancelled. Cancelling the caller cancels the awaitable too. As with
    :func:`asyncio.wait_for`, work that ignores cancellation delays the error.
    """
    if deadline.expired:
        _discard(awaitable)
        raise deadline._exceeded(step)
    task = asyncio.ensure_future(awaitable)
    try:
        done, _ = await asyncio.wait({task}, timeout=deadline.timeout())
    except BaseException:
        task.cancel()
        task.add_done_callback(_retrieve)
        raise
    if done:
        return task.result()
    task.cancel()
    await asyncio.wait({task})
    cause = None if task.cancelled() else task.exception()
    raise deadline._exceeded(step) from cause


def _retrieve(task: asyncio.Future[Any]) -> None:
    """Read a finished task's outcome so the loop never logs it as unretrieved."""
    if not task.cancelled():
        task.exception()


def _discard(awaitable: Awaitable[object]) -> None:
    """Drop work that will never start, without a "never awaited" warning."""
    if inspect.iscoroutine(awaitable):
        awaitable.close()
    elif isinstance(awaitable, asyncio.Future):
        awaitable.cancel()
