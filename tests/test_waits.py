from __future__ import annotations

import asyncio

import pytest

from deadliner import Deadline, DeadlineExceeded

from conftest import FakeClock


def test_sleep_until_stops_at_the_target(fake: FakeClock) -> None:
    deadline = fake.deadline(10.0)
    assert deadline.sleep_until(4.0) == 4.0
    assert fake.now == 4.0


def test_sleep_until_stops_at_the_deadline(fake: FakeClock) -> None:
    deadline = fake.deadline(3.0)
    assert deadline.sleep_until(50.0) == 3.0
    assert deadline.expired is True


def test_sleep_until_a_past_time_does_nothing(fake: FakeClock) -> None:
    fake.now = 5.0
    deadline = fake.deadline(10.0)
    assert deadline.sleep_until(1.0) == 0.0
    assert fake.slept == []


def test_wait_until_returns_true_as_soon_as_the_predicate_holds(fake: FakeClock) -> None:
    deadline = fake.deadline(10.0)
    assert deadline.wait_until(lambda: fake.now >= 0.3, interval=0.1) is True
    assert fake.now == pytest.approx(0.3)


def test_wait_until_returns_false_once_time_runs_out(fake: FakeClock) -> None:
    deadline = fake.deadline(1.0)
    assert deadline.wait_until(lambda: False, interval=0.4) is False
    assert fake.slept == [0.4, 0.4, pytest.approx(0.2)]


def test_wait_until_gives_the_predicate_a_last_call_at_the_deadline(fake: FakeClock) -> None:
    deadline = fake.deadline(1.0)
    assert deadline.wait_until(lambda: fake.now >= 1.0, interval=5.0) is True


def test_wait_until_does_not_sleep_when_the_predicate_already_holds(fake: FakeClock) -> None:
    assert fake.deadline(1.0).wait_until(lambda: True) is True
    assert fake.slept == []


@pytest.mark.parametrize("interval", [0.0, -1.0, float("nan")])
def test_wait_until_rejects_a_non_positive_interval(fake: FakeClock, interval: float) -> None:
    with pytest.raises(ValueError, match="interval"):
        fake.never().wait_until(lambda: False, interval=interval)


def test_sleep_async_never_overshoots(fake: FakeClock) -> None:
    deadline = fake.deadline(2.0)
    assert asyncio.run(deadline.sleep_async(10.0)) == 2.0
    assert fake.slept == [2.0]
    assert asyncio.run(deadline.sleep_async(1.0)) == 0.0


def test_sleep_async_defaults_to_asyncio_sleep() -> None:
    deadline = Deadline(10.0)
    assert asyncio.run(deadline.sleep_async(0.0)) == 0.0
    assert asyncio.run(deadline.sleep_async(0.01)) == 0.01


def test_wait_for_returns_the_result_in_time() -> None:
    async def work() -> str:
        await asyncio.sleep(0)
        return "done"

    assert asyncio.run(Deadline(10.0).wait_for(work())) == "done"


def test_wait_for_lets_errors_from_the_work_through_unchanged() -> None:
    async def work() -> None:
        raise TimeoutError("inner")

    with pytest.raises(TimeoutError, match="inner") as info:
        asyncio.run(Deadline(10.0).wait_for(work()))
    assert type(info.value) is TimeoutError


def test_wait_for_cancels_the_work_and_raises_on_expiry() -> None:
    cancelled = []

    async def work() -> None:
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            cancelled.append(True)
            raise

    with pytest.raises(DeadlineExceeded, match="during slow") as info:
        asyncio.run(Deadline(0.05).wait_for(work(), "slow"))
    assert cancelled == [True]
    assert info.value.step == "slow"


def test_wait_for_on_an_expired_deadline_never_starts_the_work() -> None:
    started = []

    async def work() -> None:
        started.append(True)

    with pytest.raises(DeadlineExceeded):
        asyncio.run(Deadline(0.0).wait_for(work()))
    assert started == []


def test_cancelling_the_caller_cancels_the_work() -> None:
    cancelled = []

    async def work() -> None:
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            cancelled.append(True)
            raise

    async def main() -> None:
        outer = asyncio.ensure_future(Deadline.never().wait_for(work()))
        await asyncio.sleep(0.01)
        outer.cancel()
        with pytest.raises(asyncio.CancelledError):
            await outer

    asyncio.run(main())
    assert cancelled == [True]


def test_wait_for_on_an_expired_deadline_cancels_a_future() -> None:
    async def main() -> bool:
        future: asyncio.Future[int] = asyncio.get_running_loop().create_future()
        with pytest.raises(DeadlineExceeded):
            await Deadline(-1.0).wait_for(future)
        return future.cancelled()

    assert asyncio.run(main()) is True
