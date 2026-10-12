from __future__ import annotations

import math

import pytest

from deadliner import DeadlineExceeded, DeadlineExpired

from conftest import FakeClock


def test_deadline_exceeded_is_the_same_class_as_deadline_expired() -> None:
    assert DeadlineExceeded is DeadlineExpired
    assert issubclass(DeadlineExceeded, TimeoutError)


def test_check_returns_the_seconds_left(fake: FakeClock) -> None:
    deadline = fake.deadline(10.0)
    fake.now = 3.0
    assert deadline.check() == 7.0


def test_check_raises_at_the_exact_deadline(fake: FakeClock) -> None:
    deadline = fake.deadline(2.0)
    fake.now = 2.0
    with pytest.raises(DeadlineExceeded) as info:
        deadline.check()
    assert info.value.overrun == 0.0
    assert info.value.step is None
    assert str(info.value) == "deadline exceeded (overrun 0.000s)"


def test_check_names_the_step_and_the_overrun(fake: FakeClock) -> None:
    deadline = fake.deadline(1.0)
    fake.now = 1.25
    with pytest.raises(DeadlineExpired, match=r"during fetch \(overrun 0\.250s\)") as info:
        deadline.check("fetch")
    assert info.value.step == "fetch"
    assert info.value.overrun == 0.25


def test_errors_raised_elsewhere_carry_no_step_or_overrun() -> None:
    error = DeadlineExpired()
    assert error.step is None
    assert error.overrun is None


def test_timeout_is_the_time_left(fake: FakeClock) -> None:
    deadline = fake.deadline(5.0)
    fake.now = 1.5
    assert deadline.timeout() == 3.5


def test_timeout_is_zero_never_negative_once_expired(fake: FakeClock) -> None:
    deadline = fake.deadline(1.0)
    fake.now = 30.0
    assert deadline.timeout() == 0.0
    assert deadline.timeout(unbounded=-1) == 0.0


def test_timeout_respects_a_cap(fake: FakeClock) -> None:
    deadline = fake.deadline(5.0)
    assert deadline.timeout(2.0) == 2.0
    assert deadline.timeout(9.0) == 5.0


def test_a_negative_cap_becomes_zero(fake: FakeClock) -> None:
    assert fake.deadline(5.0).timeout(-3.0) == 0.0


def test_an_infinite_deadline_returns_the_unbounded_sentinel(fake: FakeClock) -> None:
    deadline = fake.never()
    assert deadline.timeout() is None
    assert deadline.timeout(unbounded=-1) == -1


def test_an_infinite_deadline_with_a_cap_returns_the_cap(fake: FakeClock) -> None:
    assert fake.never().timeout(4.0) == 4.0


def test_an_infinite_deadline_never_expires(fake: FakeClock) -> None:
    deadline = fake.never()
    fake.now = 1e300
    assert deadline.infinite is True
    assert deadline.expired is False
    assert deadline.remaining == math.inf
    assert deadline.check() == math.inf


def test_nan_budgets_are_rejected(fake: FakeClock) -> None:
    with pytest.raises(ValueError, match="NaN"):
        fake.deadline(math.nan)
