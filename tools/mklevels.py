#!/usr/bin/env python3
"""The 50 levels: decode them as the original's &C418 does, and pack them.

    .venv/bin/python tools/mklevels.py [--stats]

The original keeps the levels one after another from &5B20, each run-length
packed, with a pointer (&FF5E) that moves on as each is decoded
(docs/research.md). decode() is &C418 transcribed, for the checks and the
measurements; the port runs its own transcription on the same bytes.

Writes src/data/levels.bin (decision 4): each level as &C418 leaves it
(the 32 x 32 map before &C39C's pass), packed with ZX02, one after
another; and src/data/levels.6502, a table of where each starts. Only the
interior is kept (rows and columns 1-30), a column at a time, top to
bottom, or a row at a time where that packs smaller (as it does for a
few: most pack smaller by columns), which the table's high byte marks
with LEVEL_BY_ROWS. The walls around it are the same in every level
(expand()). The port unpacks a level into its map, turns columns into
rows and puts the walls round it (level.6502's level_load), as expand()
does.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from nmsnap import mem48
import zx02

LEVELS = 50
FIRST = 0x5B20       # the first level's bytes (the pointer &FF5E's start)
BUF = 0xBC00         # the level being played, 32 x 32


def decode(m, de):
    """&C418: the level at DE into a 32 x 32 map. Returns (map, next DE).
    Before &C39C's pass, which sets the decorations from R."""
    buf = bytearray(1024)
    hl = 0x20
    buf[hl] = 5
    hl += 1

    def advance(hl):                 # &C474 (and &C480 at a row's end)
        hl += 1
        if hl & 0x1F == 0x1F:
            buf[hl] = 5
            buf[hl + 1] = 5
            hl += 2
        return hl

    while True:
        a = m[de]
        if a & 0x80:                 # &C462: a run of a & &7F
            c = a & 0x7F
            de += 1
            n = m[de] or 0xFF        # a count of 0 is DEC'd to &FF
            for _ in range(n):
                buf[hl] = c
                hl = advance(hl)
            a = c                    # ... and &C428 writes one more
        buf[hl] = a
        de += 1
        hl = advance(hl)
        if hl == 0x3E1:
            break
    for i in range(0x3E0, 0x400):    # the bottom wall
        buf[i] = 4
    for i in range(32):              # the top wall: 5 over tiles &11 and 1-5
        buf[i] = top_wall(buf[0x20 + i])
    return buf, de


SIDE = 30            # the interior's rows and columns: the map less its walls
WALL_SIDE = 5        # the left and right walls' tile
WALL_BOTTOM = 4      # the bottom wall's


def top_wall(b):
    """&C418's top wall over the tile b below it."""
    return 5 if b == 0x11 or 1 <= b <= 5 else 4


LEVEL_BY_ROWS = 0x40  # in a level's high byte: packed a row at a time (level.6502's)


def interior(buf, by_rows=False):
    """A level's map as it is packed: its interior, a column at a time
    (or a row at a time)."""
    if by_rows:
        return bytes(buf[(r + 1) * 32 + c + 1] for r in range(SIDE) for c in range(SIDE))
    return bytes(buf[(r + 1) * 32 + c + 1] for c in range(SIDE) for r in range(SIDE))


def expand(inner, by_rows=False):
    """The map from interior(map, by_rows): what level_load does."""
    buf = bytearray(1024)
    for r in range(SIDE):
        row = (r + 1) * 32
        buf[row] = buf[row + 31] = WALL_SIDE
        for c in range(SIDE):
            buf[row + c + 1] = inner[r * SIDE + c] if by_rows else inner[c * SIDE + r]
    for i in range(32):
        buf[0x3E0 + i] = WALL_BOTTOM
        buf[i] = top_wall(buf[0x20 + i])
    return bytes(buf)


def levels(m):
    out = []
    de = FIRST
    for _ in range(LEVELS):
        buf, end = decode(m, de)
        out.append((bytes(m[de:end]), buf))
        de = end
    return out, de


def main():
    m = mem48()
    lv, end = levels(m)
    packed = []                      # (by rows, the packed bytes) for each
    by_cols = 0
    for _, buf in lv:
        ways = []
        for by_rows in (False, True):
            inner = interior(buf, by_rows)
            assert expand(inner, by_rows) == bytes(buf)
            z = zx02.compress(inner)
            assert zx02.decompress(z) == inner
            ways.append((len(z), by_rows, z))
        by_cols += ways[0][0]
        packed.append(min(ways)[1:])
    if "--stats" in sys.argv:
        print(f"levels &{FIRST:04X}-&{end - 1:04X}: {end - FIRST} bytes")
        raws = [zx02.compress(raw) for raw, _ in lv]
        print(f"the original's bytes, each ZX02-packed: {sum(map(len, raws))} bytes")
        whole = [zx02.compress(bytes(buf)) for _, buf in lv]
        print(f"decoded maps, each ZX02-packed: {sum(map(len, whole))} bytes")
        print(f"their interiors by columns, each ZX02-packed: {by_cols} bytes")
        print(f"... or by rows where smaller ({sum(r for r, _ in packed)} levels): "
              f"{sum(len(z) for _, z in packed)} bytes")
        print(f"largest level: {max(len(r) for r, _ in lv)} raw, {max(len(z) for _, z in packed)} packed")
    os.makedirs("src/data", exist_ok=True)
    with open("src/data/levels.bin", "wb") as f:
        for _, z in packed:
            f.write(z)
    with open("src/data/levels.6502", "w") as f:
        f.write("\\ Where each level starts in levels.bin, low then high bytes; the\n")
        f.write("\\ high byte has LEVEL_BY_ROWS if it's packed a row at a time\n")
        f.write("\\ (tools/mklevels.py).\n")
        offs = []
        o = 0
        for by_rows, z in packed:
            offs.append((o, by_rows))
            o += len(z)
        f.write(".level_lo\n")
        for o, _ in offs:
            f.write(f"    EQUB LO(levels + {o})\n")
        f.write(".level_hi\n")
        for o, by_rows in offs:
            f.write(f"    EQUB HI(levels + {o})" + (" OR LEVEL_BY_ROWS" if by_rows else "") + "\n")
    print(f"src/data/levels.bin: {sum(len(z) for _, z in packed)} bytes")


if __name__ == "__main__":
    main()
