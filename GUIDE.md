# deadliner guide

## The model

A `Deadline` is one absolute expiry time on a monotonic clock. It is created once,
at the edge of an operation (a request, a job, a CLI command), and passed down to
every step. Steps never compute their own timeouts from scratch; they ask the
deadline. A deadline never changes its expiry, so sharing one between threads or tasks
is safe.

The default clock is `time.monotonic`, which "cannot go backwards" and "is not
affected by system clock updates" ([time docs](https://docs.python.org/3/library/time.html),
[PEP 418](https://peps.python.org/pep-0418/)). Wall-clock time is never used.

## Creating a deadline

| Call | Meaning |
| --- | --- |
| `Deadline(seconds)` / `Deadline.after(seconds)` | expires `seconds` from now (Go's `WithTimeout`) |
| `Deadline.at(when)` | expires at absolute time `when` on the same clock (Go's `WithDeadline`) |
| `Deadline.never()` | never expires; for callers that set no limit |

Zero or negative budgets are valid and already expired. `NaN` raises `ValueError`.
All three accept `clock=`, `sleep=` and `async_sleep=` for tests.

## Asking about time

| Member | Returns |
| --- | --- |
| `remaining` | seconds left, never below zero, `inf` when infinite |
| `expired` | `True` once `clock() >= when` |
| `when` | the absolute expiry time (`inf` when infinite) |
| `elapsed` | seconds since this object was created |
| `infinite` | `True` for `Deadline.never()` and infinite budgets |
| `check(step=None)` | the seconds left, or raises `DeadlineExceeded` |
| `raise_if_expired(exc)` | raises any exception you choose once expired |

`DeadlineExceeded` is the name Go's `context` package and gRPC use
(`DEADLINE_EXCEEDED`). It is the same class as `DeadlineExpired`, a subclass of
`TimeoutError`, so existing `except TimeoutError` handlers keep working. Errors
raised by `check` carry `step` (the label you passed) and `overrun` (seconds late).

## Handing time to the stdlib

`timeout(cap=None, *, unbounded=None)` returns the value for a `timeout=` argument:

- the seconds left, at most `cap` when given;
- `0.0`, never a negative number, once expired;
- `unbounded` when the deadline is infinite and no cap applies.

Why the clamp matters, from the stdlib docs:

- `threading.Lock.acquire`: "A timeout argument of -1 specifies an unbounded wait."
  A remainder of exactly -1 would block forever and any other negative raises
  `ValueError`. Pass `unbounded=-1` so an infinite deadline maps to that "block"
  value on purpose.
- `queue.Queue.get` raises `ValueError` for a negative timeout.
- `subprocess.run`, `queue.Queue.get` and `socket.settimeout` read `None` as "block".
- `socket.settimeout(0.0)` switches the socket to non-blocking mode. When a zero would
  change the meaning of a call, call `check()` first so an expired budget raises
  instead.

```python
deadline.check("connect")
sock.settimeout(deadline.timeout())
lock.acquire(timeout=deadline.timeout(unbounded=-1))
proc = subprocess.run(cmd, timeout=deadline.timeout(cap=30.0), check=True)
```

## Deriving budgets

`child(seconds)` returns a deadline `seconds` from now but never later than the
parent. This is Go's rule: "If the parent's deadline is already earlier than d,
WithDeadline(parent, d) is semantically equivalent to parent"
([pkg.go.dev/context](https://pkg.go.dev/context)).

`split(parts)` yields one deadline per step. `parts` is a step count or a sequence of
positive weights. Each step deadline is computed when the iterator reaches it, from
the time left at that moment, so a step that finishes early donates its leftover
time to the remaining steps. The last step always ends exactly at the parent.

```python
for step, url in zip(deadline.split(len(urls)), urls):
    fetch(url, timeout=step.timeout())
```

Derived deadlines share the parent's clock and sleeps.

## Waiting

| Member | Behaviour |
| --- | --- |
| `sleep(step)` | sleeps up to `step`, never past the deadline; returns the span slept |
| `sleep_until(when)` | sleeps until `when` or the deadline, whichever is first |
| `wait_until(predicate, interval=0.05)` | polls; `True` when the predicate holds, `False` on expiry |
| `await sleep_async(step)` | async `sleep` |
| `await wait_for(awaitable, step=None)` | awaits; on expiry cancels it and raises `DeadlineExceeded` |

When the deadline cuts a sleep short, `sleep` and `sleep_async` return only once
`expired` is true, even where the clock ticks more coarsely than the sleep (Windows
before Python 3.13 reads `time.monotonic` in 15.6 ms steps). So `sleep` followed by
`check` reliably raises. Sleeping on an infinite deadline passes the step straight to
`time.sleep`, which rejects values too large for the platform with `OverflowError`.

`wait_until` calls the predicate one last time at the deadline itself. `wait_for`
lets errors from the awaitable propagate unchanged (including its own
`TimeoutError`), cancels the awaitable if the caller is cancelled, and never starts
work when the deadline has already passed. An error the awaitable raises while it
is being cancelled becomes the `__cause__` of the `DeadlineExceeded`. As with
`asyncio.wait_for`, work that ignores cancellation delays the error.

## Working with asyncio.timeout

deadliner does not replace `asyncio.timeout` (Python 3.11+), which cancels a whole
block of async code. Feed it the budget instead:

```python
async with asyncio.timeout(deadline.timeout()):
    await step_one()
    await step_two()
```

`None` from an infinite deadline means "no limit" there too. With the default clock,
`deadline.when` is on the same `time.monotonic` scale as the default event loop
clock, so `asyncio.timeout_at(deadline.when)` also works.

## Crossing a process boundary

A monotonic reading means nothing in another process: "The reference point of the
returned value is undefined". So pickling stores the time left and rebases it on
load, the same move gRPC makes when it propagates a deadline: it "converts the
deadline to a timeout from which the already elapsed time is already deducted"
([grpc.io/docs/guides/deadlines](https://grpc.io/docs/guides/deadlines/)). `elapsed`
restarts from zero on the restored copy. A custom clock must itself be picklable.
`copy.copy` and `copy.deepcopy` return an exact clone that shares the clock.

## Testing code that takes a deadline

Inject a hand-driven clock and a sleep that advances it. Nothing waits for real:

```python
class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


clock = FakeClock()
deadline = Deadline(10.0, clock=clock, sleep=clock.sleep)
```

## Command line

```
deadliner [--version] DURATION [--] COMMAND [ARG ...]
```

`DURATION` is seconds or a number with `s`, `m`, `h` or `d`; `0` disables the limit.
Exit statuses follow GNU `timeout`
([manual](https://www.gnu.org/software/coreutils/manual/html_node/timeout-invocation.html)):
124 timed out, 125 deadliner failed (bad arguments), 126 cannot invoke, 127 not found,
otherwise the command's own status (128 plus the signal number when a signal killed
it). On timeout the direct child process is killed; processes it started itself are
not tracked.
