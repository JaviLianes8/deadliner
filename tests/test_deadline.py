from __future__ import annotations

import pytest

from deadliner import Deadline, DeadlineExpired


class FakeClock:
    """A clock the test drives by hand, plus a sleep that advances it."""

    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def make(seconds: float) -> tuple[Deadline, FakeClock]:
    clock = FakeClock()
    return Deadline(seconds, clock=clock.time, sleep=clock.sleep), clock


def test_remaining_decreases_as_the_clock_advances() -> None:
    deadline, clock = make(10.0)
    assert deadline.remaining == 10.0
    clock.now = 4.0
    assert deadline.remaining == 6.0


def test_remaining_never_goes_negative() -> None:
    deadline, clock = make(5.0)
    clock.now = 9.0
    assert deadline.remaining == 0.0


def test_expired_flips_once_time_runs_out() -> None:
    deadline, clock = make(3.0)
    assert deadline.expired is False
    clock.now = 3.0
    assert deadline.expired is True


def test_sleep_never_overshoots_the_deadline() -> None:
    deadline, clock = make(2.0)
    slept = deadline.sleep(10.0)
    assert slept == 2.0
    assert clock.slept == [2.0]
    assert deadline.expired is True


def test_sleep_uses_the_full_step_when_it_fits() -> None:
    deadline, _clock = make(5.0)
    assert deadline.sleep(1.0) == 1.0


def test_sleep_does_nothing_once_expired() -> None:
    deadline, clock = make(1.0)
    clock.now = 1.0
    assert deadline.sleep(5.0) == 0.0
    assert clock.slept == []


def test_raise_if_expired_stays_silent_before_expiry() -> None:
    deadline, _clock = make(1.0)
    deadline.raise_if_expired()


def test_raise_if_expired_raises_after_expiry() -> None:
    deadline, clock = make(1.0)
    clock.now = 2.0
    with pytest.raises(DeadlineExpired):
        deadline.raise_if_expired()


def test_raise_if_expired_accepts_a_custom_exception() -> None:
    deadline, clock = make(1.0)
    clock.now = 2.0
    with pytest.raises(ValueError, match="too slow"):
        deadline.raise_if_expired(ValueError("too slow"))


def test_zero_budget_is_expired_immediately() -> None:
    deadline, _clock = make(0.0)
    assert deadline.remaining == 0.0
    assert deadline.expired is True


def test_negative_budget_is_already_expired() -> None:
    deadline, _clock = make(-5.0)
    assert deadline.remaining == 0.0
    assert deadline.expired is True
    with pytest.raises(DeadlineExpired):
        deadline.raise_if_expired()


def test_deadline_expired_is_a_timeout_error() -> None:
    assert issubclass(DeadlineExpired, TimeoutError)
