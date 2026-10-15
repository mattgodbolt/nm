#!/usr/bin/env python3
"""The music's data, from the 128K's bank 1, for the port's driver.

    .venv/bin/python tools/mkmusic.py

David Whittaker's driver and its songs live in bank 1 at &C000
(tools/music/dw_decode.py, docs/research/music-driver.md). The port runs
a 6502 transcription of the driver (src/music.6502) on the original's
song data, so this takes the data the driver reads:

- the song table (&C817): each song's speed and its voices' pattern lists
- the pattern lists: pattern addresses, a 0 word to loop back to the start
- the patterns: notes and commands
- the instruments (&C575's pointers): a step time, then volumes to one
  with bit 7 set
- the arpeggios (&C558's offsets): semitone steps to one with bit 7 set
- the note table (&C498): a period for each note

It finds them by playing each song with dw_decode.py's Driver and noting
every byte it reads, until the song stops or every voice has gone round
its list twice. A walk of the bytes alone can't say where to stop: the
jingles' voices have no end of their own, their patterns running on into
the next song's lists, and the song stops (&8E) on one voice before the
others get there.

It writes src/data/music.6502 as baron source, every pointer a label, so
the assembler places it. The tables the driver indexes (notes,
arpeggios, instruments) are split into low and high bytes for the 6502;
the rest keeps the original's order and bytes.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "music"))
from nmsnap import bank
import dw_decode as dw

OUT = "src/data/music.6502"
SONGS = 7
NOTES = 96             # the note table's entries (&C498-&C557)
TABLES = 16            # entries in the arpeggio and instrument tables
SONG_BYTES = 7         # a song: its speed, then three list pointers
LOOPS = 2              # times round its list each voice of a looping song plays
MAX_FRAMES = 100000    # a song that neither stops nor loops by then is an error


def word(m, a):
    return m[a] | (m[a + 1] << 8)


def is_variable(a):
    """The driver's own variables in bank 1, which the port keeps in its
    workspace instead (src/music.6502), and the sound effects' random
    numbers (&C813-&C816), which the music doesn't use."""
    return (0xC069 <= a < 0xC0CD or a in (0xC00C, 0xC00D, 0xC0CC, 0xC0D8, 0xC0F9, 0xC125, 0xC3A1, 0xC44A)
            or 0xC47F <= a <= 0xC48A or 0xC813 <= a <= 0xC816)


class Reads(bytearray):
    """The driver's memory, noting each address it reads a byte from."""

    def __init__(self, *a):
        super().__init__(*a)
        self.read = set()
        self.table_reads = set()   # the arpeggio table's entries the row advance reads
        self.quiet = False
        self.in_row = False

    def __getitem__(self, i):
        if isinstance(i, int) and not self.quiet:
            if self.in_row and dw.ARP_TABLE <= i < dw.ARP_TABLE + TABLES:
                self.table_reads.add(i)
            else:
                self.read.add(i)
        return super().__getitem__(i)


