# deadliner guide

## Model and stable API

A `Deadline` holds one absolute expiry on a monotonic clock. Its public operations
never change that expiry. The default `time.monotonic` ignores wall-clock updates.
Injected clocks must return finite, nondecreasing float seconds. Sleep callbacks
must advance the same clock when used in tests; a frozen clock can make a settling
sleep loop forever. Callback exceptions propagate unchanged.

The six exports are `Deadline`, `DeadlineExpired`, `DeadlineExceeded`, `Clock`,
`Sleep`, and `AsyncSleep`. The last three are callable typing protocols; ordinary
functions satisfy them without inheritance. They are not runtime-checkable.
`DeadlineExceeded` is exactly the same class as `DeadlineExpired`, a `TimeoutError`.
Import public names from `deadliner`; underscore modules are implementation details.

## Creating and querying deadlines

| Operation | Contract |
| --- | --- |
| `Deadline(seconds, *, clock=time.monotonic, sleep=time.sleep, async_sleep=None)` | Expiry is the creation clock reading plus seconds |
| `Deadline.after(seconds, ...)` | Same as the constructor |
| `Deadline.at(when, ...)` | Absolute expiry on the supplied clock |
| `Deadline.never(...)` | Positive infinite expiry |
| `when` | Absolute expiry |
| `remaining` | Time left, clamped to zero |
| `elapsed` | Clock reading minus creation reading |
| `expired` | True at or after expiry |
| `infinite` | True for positive infinite expiry |
| `check(step=None)` | Remaining time, or `DeadlineExceeded` |
| `raise_if_expired(exc=DeadlineExpired)` | Raise the supplied exception class or instance on expiry |
| `timeout(cap=None, *, unbounded=None)` | Nonnegative remainder, limited by a nonnegative cap |

Zero and negative budgets are already expired. Positive infinity means no expiry;
negative infinity means already expired. NaN is refused. Calculations use Python
float precision, so a tiny budget may round to zero on a large clock reading.
An infinite timeout returns the exact `unbounded` object. A negative cap means zero;
a positive infinite cap leaves the deadline unchanged.

`check` and `wait_for` errors carry `step` (the full supplied label) and `overrun`
(nonnegative seconds late). Labels are omitted from messages to keep credentials
and large values out of logs. Manually constructed errors have both attributes set
to `None`; caller-supplied exception messages are not rewritten.

```python
from deadliner import Deadline, DeadlineExpired

now = [10.0]
deadline = Deadline(2, clock=lambda: now[0])
assert deadline.when == 12.0
assert deadline.check() == 2.0
now[0] = 12.5
assert deadline.timeout() == 0.0
try:
    deadline.check("connect")
except DeadlineExpired as error:
    assert error.step == "connect" and error.overrun == 0.5
```

## Passing timeouts to standard-library calls

`queue.Queue.get`, `socket.settimeout`, and `subprocess.run` accept `None` for an
unbounded wait. `threading.Lock.acquire` uses `-1`; pass `unbounded=-1`.
A socket timeout of zero selects nonblocking mode, so call `check` first if expiry
should raise instead. Downstream timeout exceptions keep their own types.

```python
import threading
from deadliner import Deadline

lock = threading.Lock()
assert lock.acquire(timeout=Deadline.never().timeout(unbounded=-1))
lock.release()
```

## Derived budgets

`child(seconds)` ends at the earlier of the parent's expiry and now plus seconds.
`split(parts)` accepts a positive integer count (not bool) or a nonempty sequence
of positive finite weights. Validation is eager; deadlines are generated lazily.
Each share uses the time left when requested, so unused time rolls forward. The
last share ends exactly at the parent. An expired parent gives expired shares;
an infinite parent gives infinite shares. Extremely small ratios can round to zero.
Weighted splitting uses linear time and memory; integer splitting uses constant
memory. Derived deadlines share clock and sleep callbacks and restart elapsed time.

```python
from deadliner import Deadline

now = [0.0]
root = Deadline(9, clock=lambda: now[0])
stages = root.split(3)
assert next(stages).when == 3.0
now[0] = 1.0
assert next(stages).when == 5.0
assert next(stages).when == 9.0
```

