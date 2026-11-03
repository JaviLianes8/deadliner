"""Monotonic deadline and time-budget primitive for bounding multi-step operations."""

from __future__ import annotations

from ._deadline import Deadline
from ._errors import DeadlineExceeded, DeadlineExpired
from ._types import AsyncSleep, Clock, Sleep

__version__ = "1.0.0"

__all__ = ["AsyncSleep", "Clock", "Deadline", "DeadlineExceeded", "DeadlineExpired", "Sleep"]
