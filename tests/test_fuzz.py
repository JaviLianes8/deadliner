"""Seeded generated inputs, distinct from external source examples."""

from __future__ import annotations

import math
import random
from fractions import Fraction

import pytest

from deadliner import Deadline
from deadliner._cli import parse_duration

from conftest import FakeClock


@pytest.mark.parametrize("seed", [712, 4019, 90210])
def test_weighted_splits_against_exact_rational_arithmetic(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(1000):
        weights = [rng.randint(1, 10000) for _ in range(rng.randint(1, 30))]
        clock = FakeClock()
        budget = float(rng.randint(1, 10000))
        root = Deadline(budget, clock=clock.time)
        for index, step in enumerate(root.split(weights)):
            ratio = Fraction(weights[index], sum(weights[index:]))
            expected = clock.now + float(Fraction(budget - clock.now) * ratio)
            assert step.when == pytest.approx(expected)
            assert clock.now <= step.when <= root.when
            clock.now += (step.when - clock.now) * rng.random()
        assert step.when == root.when


@pytest.mark.parametrize("seed", [17, 43, 109])
def test_generated_duration_strings_never_crash_or_echo_input(seed: int) -> None:
    rng = random.Random(seed)
    alphabet = "0123456789eE.+-infINFsmdh _\n\x00\ud800"
    for _ in range(10000):
        text = "".join(rng.choices(alphabet, k=rng.randrange(80)))
        try:
            result = parse_duration(text)
        except ValueError as error:
            assert str(error) == "invalid duration"
        else:
            assert not math.isnan(result) and result >= 0


@pytest.mark.parametrize("seed", [123, 456])
def test_queries_children_and_timeouts_over_seeded_clocks(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(10000):
        start, budget, delta, cap = (rng.uniform(-1e6, 1e6) for _ in range(4))
        clock = FakeClock()
        clock.now = start
        root = Deadline(budget, clock=clock.time)
        clock.now += abs(delta)
        expected = max(0, start + budget - clock.now)
        assert root.remaining == expected
        assert root.timeout(cap) == min(expected, max(0, cap))
        assert root.child(delta).when == min(root.when, clock.now + delta)
        assert root.expired == (clock.now >= start + budget)