## Waiting

| Operation | Contract |
| --- | --- |
| `sleep(step)` | Request at most the remaining budget; return seconds requested of callbacks |
| `sleep_until(when)` | Sleep toward the earlier of the target and expiry |
| `wait_until(predicate, interval=0.05)` | Poll until truthy or expired; return bool |
| `await sleep_async(step)` | Same budget logic as sleep, using the async callback or asyncio.sleep |
| `await wait_for(awaitable, step=None)` | Return work's result, or cancel it and raise on timeout |

Negative sleep steps do nothing. NaN steps and targets raise `ValueError`.
Polling requires an interval above zero and calls the predicate once even on an
expired deadline. Predicates and ordinary synchronous code are not interrupted.
When a deadline truncates a sleep, extra settling waits may be requested until the
clock observes expiry. The returned total can exceed the original request on a
coarse clock; operating-system scheduling may add further delay. Infinite or huge
sleep requests can raise platform `OverflowError` or `OSError`.

`wait_for` uses the event loop's real timeout machinery; injecting a fake clock does
not replace its timers. It accepts cancellation as cooperative: work that ignores
cancellation can delay completion indefinitely. Errors from work propagate unchanged,
including its own `TimeoutError`. Cleanup errors after deadline cancellation are
chained to `DeadlineExceeded`. Cancelling the caller cancels the work; cleanup may
finish later. Already-expired waits close coroutine objects or cancel futures without
starting them; arbitrary custom awaitables have no generic disposal operation.

On Python 3.11+, `asyncio.timeout(deadline.timeout())` can bound a whole async block.
`asyncio.timeout_at(deadline.when)` is appropriate only when the loop clock and the
deadline clock share a scale. Custom event loops need not do so.

## Copies and serialization

`copy.copy` and `copy.deepcopy` copy the deadline's timing state and share callbacks.
Pickle stores the remaining budget and rebases it when loaded; elapsed restarts at
zero. Transit/storage time is not deducted. Custom callbacks must be picklable.
Monotonic reference points are unspecified, so do not persist the raw `when` value.
Derived objects retain the subclass type, but additional subclass or instance state
is not copied or serialized. Prefer composition for stateful extensions.
The internal pickle and deepcopy hooks use `Any` for Python's serialization protocol;
normal public operations have concrete or generic result types.

## Errors and CLI

Invalid NaN time values, empty or invalid weights, and nonpositive polling intervals
raise `ValueError`; invalid argument types raise `TypeError`. Numeric values too
large for conversion may raise `OverflowError`. Callback and awaitable errors
propagate. Supplied labels and command arguments are not echoed in library-generated
error messages. Do not put secrets in the explicit `step` attribute when logging it.

```
deadliner [--version] DURATION [--] COMMAND [ARG ...]
```

Durations accept nonnegative decimal seconds, scientific notation, `inf` or
`infinity` (case insensitive), optionally followed by lowercase `s`, `m`, `h`, `d`.
Zero disables the limit. Signs, whitespace, hexadecimal, and digit separators are
refused. This grammar is intentionally narrower than GNU timeout's.
Exit statuses: 124 timeout, 125 invalid arguments, 126 cannot invoke, 127 not found,
130 keyboard interruption, otherwise the child's status (128 plus signal number
for a negative subprocess return code). Options after DURATION belong to the child.
Only the direct child is killed and waited for; descendants are not tracked.
Process creation can delay timeout delivery on some platforms.

## Changes from 0.2.0

The callable aliases are now callable protocols, preserving annotated callback use
while giving each public name its own documentation. Error messages omit input labels
and command arguments, and huge overruns use scientific notation. Weighted splitting
handles overflowing sums and tiny suffixes; its final share uses the exact parent
expiry. Async cancellation retrieves eventual errors even if the caller leaves during
cleanup or passes an already-completed future to an expired deadline. Duration parsing
avoids ambiguous repeated-digit matching on long invalid inputs. See the
[CHANGELOG](https://github.com/JaviLianes8/deadliner/blob/main/CHANGELOG.md).
