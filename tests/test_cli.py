from __future__ import annotations

import math
import subprocess
import sys

import pytest

from deadliner._cli import main, parse_duration

PY = sys.executable


@pytest.mark.parametrize(
    ("text", "seconds"),
    [("2.5", 2.5), ("30s", 30.0), ("5m", 300.0), ("1.5h", 5400.0), ("1d", 86400.0), ("0", 0.0)],
)
def test_parse_duration_understands_gnu_suffixes(text: str, seconds: float) -> None:
    assert parse_duration(text) == seconds


def test_parse_duration_accepts_inf() -> None:
    assert parse_duration("inf") == math.inf


@pytest.mark.parametrize("text", ["", "abc", "-1", "nan", "5x", "s", " 5", "1_000", "5 ", "+5"])
def test_parse_duration_rejects_bad_input(text: str) -> None:
    with pytest.raises(ValueError, match="invalid duration"):
        parse_duration(text)


def test_the_commands_own_status_is_returned() -> None:
    assert main(["10", PY, "-c", "import sys; sys.exit(3)"]) == 3


def test_a_leading_double_dash_is_dropped() -> None:
    assert main(["10", "--", PY, "-c", "pass"]) == 0


def test_a_command_that_runs_out_of_time_exits_124(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["0.3", PY, "-c", "import time; time.sleep(30)"]) == 124
    assert "timed out after 0.3s" in capsys.readouterr().err


def test_a_zero_duration_disables_the_limit() -> None:
    assert main(["0", PY, "-c", "pass"]) == 0


def test_a_missing_command_exits_127(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["5", "deadliner-no-such-command-xyz"]) == 127
    assert "command not found" in capsys.readouterr().err


def test_a_bad_duration_exits_125() -> None:
    with pytest.raises(SystemExit) as info:
        main(["soon", PY])
    assert info.value.code == 125


def test_no_command_exits_125() -> None:
    with pytest.raises(SystemExit) as info:
        main(["5"])
    assert info.value.code == 125


def test_a_signal_death_maps_to_128_plus_the_signal(monkeypatch: pytest.MonkeyPatch) -> None:
    def killed(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess([], -9)

    monkeypatch.setattr(subprocess, "run", killed)
    assert main(["5", "anything"]) == 137


def test_a_command_that_cannot_be_invoked_exits_126(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(subprocess, "run", denied)
    assert main(["5", "anything"]) == 126


def test_a_second_double_dash_belongs_to_the_command() -> None:
    script = "import sys; sys.exit(0 if sys.argv[1:] == ['--'] else 1)"
    assert main(["10", "--", PY, "-c", script, "--"]) == 0


def test_options_after_the_duration_belong_to_the_command() -> None:
    assert main(["10", PY, "--version"]) == 0


def test_ctrl_c_exits_130(monkeypatch: pytest.MonkeyPatch) -> None:
    def interrupted(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        raise KeyboardInterrupt

    monkeypatch.setattr(subprocess, "run", interrupted)
    assert main(["5", "anything"]) == 130


def test_version_and_help_still_work(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as info:
        main(["--version"])
    assert info.value.code == 0
    assert "deadliner 0.2.0" in capsys.readouterr().out
