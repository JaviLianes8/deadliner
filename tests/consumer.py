"""External consumer used before and after installation and upgrade."""

from __future__ import annotations

import asyncio
import copy
import json
import pickle
import queue
import threading

from deadliner import AsyncSleep, Clock, Deadline, DeadlineExceeded, DeadlineExpired, Sleep


def main() -> None:
    now = [0.0]

    def read() -> float:
        return now[0]

    clock: Clock = read

    def advance(seconds: float) -> None:
        now[0] += seconds

    sleep: Sleep = advance

    async def advance_async(seconds: float) -> None:
        advance(seconds)

    async_sleep: AsyncSleep = advance_async
    root = Deadline.after(8, clock=clock, sleep=sleep, async_sleep=async_sleep)
    assert root.when == 8 and root.remaining == 8 and root.elapsed == 0
    assert not root.expired and not root.infinite
    assert root.check() == 8 and root.timeout(2) == 2
    root.raise_if_expired()
    assert root.child(100).when == 8
    ends = []
    for stage in root.split([1, 2, 1]):
        ends.append(stage.when)
        stage.sleep(100)
    assert ends == [2, 6, 8]
    assert root.expired and root.remaining == 0
    try:
        root.check("step")
    except DeadlineExceeded as error:
        assert isinstance(error, DeadlineExpired)
        assert error.step == "step" and error.overrun == 0
    else:
        raise AssertionError("expired check did not raise")
    later = Deadline.at(10, clock=clock, sleep=sleep, async_sleep=async_sleep)
    assert later.sleep_until(9) == 1
    assert asyncio.run(later.sleep_async(1)) == 1
    assert later.wait_until(lambda: True)
    assert not later.wait_until(lambda: False)
    assert copy.copy(later).when == later.when
    assert copy.deepcopy(later).when == later.when
    assert pickle.loads(pickle.dumps(Deadline.never())).infinite
    assert repr(later).startswith("Deadline(expired")
    lock = threading.Lock()
    assert lock.acquire(timeout=Deadline.never().timeout(unbounded=-1))
    lock.release()
    jobs: queue.Queue[int] = queue.Queue()
    jobs.put(7)
    assert jobs.get(timeout=Deadline.never().timeout()) == 7

    async def work() -> int:
        return 7

    assert asyncio.run(Deadline.never().wait_for(work())) == 7
    print(
        json.dumps(
            {
                "ends": ends,
                "remaining": root.remaining,
                "aliases": DeadlineExpired is DeadlineExceeded,
            }
        )
    )


if __name__ == "__main__":
    main()
