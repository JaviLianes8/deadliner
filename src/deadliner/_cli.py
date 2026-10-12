"""Command line: run a command under a total time budget.

Exit statuses follow GNU ``timeout``: 124 when the command runs out of time, 125
when deadliner itself fails (for example a bad duration), 126 when the command
cannot be invoked, 127 when it cannot be found, and otherwise the command's own
status (128 plus the signal number when a signal killed it).
"""

from __future__ import annotations

import argparse
import math
import subprocess
import sys
from collections.abc import Sequence
from typing import NoReturn

from ._deadline import Deadline

__all__ = ["main", "parse_duration"]

TIMED_OUT = 124
FAILED = 125
CANNOT_INVOKE = 126
NOT_FOUND = 127
_UNITS = {"s": 1.0, "m": 60.0, "h": 3600.0, "d": 86400.0}


def parse_duration(text: str) -> float:
    """Parse ``2.5``, ``30s``, ``5m``, ``1h`` or ``1d`` into seconds (GNU suffixes)."""
    number, unit = (text[:-1], text[-1]) if text[-1:] in _UNITS else (text, "s")
    try:
        value = float(number)
    except ValueError:
        raise ValueError(f"invalid duration: {text!r}") from None
    if math.isnan(value) or value < 0.0:
        raise ValueError(f"invalid duration: {text!r}")
    return value * _UNITS[unit]


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(FAILED, f"{self.prog}: error: {message}\n")


def _duration(text: str) -> float:
    try:
        return parse_duration(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def _parser() -> _Parser:
    from . import __version__

    parser = _Parser(
        prog="deadliner",
        description="Run COMMAND and stop it once DURATION has passed. "
        "A duration of 0 disables the limit.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("duration", type=_duration, help="seconds, or a number with s/m/h/d")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="the command and its arguments")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI with ``argv`` (default: ``sys.argv[1:]``) and return the exit status."""
    parser = _parser()
    args = parser.parse_args(argv)
    command: list[str] = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("missing COMMAND")
    deadline = Deadline.never() if args.duration == 0.0 else Deadline(args.duration)
    try:
        status = subprocess.run(command, timeout=deadline.timeout(), check=False).returncode
    except subprocess.TimeoutExpired:
        print(f"deadliner: {command[0]} timed out after {args.duration:g}s", file=sys.stderr)
        return TIMED_OUT
    except FileNotFoundError:
        print(f"deadliner: {command[0]}: command not found", file=sys.stderr)
        return NOT_FOUND
    except OSError as exc:
        print(f"deadliner: {command[0]}: {exc.strerror or exc}", file=sys.stderr)
        return CANNOT_INVOKE
    return 128 - status if status < 0 else status
