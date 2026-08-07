"""Decide from a console screenshot whether the CJK glyphs really rendered.

The patch does not change vc_font, so no ioctl can answer this: the console
still reports the 256-glyph base font while cjktty draws CJK from its own
buffer. What separates a working kernel from a broken one is on screen — real
glyphs differ from each other, missing ones are all the same box.

The test prints from a cleared screen, so the CJK lines sit at known rows.

A rotated console moves those rows, so `--rotated` drops the cell comparison and
asks only that the screen carries the ink of a drawn line. Rotation runs
fbcon_rotate_font_utf, and a failure there paints nothing at all.

Usage: check-console.py [--rotated] <screenshot.ppm>
"""

from __future__ import annotations

import sys
from pathlib import Path

CELL_WIDTH = 8
CELL_HEIGHT = 16
#: init.c writes a title line first, then Simplified on the next row.
CJK_ROW = 1
#: "Simplified:  " is thirteen columns; the CJK text starts after it.
FIRST_COLUMN = 13
#: A CJK glyph is two cells wide.
GLYPH_CELLS = 2
#: One rotated line of the test text lights this many subpixels; half of it is
#: still unmistakably a line of text and not a stray cursor.
ROTATED_MIN_INK = 1000


class CheckFailed(Exception):
    pass


def read_ppm(path: Path) -> tuple[int, int, bytes]:
    data = path.read_bytes()
    fields: list[bytes] = []
    at = 0
    while len(fields) < 4:
        while at < len(data) and data[at : at + 1].isspace():
            at += 1
        if data[at : at + 1] == b"#":
            at = data.index(b"\n", at) + 1
            continue
        end = at
        while end < len(data) and not data[end : end + 1].isspace():
            end += 1
        fields.append(data[at:end])
        at = end
    if fields[0] != b"P6":
        raise CheckFailed(f"{path} is not a binary PPM")
    return int(fields[1]), int(fields[2]), data[at + 1 :]


def glyph(pixels: bytes, width: int, row: int, column: int) -> bytes:
    """The pixels of one glyph cell, as a flat block."""
    out = bytearray()
    for y in range(row * CELL_HEIGHT, (row + 1) * CELL_HEIGHT):
        start = (y * width + column * CELL_WIDTH) * 3
        out += pixels[start : start + CELL_WIDTH * GLYPH_CELLS * 3]
    return bytes(out)


def ink(block: bytes) -> int:
    return sum(1 for value in block if value > 0x40)


def lit_box(pixels: bytes, width: int, height: int) -> tuple[int, int, int, int]:
    xs: list[int] = []
    ys: list[int] = []
    for y in range(height):
        row = pixels[y * width * 3 : (y + 1) * width * 3]
        for x in range(width):
            if max(row[x * 3 : x * 3 + 3]) > 0x40:
                xs.append(x)
                ys.append(y)
    if not xs:
        raise CheckFailed("the screen is blank; rotation painted nothing")
    return min(xs), min(ys), max(xs), max(ys)


def check_rotated(path: Path) -> str:
    width, height, pixels = read_ppm(path)
    lit = ink(pixels)
    if lit < ROTATED_MIN_INK:
        raise CheckFailed(
            f"the rotated console drew {lit} lit subpixels, under {ROTATED_MIN_INK}; "
            "rotation painted nothing"
        )
    left, top, right, bottom = lit_box(pixels, width, height)
    box_width = right - left + 1
    box_height = bottom - top + 1
    # A line of text is long along the reading direction. Rotated by 90 degrees
    # it stands taller than it is wide, which an unrotated line can never do.
    if box_height <= box_width:
        raise CheckFailed(
            f"the drawn text is {box_width} by {box_height} pixels, wider than tall; "
            "the console did not rotate"
        )
    return (
        f"the rotated console drew a line running down the screen "
        f"({box_width} by {box_height} pixels, {lit} lit subpixels)"
    )


def check(path: Path) -> str:
    width, height, pixels = read_ppm(path)
    if height < (CJK_ROW + 1) * CELL_HEIGHT:
        raise CheckFailed(f"{path} is only {height} pixels tall")

    first = glyph(pixels, width, CJK_ROW, FIRST_COLUMN)
    second = glyph(pixels, width, CJK_ROW, FIRST_COLUMN + GLYPH_CELLS)

    if ink(first) == 0 or ink(second) == 0:
        raise CheckFailed("the CJK cells are blank; no glyph was drawn")
    if first == second:
        raise CheckFailed("two different CJK characters drew the same shape; the font is missing")
    return f"CJK glyphs differ and carry ink ({ink(first)} and {ink(second)} lit subpixels)"


if __name__ == "__main__":
    arguments = sys.argv[1:]
    rotated = "--rotated" in arguments
    if rotated:
        arguments.remove("--rotated")
    if len(arguments) != 1:
        raise SystemExit("usage: check-console.py [--rotated] <screenshot.ppm>")
    try:
        print((check_rotated if rotated else check)(Path(arguments[0])))
    except CheckFailed as error:
        raise SystemExit(f"console check failed: {error}")
