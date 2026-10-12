from __future__ import annotations

import copy
import math
import pickle
import time
import weakref

import pytest

from deadliner import Deadline

from conftest import FakeClock


def test_repr_shows_the_time_left(fake: FakeClock) -> None:
    assert repr(fake.deadline(2.5)) == "Deadline(remaining=2.500s)"


def test_repr_shows_the_overrun_once_expired(fake: FakeClock) -> None:
    deadline = fake.deadline(1.0)
    fake.now = 1.5
    assert repr(deadline) == "Deadline(expired, overrun=0.500s)"


def test_repr_of_never(fake: FakeClock) -> None:
    assert repr(fake.never()) == "Deadline(never)"


def test_copy_is_an_exact_clone_sharing_the_clock(fake: FakeClock) -> None:
    deadline = fake.deadline(1.0)
    fake.now = 0.25
    for clone in (copy.copy(deadline), copy.deepcopy(deadline), copy.deepcopy([deadline])[0]):
        assert clone is not deadline
        assert clone.when == deadline.when
        assert clone.elapsed == deadline.elapsed
        assert clone._clock == deadline._clock


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


def test_deadlines_keep_the_0_1_0_object_model(fake: FakeClock) -> None:
    deadline = fake.deadline(1.0)
    assert weakref.ref(deadline)() is deadline
    deadline.tag = "request-42"  # type: ignore[attr-defined]


class Budget(Deadline):
    pass


def test_subclasses_survive_every_derivation(fake: FakeClock) -> None:
    root = Budget.at(5.0, clock=fake.time)
    assert type(root) is Budget
    assert type(Budget.after(1.0)) is Budget
    assert type(Budget.never()) is Budget
    assert type(root.child(1.0)) is Budget
    assert all(type(step) is Budget for step in root.split(2))
    assert type(copy.copy(root)) is Budget
    assert type(pickle.loads(pickle.dumps(Budget(1.0)))) is Budget
