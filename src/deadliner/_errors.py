"""The error raised when a deadline has passed."""

from __future__ import annotations

__all__ = ["DeadlineExceeded", "DeadlineExpired"]


class DeadlineExpired(TimeoutError):
    """Raised when an operation runs past its deadline.

    A subclass of :class:`TimeoutError`, so code that already handles timeouts
    catches it too. :meth:`Deadline.check` fills in two extra attributes:

    ``step``
        The label passed to ``check`` (``None`` when no label was given).
    ``overrun``
        Seconds past the deadline at the moment of the check (``None`` when the
        error was raised some other way).

    >>> from deadliner import Deadline, DeadlineExpired
    >>> try:
    ...     Deadline(0, clock=lambda: 0.0).check("fetch")
    ... except DeadlineExpired as error:
    ...     print(error.step, error.overrun)
    fetch 0.0
    """

    step: str | None = None
    overrun: float | None = None


#: The same class under the name Go's ``context`` package and gRPC use. Catching
#: either name catches errors raised under the other.
DeadlineExceeded = DeadlineExpired


def exceeded(step: str | None, overrun: float) -> DeadlineExpired:
    """Build the error :meth:`Deadline.check` raises, with a readable message."""
    span = f"{overrun:.3f}" if overrun < 1e9 else f"{overrun:.3g}"
    error = DeadlineExceeded(f"deadline exceeded (overrun {span}s)")
    error.step = step
    error.overrun = overrun
    return error
