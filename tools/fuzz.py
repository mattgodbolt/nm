#!/usr/bin/env python3
"""Random scenarios, played on the original and the port and compared.

    python3 tools/fuzz.py [count] [--seed n] [--passes n]

Each scenario starts on a random level, with one or two players, and holds
random keys over random stretches of passes; some give player 1 scrolls
first (the original's &BA5A), so the smart bomb goes off. They're written
to build/fuzz/scenarios.txt and run by tools/passcheck.sh, as make passes
runs tests/scenarios.txt. A scenario that differs can be copied into
tests/scenarios.txt as it is.
"""
import argparse
import os
import random
import subprocess
import sys

P1 = ["up", "down", "left", "right", "fire"]
P2 = ["p2up", "p2down", "p2left", "p2right", "p2fire"]
SCROLLS = 0xBA5A


def scenario(rng, n, passes):
    two = rng.random() < 0.3
    keys = []
    for names in (P1, P2) if two else (P1,):
        at = rng.randrange(5)
        while at < passes:
            length = rng.randrange(5, 80)
            held = rng.sample(names, rng.choice([1, 1, 1, 2]))
            for k in held:
                keys.append(f"{k}:{at}-{min(at + length, passes - 1)}")
            at += length + rng.randrange(0, 20)
    flags = [f"--level {rng.randrange(1, 51)}"]
    if two:
        flags.append("--two")
    if rng.random() < 0.2:
        flags.append(f"--poke 1:{SCROLLS:#x}:3")
        at = rng.randrange(10, passes - 10)
        keys.append(f"magic:{at}")
    return f"fuzz{n} | {','.join(keys)} | {passes} | {' '.join(flags)}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("count", nargs="?", type=int, default=8)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--passes", type=int, default=300)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    os.makedirs("build/fuzz", exist_ok=True)
    path = "build/fuzz/scenarios.txt"
    with open(path, "w") as f:
        f.write(f"# tools/fuzz.py --seed {args.seed}\n")
        for n in range(args.count):
            f.write(scenario(rng, n, args.passes) + "\n")
    env = dict(os.environ, SCENARIOS=path, PASSDIR="build/fuzz/passes")
    return subprocess.call(["tools/passcheck.sh"], env=env)


if __name__ == "__main__":
    sys.exit(main())
