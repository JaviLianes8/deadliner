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
    """

    step: str | None = None
    overrun: float | None = None


#: The same class under the name Go's ``context`` package and gRPC use. Catching
#: either name catches errors raised under the other.
DeadlineExceeded = DeadlineExpired


def exceeded(step: str | None, overrun: float) -> DeadlineExpired:
    """Build the error :meth:`Deadline.check` raises, with a readable message."""
    where = f" during {step}" if step else ""
    error = DeadlineExceeded(f"deadline exceeded{where} (overrun {overrun:.3f}s)")
    error.step = step
    error.overrun = overrun
    return error
