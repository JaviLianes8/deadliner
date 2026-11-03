"""Cross-check fetched official sources and the installed GNU timeout program."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

from deadliner import Deadline
from deadliner._cli import CANNOT_INVOKE, FAILED, NOT_FOUND, TIMED_OUT, main


def source(name: str) -> str:
    folder = os.environ.get("DEADLINER_UPSTREAM")
    if not folder:
        pytest.skip("set DEADLINER_UPSTREAM to the fetched source directory")
    data = (Path(folder) / name).read_bytes()
    manifest = json.loads((Path(__file__).parents[1] / "UPSTREAM-MANIFEST.json").read_text())
    assert hashlib.sha256(data).hexdigest() == manifest[name]["sha256"]
    assert len(data) == manifest[name]["size"]
    return data.decode("utf-8")


def test_exit_codes_are_extracted_from_the_fetched_gnu_manual() -> None:
    text = source("coreutils.texi").split("@node timeout invocation", 1)[1]
    text = text.split("@node ", 1)[0]
    codes = re.findall(r"^(12[4-7]) if", text, re.M)
    assert [int(value) for value in codes] == [TIMED_OUT, FAILED, CANNOT_INVOKE, NOT_FOUND]


def test_child_rule_matches_the_fetched_go_reference() -> None:
    code = source("context.go")
    assert "cur.Before(d)" in code and "return WithCancel(parent)" in code
    # Generated boundary cases exercise the earlier-parent branch in that source.
    for parent in [-10.0, 0.0, 10.0]:
        for child in [-20.0, -10.0, 0.0, 10.0, 20.0]:
            result = Deadline.at(parent, clock=lambda: 0.0).child(child)
            assert result.when == (parent if parent < child else child)


def test_default_clock_matches_the_fetched_python_contract() -> None:
    text = source("time.rst")
    assert "cannot go backwards" in text
    assert "not affected by system clock updates" in text
    info = time.get_clock_info("monotonic")
    assert info.monotonic and not info.adjustable
    before = time.monotonic()
    deadline = Deadline(10.0)
    after = time.monotonic()
    assert before + 10 <= deadline.when <= after + 10


@pytest.mark.parametrize("status", [0, 3, 42])
def test_exit_status_matches_real_gnu_timeout(status: int) -> None:
    executable = os.environ.get("DEADLINER_GNU_TIMEOUT")
    if not executable:
        pytest.skip("set DEADLINER_GNU_TIMEOUT to the GNU timeout executable")
    command = [sys.executable, "-c", f"raise SystemExit({status})"]
    reference = subprocess.run([executable, "5", *command], check=False, timeout=15)
    assert main(["5", *command]) == reference.returncode == status


def test_missing_command_matches_real_gnu_timeout() -> None:
    executable = os.environ.get("DEADLINER_GNU_TIMEOUT")
    if not executable:
        pytest.skip("set DEADLINER_GNU_TIMEOUT to the GNU timeout executable")
    command = "deadliner-not-a-real-command-xyz"
    reference = subprocess.run([executable, "1", command], check=False, timeout=10)
    assert main(["1", command]) == reference.returncode == 127
