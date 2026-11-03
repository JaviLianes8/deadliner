"""Built distributions exercised from isolated environments outside the source tree."""

from __future__ import annotations

import os
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest


def artifact(variable: str) -> Path:
    value = os.environ.get(variable)
    if not value:
        pytest.skip(f"set {variable} to the built distribution")
    return Path(value).resolve()


def run(command: list[str], cwd: Path, expected: int = 0) -> str:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=180)
    assert result.returncode == expected, result.stdout + result.stderr
    return result.stdout


def test_distribution_contents() -> None:
    wheel = artifact("DEADLINER_WHEEL")
    sdist = artifact("DEADLINER_SDIST")
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        assert "deadliner/py.typed" in names
        assert any(name.endswith("licenses/LICENSE") for name in names)
        assert all(name.startswith(("deadliner/", "deadliner-1.0.0.dist-info/")) for name in names)
        metadata = archive.read("deadliner-1.0.0.dist-info/METADATA").decode()
        assert "Version: 1.0.0" in metadata
        assert "Development Status :: 5 - Production/Stable" in metadata
        assert "Requires-Python: >=3.10" in metadata
        assert not any(
            line.startswith("Requires-Dist:") and ";" not in line for line in metadata.splitlines()
        )
    with tarfile.open(sdist) as archive:
        names = archive.getnames()
        assert "deadliner-1.0.0/LICENSE" in names
        assert "deadliner-1.0.0/src/deadliner/py.typed" in names
        assert not any(
            part in name
            for name in names
            for part in ("__pycache__", ".pyc", "/upstream/", ".git/", "CERT-", "IMPROVEMENTS")
        )


@pytest.mark.parametrize("upgrade", [False, True], ids=["clean", "upgrade"])
def test_installed_wheel_and_cli(tmp_path: Path, upgrade: bool) -> None:
    wheel = artifact("DEADLINER_WHEEL")
    if upgrade and os.environ.get("DEADLINER_PYPI") != "1":
        pytest.skip("set DEADLINER_PYPI=1 for the live 0.2.0 upgrade")
    run([sys.executable, "-m", "venv", str(tmp_path / "venv")], tmp_path)
    scripts = tmp_path / "venv" / ("Scripts" if os.name == "nt" else "bin")
    python = str(scripts / ("python.exe" if os.name == "nt" else "python"))
    cli = str(scripts / ("deadliner.exe" if os.name == "nt" else "deadliner"))
    consumer = Path(__file__).with_name("consumer.py").read_text()
    baseline = None
    if upgrade:
        run([python, "-m", "pip", "install", "--no-cache-dir", "deadliner==0.2.0"], tmp_path)
        assert (
            run(
                [python, "-I", "-c", "import deadliner; print(deadliner.__version__)"], tmp_path
            ).strip()
            == "0.2.0"
        )
        baseline = run([python, "-I", "-c", consumer], tmp_path)
        old = (
            "from deadliner import Deadline; "
            "print([d.when for d in Deadline(8, clock=lambda: 0.).split([1e308, 1e308])])"
        )
        assert run([python, "-I", "-c", old], tmp_path).strip() == "[0.0, 8.0]"
    run([python, "-m", "pip", "install", "--no-deps", "--no-cache-dir", str(wheel)], tmp_path)
    run([python, "-m", "pip", "check"], tmp_path)
    result = run([python, "-I", "-c", consumer], tmp_path)
    if baseline is not None:
        assert result == baseline
    assert run([cli, "--version"], tmp_path).strip() == "deadliner 1.0.0"
    assert "DURATION" in run([cli, "--help"], tmp_path)
    for prefix in ([cli], [python, "-I", "-m", "deadliner"]):
        assert run([*prefix, "5", python, "-c", "print('ready')"], tmp_path).strip() == "ready"
        run([*prefix, "0", python, "-c", "raise SystemExit(3)"], tmp_path, 3)
        run([*prefix, "0.1", python, "-c", "import time; time.sleep(30)"], tmp_path, 124)
        run([*prefix, "bad", python], tmp_path, 125)
        run([*prefix, "5", "deadliner-no-command-xyz"], tmp_path, 127)
    new = (
        "from deadliner import Deadline; "
        "assert [d.when for d in Deadline(8, clock=lambda: 0.).split([1e308, 1e308])] == [4., 8.]"
    )
    run([python, "-I", "-c", new], tmp_path)
