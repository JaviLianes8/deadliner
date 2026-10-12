"""Monotonic deadline and time-budget primitive for bounding multi-step operations."""

from __future__ import annotations

from ._deadline import Deadline
from ._errors import DeadlineExceeded, DeadlineExpired

__version__ = "0.2.0"

__all__ = ["Deadline", "DeadlineExceeded", "DeadlineExpired"]
