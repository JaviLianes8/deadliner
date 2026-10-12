"""Budget splitting behind :meth:`Deadline.split`."""

from __future__ import annotations

import math
from collections.abc import Iterator, Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._deadline import Deadline

__all__ = ["split"]


def _weights(parts: int | Sequence[float]) -> list[float]:
    if isinstance(parts, bool):
        raise TypeError("parts must be an int or a sequence of weights, not bool")
    if isinstance(parts, int):
        if parts < 1:
            raise ValueError("parts must be at least 1")
        return [1.0] * parts
    weights = [float(w) for w in parts]
    if not weights:
        raise ValueError("weights must not be empty")
    if any(not math.isfinite(w) or w <= 0.0 for w in weights):
        raise ValueError("every weight must be a finite number above zero")
    return weights


def split(parent: Deadline, parts: int | Sequence[float]) -> Iterator[Deadline]:
    """Validate ``parts`` now and return the lazy iterator of step deadlines."""
    return _steps(parent, _weights(parts))


def _steps(parent: Deadline, weights: list[float]) -> Iterator[Deadline]:
    for index, weight in enumerate(weights):
        share = weight / math.fsum(weights[index:])
        now = parent._clock()
        left = max(0.0, parent.when - now)
        yield parent._spawn(min(parent.when, now + left * share))
