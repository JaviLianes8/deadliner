"""Contract over the complete promise of Deadline, swept over a grid with an injected clock."""

from __future__ import annotations

import itertools
import math
import pickle

import pytest

from deadliner import Deadline, DeadlineExceeded

BUDGETS = [-2.0, 0.0, 0.001, 0.5, 1.0, 7.25, 1e6, math.inf]
OFFSETS = [0.0, 0.0005, 0.25, 0.5, 1.0, 3.0, 8.0, 2e6]
CAPS = [None, -1.0, 0.0, 0.1, 2.0, math.inf]


class PicklableClock:
    """A hand-driven clock that survives pickling, so the rebase rule can be checked."""

    def __init__(self, now: float = 0.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def build(budget: float, start: float = 100.0) -> tuple[Deadline, PicklableClock]:
    clock = PicklableClock(start)
    return Deadline(budget, clock=clock, sleep=clock.sleep), clock


@pytest.mark.parametrize(("budget", "offset"), itertools.product(BUDGETS, OFFSETS))
def test_queries_agree_with_each_other(budget: float, offset: float) -> None:
    deadline, clock = build(budget)
    clock.now += offset
    left = deadline.when - clock.now
    assert deadline.remaining == max(0.0, left)
    assert deadline.expired is (left <= 0.0)
    assert deadline.infinite is (budget == math.inf)
    assert deadline.elapsed == offset or math.isclose(deadline.elapsed, offset)
    if deadline.expired:
        with pytest.raises(DeadlineExceeded) as info:
            deadline.check("step")
        assert info.value.overrun is not None
        assert info.value.overrun >= 0.0
    else:
        assert deadline.check() == deadline.remaining > 0.0


@pytest.mark.parametrize(("budget", "offset", "cap"), itertools.product(BUDGETS, OFFSETS, CAPS))
def test_timeout_is_never_negative_and_never_above_remaining_or_cap(
    budget: float, offset: float, cap: float | None
) -> None:
    deadline, clock = build(budget)
    clock.now += offset
    value = deadline.timeout(cap, unbounded="unbounded")
    if deadline.infinite and (cap is None or cap == math.inf):
        assert value == "unbounded"
        return
    assert isinstance(value, float)
    assert 0.0 <= value <= deadline.remaining
    if cap is not None:
        assert value <= max(0.0, cap)


@pytest.mark.parametrize(("budget", "offset"), itertools.product(BUDGETS, OFFSETS))
def test_remaining_never_increases_as_time_passes(budget: float, offset: float) -> None:
    deadline, clock = build(budget)
    before = deadline.remaining
    clock.now += offset
    assert deadline.remaining <= before


@pytest.mark.parametrize(
    ("budget", "offset", "child"), itertools.product(BUDGETS, OFFSETS, BUDGETS)
)
def test_a_child_ends_at_the_earlier_of_its_parent_and_its_own_budget(
    budget: float, offset: float, child: float
) -> None:
    parent, clock = build(budget)
    clock.now += offset
    derived = parent.child(child)
    assert derived.when == min(parent.when, clock.now + child)
    assert derived.when <= parent.when


@pytest.mark.parametrize(
    ("budget", "parts"),
    itertools.product(BUDGETS, [1, 2, 3, 10, [1.0], [3.0, 1.0], [1.0, 2.0, 1.0, 0.5]]),
)
def test_split_steps_stay_inside_the_parent_and_the_last_ends_with_it(
    budget: float, parts: int | list[float]
) -> None:
    parent, clock = build(budget)
    whens = []
    for step in parent.split(parts):
        assert step.when <= parent.when
        whens.append(step.when)
        clock.now = min(step.when, clock.now + 1e7)  # each step uses its whole share
    assert whens == sorted(whens)
    assert whens[-1] == parent.when


@pytest.mark.parametrize(("budget", "step"), itertools.product(BUDGETS, [0.0, 0.3, 5.0, 1e9]))
def test_sleeping_never_passes_the_deadline(budget: float, step: float) -> None:
    deadline, clock = build(budget)
    slept = deadline.sleep(step)
    assert 0.0 <= slept <= step
    assert deadline.infinite or clock.now <= max(deadline.when, 100.0)
    assert deadline.sleep_until(clock.now + step) <= step


@pytest.mark.parametrize(("budget", "offset"), itertools.product(BUDGETS, OFFSETS))
def test_pickling_preserves_the_time_left_on_a_rebased_clock(budget: float, offset: float) -> None:
    deadline, clock = build(budget)
    clock.now += offset
    restored = pickle.loads(pickle.dumps(deadline))
    assert restored.remaining == deadline.remaining
    assert restored.expired is deadline.expired
    assert restored.infinite is deadline.infinite
