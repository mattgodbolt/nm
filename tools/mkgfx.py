#!/usr/bin/env python3
"""Take the original's graphics and tables into src/data/.

    .venv/bin/python tools/mkgfx.py

From the 48K load (build/nm48.z80, make zx). They stay one bit a pixel, as
the original's are: the port colours them as it draws, as the original's
attributes do (docs/research.md).

- blocks.bin: the 192 graphics blocks at &DD00, 16 x 16, 32 bytes each
  (the drawer at &C5FC: block n at &DD00 + 32n). The original's are two
  bytes a pixel line, top line first; here each block is four 8 x 8
  quarters, and the file is four planes of quarters, eight bytes (lines)
  each in block order: the top left quarters, then the top right, the
  bottom left and the bottom right. So a block's quarters are the same
  distance apart, and one index reads a line of each (view.6502's
  draw_block_at)
- font.bin: the font at &F500, 8 bytes a character from code 32 (the
  print routine indexes it from &F400, 8 bytes a code) to Z, the last the
  game prints (the font's last two, [ and \\, are blank)
- tileattr.bin: each tile type's attribute, &FF02 (40 bytes)
- passwords.bin: the 8 passwords at &FF62 (5 bytes each: the word, then
  the level it starts)
- titleattr.bin: the title's attributes, &FF8A: two rows of 10 (&C1A6)
- panel.zx02: the status panel, the loading screen's left 8 columns, which
  the game never draws but keeps: the 24 rows of 8 attributes, then each
  character cell's 8 pixel lines, top first, a row of cells at a time (as
  panel.6502's draw_panel reads them; and ZX02 packs cells smaller than
  pixel lines); packed with ZX02 (decision 20: the game unpacks it once,
  at start-up)
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

    blocks = bytearray()
    for half in (0, 16):
        for side in (0, 1):
            for n in range(192):
                block = m[0xDD00 + 32 * n:0xDD00 + 32 * n + 32]
                blocks += bytes(block[half + 2 * line + side] for line in range(8))
    write("blocks.bin", blocks)
    write("font.bin", m[0xF500:0xF500 + 8 * (ord("Z") + 1 - 32)])
    write("tileattr.bin", m[0xFF02:0xFF2A])
    write("passwords.bin", m[0xFF62:0xFF8A])
    write("titleattr.bin", m[0xFF8A:0xFF9E])
    panel = bytearray()
    for r in range(24):
        panel += m[0x5800 + 32 * r:0x5800 + 32 * r + 8]
    for r in range(24):
        for c in range(8):
            for line in range(8):
                y = r * 8 + line
                panel.append(m[0x4000 + ((y & 0xC0) << 5) + ((y & 7) << 8) + ((y & 0x38) << 2) + c])
    write("panel.zx02", zx02.compress(bytes(panel)))


if __name__ == "__main__":
    main()
