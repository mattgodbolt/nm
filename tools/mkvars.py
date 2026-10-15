#!/usr/bin/env python3
"""The original's variables, as the port keeps them.

    .venv/bin/python tools/mkvars.py

The original keeps its variables at &BA29-&BA9F and &FF2A-&FF61, some of
them tables it reads (the star's picture, the floor's quarter, the stars'
directions), and reaches a player's by offset from its record. The port
keeps both blocks in the same layout, starting with the tape's own bytes
(decision 10), and names each address by its label in disasm/*.ctl.

Writes src/data/vars_ba.bin and vars_ff.bin (the tape's bytes) and
src/data/vars.6502 (each label as an offset into its block).
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from nmsnap import mem48

BLOCKS = [("vars_ba", 0xBA29, 0xBAA0), ("vars_ff", 0xFF2A, 0xFF62)]


def main():
    m = mem48()
    labels = {}
    for path in sorted(glob.glob("disasm/*.ctl")):
        for line in open(path):
            mo = re.match(r"@ \$([0-9A-F]{4}) label=(\w+)", line)
            if mo:
                labels[int(mo.group(1), 16)] = mo.group(2)
    out = ["\\ The original's variables (tools/mkvars.py, decision 10): each",
           "\\ label from disasm/*.ctl, at its offset in the port's copy of the block.", ""]
    for name, start, end in BLOCKS:
        with open(f"src/data/{name}.bin", "wb") as f:
            f.write(bytes(m[start:end]))
        out.append(f"\\ &{start:04X}-&{end - 1:04X}: {name}")
        for addr in sorted(a for a in labels if start <= a < end):
            out.append(f"{labels[addr]} = {name} + &{addr - start:02X}   ; &{addr:04X}")
        out.append("")
    with open("src/data/vars.6502", "w") as f:
        f.write("\n".join(out))
    print(f"src/data/vars.6502: {sum(1 for a in labels if any(s <= a < e for _, s, e in BLOCKS))} labels")


if __name__ == "__main__":
    main()
