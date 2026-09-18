#!/usr/bin/env python3
"""Offline installer using only the Python standard library.

Run this script with the Python interpreter of the target virtual environment.
It intentionally avoids pip build backends so a new Python 3.12 venv can install
Segmenta without network access or preinstalled setuptools.
"""

from __future__ import annotations

import os
import shutil
import stat
import sys
import sysconfig
from pathlib import Path


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    source = repo / "src" / "segmenta"
    purelib = Path(sysconfig.get_path("purelib"))
    scripts = Path(sysconfig.get_path("scripts"))
    destination = purelib / "segmenta"
    purelib.mkdir(parents=True, exist_ok=True)
    scripts.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    launcher = scripts / "segmenta"
    launcher.write_text(
        f"#!{sys.executable}\nfrom segmenta.cli import main\nraise SystemExit(main())\n",
        encoding="utf-8",
    )
    launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"installed Segmenta to {destination}")
    print(f"installed CLI to {launcher}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

