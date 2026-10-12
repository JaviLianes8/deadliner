# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0]

Additive API. Behaviour changes for 0.1.0 callers are listed under Changed.

### Added

- `Deadline.check(step=None)` returns the seconds left or raises `DeadlineExceeded`,
  whose `step` and `overrun` attributes say where and how late.
- `DeadlineExceeded`: the same class as `DeadlineExpired`, under the Go and gRPC name.
- `Deadline.timeout(cap=None, *, unbounded=None)`: a stdlib `timeout=` value that is
  never negative; infinite deadlines return the `unbounded` sentinel.
- `Deadline.child(seconds)`: a deadline never later than its parent.
- `Deadline.split(parts)`: lazy per-step deadlines by count or weights, with unused
  time rolling over to later steps.
- `Deadline.after`, `Deadline.at` and `Deadline.never` constructors; `when`, `elapsed`
  and `infinite` properties.
- `Deadline.sleep_until(when)` and `Deadline.wait_until(predicate, interval)`.
- Async: `Deadline.sleep_async(step)` and `Deadline.wait_for(awaitable, step=None)`.
- `repr`, pickling that rebases the time left on load, and `copy` support.
- `deadliner DURATION COMMAND...` CLI (also `python -m deadliner`) with GNU `timeout`
  exit statuses.
- `Clock`, `Sleep` and `AsyncSleep` type aliases for annotating injected clocks.
- `GUIDE.md` with the full API, the rules it follows and recipes.

### Changed

- A `NaN` budget, step or cap now raises `ValueError` instead of building a deadline
  that reported zero time left yet never expired, or silently doing nothing.
- `sleep` cut short by the deadline now returns only once `expired` is true, even on
  a clock coarser than the sleep (Windows before Python 3.13), so `sleep` followed by
  `check` reliably raises.
- `copy.copy` and `copy.deepcopy` return an exact clone that shares the clock; a deep
  copy no longer copies the clock or sleep callables.

## [0.1.0]

- First release.
- `Deadline`: a monotonic time budget with `remaining`, `expired`, `sleep` (never
  oversleeps past the deadline) and `raise_if_expired`.
- `DeadlineExpired`: the default error raised when a deadline has passed.
