"""Regression contracts for release boundaries and safe diagnostics."""

from __future__ import annotations

import asyncio
import math

import pytest

from deadliner import Deadline, DeadlineExceeded
from deadliner._cli import main, parse_duration

from conftest import FakeClock


@pytest.mark.parametrize("weights", [[1e308, 1e308], [1e308, 1e-308, 1e-308]])
def test_weight_sums_do_not_overflow_or_lose_tiny_suffixes(weights: list[float]) -> None:
    steps = list(Deadline(8, clock=lambda: 0.0).split(weights))
    assert steps[0].when == (4.0 if len(weights) == 2 else 8.0)
    assert steps[-2].when == 4.0
    assert steps[-1].when == 8.0


def test_final_share_retains_the_exact_expiry() -> None:
    parent = Deadline.at(1.0, clock=lambda: -1e17)
    assert next(parent.split(1)).when == 1.0


def test_never_with_extreme_weights_has_only_infinite_shares() -> None:
    assert all(d.infinite for d in Deadline.never().split([1e-308, 1e308]))


@pytest.mark.parametrize(
    "label", ["secret-token", "password" * 100000, "\n\x1b[31m"], ids=["short", "huge", "control"]
)
def test_errors_never_echo_labels(label: str) -> None:
    with pytest.raises(DeadlineExceeded) as info:
        Deadline.at(-1e308, clock=lambda: 0.0).check(label)
    assert info.value.step == label
    assert info.value.overrun == 1e308
    assert label not in str(info.value)
    assert len(str(info.value)) < 80


@pytest.mark.parametrize(
    "argument",
    ["secret-token", "9" * 100000 + "x", "--secret-token"],
    ids=["short", "huge", "option"],
)
def test_cli_usage_errors_do_not_echo_inputs(
    argument: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as info:
        main([argument])
    assert info.value.code == 125
    error = capsys.readouterr().err
    assert argument not in error
    assert len(error) < 250


def test_invalid_weights_do_not_echo_values(fake: FakeClock) -> None:
    with pytest.raises(ValueError) as info:
        fake.deadline(1).split(["secret-token"])  # type: ignore[list-item]
    assert "secret-token" not in str(info.value)


def test_duration_parser_handles_large_bad_numbers() -> None:
    for text in ["9" * 100000 + "x", "9" * 100000 + ".x", "1e" + "9" * 100000 + "x"]:
        with pytest.raises(ValueError, match=r"^invalid duration$"):
            parse_duration(text)
    assert math.isinf(parse_duration("9" * 100000))


def test_expired_wait_retrieves_an_existing_failed_future() -> None:
    reported: list[object] = []

    async def run() -> None:
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(lambda _loop, context: reported.append(context))
        future: asyncio.Future[int] = loop.create_future()
        future.set_exception(ValueError("cleanup"))
        with pytest.raises(DeadlineExceeded):
            await Deadline(0).wait_for(future)
        await asyncio.sleep(0)
        del future

    asyncio.run(run())
    assert reported == []


def test_caller_cancelled_during_timeout_cleanup_retrieves_errors() -> None:
    reported: list[object] = []

    async def run() -> None:
        started = asyncio.Event()
        cleaning = asyncio.Event()
        finish = asyncio.Event()
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(lambda _loop, context: reported.append(context))

        async def work() -> None:
            started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cleaning.set()
                await finish.wait()
                raise ValueError("cleanup") from None

        outer = asyncio.create_task(Deadline(0.1).wait_for(work()))
        await started.wait()
        await cleaning.wait()
        outer.cancel()
        with pytest.raises(asyncio.CancelledError):
            await outer
        finish.set()
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    asyncio.run(run())
    assert reported == []
