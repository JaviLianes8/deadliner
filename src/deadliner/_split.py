"""Budget splitting behind :meth:`Deadline.split`."""

from __future__ import annotations

import math
from collections.abc import Iterator, Sequence
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from ._deadline import Deadline

__all__ = ["split"]

_D = TypeVar("_D", bound="Deadline")


def _shares(parts: int | Sequence[float]) -> Iterator[float]:
    """Validate ``parts`` and return each step's share of the time then left."""
    if isinstance(parts, bool):
        raise TypeError("parts must be an int or a sequence of weights, not bool")
    if isinstance(parts, int):
        if parts < 1:
            raise ValueError("parts must be at least 1")
        return (1.0 / (parts - index) for index in range(parts))
    try:
        weights = [float(w) for w in parts]
    except (ValueError, OverflowError):
        raise ValueError("every weight must be a finite number above zero") from None
    if not weights:
        raise ValueError("weights must not be empty")
    if any(not math.isfinite(w) or w <= 0.0 for w in weights):
        raise ValueError("every weight must be a finite number above zero")
    # Scale each suffix independently so neither its sum nor a tiny tail is lost.
    shares = []
    scale = total = 0.0
    for weight in reversed(weights):
        if weight > scale:
            total = total * (scale / weight) + 1.0
            scale = weight
        else:
            total += weight / scale
        shares.append((weight / scale) / total)
    return reversed(shares)


def split(parent: _D, parts: int | Sequence[float]) -> Iterator[_D]:
    """Validate ``parts`` now and return the lazy iterator of step deadlines."""
    return _steps(parent, _shares(parts))


def _steps(parent: _D, shares: Iterator[float]) -> Iterator[_D]:
    for share in shares:
        now = parent._clock()
        left = max(0.0, parent.when - now)
        when = parent.when if share == 1.0 or parent.infinite else now + left * share
        yield parent._spawn(min(parent.when, when))
