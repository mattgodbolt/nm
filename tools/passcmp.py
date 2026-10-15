#!/usr/bin/env python3
"""Compare two pass logs (tools/passlog.py's and tools/passlog.mjs's).

    python3 tools/passcmp.py zx.json bbc.json [--ignore name,...] [--all]

Each pass's variables (the original's two blocks) and map are compared
byte for byte, and the first pass that differs is reported with the
variables (by their labels, src/data/vars.6502) and map cells that do.
Exits non-zero if any pass differs.

Always ignored: LevelPtr (the original's pointer into its level data; the
port finds a level by its number, decision 4).
"""
import re
import sys

BASES = {"ba": 0xBA29, "ff": 0xFF2A}
IGNORE = {"LevelPtr"}


def labels():
    """address -> (name, offset in it) for every byte of the blocks."""
    named = []
    for line in open("src/data/vars.6502"):
        m = re.match(r"(\w+) = vars_(ba|ff) \+ &([0-9A-F]+)", line)
        if m:
            named.append((BASES[m.group(2)] + int(m.group(3), 16), m.group(1)))
    named.sort()
    out = {}
    for block, base in BASES.items():
        end = base + (0x77 if block == "ba" else 0x38)
        for a in range(base, end):
            prev = [(addr, n) for addr, n in named if addr <= a]
            out[a] = (prev[-1][1], a - prev[-1][0]) if prev else (f"&{a:04X}", 0)
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ignore = set(IGNORE)
    if "--ignore" in sys.argv:
        ignore |= set(sys.argv[sys.argv.index("--ignore") + 1].split(","))
        args = [a for a in args if a != sys.argv[sys.argv.index("--ignore") + 1]]
    zx, bbc = (__import__("json").load(open(p)) for p in args[:2])
    names = labels()
    bad = 0
    for z, b in zip(zx, bbc):
        diffs = []
        for block, base in BASES.items():
            zb, bb = bytes.fromhex(z[block]), bytes.fromhex(b[block])
            for i, (x, y) in enumerate(zip(zb, bb)):
                name, off = names[base + i]
                if x != y and name not in ignore:
                    diffs.append(f"{name}{'+%d' % off if off else ''} (&{base + i:04X}): {x:02x} vs {y:02x}")
        zm, bm = bytes.fromhex(z["map"]), bytes.fromhex(b["map"])
        cells = [i for i in range(1024) if zm[i] != bm[i]]
        if cells and "map" not in ignore:
            diffs.append("map: " + ", ".join(f"({i // 32},{i % 32}) {zm[i]:02x} vs {bm[i]:02x}" for i in cells[:8])
                         + (f" and {len(cells) - 8} more" if len(cells) > 8 else ""))
        if diffs:
            bad += 1
            if bad == 1 or "--all" in sys.argv:
                print(f"pass {z['pass']} differs (original vs port):")
                for d in diffs:
                    print("   ", d)
            if "--all" not in sys.argv:
                break
    n = min(len(zx), len(bbc))
    if not bad:
        print(f"{n} passes match")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