class Tracker(dw.Driver):
    """dw_decode.py's Driver, noting what it reads: bytes, pointer words,
    and which instruments and arpeggios it picks."""

    def __init__(self, b1):
        super().__init__(b1)
        self.mem = Reads(self.mem)
        self.voices = [dw.Voice(self.mem, vb) for vb in dw.VOICE_BASE]
        self.words = {}            # address of a pointer word -> its value
        self.insts = set()
        self.arps = set()
        self.top_note = 0
        self.max_offset = 0

    def word(self, addr):
        self.mem.quiet = True
        v = super().word(addr)
        self.mem.quiet = False
        if dw.INST_TABLE <= addr < dw.INST_TABLE + 2 * TABLES:
            self.insts.add((addr - dw.INST_TABLE) // 2)
        elif not dw.NOTE_TABLE <= addr < dw.NOTE_TABLE + 2 * NOTES:
            self.words[addr] = v
        return v

    def log_note(self, vi, note, porta):
        # (dw_decode's event log reads every table entry: none of that here.)
        v = self.voices[vi]
        self.mem.quiet = True
        if v.get16(0x14) == 0 or v.get16(0x09) == 0:
            raise SystemExit(f"voice {vi} plays a note before choosing an instrument and an arpeggio")
        self.mem.quiet = False

    def row_advance(self, vi):
        # (Only the row advance reads the arpeggio table, whose last
        # entries are the first arpeggio's steps.)
        self.mem.in_row = True
        super().row_advance(vi)
        self.mem.in_row = False
        self.max_offset = max(self.max_offset, self.voices[vi].get16(0x05))

    def render(self, vi):
        self.mem.quiet = True
        v = self.voices[vi]
        step = self.mem[v.get16(0x0B)]
        note = (self.mem[0xC3A1] + v[0x12] + (step & 0x7F)) & 0x7F
        self.top_note = max(self.top_note, note)
        self.mem.quiet = False
        return super().render(vi)


def play_all(b1):
    """Each song from the bank's starting state, until it stops or loops.
    Returns the merged reads."""
    kinds, words, insts, arps = {}, {}, set(), set()
    top = offset = 0
    for s in range(SONGS):
        d = Tracker(b1)
        d.init(s)
        frames = 0
        while d.playing and min(d.list_wraps) < LOOPS:
            d.tick()
            frames += 1
            if frames > MAX_FRAMES:
                raise SystemExit(f"song {s} neither stops nor loops")
        arps |= {a - dw.ARP_TABLE for a in d.mem.table_reads}    # (the port's own table)
        for a in d.mem.read:
            if a >= 0xC000 and not is_variable(a) and not dw.NOTE_TABLE <= a < dw.NOTE_TABLE + 2 * NOTES:
                kinds[a] = "b"
        words.update(d.words)
        insts |= d.insts
        top = max(top, d.top_note)
        offset = max(offset, d.max_offset)
    return kinds, words, insts, arps, top, offset


def emit(m, kinds, words, insts, arps, notes):
    labels = {}

    def label(addr, name):
        labels.setdefault(addr, [])
        if name not in labels[addr]:
            labels[addr].append(name)

    song_end = dw.SONG_TABLE + SONG_BYTES * SONGS
    label(dw.SONG_TABLE, "mu_songs")
    for at, target in words.items():
        if dw.SONG_TABLE <= at < song_end:
            label(target, f"mu_list_{target:04X}")
        elif target:
            label(target, f"mu_pat_{target:04X}")
        for a, k in ((at, "w"), (at + 1, "w+")):
            if kinds.get(a, k) not in (k, "b"):
                raise SystemExit(f"&{a:04X} is both a byte and part of a pointer")
            kinds[a] = k
    for i in insts:
        at = word(m, dw.INST_TABLE + 2 * i)
        label(at, f"mu_inst_{i}")
        # src/music.6502's mu_render counts an envelope's frames down from
        # its step time and takes a negative count as past 0.
        if m[at - 1] >= 0x80:
            raise SystemExit(f"instrument {i}'s step time &{m[at - 1]:02X} is past &7F")
    for i in arps:
        label(dw.ARP_TABLE + i + m[dw.ARP_TABLE + i], f"mu_arp_{i}")
    for a, names in labels.items():
        if a not in kinds or kinds[a] == "w+":
            raise SystemExit(f"{names} at &{a:04X} isn't the start of something read")

    out = []
    w = out.append
    w("\\ Ninja Massacre's music: David Whittaker's song data from the 128K's")
    w("\\ bank 1, for src/music.6502's transcription of his driver. Made by")
    w("\\ tools/mkmusic.py from build/nm128.z80: don't edit it by hand.")
    w("\\ docs/research/music-driver.md describes the format. Each label")
    w("\\ ending in an address names the original's address of what it labels.")
    w("")
    w("\\ The note table (&C498): each note's AY tone period, low then high")
    w("\\ bytes, as far up as the songs go.")
    periods = [word(m, dw.NOTE_TABLE + 2 * i) for i in range(notes)]
    for part, f in (("lo", "LO"), ("hi", "HI")):
        w(f".mu_periods_{part}")
        for i in range(0, notes, 8):
            w("    EQUB " + ", ".join(f"{f}({p})" for p in periods[i:i + 8]))
    w(f"MU_NOTES = {notes}")
    w("")
    for name, used, what in (("arp", arps, "arpeggio, for C0-CF in a pattern (the offsets at &C558)"),
                             ("inst", insts, "instrument, for D0-DF in a pattern (the pointers at &C575)")):
        w(f"\\ Each {what},")
        w("\\ low then high bytes. Those no song uses are 0.")
        top = max(used) + 1
        for part, f in (("lo", "LO"), ("hi", "HI")):
            w(f".mu_{name}_{part}")
            w("    EQUB " + ", ".join(f"{f}(mu_{name}_{i})" if i in used else "0" for i in range(top)))
        w(f"MU_{name.upper()}S = {top}")
        w("")
    w("\\ The rest as the original keeps it, in its order: the song table, the")
    w("\\ pattern lists, the patterns, the instruments (each a step time, then")
    w("\\ volumes) and the arpeggios; only the bytes the songs read.")

    line = []

    def flush():
        if line:
            w("    EQUB " + ", ".join(line))
            line.clear()

    prev = None
    for a in sorted(kinds):
        k = kinds[a]
        if prev is None or a != prev + 1:
            flush()
            w(f"\\ &{a:04X}")
        prev = a
        for name in labels.get(a, []):
            flush()
            w(f".{name}")
        if k == "b":
            if len(line) == 12:
                flush()
            line.append(f"&{m[a]:02X}")
        elif k == "w":
            flush()
            t = words[a]
            w(f"    EQUW {labels[t][0] if t else 0}")
    flush()
    return "\n".join(out) + "\n", len(kinds)


def main():
    b1 = bank(1)
    m = bytearray(0x10000)
    m[0xC000:] = b1
    # The driver's starting state that the port sets up (music_init): the
    # voices all zeros but for their mixer masks.
    for vb in dw.VOICE_BASE:
        if any(m[vb:vb + 0x20]):
            raise SystemExit(f"voice at &{vb:04X} doesn't start as zeros")
    # src/music.6502's mu_pattern goes back to a list's start on a 0
    # without looking again: a list starting with one would never end.
    for s in range(SONGS):
        for v in range(3):
            at = word(m, dw.SONG_TABLE + SONG_BYTES * s + 1 + 2 * v)
            if word(m, at) == 0:
                raise SystemExit(f"song {s}'s voice {v}: its list (&{at:04X}) starts with a 0")
    kinds, words, insts, arps, top, offset = play_all(b1)
    if top >= NOTES:
        raise SystemExit(f"note {top} is past the note table")
    # src/music.6502 keeps a voice's place in its list in a byte.
    if offset > 0xFF:
        raise SystemExit(f"a pattern list is longer than a byte's offset: {offset}")
    text, nbytes = emit(m, kinds, words, insts, arps, top + 1)
    with open(OUT, "w") as f:
        f.write(text)
    print(f"{OUT}: {nbytes} bytes of songs from the bank, {len(insts)} instruments, "
          f"{len(arps)} arpeggios, notes up to {top}")


if __name__ == "__main__":
    main()
