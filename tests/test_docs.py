"""Execute all public docstrings and the complete Markdown Python examples."""

from __future__ import annotations

import doctest
import importlib
import inspect
import re
from pathlib import Path

import pytest

import deadliner


@pytest.mark.parametrize("name", ["_core", "_deadline", "_errors", "_types", "_waits"])
def test_public_doctests(name: str) -> None:
    result = doctest.testmod(importlib.import_module("deadliner." + name))
    assert result.attempted > 0
    assert result.failed == 0


def test_every_public_name_and_method_has_a_runnable_example() -> None:
    for name in deadliner.__all__:
        symbol = getattr(deadliner, name)
        assert ">>>" in (inspect.getdoc(symbol) or ""), name
    for name, member in inspect.getmembers(deadliner.Deadline):
        if not name.startswith("_"):
            assert ">>>" in (inspect.getdoc(member) or ""), name


@pytest.mark.parametrize("name", ["README.md", "GUIDE.md"])
def test_markdown_python_examples(name: str) -> None:
    text = (Path(__file__).resolve().parents[1] / name).read_text(encoding="utf-8")
    blocks = re.findall(r"```python\n(.*?)```", text, re.S)
    assert blocks
    for block in blocks:
        exec(compile(block, name, "exec"), {})
    assert not re.search(r"\]\((?!https://)[^)]+\)", text)
