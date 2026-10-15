#!/usr/bin/env python3
"""The 50 levels: decode them as the original's &C418 does, and pack them.

    .venv/bin/python tools/mklevels.py [--stats]

The original keeps the levels one after another from &5B20, each run-length
packed, with a pointer (&FF5E) that moves on as each is decoded
(docs/research.md). decode() is &C418 transcribed, for the checks and the
measurements; the port runs its own transcription on the same bytes.

Writes src/data/levels.bin (decision 4): each level as &C418 leaves it
(the 32 x 32 map, walls and all, before &C39C's pass), packed with ZX02,
one after another; and src/data/levels.6502, a table of where each
starts. The port unpacks a level straight into its map.
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
        b = buf[0x20 + i]
        buf[i] = 5 if b == 0x11 or 1 <= b <= 5 else 4
    return buf, de


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
    packed = [zx02.compress(bytes(buf)) for _, buf in lv]
    for (_, buf), z in zip(lv, packed):
        assert zx02.decompress(z) == bytes(buf)
    if "--stats" in sys.argv:
        print(f"levels &{FIRST:04X}-&{end - 1:04X}: {end - FIRST} bytes")
        raws = [zx02.compress(raw) for raw, _ in lv]
        print(f"the original's bytes, each ZX02-packed: {sum(map(len, raws))} bytes")
        print(f"decoded maps, each ZX02-packed: {sum(map(len, packed))} bytes")
        print(f"largest level: {max(len(r) for r, _ in lv)} raw, {max(map(len, packed))} packed")
    os.makedirs("src/data", exist_ok=True)
    with open("src/data/levels.bin", "wb") as f:
        for z in packed:
            f.write(z)
    with open("src/data/levels.6502", "w") as f:
        f.write("\\ The levels' offsets into levels.bin, low then high bytes,\n")
        f.write("\\ and one past the last (tools/mklevels.py).\n")
        offs = [0]
        for z in packed:
            offs.append(offs[-1] + len(z))
        f.write(".level_lo\n")
        for o in offs:
            f.write(f"    EQUB LO(levels + {o})\n")
        f.write(".level_hi\n")
        for o in offs:
            f.write(f"    EQUB HI(levels + {o})\n")
    print(f"src/data/levels.bin: {sum(map(len, packed))} bytes")


if __name__ == "__main__":
    main()
