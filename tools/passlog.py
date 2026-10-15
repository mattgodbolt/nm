#!/usr/bin/env python3
"""Play the original pass by pass and log its state each pass.

    .venv/bin/python tools/passlog.py '<inputs>' passes [--out build/zx_passes.json] [--level n] [--two]

The BBC counterpart is tools/passlog.mjs; tools/passcmp.py compares the
two. <inputs> holds keys over ranges of main-loop passes (inclusive),
comma separated: `right:10-40,fire:45,up:50-60`. Names: up down left right
fire magic for player 1, and p2up p2down p2left p2right p2fire p2magic.
Pass 0 is the first time the main loop (&C014) is reached after the game
starts; keys are set at the top of a pass, before the original reads them.

The game starts as the menu's 1 (or 2 with --two) starts it, at level 1
(or --level n: the level's set-up, &C34F, is made level n, as
tools/zxviews.py does), with the random generator shared and seeded
(tools/zx.py's share_random, decision 7).

--screens N also logs the screen (6,912 bytes) every N passes and on the
last, for tools/passcmp.py to compare with the port's.

Each pass logs the original's variables (&BA29-&BA9F and &FF2A-&FF61, the
blocks the port keeps in the same layout: decision 10) and the map
(&BC00, 1K), as hex.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import zx  # noqa: E402
from mklevels import FIRST, LEVELS, decode  # noqa: E402
from nmsnap import SNAP48, mem48  # noqa: E402
from skoolkit.simutils import A  # noqa: E402

MAIN_LOOP = 0xC014
LEVEL_SETUP = 0xC34F
SEED = 1
KEYS = {"up": "Q", "down": "A", "left": "O", "right": "P", "fire": "SPACE", "magic": "ENTER",
        "p2up": "9", "p2down": "8", "p2left": "6", "p2right": "7", "p2fire": "0", "p2magic": "CAPS"}
BLOCKS = {"ba": (0xBA29, 0xBAA0), "ff": (0xFF2A, 0xFF62), "map": (0xBC00, 0xC000)}


def parse_inputs(spec):
    out = []
    for part in filter(None, spec.split(",")):
        name, _, rng = part.partition(":")
        a, _, b = rng.partition("-")
        out.append((KEYS[name], int(a), int(b or a)))
    return out


def state(m, n):
    s = {"pass": n}
    for name, (a, b) in BLOCKS.items():
        s[name] = "".join(f"{m[i]:02x}" for i in range(a, b))
    return s


def level_start(n):
    m = mem48()
    de = FIRST
    for _ in range(n - 1):
        de = decode(m, de)[1]
    return de


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs")
    ap.add_argument("passes", type=int)
    ap.add_argument("--out", default="build/zx_passes.json")
    ap.add_argument("--level", type=int, default=1)
    ap.add_argument("--two", action="store_true")
    ap.add_argument("--screens", type=int, default=0,
                    help="every N passes (and the last), log the screen too")
    args = ap.parse_args()
    inputs = parse_inputs(args.inputs)

    spec = zx.Spectrum(SNAP48)
    zx.share_random(spec, SEED)
    menu_key = "2" if args.two else "1"
    zx.run_script(spec, f"3,SPACE:tap,2,{menu_key}:down", "build/x_")
    pc = spec.run_tstates(30 * 50 * spec.frame, stop=LEVEL_SETUP)
    assert pc == LEVEL_SETUP, "no level set-up"
    spec.key(menu_key, False)
    if args.level != 1:
        spec.sim.registers[A] = args.level - 1
        de = level_start(args.level)
        spec.mem[0xFF5E], spec.mem[0xFF5F] = de & 0xFF, de >> 8
    spec.mem[zx.RNG_STATE] = SEED

    log = []
    for n in range(args.passes):
        pc = spec.run_tstates(60 * 50 * spec.frame, stop=MAIN_LOOP)
        assert pc == MAIN_LOOP, f"pass {n}: the main loop wasn't reached"
        for key, a, b in inputs:
            spec.key(key, False)
        for key, a, b in inputs:
            if a <= n <= b:
                spec.key(key, True)
        log.append(state(spec.mem, n))
        if args.screens and (n % args.screens == 0 or n == args.passes - 1):
            log[-1]["scr"] = "".join(f"{spec.mem[a]:02x}" for a in range(0x4000, 0x5B00))
        spec.run_tstates(1)          # off the breakpoint
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(log, f)
    print(f"{args.out}: {len(log)} passes")


if __name__ == "__main__":
    main()
