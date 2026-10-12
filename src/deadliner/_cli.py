"""Command line: run a command under a total time budget.

Exit statuses follow GNU ``timeout``: 124 when the command runs out of time, 125
when deadliner itself fails (for example a bad duration), 126 when the command
cannot be invoked, 127 when it cannot be found, and otherwise the command's own
status (128 plus the signal number when a signal killed it, 130 on Ctrl+C).
"""

from __future__ import annotations

import argparse
import re
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
INTERRUPTED = 130
_UNITS = {"s": 1.0, "m": 60.0, "h": 3600.0, "d": 86400.0}
_NUMBER = re.compile(r"(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][-+]?[0-9]+)?|inf(?:inity)?", re.I)


def parse_duration(text: str) -> float:
    """Parse ``2.5``, ``30s``, ``5m``, ``1h`` or ``1d`` into seconds (GNU suffixes)."""
    number, unit = (text[:-1], text[-1]) if text[-1:] in _UNITS else (text, "s")
    if not _NUMBER.fullmatch(number):
        raise ValueError(f"invalid duration: {text!r}")
    return float(number) * _UNITS[unit]


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
        usage="%(prog)s [-h] [--version] DURATION [--] COMMAND [ARG ...]",
        description="Run COMMAND and stop it once DURATION has passed. "
        "A duration of 0 disables the limit.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "duration", metavar="DURATION", type=_duration, help="seconds, or a number with s/m/h/d"
    )
    return parser


def _split_argv(argv: list[str]) -> tuple[list[str], list[str]]:
    """Split into deadliner's own arguments (options, then DURATION) and the command."""
    for index, token in enumerate(argv):
        if not token.startswith("-") or token == "-":
            command = argv[index + 1 :]
            return argv[: index + 1], command[1:] if command[:1] == ["--"] else command
    return argv, []


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI with ``argv`` (default: ``sys.argv[1:]``) and return the exit status."""
    parser = _parser()
    own, command = _split_argv(list(sys.argv[1:] if argv is None else argv))
    args = parser.parse_args(own)
    if not command:
        parser.error("missing COMMAND")
    deadline = Deadline.never() if args.duration == 0.0 else Deadline(args.duration)
    try:
        status = subprocess.run(command, timeout=deadline.timeout(), check=False).returncode
    except KeyboardInterrupt:
        return INTERRUPTED  # subprocess.run has already killed the child
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
