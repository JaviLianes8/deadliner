# deadliner

Monotonic deadline and time-budget primitive for bounding multi-step operations.

Create one `Deadline`, pass it down the call stack, and every step can ask how much
time is left, stop with a typed error once it is gone, hand a safe `timeout=` to any
blocking stdlib call, and carve out tighter budgets for sub-steps. Sync and async,
fully typed, zero runtime dependencies.

## Install

```
pip install deadliner
```

## Usage

```python
import queue
import subprocess

from deadliner import Deadline, DeadlineExceeded

deadline = Deadline(5.0)  # five seconds from now, on time.monotonic()

try:
    deadline.check("fetch")  # raises DeadlineExceeded once the budget is gone
    item = jobs.get(timeout=deadline.timeout())  # never negative, None if unbounded
    subprocess.run(["make", "build"], timeout=deadline.timeout(), check=True)
except DeadlineExceeded as exc:
    print(exc.step, exc.overrun)  # "fetch", seconds past the deadline
```

Derive tighter budgets. A child never outlives its parent, like Go's
`context.WithDeadline`:

```python
connect = deadline.child(1.0)  # at most 1s, and never past `deadline`

for step in deadline.split(3):  # three equal shares; unused time rolls over
    run_stage(timeout=step.timeout())

for step in deadline.split([1, 2, 1]):  # weighted shares
    ...
```

Wait without overshooting:

```python
deadline.sleep(0.5)  # back off, but never past the deadline
deadline.wait_until(lambda: job.done, interval=0.1)  # poll; False on expiry
await deadline.sleep_async(0.5)
result = await deadline.wait_for(fetch(), "fetch")  # cancels fetch on expiry
```

An infinite deadline is a real value, so "no limit" needs no special cases:

```python
deadline = Deadline.never()
deadline.timeout()  # None, which queue/subprocess/socket read as "block"
lock.acquire(timeout=deadline.timeout(unbounded=-1))  # -1 is Lock's "block"
```

The clock and sleeps are injectable, so tests never wait for real:

```python
now = [0.0]
deadline = Deadline(10.0, clock=lambda: now[0], sleep=lambda s: None)
now[0] = 11.0
assert deadline.expired
```

See [GUIDE.md](GUIDE.md) for the full API, the rules it follows and recipes.

## Command line

`deadliner DURATION COMMAND...` runs a command and stops it once the duration has
passed, with the exit statuses of GNU `timeout` (124 on timeout). It works the same on
Windows, where no such tool ships:

```
deadliner 30s -- python -m pytest
deadliner 5m make release
```

## Why

Bounding a multi-step operation usually means scattering `time.monotonic()`
arithmetic across the call stack, and a negative remainder passed straight to a
stdlib call is a real bug: `threading.Lock.acquire` waits forever on `-1` and raises
`ValueError` on other negatives, and `queue.Queue.get` raises `ValueError` too. `asyncio.timeout` cancels a block of async
code, but it is not an object you can pass to sync code, split across steps or check
from a helper. deadliner is that object. The obvious package names do not fill this
gap: `timebudget` is a speed profiler, and `deadline` wraps AWS Deadline Cloud.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
