"""Monotonic deadline and time-budget primitive for bounding multi-step operations."""

from __future__ import annotations

from ._deadline import Deadline, DeadlineExpired

__version__ = "0.1.0"

__all__ = ["Deadline", "DeadlineExpired"]
