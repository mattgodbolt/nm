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


def floor_ink(level):
    return ((level + 1) & 3) + 1        # &C357: level from 0


def logical(colour, floor):
    """src/colour.6502's mapping of a Spectrum colour (decision 5)."""
    if colour == 0:
        return 0
    if colour == 6:
        return 1
    if colour == floor:
        return 2
    return 3


def zx_pixel(scr, x, y):
    row = ((y & 0xC0) << 5) + ((y & 7) << 8) + ((y & 0x38) << 2)
    bit = scr[row + x // 8] & (0x80 >> (x & 7))
    attr = scr[0x1800 + (y // 8) * 32 + x // 8]
    return bool(bit), (attr & 7) if bit else (attr >> 3) & 7


def bbc_pixel(scr, x, y):
    b = scr[(y // 8) * 512 + (x // 4) * 8 + (y & 7)]
    i = x & 3
    return ((b >> (7 - i)) & 1) << 1 | ((b >> (3 - i)) & 1)


def screen_diffs(z, b, level):
    """Pixels that differ: the playfield (columns 8-31) in the port's
    colours; the panel (0-7) by shape, lit or not (its pictures and the
    figures printed on it map colours differently: decision 5)."""
    zs, bs, attrs = bytes.fromhex(z["scr"]), bytes.fromhex(b["scr"]), bytes.fromhex(b["attrs"])
    floor = floor_ink(level)
    out = []
    for y in range(192):
        for x in range(256):
            lit, colour = zx_pixel(zs, x, y)
            got = bbc_pixel(bs, x, y)
            if x >= 64:
                want = logical(colour, floor)
                if got != want:
                    out.append((x, y, want, got))
            else:
                # the panel's own colours (src/panel.6502's panel_ink):
                # black as 0, yellow as 1, the rest as 3
                paper = (attrs[(y // 8) * 32 + x // 8] >> 3) & 7
                unlit = 0 if paper == 0 else 1 if paper == 6 else 3
                if lit != (got != unlit):
                    out.append((x, y, int(lit), got))
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
        if "end" in z or "end" in b:
            if "end" not in z or "end" not in b:
                bad += 1
                print(f"pass {z['pass']}: {'the original' if 'end' in z else 'the port'}'s game ended, the other's didn't")
            break
        diffs = []
        for block, base in BASES.items():
            zb, bb = bytes.fromhex(z[block]), bytes.fromhex(b[block])
            for i, (x, y) in enumerate(zip(zb, bb)):
                name, off = names[base + i]
                if x != y and name not in ignore:
                    diffs.append(f"{name}{'+%d' % off if off else ''} (&{base + i:04X}): {x:02x} vs {y:02x}")
        if "rng" in z and "rng" in b and z["rng"] != b["rng"] and "rng" not in ignore:
            diffs.append(f"the random generator: {z['rng']:02x} vs {b['rng']:02x}")
        zm, bm = bytes.fromhex(z["map"]), bytes.fromhex(b["map"])
        cells = [i for i in range(1024) if zm[i] != bm[i]]
        if cells and "map" not in ignore:
            diffs.append("map: " + ", ".join(f"({i // 32},{i % 32}) {zm[i]:02x} vs {bm[i]:02x}" for i in cells[:8])
                         + (f" and {len(cells) - 8} more" if len(cells) > 8 else ""))
        if "scr" in z and "scr" in b:
            level = bytes.fromhex(z["ba"])[0xBA74 - 0xBA29]
            sd = screen_diffs(z, b, level)
            if sd and "screen" not in ignore:
                x, y, w, g = sd[0]
                diffs.append(f"screen: {len(sd)} pixels differ, the first at ({x},{y}): {w} vs {g}")
        if diffs:
            bad += 1
            if bad == 1 or "--all" in sys.argv:
                print(f"pass {z['pass']} differs (original vs port):")
                for d in diffs:
                    print("   ", d)
            if "--all" not in sys.argv:
                break
    n = min(len(zx), len(bbc))
    if not bad and len(zx) != len(bbc):
        bad += 1
        print(f"the logs differ in length: {len(zx)} and {len(bbc)}")
    if not bad:
        ended = " (then both games ended)" if zx and "end" in zx[-1] else ""
        print(f"{n - (1 if ended else 0)} passes match{ended}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
