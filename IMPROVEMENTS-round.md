# Improvement round: deadliner 0.2.0

Progress:
- [x] Repo read, main has the real 0.1.0 implementation
- [x] Ground truth fetched and cited (see Sources)
- [x] Brainstorm ranked (this file)
- [x] Core API: DeadlineExceeded alias, at/after/never constructors, when/elapsed, check()
- [x] Child deadlines and budget splitting
- [x] Stdlib timeout helper (never negative, unbounded sentinel)
- [x] sleep_until, wait_until polling
- [x] Async helpers (sleep_async, wait_for)
- [x] repr, pickling (rebased on load), copy
- [x] CLI: run a command under a total budget
- [x] Docs: docstrings, README, GUIDE, CHANGELOG, version 0.2.0
- [x] Contract test with injected clock
- [x] Real stdlib integration tests (queue, Lock, subprocess, socket accept)
- [x] Real e2e: wheel, throwaway venv, external consumer, CLI
- [x] Gates green (ruff format, ruff check, mypy --strict src, pytest)
- [x] PR opened (#2)
- [x] Independent review and fixes
- [ ] Guard CLEAN after fixes

## Sources (fetched 2026-10-12)

- Go `context`: https://pkg.go.dev/context. `WithDeadline` returns a derived context
  whose deadline is "no later than d. If the parent's deadline is already earlier than
  d, WithDeadline(parent, d) is semantically equivalent to parent." `WithTimeout`
  is `WithDeadline(parent, time.Now().Add(timeout))`. `DeadlineExceeded` is the error
  returned when the deadline passes. `Deadline()` returns `ok==false` when no
  deadline is set.
- gRPC deadlines guide: https://grpc.io/docs/guides/deadlines/. A call past its
  deadline fails with `DEADLINE_EXCEEDED`; servers should propagate the incoming
  deadline to outgoing calls; "Since a deadline is set point in time, propagating it
  as-is to a server can be problematic as the clocks on the two servers might not be
  synchronized. To address this gRPC converts the deadline to a timeout from which the
  already elapsed time is already deducted."
- `asyncio.timeout` / `asyncio.Timeout` (3.11+):
  https://docs.python.org/3/library/asyncio-task.html. An async context manager that
  cancels the current task and raises `TimeoutError`; `delay=None` means no limit;
  `when()`, `reschedule()`, `expired()`.
- `time.monotonic`: https://docs.python.org/3/library/time.html and PEP 418
  https://peps.python.org/pep-0418/. "a clock that cannot go backwards. The clock is
  not affected by system clock updates. The reference point of the returned value is
  undefined, so that only the difference between the results of two calls is valid."
- `threading.Lock.acquire`: https://docs.python.org/3/library/threading.html.
  "A timeout argument of -1 specifies an unbounded wait." Other negative values raise
  `ValueError` (observed on 3.11 and 3.13), so a raw negative remainder is never a
  short wait.
- `queue.Queue.get`: https://docs.python.org/3/library/queue.html. A negative timeout
  raises `ValueError: 'timeout' must be a non-negative number` (observed on 3.13).
- `socket.settimeout`: https://docs.python.org/3/library/socket.html. "If zero is
  given, the socket is put in non-blocking mode."
- GNU `timeout`: https://www.gnu.org/software/coreutils/manual/html_node/timeout-invocation.html.
  Exit status 124 if the command times out, 125 if timeout itself fails, 126 if the
  command cannot be invoked, 127 if it cannot be found.

## Positioning

`asyncio.timeout` already cancels a block of async code; deadliner does not duplicate
it. The value is a plain object you create once and pass down a call stack, sync or
async, that answers how much is left, raises a typed error, derives child deadlines,
splits itself across steps, and hands stdlib calls a timeout that is never negative.

## Ranked improvements

1. `check()` raising `DeadlineExceeded` (the Go and gRPC name) with a message naming
   the step and the overrun; returns the seconds left so it composes. `DeadlineExceeded`
   is the same class as `DeadlineExpired`, so existing `except` clauses keep working.
2. `timeout(cap=None, *, unbounded=None)`: the value to hand a stdlib call. Clamped
   at zero (a negative `Lock.acquire` timeout means wait forever, a negative queue
   timeout raises). An infinite deadline returns the caller's `unbounded` sentinel
   (`None` for queue/subprocess/socket, `-1` for `Lock.acquire`).
3. `child(seconds)`: a deadline no later than the parent (Go `WithDeadline` rule).
4. `split(n)` / `split(weights)`: per-step child deadlines computed lazily when each
   step starts, so time an early step leaves unused rolls over to the rest.
5. `Deadline.after`, `Deadline.at` (absolute monotonic time), `Deadline.never()`;
   `when`, `elapsed`, `infinite` properties.
6. `sleep_until(when)` and `wait_until(predicate, interval)`: bounded polling.
7. Async: `sleep_async`, `wait_for(awaitable)` raising `DeadlineExceeded`; the GUIDE
   shows `asyncio.timeout(deadline.timeout())` instead of wrapping it.
8. `repr`, pickling that stores the remaining time and rebases on load (the gRPC
   deadline-to-timeout rule, since the monotonic reference point is per process),
   `copy` returning the same immutable object.
9. Docs: docstrings on every public name, README refresh, GUIDE.md.
10. CLI `deadliner SECONDS -- CMD...`: runs a command under a total budget with GNU
    `timeout` exit codes. Justified because Windows has no equivalent (its
    `timeout.exe` only sleeps), and the local CI scripts of this project run there.

Kept as is: `remaining` and `expired` stay properties (changing them to methods would
break 0.1.0 callers; the round is additive only).
