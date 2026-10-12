from __future__ import annotations

import asyncio
import gc
import math
import time

import pytest

from deadliner import Deadline, DeadlineExceeded

from conftest import FakeClock

TICK = 0.015625  # the 15.6 ms monotonic tick of Windows before Python 3.13


class CoarseClock(FakeClock):
    """Precise sleeps read through a clock that only moves in whole ticks."""

    def time(self) -> float:
        return math.floor(self.now / TICK) * TICK


def test_a_cut_sleep_returns_only_once_a_coarse_clock_shows_expiry() -> None:
    clock = CoarseClock()
    clock.now = 0.004  # reads as 0.0
    deadline = clock.deadline(0.02)  # expires at a reading of 0.02
    deadline.sleep(10.0)
    assert deadline.expired
    assert clock.time() >= deadline.when


def test_a_cut_async_sleep_returns_only_once_a_coarse_clock_shows_expiry() -> None:
    clock = CoarseClock()
    clock.now = 0.004
    deadline = clock.deadline(0.02)
    asyncio.run(deadline.sleep_async(10.0))
    assert deadline.expired


def test_a_sleep_that_fits_never_adds_settling_time(fake: FakeClock) -> None:
    deadline = fake.deadline(10.0)
    assert deadline.sleep(1.0) == 1.0
    assert fake.slept == [1.0]


def test_sleep_until_past_the_deadline_settles_on_the_deadline() -> None:
    clock = CoarseClock()
    deadline = clock.deadline(0.02)
    deadline.sleep_until(5.0)
    assert deadline.expired


@pytest.mark.parametrize(
    "call",
    [
        lambda d: d.sleep(math.nan),
        lambda d: d.sleep_until(math.nan),
        lambda d: d.timeout(math.nan),
        lambda d: asyncio.run(d.sleep_async(math.nan)),
    ],
)
def test_nan_is_rejected_everywhere(fake: FakeClock, call: object) -> None:
    with pytest.raises(ValueError, match="NaN"):
        call(fake.deadline(1.0))  # type: ignore[operator]


def test_split_of_a_huge_count_is_lazy() -> None:
    start = time.monotonic()
    steps = Deadline(10.0).split(10**8)
    first = next(steps)
    assert time.monotonic() - start < 5.0  # no list of 10**8 items is built
    assert first.remaining <= 10.0 / 10**8 + 1e-6


def test_an_error_during_cancellation_is_chained_to_the_deadline_error() -> None:
    async def work() -> None:
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            raise ValueError("cleanup failed") from None

    with pytest.raises(DeadlineExceeded) as info:
        asyncio.run(Deadline(0.05).wait_for(work()))
    assert isinstance(info.value.__cause__, ValueError)


def test_cancelling_the_caller_leaves_no_unretrieved_error() -> None:
    reported: list[object] = []

    async def work() -> None:
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            raise ValueError("cleanup failed") from None

    async def main() -> None:
        asyncio.get_running_loop().set_exception_handler(lambda _l, ctx: reported.append(ctx))
        outer = asyncio.ensure_future(Deadline.never().wait_for(work()))
        await asyncio.sleep(0.01)
        outer.cancel()
        with pytest.raises(asyncio.CancelledError):
            await outer
        await asyncio.sleep(0.01)
        gc.collect()

    asyncio.run(main())
    assert reported == []
