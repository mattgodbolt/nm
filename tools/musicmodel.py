#!/usr/bin/env python3
"""What the port's music should do, for tools/musiccheck.mjs.

    .venv/bin/python tools/musicmodel.py > build/music/model.json

Plays the songs on tools/music/dw_decode.py's Driver (the original's
driver in Python, from build/nm128.z80's bank 1) in the order and for the
frames the music check's build (startup.6502's music_check) plays them on
one driver: song 0, then each next song started after a whole number of
MC_FRAMES chunks, enough for each song's capture (music/song_N.psg). For
each frame: the shadow AY registers (&C47F-&C48A) and whether a song is
playing. Then what src/music.6502's mu_output writes to the SN76489 for
those frames, from a model of its conversion here.

First it checks the Driver against the captures, each song from the
bank's state, as they were made (tools/music/build.sh).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "music"))
from nmsnap import bank
import dw_decode as dw

SONGS = 7
MC_FRAMES = 48          # startup.6502's records a chunk
SHADOW = 0xC47F         # the shadow AY registers 0-11
AY_REGS = 12

# src/music.6502's conversion (decisions 15-18), for the bytes it writes.
ATT = [0 if v == 15 else 15 - (v + (v & 1)) for v in range(16)]
SILENT = 15
NOISE_WHITE = 0xE4
NOISE_SLOW = 19
SN_PERIODS = 1024
BASS_PER_PERIOD = 4     # bass.6502's: a bass half-cycle's microseconds per SN period


def sn_period(p):
    """An AY period (12 bits) as the SN's, the octaves it went up, and
    the period before it did."""
    s = p + ((p * 131 + 512) >> 10)
    if s == 0:
        s = 1
    whole = s
    octaves = 0
    while s >= SN_PERIODS:
        s >>= 1
        octaves += 1
    return s, octaves, whole


class SN:
    """mu_output: the chip's registers as last written, and the bytes
    each frame writes; and the bass's half-cycles (bass.6502), 0 for a
    channel that isn't playing bass."""

    def __init__(self):
        self.tone = [None] * 3
        self.att = [None] * 4
        self.noise = None
        self.half = [0] * 3

    def frame(self, ay, on):
        out = []
        for c in range(3):
            att = SILENT
            bass = False
            if on:
                s, octaves, whole = sn_period(ay[2 * c] | ((ay[2 * c + 1] & 15) << 8))
                if not ay[7] & (1 << c):
                    att = ATT[ay[8 + c] & 15]
                if octaves and att != SILENT:
                    # bass: the tone at period 1, its volume switched by a timer
                    bass = True
                    s = 1
                if s != self.tone[c]:
                    self.tone[c] = s
                    out += [0x80 | (c << 5) | (s & 15), s >> 4]
            if bass:
                if not self.half[c]:
                    out.append(0x90 | (c << 5) | att)      # heard first
                self.half[c] = BASS_PER_PERIOD * whole
                self.att[c] = None                          # the edges' meanwhile
                continue
            self.half[c] = 0
            if att != self.att[c]:
                self.att[c] = att
                out.append(0x90 | (c << 5) | att)
        att = SILENT
        if on and ay[6] & 31:
            loudest = 0
            for c in range(3):
                if not ay[7] & (8 << c):
                    loudest = max(loudest, ay[8 + c] & 15)
            att = ATT[loudest]
            if att != SILENT:
                noise = NOISE_WHITE | (1 if ay[6] & 31 >= NOISE_SLOW else 0)
                if noise != self.noise:
                    self.noise = noise
                    out.append(noise)
        if att != self.att[3]:
            self.att[3] = att
            out.append(0xF0 | att)
        return out


def captures():
    return [dw.parse_psg(os.path.join(HERE, "..", "music", f"song_{s}.psg")) for s in range(SONGS)]


def check_captures(b1, caps):
    for s, cap in enumerate(caps):
        d = dw.Driver(b1)
        d.init(s)
        for i, want in enumerate(cap):
            d.tick()
            if d.frame() != want:
                raise SystemExit(f"dw_decode.py's song {s} differs from its capture at frame {i}")


def main():
    b1 = bank(1)
    caps = captures()
    check_captures(b1, caps)
    d = dw.Driver(b1)
    sn = SN()
    songs = []
    writes = []
    for s in range(SONGS):
        d.init(s)
        chunks = -(-len(caps[s]) // MC_FRAMES)
        records = []
        for _ in range(chunks * MC_FRAMES):
            d.tick()
            ay = list(d.mem[SHADOW:SHADOW + AY_REGS])
            on = int(d.playing)
            writes += sn.frame(ay, on)
            halves = [h & 255 for h in sn.half] + [h >> 8 for h in sn.half]
            records.append(ay + [on] + halves)
        songs.append(dict(song=s, captured=len(caps[s]), chunks=chunks, records=records))
    json.dump(dict(mc_frames=MC_FRAMES, songs=songs, sn=writes), sys.stdout)


if __name__ == "__main__":
    main()
