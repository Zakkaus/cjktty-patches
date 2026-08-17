#!/usr/bin/env python3
"""Hold the fbcon rebind assertion against the ways it used to pass wrongly."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any


TOOLS = Path(__file__).resolve().parent


def load(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, TOOLS / filename)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


PROBE = load("console_probe", "console_probe.py")


def console(root: Path, name: str, kind: str, writable: bool) -> None:
    directory = root / name
    directory.mkdir()
    (directory / "name").write_text(f"{kind}\n")
    bind = directory / "bind"
    bind.write_text("1\n")
    if not writable:
        bind.chmod(0o444)


def run(root: Path, value: int) -> int:
    command = PROBE.rebind_command(value, glob=f"{root}/vtcon*", settle=0)
    result = subprocess.run(
        ["bash", "-c", command],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode


CASES = (
    (
        "a writable framebuffer console",
        (("vtcon0", "frame buffer device", True),),
        0,
    ),
    (
        "no framebuffer console at all",
        (("vtcon0", "dummy device", True),),
        1,
    ),
    (
        "a framebuffer console whose bind rejects the write",
        (("vtcon0", "frame buffer device", False),),
        1,
    ),
    (
        "one framebuffer console beside a dummy one",
        (("vtcon0", "dummy device", True), ("vtcon1", "frame buffer device", True)),
        0,
    ),
    (
        "a second framebuffer console that rejects the write",
        (
            ("vtcon0", "frame buffer device", True),
            ("vtcon1", "frame buffer device", False),
        ),
        1,
    ),
)


def main() -> int:
    failures = 0
    for label, consoles, expected in CASES:
        scratch = Path(tempfile.mkdtemp())
        try:
            for name, kind, writable in consoles:
                console(scratch, name, kind, writable)
            actual = 0 if run(scratch, 0) == 0 else 1
        finally:
            for name, _kind, _writable in consoles:
                (scratch / name / "bind").chmod(0o644)
            shutil.rmtree(scratch)
        if actual == expected:
            verdict = "succeeds" if expected == 0 else "fails"
            print(f"PASS: {label} {verdict}")
        else:
            print(f"FAIL: {label} gave {actual}, expected {expected}")
            failures += 1
    print(f"console probe: {len(CASES) - failures} passed, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
