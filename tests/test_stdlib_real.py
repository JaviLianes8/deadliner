"""Real stdlib calls bounded by a real Deadline.

Timing assertions are lower bounds plus a generous ceiling that only proves the call
did not hang, so the tests stay stable on a loaded machine. A small slack absorbs
timer granularity, since some platforms wake a blocking call a few milliseconds early.
"""

from __future__ import annotations

import queue
import socket
import subprocess
import sys
import threading
import time

import pytest

from deadliner import Deadline, DeadlineExceeded

BUDGET = 0.3
SLACK = 0.05
CEILING = 10.0


def test_queue_get_waits_for_the_budget_and_no_longer() -> None:
    deadline = Deadline(BUDGET)
    start = time.monotonic()
    with pytest.raises(queue.Empty):
        queue.Queue[int]().get(timeout=deadline.timeout())
    took = time.monotonic() - start
    assert BUDGET - SLACK <= took < CEILING


def test_queue_get_on_an_expired_budget_does_not_raise_value_error() -> None:
    # A raw negative timeout raises ValueError; the derived one is clamped at zero.
    deadline = Deadline(-1.0)
    with pytest.raises(queue.Empty):
        queue.Queue[int]().get(timeout=deadline.timeout())


def test_lock_acquire_gives_up_when_the_budget_runs_out() -> None:
    lock = threading.Lock()
    lock.acquire()
    try:
        deadline = Deadline(BUDGET)
        start = time.monotonic()
        assert lock.acquire(timeout=deadline.timeout(unbounded=-1)) is False
        took = time.monotonic() - start
        assert BUDGET - SLACK <= took < CEILING
    finally:
        lock.release()


def test_lock_acquire_on_an_expired_budget_returns_at_once_instead_of_forever() -> None:
    # Lock.acquire(timeout=-1) waits forever and other negatives raise ValueError.
    lock = threading.Lock()
    lock.acquire()
    try:
        start = time.monotonic()
        assert lock.acquire(timeout=Deadline(-1.0).timeout(unbounded=-1)) is False
        assert time.monotonic() - start < CEILING
    finally:
        lock.release()


def test_lock_acquire_with_an_infinite_deadline_still_acquires() -> None:
    lock = threading.Lock()
    assert lock.acquire(timeout=Deadline.never().timeout(unbounded=-1)) is True
    lock.release()


def test_subprocess_run_is_killed_when_the_budget_runs_out() -> None:
    deadline = Deadline(1.0)
    start = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        subprocess.run(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            timeout=deadline.timeout(),
            check=False,
        )
    took = time.monotonic() - start
    assert 1.0 - SLACK <= took < 1.0 + CEILING
    assert deadline.remaining <= SLACK  # Windows rounds the wait down to whole ms


def test_subprocess_run_finishes_inside_the_budget() -> None:
    deadline = Deadline(60.0)
    done = subprocess.run([sys.executable, "-c", "pass"], timeout=deadline.timeout(), check=False)
    assert done.returncode == 0
    assert not deadline.expired


def test_socket_accept_times_out_with_the_budget() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        deadline = Deadline(BUDGET)
        server.settimeout(deadline.timeout())
        start = time.monotonic()
        with pytest.raises(TimeoutError):
            server.accept()
        took = time.monotonic() - start
        assert BUDGET - SLACK <= took < CEILING


def test_socket_accept_succeeds_inside_the_budget() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        deadline = Deadline(CEILING)
        server.settimeout(deadline.timeout())
        client = socket.create_connection(server.getsockname(), timeout=deadline.timeout())
        try:
            peer, _ = server.accept()
            peer.close()
        finally:
            client.close()
    assert not deadline.expired


def test_one_budget_bounds_several_real_steps() -> None:
    deadline = Deadline(BUDGET * 2)
    blocked = threading.Lock()
    blocked.acquire()
    start = time.monotonic()
    try:
        for step in deadline.split(3):
            assert blocked.acquire(timeout=step.timeout(unbounded=-1)) is False
    finally:
        blocked.release()
    took = time.monotonic() - start
    assert BUDGET * 2 - SLACK <= took < CEILING
    deadline.sleep(CEILING)
    with pytest.raises(DeadlineExceeded, match="after the last step"):
        deadline.check("after the last step")


def test_real_sleep_is_cut_at_the_deadline() -> None:
    deadline = Deadline(BUDGET)
    start = time.monotonic()
    deadline.sleep(30.0)
    took = time.monotonic() - start
    assert BUDGET - SLACK <= took < CEILING
    assert deadline.expired
