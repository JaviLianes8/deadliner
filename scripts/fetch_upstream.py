"""Fetch the official reference sources into a caller-selected directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

SOURCES = {
    "time.rst": (
        "https://raw.githubusercontent.com/python/cpython/v3.14.0/Doc/library/time.rst",
        "PSF-2.0",
    ),
    "asyncio-task.rst": (
        "https://raw.githubusercontent.com/python/cpython/v3.14.0/Doc/library/asyncio-task.rst",
        "PSF-2.0",
    ),
    "context.go": (
        "https://raw.githubusercontent.com/golang/go/go1.25.0/src/context/context.go",
        "BSD-3-Clause",
    ),
    "coreutils.texi": (
        "https://raw.githubusercontent.com/coreutils/coreutils/v9.7/doc/coreutils.texi",
        "GFDL-1.3-or-later",
    ),
    "pypi.json": ("https://pypi.org/pypi/deadliner/json", "PyPI metadata"),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, (url, license_name) in SOURCES.items():
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read()
        (args.destination / name).write_bytes(data)
        manifest[name] = {
            "url": url,
            "fetched": "2026-11-03",
            "revision": url,
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "license": license_name,
        }
        print(name, len(data))
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
