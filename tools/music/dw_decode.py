#!/usr/bin/env python3
"""Decode David Whittaker's Ninja Massacre music driver data into note events.

Rather than heuristically transcribing captured AY register dumps, this is a
faithful Python port of the actual Z80 driver (bank 1 @ 0xC000, reverse
engineered from the disassembly). It interprets the original song data byte
stream, so it recovers the *written* music: notes, durations, volume-envelope
instruments, arpeggio (chord) tables, vibrato/portamento parameters and drum
modes -- everything a notation program needs, with no guesswork.

Because it is a full port, it also renders the AY register frames the real
driver would produce.  --verify diffs those frame-by-frame against a captured
.psg file, proving the decode is correct at the register level.

Driver memory map (all addresses in the 64K image; bank 1 loads at 0xC000):
  c000/c003/c006/c009  jump table: init / tick / stop / sfx
  c069,c08a,c0ab       three 0x21-byte voice structs (see Voice)
  c0cc                 row countdown; c0f9 speed (self-modified operand)
  c125                 noise period (self-modified operand)
  c3a1                 global transpose (self-modified operand)
  c44a                 mixer template: the operand of "LD A,0x38" at c449,
                       self-modified by cmds 8a-8c (tone/noise per voice)
  c47f-c48a            shadow AY registers 0-11, written to the chip each tick
  c498                 note -> 12-bit period table (96 entries, note 0 = A#0)
  c558                 16 arpeggio table offsets; arp data = semitone steps,
                       bit 7 = last step + loop
  c575                 16 instrument pointers; byte before data = step time,
                       data = volume per step, bit 7 = sustain here
  c817                 song table: 7 x [speed, voice0 ptr, voice1, voice2]
  each voice ptr       list of pattern addresses, word 0 = loop to start
  pattern bytes        00-7f note  80-b7 command  b8-bf speed 1-8
                       c0-cf arpeggio  d0-df instrument  e0-ff duration 1-32

Voice struct offsets (IX+n):
  +0 flags: b1 alternate tone/noise (drum), b2 portamento on, b3 pitch slide,
            b5 envelope running, b7 slide direction up, b0 frame parity
  +1/2 stream ptr   +3/4 pattern list   +5/6 next list offset
  +7/8 portamento accumulator  +d/e portamento step/delay
  +f envelope step time  +10 rows left  +11 note duration  +12 note
  +13 current volume  +14/15 instrument ptr  +16/17 envelope pos
  +18 envelope volume  +19 envelope countdown  +1a/1b/1c vibrato
  depth/step/phase  +1d vibrato mode (0/40/c0)  +1e noise-pitch-from-note
  +1f hi-hat (one frame of period-1 noise per row)  +20 AY mixer mask

Stream commands (via offset table at c1b2):
  80 rest  81/82/83 vibrato off/on/on-alternate-frames  84 nn dd portamento
  85/86 pitch slide down/up (semitone per row)  87 end of pattern
  88 ss dd vibrato step/depth  89 tt global transpose  8a tone only
  8b noise only  8c tone+noise  8d drum (alternate tone/noise per frame)
  8e stop song  8f tie (extend note)  90/91 hi-hat on/off
"""

import argparse
import json
import sys

VOICE_BASE = [0xC069, 0xC08A, 0xC0AB]
NOTE_TABLE = 0xC498
ARP_TABLE = 0xC558
INST_TABLE = 0xC575
SONG_TABLE = 0xC817
CMD_BASE = 0xC1B2

