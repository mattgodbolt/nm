"""The original's memory, from the snapshots `make zx` makes.

    from nmsnap import mem48, bank
    m = mem48()        # 64K: the 48K load (the game at &C000, before it runs)
    b1 = bank(1)       # a 128K RAM bank's 16K (bank 1: the music)
"""
from skoolkit.snapshot import Snapshot

SNAP48 = "build/nm48.z80"
SNAP128 = "build/nm128.z80"


def mem48(path=SNAP48):
    m = bytearray(0x10000)
    m[0x4000:] = bytes(Snapshot.get(path).ram(-1))
    return m


def bank(n, path=SNAP128):
    """A 128K RAM bank's 16K: snapshot.ram(n) gives &4000-&FFFF with bank n
    paged in at &C000."""
    return bytes(Snapshot.get(path).ram(n)[0x8000:])
