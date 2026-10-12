from __future__ import annotations

from collections.abc import Callable

import pytest

from deadliner import Deadline


class FakeClock:
    """A clock the test drives by hand, plus sync and async sleeps that advance it."""

    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds

    async def async_sleep(self, seconds: float) -> None:
        self.sleep(seconds)

    def deadline(self, seconds: float) -> Deadline:
        return Deadline(seconds, clock=self.time, sleep=self.sleep, async_sleep=self.async_sleep)

    def never(self) -> Deadline:
        return Deadline.never(clock=self.time, sleep=self.sleep, async_sleep=self.async_sleep)


@pytest.fixture
def fake() -> FakeClock:
    return FakeClock()


MakeDeadline = Callable[[float], Deadline]