NOTE_NAMES = ["A#", "B", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A"]


def note_name(n):
    """Driver note index -> name. Note 0 is A#0."""
    octave = (n + 10) // 12  # A#0 is two semitones below C1
    return f"{NOTE_NAMES[n % 12]}{octave}"


class Voice:
    """Accessor for one 0x21-byte voice struct inside the memory image."""

    def __init__(self, mem, base):
        self.mem = mem
        self.base = base

    def __getitem__(self, off):
        return self.mem[self.base + off]

    def __setitem__(self, off, val):
        self.mem[self.base + off] = val & 0xFF

    def get16(self, off):
        return self[off] | (self[off + 1] << 8)

    def set16(self, off, val):
        self[off], self[off + 1] = val & 0xFF, (val >> 8) & 0xFF


class Driver:
    """Python port of the Z80 music driver, tick-accurate."""

    def __init__(self, page4):
        self.mem = bytearray(65536)
        self.mem[0xC000:0xC000 + len(page4)] = page4
        self.voices = [Voice(self.mem, b) for b in VOICE_BASE]
        self.ay = [0] * 14      # the AY chip registers as last written
        self.playing = False
        self.row = 0            # musical row counter (for the event log)
        self.events = []        # decoded IR events
        self.mode_1e = [0, 0, 0]  # per-voice "notes drive noise pitch" flag
        self.drum_flag = [0, 0, 0]  # cmd 8d seen for the current note
        self.list_wraps = [0, 0, 0]

    def word(self, addr):
        return self.mem[addr] | (self.mem[addr + 1] << 8)

    # --- init (c00e) ---
    def init(self, song):
        entry = SONG_TABLE + 7 * song
        self.mem[0xC0F9] = self.mem[entry]          # speed
        for i, v in enumerate(self.voices):
            list_ptr = self.word(entry + 1 + 2 * i)
            v[0x10] = 1
            v[0x00] = 0
            v[0x1D] = 0
            v[0x1F] = 0
            v.set16(0x03, list_ptr)
            v.set16(0x01, self.word(list_ptr))
            v.set16(0x05, 2)
            self.events.append(dict(voice=i, row=0, type="pattern",
                                    addr=self.word(list_ptr)))
        self.mem[0xC3A1] = 0                        # transpose
        self.mem[0xC0CC] = 1                        # row countdown
        self.mem[0xC00C] = 1                        # music-on flag
        self.playing = True

    # --- stop (c19d): silences the chip directly, shadows are untouched ---
    def stop(self):
        self.playing = False
        self.mem[0xC00C] = 0
        self.ay = [0] * 14
        self.ay[7] = 0x3F                           # mixer: everything off
        for r in range(0xC487, 0xC48A):             # volume shadows only
            self.mem[r] = 0

    # --- row advance (c2ae) ---
    def row_advance(self, vi):
        v = self.voices[vi]
        v[0x10] -= 1
        if v[0x10] != 0:
            if v[0x00] & 0x08:                       # per-row pitch slide
                v[0x12] += 1 if v[0x00] & 0x80 else -1
            return

        v[0x00] = 0
        self.drum_flag[vi] = 0
        de = v.get16(0x01)
        porta = None

        while True:
            b = self.mem[de]
            de += 1
            if b < 0x80:                             # note
                v[0x12] = b
                if v[0x1E] & 1:
                    self.mem[0xC0D8] = b             # noise pitch source
                inst = v.get16(0x14)
                v.set16(0x16, inst)
                v[0x18] = v[0x13] = self.mem[inst]
                v[0x19] = v[0x0F]
                v[0x00] |= 0x20
                self.log_note(vi, b, porta)
                break
            if b >= 0xE0:                            # duration 1-32 rows
                v[0x11] = b - 0xE0 + 1
            elif b >= 0xD0:                          # instrument select
                ptr = self.word(INST_TABLE + 2 * (b - 0xD0))
                v.set16(0x14, ptr)
                v[0x0F] = self.mem[ptr - 1]
            elif b >= 0xC0:                          # arpeggio select
                tgt = ARP_TABLE + (b - 0xC0)
                tgt += self.mem[tgt]
                v.set16(0x09, tgt)
                v.set16(0x0B, tgt)
            elif b >= 0xB8:                          # speed 1-8
                self.mem[0xC0F9] = b - 0xB7
            elif b == 0x80:                          # rest
                v[0x13] = 0
                v[0x00] &= ~0x20
                self.events.append(dict(voice=vi, row=self.row, type="rest",
                                        dur=v[0x11]))
                break
            elif b == 0x8F:                          # tie
                v[0x00] |= 0x20
                self.events.append(dict(voice=vi, row=self.row, type="tie",
                                        dur=v[0x11]))
                break
            elif b == 0x81:
                v[0x1D] = 0
            elif b == 0x82:
                v[0x1D] = 0x40
            elif b == 0x83:
                v[0x1D] = 0xC0
            elif b == 0x84:                          # portamento
                v[0x0D] = self.mem[de]
                v[0x0E] = self.mem[de + 1]
                de += 2
                v.set16(0x07, 0)
                v[0x00] |= 0x04
                step = v[0x0D] - 256 if v[0x0D] & 0x80 else v[0x0D]
                porta = dict(step=step, delay=v[0x0E])
            elif b == 0x85:
                v[0x00] |= 0x08
            elif b == 0x86:
                v[0x00] |= 0x88
            elif b == 0x87:                          # end of pattern
                lst = v.get16(0x03)
                off = v.get16(0x05)
                ptr = self.word(lst + off)
                off += 2
                if ptr == 0:                         # end of list: loop
                    ptr = self.word(lst)
                    off = 2
                    self.list_wraps[vi] += 1
                v.set16(0x05, off)
                de = ptr
                self.events.append(dict(voice=vi, row=self.row,
                                        type="pattern", addr=ptr))
            elif b == 0x88:                          # vibrato params
                v[0x1B] = self.mem[de]
                v[0x1A] = v[0x1C] = self.mem[de + 1]
                de += 2
            elif b == 0x89:                          # global transpose
                self.mem[0xC3A1] = self.mem[de]
                de += 1
            elif b in (0x8A, 0x8B, 0x8C):
                # update the mixer template at c44a (never read back by the
                # driver, but modelled to keep RAM identical to the Z80):
                # 8a = tone only, 8b = noise only, 8c = tone+noise
                mask = v[0x20]
                bits = {0x8A: mask & 0x38, 0x8B: mask & 0x07, 0x8C: 0}[b]
                tmpl = self.mem[0xC44A]
                self.mem[0xC44A] = ((bits ^ tmpl) & mask) ^ tmpl
                v[0x1E] = 0 if b == 0x8A else 1
            elif b == 0x8D:
                v[0x00] |= 0x02                      # drum: alternate noise
                self.drum_flag[vi] = 1
            elif b == 0x8E:                          # stop song
                self.stop()
                self.events.append(dict(voice=vi, row=self.row, type="stop"))
                return
            elif b == 0x90:
                v[0x1F] = 0xFF                       # hi-hat on
            elif b == 0x91:
                v[0x1F] = 0
            else:
                raise ValueError(f"unknown command {b:02x} at {de-1:04x}")

        # finish row (c2eb)
        v[0x10] = v[0x11]
        v.set16(0x01, de)
        if v[0x1F]:
            v[0x1F] = 0xFF

    def log_note(self, vi, note, porta):
        v = self.voices[vi]
        ev = dict(voice=vi, row=self.row, type="note", note=note,
                  name=note_name(note), dur=v[0x11],
                  transpose=self.mem[0xC3A1])
        inst = v.get16(0x14)
        ev["inst"] = next((i for i in range(16)
                           if self.word(INST_TABLE + 2 * i) == inst), None)
        arp = v.get16(0x09)
        ev["arp"] = self.arp_id(arp)
        if v[0x1D]:
            ev["vib"] = dict(mode=v[0x1D], step=v[0x1B], depth=v[0x1A])
        if v[0x00] & 0x08:
            ev["slide"] = 1 if v[0x00] & 0x80 else -1
        if porta:
            ev["porta"] = porta
        if self.drum_flag[vi]:
            ev["drum"] = True
        if v[0x1E] & 1:
            ev["noise_pitched"] = True
        if v[0x1F]:
            ev["hihat"] = True
        self.events.append(ev)

    def arp_id(self, ptr):
        for i in range(16):
            tgt = ARP_TABLE + i + self.mem[ARP_TABLE + i]
            if tgt == ptr:
                return i
        return None

    def arp_steps(self, i):
        a = ARP_TABLE + i + self.mem[ARP_TABLE + i]
        steps = []
        while len(steps) < 16:
            b = self.mem[a]
            steps.append(b & 0x7F)
            if b & 0x80:
                break
            a += 1
        return steps

    # --- per-frame renderer (c36e) ---
    def render(self, vi):
        v = self.voices[vi]
        flags = v[0x00]

        if flags & 0x20:                             # volume envelope
            if v[0x19] == 0:
                v[0x19] = v[0x0F]
                pos = v.get16(0x16) + 1
                b = self.mem[pos]
                if not b & 0x80:                     # bit 7 = sustain here
                    v.set16(0x16, pos)
                    v[0x18] = b
            else:
                v[0x19] -= 1
            v[0x13] = v[0x18]

        note = (self.mem[0xC3A1] + v[0x12]) & 0xFF

        pos = v.get16(0x0B)                          # arpeggio walk
        b = self.mem[pos]
        pos += 1
        if b & 0x80:
            pos = v.get16(0x09)
            b &= 0x7F
        v.set16(0x0B, pos)
        note = (note + b) & 0xFF

        period = self.word(NOTE_TABLE + ((2 * note) & 0xFF))

        if v[0x1D] & 0x40:                           # vibrato
            span = (v[0x1A] << 1) & 0xFF
            phase = v[0x1C]
            if not (v[0x1D] & 0x80 and flags & 0x01):
                if not v[0x1D] & 0x20:               # bit 5 = direction
                    phase -= v[0x1B]
                    if phase < 0:
                        v[0x1D] |= 0x20
                        phase = 0
                else:
                    phase = (phase + v[0x1B]) & 0xFF
                    if phase >= span:
                        v[0x1D] &= ~0x20
                        phase = span
                v[0x1C] = phase & 0xFF
                phase = v[0x1C]
            offset = phase - (span >> 1)             # signed, triangle wave
            # scale by octave: the Z80 reuses the doubled table offset
            # (2*note) as the scaling counter, one doubling per 12 notes
            a = ((2 * note) & 0xFF) + 0xA0
            if a < 0x100:
                while True:
                    offset <<= 1
                    a += 0x18
                    if a >= 0x100:
                        break
            period = (period + offset) & 0xFFFF

        v[0x00] = flags ^ 0x01                       # frame parity

        if flags & 0x04:                             # portamento
            if v[0x0E] - 1 == 0:
                step = v[0x0D] - 256 if v[0x0D] & 0x80 else v[0x0D]
                acc = (v.get16(0x07) + step) & 0xFFFF
                v.set16(0x07, acc)
                period = (period + acc) & 0xFFFF
            else:
                v[0x0E] -= 1

        # tone/noise select. Default is the mixer template at c44a -- the
        # self-modified operand of "LD A,0x38" at c449, patched by commands
        # 8a/8b/8c. Drum notes (cmd 8d) override with noise-only on alternate
        # frames, flipping bit 3 of the noise period for a two-timbre rattle.
        if flags & 0x02 and not flags & 0x01:
            self.mem[0xC125] = self.mem[0xC0D8] ^ 0x08
            mix = 0x07                               # noise on, tone off
        else:
            mix = self.mem[0xC44A]
        mask = v[0x20]
        self.mem[0xC486] = ((mix ^ self.mem[0xC486]) & mask) ^ self.mem[0xC486]

        if v[0x1F] & 0x80:                           # hi-hat: 1-frame noise
            v[0x1F] &= 0x7F
            self.mem[0xC486] &= ~(mask & 0x38) & 0xFF
            self.mem[0xC125] = 0x41

        return period, v[0x13]

    # --- SFX noise PRNG (c7f8), music-inaudible but keeps RAM identical ---
    def prng(self):
        a = (self.mem[0xC813] & 0x48) + 0x38
        carry = 0
        for _ in range(2):
            carry, a = a >> 7, (a << 1) & 0xFF
        for addr in (0xC816, 0xC815, 0xC814, 0xC813):
            old = self.mem[addr]
            self.mem[addr] = ((old << 1) | carry) & 0xFF
            carry = old >> 7

    # --- tick (c0cd) ---
    def tick(self):
        self.prng()
        if not self.playing:
            return
        # c0d7: reload noise period from the current noise note (the LD A,n
        # operand at c0d8 is self-modified whenever a noise-mode note plays)
        self.mem[0xC125] = self.mem[0xC0D8]
        self.mem[0xC0CC] -= 1
        if self.mem[0xC0CC] == 0:
            for vi in range(3):
                self.row_advance(vi)
                if not self.playing:
                    return
            self.mem[0xC0CC] = self.mem[0xC0F9]
            self.row += 1
        for vi in range(3):
            period, vol = self.render(vi)
            self.mem[0xC47F + 2 * vi] = period & 0xFF
            self.mem[0xC480 + 2 * vi] = (period >> 8) & 0xFF
            self.mem[0xC487 + vi] = vol
        self.mem[0xC485] = self.mem[0xC125]
        for r in range(12):                          # OUTD loop at c161
            self.ay[r] = self.mem[0xC47F + r]

    def frame(self):
        """Current AY registers 0-13 as the capture records them."""
        return list(self.ay)


def parse_psg(path):
    data = open(path, "rb").read()
    assert data[:4] == b"PSG\x1a"
    pos, regs, frames = 16, [0] * 14, []
    while pos < len(data):
        b = data[pos]
        if b == 0xFF:
            frames.append(list(regs))
            pos += 1
        else:
            regs[b] = data[pos + 1]
            pos += 2
    return frames


def verify(drv, psg_path, nframes):
    captured = parse_psg(psg_path)[:nframes]
    mismatches = 0
    first = None
    for i, want in enumerate(captured):
        drv.tick()
        got = drv.frame()
        if got != want:
            mismatches += 1
            if first is None:
                first = (i, want, got)
    total = len(captured)
    print(f"{psg_path}: {total - mismatches}/{total} frames match "
          f"({100 * (total - mismatches) / total:.2f}%)")
    if first:
        i, want, got = first
        print(f"  first mismatch frame {i}:")
        print(f"    want {[f'{x:02x}' for x in want]}")
        print(f"    got  {[f'{x:02x}' for x in got]}")
    return mismatches == 0


def main():
    ap = argparse.ArgumentParser(description="Decode/verify the NM music driver")
    ap.add_argument("--page", default="page_4.bin")
    ap.add_argument("--song", type=int, default=0)
    ap.add_argument("--frames", type=int, default=3500)
    ap.add_argument("--verify", metavar="PSG",
                    help="diff rendered AY frames against a captured .psg")
    ap.add_argument("--ir", metavar="JSON", help="write decoded events as JSON")
    ap.add_argument("--dump", action="store_true",
                    help="print decoded events as text")
    args = ap.parse_args()

    drv = Driver(open(args.page, "rb").read())
    drv.init(args.song)

    if args.verify:
        ok = verify(drv, args.verify, args.frames)
    else:
        for _ in range(args.frames):
            drv.tick()
        ok = True

    if args.dump:
        for ev in drv.events:
            print(ev)

    if args.ir:
        meta = dict(song=args.song, speed=drv.mem[0xC0F9],
                    arps={i: drv.arp_steps(i) for i in range(7)},
                    list_wraps=drv.list_wraps)
        with open(args.ir, "w") as f:
            json.dump(dict(meta=meta, events=drv.events), f, indent=1)
        print(f"wrote {args.ir} ({len(drv.events)} events, "
              f"{drv.row} rows, wraps={drv.list_wraps})")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
