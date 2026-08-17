#!/usr/bin/env python3
"""Hold the rotated console check to the cell size the kernel was built for.

check-console.py addresses glyphs by cell, so sampling a 16x32 screen with the
8x16 default lands between glyphs and rejects a working kernel. --cjk32 builds
FONT_TER16x32 with FONT_8x16 off, which makes that the only screen it produces.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
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


CHECKER = load("check_console", "check-console.py")
DRIVER = load("drive_system", "drive-system.py")


def paint_rotated(path: Path, cell: tuple[int, int]) -> None:
    """Write a rotated screen carrying the expected glyphs at one cell size."""
    cell_width, cell_height = cell
    width = cell_height
    height = (
        CHECKER.ROTATED_PREFIX_CELLS
        + len(CHECKER.EXPECTED_GLYPHS) * CHECKER.GLYPH_CELLS
    ) * cell_width
    pixels = bytearray(width * height * 3)
    for index, (_codepoint, bitmap) in enumerate(CHECKER.EXPECTED_GLYPHS):
        mask = CHECKER.expected_mask(bitmap, cell, True)
        top = (CHECKER.ROTATED_PREFIX_CELLS + index * CHECKER.GLYPH_CELLS) * cell_width
        for offset, lit in enumerate(mask):
            if not lit:
                continue
            y = top + offset // width
            x = offset % width
            base = (y * width + x) * 3
            pixels[base : base + 3] = b"\xaa\xaa\xaa"
    path.write_bytes(f"P6\n{width} {height}\n255\n".encode() + bytes(pixels))


def rotated_check(image: Path, cell: str) -> str | None:
    """The failure message drive-system.py would raise, or None on success."""
    try:
        DRIVER.check_rotated(image, cell)
    except DRIVER.Failed as failure:
        return str(failure)
    return None


def main() -> int:
    failures = 0
    with tempfile.TemporaryDirectory() as scratch:
        for painted, matching, mismatched in (("16x32", "16x32", "8x16"),
                                              ("8x16", "8x16", "16x32")):
            image = Path(scratch) / f"rotated-{painted}.ppm"
            paint_rotated(image, CHECKER.parse_cell(painted))

            if rotated_check(image, matching) is None:
                print(f"PASS: a {painted} screen passes with --cell {matching}")
            else:
                print(f"FAIL: a {painted} screen was rejected with --cell {matching}")
                failures += 1

            if rotated_check(image, mismatched) is not None:
                print(f"PASS: a {painted} screen fails with --cell {mismatched}")
            else:
                print(f"FAIL: a {painted} screen passed with --cell {mismatched}")
                failures += 1

    environment = os.environ.pop("CJKTTY_CONSOLE_CELL", None)
    try:
        if DRIVER.console_cell() == "8x16":
            print("PASS: the cell defaults to 8x16")
        else:
            print(f"FAIL: the cell defaults to {DRIVER.console_cell()}")
            failures += 1
        os.environ["CJKTTY_CONSOLE_CELL"] = "16x32"
        if DRIVER.console_cell() == "16x32":
            print("PASS: CJKTTY_CONSOLE_CELL reaches the rotated check")
        else:
            print(f"FAIL: CJKTTY_CONSOLE_CELL gave {DRIVER.console_cell()}")
            failures += 1
    finally:
        os.environ.pop("CJKTTY_CONSOLE_CELL", None)
        if environment is not None:
            os.environ["CJKTTY_CONSOLE_CELL"] = environment

    total = 6
    print(f"console cell: {total - failures} passed, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
