#!/usr/bin/env python3
"""Check tools/mklevels.py's decode() against the original's own decoder.

    .venv/bin/python tools/levelcheck.py

Runs &C418 in the original (build/nm48.z80) for each of the 50 levels in
turn, as the game does, and compares the map it leaves at &BC00, and where
its pointer (&FF5E) ends, with decode()'s.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import zx
from mklevels import BUF, FIRST, LEVELS, decode
from nmsnap import SNAP48, mem48
from skoolkit.simutils import PC, SP

STOP = 0x0000        # a return address the game never runs: the ROM's start


def call(spec, addr):
    regs = spec.sim.registers
    regs[SP] = (regs[SP] - 2) & 0xFFFF
    spec.mem[regs[SP]] = STOP & 0xFF
    spec.mem[(regs[SP] + 1) & 0xFFFF] = STOP >> 8
    regs[PC] = addr
    pc = spec.run_tstates(10 ** 8, stop=STOP)
    assert pc == STOP, f"&{addr:04X} didn't return"


def main():
    spec = zx.Spectrum(SNAP48)
    spec.sim.registers[SP] = 0xFF00
    m = mem48()
    de = FIRST
    spec.mem[0xFF5E] = FIRST & 0xFF
    spec.mem[0xFF5F] = FIRST >> 8
    bad = 0
    for n in range(LEVELS):
        call(spec, 0xC418)
        got = bytes(spec.mem[BUF:BUF + 1024])
        want, de = decode(m, de)
        ptr = spec.mem[0xFF5E] | spec.mem[0xFF5F] << 8
        if got != bytes(want) or ptr != de:
            bad += 1
            print(f"level {n + 1}: differs (pointer &{ptr:04X}, decode() &{de:04X})")
    print(f"{LEVELS - bad} of {LEVELS} levels decode as the original's &C418 does")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
