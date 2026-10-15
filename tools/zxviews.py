#!/usr/bin/env python3
"""The oracle for the view: each level's first view, drawn by the original.

    .venv/bin/python tools/zxviews.py [levels...]

For each level (1-50; all by default): from the tape's 128K snapshot,
start a one-player game (a key, then 1), stop where the level is set up (&C34F, with A the
level, 0-49), make it this level (A, and the level pointer &FF5E at its
bytes), share the port's random generator (seeded 1, as the port's view
check seeds it), and run until the view is drawn (&C54C's RET, &C573).
Saves the Spectrum's screen (6,912 bytes) to build/views/zx_NN.scr.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import zx
from mklevels import FIRST, LEVELS, decode
from nmsnap import SNAP128, mem48
from skoolkit.simutils import A

LEVEL_SETUP = 0xC34F
VIEW_DRAWN = 0xC573
SEED = 1


def main():
    levels = [int(a) for a in sys.argv[1:]] or range(1, LEVELS + 1)
    m = mem48()
    starts = [FIRST]
    for _ in range(LEVELS):
        starts.append(decode(m, starts[-1])[1])
    os.makedirs("build/views", exist_ok=True)
    for n in levels:
        spec = zx.Spectrum(SNAP128)
        zx.share_random(spec, SEED)
        zx.run_script(spec, "3,SPACE:tap,2,1:down", "build/x_")
        pc = spec.run_tstates(30 * 50 * spec.frame, stop=LEVEL_SETUP)
        assert pc == LEVEL_SETUP, "no level set-up"
        spec.key("1", False)
        spec.sim.registers[A] = n - 1
        spec.mem[0xFF5E] = starts[n - 1] & 0xFF
        spec.mem[0xFF5F] = starts[n - 1] >> 8
        spec.mem[zx.RNG_STATE] = SEED
        pc = spec.run_tstates(30 * 50 * spec.frame, stop=VIEW_DRAWN)
        assert pc == VIEW_DRAWN, f"level {n}: the view wasn't drawn"
        with open(f"build/views/zx_{n:02d}.scr", "wb") as f:
            f.write(bytes(spec.mem[a] for a in range(0x4000, 0x5B00)))
    print(f"build/views: {len(levels)} views")


if __name__ == "__main__":
    main()
