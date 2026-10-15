#!/usr/bin/env python3
"""Take the original's graphics and tables into src/data/.

    .venv/bin/python tools/mkgfx.py

From the 48K load (build/nm48.z80, make zx). They stay one bit a pixel, as
the original's are: the port colours them as it draws, as the original's
attributes do (docs/research.md).

- blocks.bin: the 192 graphics blocks at &DD00, 16 x 16, 32 bytes each,
  two bytes a pixel line, top line first (the drawer at &C5FC: block n at
  &DD00 + 32n)
- font.bin: the font at &F500, 8 bytes a character from code 32 (the
  print routine indexes it from &F400, 8 bytes a code)
- tileattr.bin: each tile type's attribute, &FF02 (40 bytes)
- passwords.bin: the 8 passwords at &FF62 (5 bytes each: the word, then
  the level it starts)
- titleattr.bin: the title's attributes, &FF8A: two rows of 10 (&C1A6)
- panel.zx02: the status panel, the loading screen's left 8 columns, which
  the game never draws but keeps: 192 pixel lines of 8 bytes, top first,
  then the 24 rows of 8 attributes; packed with ZX02 (decision 20: the
  game unpacks it once, at start-up)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import zx02

sys.path.insert(0, os.path.dirname(__file__))
from nmsnap import mem48

OUT = "src/data"


def main():
    m = mem48()
    os.makedirs(OUT, exist_ok=True)

    def write(name, data):
        with open(f"{OUT}/{name}", "wb") as f:
            f.write(bytes(data))
        print(f"{OUT}/{name}: {len(data)} bytes")

    write("blocks.bin", m[0xDD00:0xF500])
    write("font.bin", m[0xF500:0xF6EE - (0xF6EE - 0xF500) % 8])
    write("tileattr.bin", m[0xFF02:0xFF2A])
    write("passwords.bin", m[0xFF62:0xFF8A])
    write("titleattr.bin", m[0xFF8A:0xFF9E])
    panel = bytearray()
    for y in range(192):
        row = 0x4000 + ((y & 0xC0) << 5) + ((y & 7) << 8) + ((y & 0x38) << 2)
        panel += m[row:row + 8]
    for r in range(24):
        panel += m[0x5800 + 32 * r:0x5800 + 32 * r + 8]
    write("panel.zx02", zx02.compress(bytes(panel)))


if __name__ == "__main__":
    main()
