#!/usr/bin/env python3
"""Compare each level's first view, the BBC's with the original's.

    python3 tools/viewcmp.py [--png]

build/views/bbc_NN.bin (tools/viewcheck.mjs) against zx_NN.scr
(tools/zxviews.py), over the playfield (the screen's columns 8-31). Each
of the original's pixels is its cell's ink if set, else its paper; the
BBC's must be the logical colour the port gives that colour in that level
(src/colour.6502, decision 5): black 0, yellow 1, the floor's colour 2,
any other 3. --png writes build/views/diff_NN.png where they differ.
"""
import sys

LEVELS = 50
SCREEN = 0x5000


def floor_ink(n):
    return (n & 3) + 1             # level n (1-50): &C357, ((n - 1) + 1) AND 3, plus 1


def logical(ink, floor):
    if ink == 0:
        return 0
    if ink == 6:
        return 1
    if ink == floor:
        return 2
    return 3


def zx_pixel(scr, x, y):
    row = ((y & 0xC0) << 5) + ((y & 7) << 8) + ((y & 0x38) << 2)
    bit = scr[row + x // 8] & (0x80 >> (x & 7))
    attr = scr[0x1800 + (y // 8) * 32 + x // 8]
    return (attr & 7) if bit else (attr >> 3) & 7


def bbc_pixel(scr, x, y):
    addr = (y // 8) * 512 + (x // 4) * 8 + (y & 7)
    b = scr[addr]
    i = x & 3
    return ((b >> (7 - i)) & 1) << 1 | ((b >> (3 - i)) & 1)


def main():
    bad = 0
    for n in range(1, LEVELS + 1):
        zx = open(f"build/views/zx_{n:02d}.scr", "rb").read()
        bbc = open(f"build/views/bbc_{n:02d}.bin", "rb").read()
        floor = floor_ink(n)
        diffs = []
        for y in range(192):
            for x in range(64, 256):
                want = logical(zx_pixel(zx, x, y), floor)
                got = bbc_pixel(bbc, x, y)
                if want != got:
                    diffs.append((x, y, want, got))
        if diffs:
            bad += 1
            x, y, w, g = diffs[0]
            print(f"level {n}: {len(diffs)} pixels differ (first at {x},{y}: want {w}, got {g})")
            if "--png" in sys.argv:
                from PIL import Image
                im = Image.new("RGB", (256, 192))
                for x, y, w, g in diffs:
                    im.putpixel((x, y), (255, 0, 0))
                im.resize((512, 384)).save(f"build/views/diff_{n:02d}.png")
    print(f"{LEVELS - bad} of {LEVELS} levels' views match the original's")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
