from __future__ import annotations

import math

import pytest

from conftest import FakeClock
from deadliner import Deadline


def test_after_matches_the_constructor(fake: FakeClock) -> None:
    fake.now = 100.0
    deadline = Deadline.after(5.0, clock=fake.time)
    assert deadline.when == 105.0
    assert deadline.remaining == 5.0


def test_at_takes_an_absolute_time_on_the_clock(fake: FakeClock) -> None:
    fake.now = 100.0
    deadline = Deadline.at(103.0, clock=fake.time)
    assert deadline.when == 103.0
    assert deadline.remaining == 3.0


def test_at_in_the_past_is_already_expired(fake: FakeClock) -> None:
    fake.now = 100.0
    assert Deadline.at(90.0, clock=fake.time).expired is True


def test_at_rejects_nan(fake: FakeClock) -> None:
    with pytest.raises(ValueError, match="NaN"):
        Deadline.at(math.nan, clock=fake.time)


def test_never_is_infinite(fake: FakeClock) -> None:
    deadline = fake.never()
    assert deadline.when == math.inf
    assert deadline.infinite is True
    assert fake.deadline(1.0).infinite is False


def test_elapsed_counts_from_creation(fake: FakeClock) -> None:
    fake.now = 10.0
    deadline = fake.deadline(5.0)
    fake.now = 12.5
    assert deadline.elapsed == 2.5


def test_child_is_tighter_when_it_asks_for_less(fake: FakeClock) -> None:
    parent = fake.deadline(10.0)
    fake.now = 2.0
    child = parent.child(3.0)
    assert child.when == 5.0


def test_child_never_outlives_its_parent(fake: FakeClock) -> None:
    parent = fake.deadline(10.0)
    fake.now = 8.0
    assert parent.child(60.0).when == parent.when


def test_child_shares_the_clock_and_sleep(fake: FakeClock) -> None:
    child = fake.deadline(10.0).child(1.0)
    assert child.sleep(5.0) == 1.0
    assert fake.slept == [1.0]


def test_child_of_never_is_bounded_by_its_own_budget(fake: FakeClock) -> None:
    assert fake.never().child(4.0).when == 4.0
    assert fake.never().child(math.inf).infinite is True


def test_child_rejects_nan(fake: FakeClock) -> None:
    with pytest.raises(ValueError, match="NaN"):
        fake.deadline(1.0).child(math.nan)


def test_split_gives_equal_shares(fake: FakeClock) -> None:
    steps = fake.deadline(9.0).split(3)
    first = next(steps)
    assert first.when == 3.0


def test_split_rolls_unused_time_over_to_later_steps(fake: FakeClock) -> None:
    whens = []
    for step in fake.deadline(9.0).split(3):
        whens.append(step.when)
        fake.now += 1.0  # each step finishes early
    assert whens == [3.0, 5.0, 9.0]


def test_split_by_weights(fake: FakeClock) -> None:
    whens = []
    for step in fake.deadline(8.0).split([1, 2, 1]):
        whens.append(step.when)
        fake.now = step.when  # each step uses its whole share
    assert whens == [2.0, 6.0, 8.0]


def test_the_last_step_ends_exactly_at_the_parent(fake: FakeClock) -> None:
    parent = fake.deadline(1.0)
    fake.now = 0.1
    steps = list(parent.split(7))
    assert steps[-1].when == parent.when
    assert all(step.when <= parent.when for step in steps)


def test_split_of_an_expired_budget_gives_expired_steps(fake: FakeClock) -> None:
    parent = fake.deadline(1.0)
    fake.now = 5.0
    assert all(step.expired for step in parent.split(2))


def test_split_of_never_gives_infinite_steps(fake: FakeClock) -> None:
    assert all(step.infinite for step in fake.never().split(3))


@pytest.mark.parametrize("parts", [0, -2, [], [1, 0], [1, -1], [math.inf], [math.nan]])
def test_split_validates_eagerly(fake: FakeClock, parts: object) -> None:
    with pytest.raises(ValueError):
        fake.deadline(1.0).split(parts)  # type: ignore[arg-type]


def test_split_rejects_bool(fake: FakeClock) -> None:
    with pytest.raises(TypeError):
        fake.deadline(1.0).split(True)
