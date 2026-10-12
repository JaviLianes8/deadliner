from __future__ import annotations

import copy
import math
import pickle
import time

import pytest

from conftest import FakeClock
from deadliner import Deadline


def test_repr_shows_the_time_left(fake: FakeClock) -> None:
    assert repr(fake.deadline(2.5)) == "Deadline(remaining=2.500s)"


def test_repr_shows_the_overrun_once_expired(fake: FakeClock) -> None:
    deadline = fake.deadline(1.0)
    fake.now = 1.5
    assert repr(deadline) == "Deadline(expired, overrun=0.500s)"


def test_repr_of_never(fake: FakeClock) -> None:
    assert repr(fake.never()) == "Deadline(never)"


def test_copy_returns_the_same_immutable_object(fake: FakeClock) -> None:
    deadline = fake.deadline(1.0)
    assert copy.copy(deadline) is deadline
    assert copy.deepcopy(deadline) is deadline
    assert copy.deepcopy([deadline])[0] is deadline


def test_pickle_stores_the_time_left_and_rebases_it() -> None:
    deadline = Deadline(60.0)
    before = deadline.remaining
    restored = pickle.loads(pickle.dumps(deadline))
    assert isinstance(restored, Deadline)
    assert 0.0 < restored.remaining <= before


def test_pickle_keeps_an_infinite_deadline_infinite() -> None:
    restored = pickle.loads(pickle.dumps(Deadline.never()))
    assert restored.infinite is True
    assert restored.when == math.inf


def test_pickle_keeps_an_expired_deadline_expired() -> None:
    restored = pickle.loads(pickle.dumps(Deadline(-5.0)))
    assert restored.expired is True


def test_pickle_keeps_the_injected_clock_and_sleep() -> None:
    restored = pickle.loads(pickle.dumps(Deadline(1.0, clock=time.perf_counter)))
    assert restored._clock is time.perf_counter
    assert restored._sleep is time.sleep


def test_pickle_fails_loudly_on_an_unpicklable_clock() -> None:
    deadline = Deadline(1.0, clock=lambda: 0.0)
    with pytest.raises((pickle.PicklingError, AttributeError)):
        pickle.dumps(deadline)


def test_deadlines_are_slotted(fake: FakeClock) -> None:
    deadline = fake.deadline(1.0)
    with pytest.raises(AttributeError):
        deadline.extra = 1  # type: ignore[attr-defined]
