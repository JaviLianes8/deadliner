# deadliner

Monotonic deadline and time-budget primitive for bounding multi-step operations

## Install

```
pip install deadliner
```

## Usage

One `Deadline` bounds a whole multi-step operation. Each step reads what is left,
waits no longer than the budget allows, and stops the moment it is spent.

```python
from deadliner import Deadline, DeadlineExpired

deadline = Deadline(5.0)

for item in work_items:
    deadline.raise_if_expired()   # stop once the budget is gone
    process(item)
    deadline.sleep(0.5)           # back off, but never past the deadline

print(deadline.remaining)         # seconds left, never below zero
print(deadline.expired)           # True once no time is left
```

`sleep` returns the seconds it actually slept, which shrinks to zero near the end:

```python
deadline = Deadline(2.0)
deadline.sleep(10.0)   # sleeps 2.0, not 10.0
assert deadline.expired
```

Pass any exception (a type or an instance) to `raise_if_expired`; it defaults to
`DeadlineExpired`, a subclass of `TimeoutError`:

```python
deadline.raise_if_expired(TimeoutError("request budget exhausted"))
```

The clock and the sleep call are injectable, so budgets are trivial to test without
real waiting:

```python
clock = {"now": 0.0}
deadline = Deadline(10.0, clock=lambda: clock["now"], sleep=lambda s: None)
clock["now"] = 11.0
assert deadline.expired
```

## Why

Bounding a multi-step operation usually means scattering `time.monotonic()`
arithmetic across the call stack, which is easy to get wrong and tempting to base on
`time.time()` (which jumps when the wall clock is adjusted). The obvious package
names do not fill this gap: `timebudget` is a speed profiler, and `deadline` wraps
AWS Deadline Cloud. `deadliner` is a single, small, fully typed primitive that holds
the deadline once, answers how much is left, and refuses to oversleep past it. It has
zero runtime dependencies and ships `py.typed`.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
