# deadliner

[![Lianes8 Certified](https://lianes8studio.com/certified/lianes8-certified-badge.svg)](https://lianes8studio.com/certified)

One monotonic time budget for a multi-step operation. Create a deadline, pass it to
helpers, and give each blocking call the time still available. Sync and async,
Python 3.10+, typed, with no runtime dependencies.

## Install

```
pip install deadliner
```

## Quick start

```python
import queue
from deadliner import Deadline, DeadlineExceeded

jobs: queue.Queue[str] = queue.Queue()
jobs.put("ready")
deadline = Deadline(5.0)
deadline.check("fetch")
assert jobs.get(timeout=deadline.timeout()) == "ready"
assert deadline.child(1.0).when <= deadline.when

try:
    Deadline(0).check("finish")
except DeadlineExceeded as error:
    assert error.step == "finish"
```

Allocate the remaining budget across stages. Unused time rolls into later stages:

```python
from deadliner import Deadline

now = [0.0]
deadline = Deadline(8.0, clock=lambda: now[0])
ends = []
for stage in deadline.split([1, 2, 1]):
    ends.append(stage.when)
    now[0] = stage.when
assert ends == [2.0, 6.0, 8.0]
assert Deadline.never().timeout() is None
```

Await work under the same budget:

```python
import asyncio
from deadliner import Deadline


async def example() -> int:
    deadline = Deadline(5.0)
    return await deadline.wait_for(asyncio.sleep(0, result=7))


assert asyncio.run(example()) == 7
```

## Command line

```
deadliner 30s -- python -c "print('ready')"
python -m deadliner 5m -- python -c "print('ready')"
```

Durations accept seconds or `s`, `m`, `h`, `d` suffixes; zero disables the limit.
A timeout exits 124. Only the direct child is killed, not its descendants.

## Why

Manual `time.monotonic()` arithmetic works well for a single call. Across several
helpers, deadliner centralizes the expiry and clamps negative remainders to zero.
[`asyncio.timeout`](https://docs.python.org/3/library/asyncio-task.html#asyncio.timeout)
(Python 3.11+) bounds an async block; deadliner also supplies timeout values to sync
code and divides budgets among stages. Use the standard library directly when
those extra operations are unnecessary.

The CLI follows the basic exit-status convention of
[GNU timeout](https://www.gnu.org/software/coreutils/manual/html_node/timeout-invocation.html).
It is not a full replacement: it has no process-group management, signal selection,
or kill grace period. Deadlines do not interrupt ordinary Python code; callers must
check them or pass their timeout to an operation that enforces it. Sleeps can
overshoot because of scheduling or coarse clocks.

See the [GUIDE](https://github.com/JaviLianes8/deadliner/blob/main/GUIDE.md) for every
operation, error and limitation, and the
[CHANGELOG](https://github.com/JaviLianes8/deadliner/blob/main/CHANGELOG.md) for changes.

## Development

Install `deadliner[dev]`. `scripts/check.ps1` runs formatting, lint, strict typing
and tests. Set `DEADLINER_SCRATCH` to a private working directory for test files.
`scripts/fetch_upstream.py DESTINATION --manifest MANIFEST` fetches the official
sources. Set `DEADLINER_UPSTREAM` to that destination to enable reference tests.
The committed `UPSTREAM-MANIFEST.json` records the certification source hashes;
fetched text is neither committed nor distributed.

## License

MIT. See [LICENSE](https://github.com/JaviLianes8/deadliner/blob/main/LICENSE).
