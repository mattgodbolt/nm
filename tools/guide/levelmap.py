#!/usr/bin/env python3
"""A level's whole 32 x 32 map, with the first view outlined, for
docs/how-it-works.md.

    .venv/bin/python tools/guide/levelmap.py [level] [out.png]

Drawn from the port's own data (src/data: the packed levels, the blocks,
the tiles' attributes) in the Spectrum's colours, as the original's set-up
leaves the map: monsters as their kind's first frame (in health 0's ink),
the start as player 1. The view is where the level starts (&C3CD: ten
characters up and left of the start, kept within the map), and inside it,
dashed, the area a player can walk in before the view slides
(players.md, "The view").
"""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import zx02  # noqa: E402

DATA = os.path.join(os.path.dirname(__file__), "..", "..", "src", "data")
ZX = [(0, 0, 0), (0, 0, 215), (215, 0, 0), (215, 0, 215),
      (0, 215, 0), (0, 215, 215), (215, 215, 0), (215, 215, 215)]
TILE = 16
VIEW_CHARS = 24          # the view is 24 x 24 characters
ORIGIN_MAX = 40          # ... so its origin is 0-40 in a 64-character map
WALK_LO, WALK_HI = 2, 20  # a player's view position kept within these


def level_map(n):
    raw = open(os.path.join(DATA, "levels.bin"), "rb").read()
    offs = []
    for line in open(os.path.join(DATA, "levels.6502")):
        if line.strip().startswith("EQUB LO(levels + "):
            offs.append(int(line.split("+")[1].rstrip(")\n ")))
    return zx02.decompress(raw[offs[n]:offs[n + 1]])


def block(blocks, b, ink, paper):
    img = Image.new("RGB", (16, 16), ZX[paper])
    px = img.load()
    for y in range(16):
        for half in range(2):
            byte = blocks[32 * b + 2 * y + half]
            for x in range(8):
                if byte & (0x80 >> x):
                    px[8 * half + x, y] = ZX[ink]
    return img


def main():
    level = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    out = sys.argv[2] if len(sys.argv) > 2 else "docs/images/level1-map.png"
    m = level_map(level)
    blocks = open(os.path.join(DATA, "blocks.bin"), "rb").read()
    attrs = bytearray(open(os.path.join(DATA, "tileattr.bin"), "rb").read())
    floor = ((level + 1) & 3) + 1            # &C357
    for t in (0x00, 0x16, 0x1E):
        attrs[t] = floor
    img = Image.new("RGB", (32 * TILE, 32 * TILE))
    start = None
    for i, code in enumerate(m):
        r, c = divmod(i, 32)
        if code == 0x7F:
            start = (r, c)
            b, a = 0x30, 0x45                # player 1, bright cyan
        elif 0x28 <= code <= 0x2F:
            b, a = 0x40 + (code & 7) * 16, 4  # a monster's first frame, health 0
        else:
            b, a = code, attrs[code]
        img.paste(block(blocks, b, a & 7, (a >> 3) & 7), (c * TILE, r * TILE))
    d = ImageDraw.Draw(img)
    # &C3CD: the origin, in characters, from the start's position
    orow = min(max(start[0] * 2 - 10, 0), ORIGIN_MAX)
    ocol = min(max(start[1] * 2 - 10, 0), ORIGIN_MAX)
    px = TILE // 2                           # a character's pixels
    x0, y0 = ocol * px, orow * px
    side = VIEW_CHARS * px
    d.rectangle([x0, y0, x0 + side - 1, y0 + side - 1], outline=(255, 255, 255), width=3)
    lo, hi = WALK_LO * px, (WALK_HI + 2) * px
    for x in range(x0 + lo, x0 + hi, 8):
        d.line([x, y0 + lo, min(x + 4, x0 + hi), y0 + lo], fill=(255, 255, 255))
        d.line([x, y0 + hi, min(x + 4, x0 + hi), y0 + hi], fill=(255, 255, 255))
    for y in range(y0 + lo, y0 + hi, 8):
        d.line([x0 + lo, y, x0 + lo, min(y + 4, y0 + hi)], fill=(255, 255, 255))
        d.line([x0 + hi, y, x0 + hi, min(y + 4, y0 + hi)], fill=(255, 255, 255))
    img.save(out)
    print(out, "start", start, "origin", (orow, ocol))


if __name__ == "__main__":
    main()
