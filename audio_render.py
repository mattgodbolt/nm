#!/usr/bin/env python3
"""Render the Ninja Massacre music to WAV, two ways, for A/B comparison:

  --chip   the exact AY-3-8910 register frames from the decoded driver
           (a miniature AY emulator: tone squares, LFSR noise, log DAC)
  --score  the notation as written: equal-tempered square waves, straight
           rows, block chords, simple noise drums -- no vibrato/portamento

If the transcription is faithful, both should be recognisably the same tune;
the difference is performance (chip effects) versus the written page.
"""

import argparse
import wave

import numpy as np

from dw_decode import Driver
from score_gen import MIDI_BASE, decode_song

AY_CLOCK = 1_773_400
FRAME_HZ = 50
RATE = 44100
SPF = RATE // FRAME_HZ  # samples per frame

# AY DAC is roughly -3dB per volume step
DAC = np.array([0.0] + [2 ** ((v - 15) / 2) for v in range(1, 16)])


def ay_render(frames):
    """Tiny AY emulator over 50Hz register frames."""
    n = len(frames) * SPF
    out = np.zeros(n)
    phase = [0.0, 0.0, 0.0]
    nphase, lfsr, nbit = 0.0, 1, 1.0
    rng = np.random.default_rng(1)
    for fi, f in enumerate(frames):
        sl = slice(fi * SPF, (fi + 1) * SPF)
        t = np.arange(SPF)
        mixer = f[7]
        # noise: one shared channel, approximated as random square wave
        nper = max(1, f[6] & 0x1F)
        nfreq = AY_CLOCK / 16 / nper
        steps = (nphase + nfreq * (t + 1) / RATE).astype(int)
        nphase += nfreq * SPF / RATE
        noise_seq = rng.choice([1.0, -1.0], size=steps.max() + 1)
        noise = noise_seq[steps]
        for ch in range(3):
            per = (f[2 * ch] | ((f[2 * ch + 1] & 0x0F) << 8))
            vol = DAC[f[8 + ch] & 0x0F]
            if vol == 0:
                continue
            tone_on = not (mixer >> ch) & 1
            noise_on = not (mixer >> (ch + 3)) & 1
            sig = np.ones(SPF)
            if tone_on and per > 0:
                freq = AY_CLOCK / 16 / per
                ph = phase[ch] + freq * t / RATE
                sig = sig * np.where((ph % 1) < 0.5, 1.0, -1.0)
                phase[ch] = (phase[ch] + freq * SPF / RATE) % 1
            if noise_on:
                sig = sig * noise
            if tone_on or noise_on:
                out[sl] += vol * sig
    return out / 3


def square(freq, nsamp, amp):
    t = np.arange(nsamp)
    env = np.minimum(1, np.linspace(1.2, 0.25, nsamp))  # gentle decay
    return amp * env * np.sign(np.sin(2 * np.pi * freq * t / RATE) + 1e-9)


def midi_freq(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def drum_burst(kind, nsamp):
    rng = np.random.default_rng(kind)
    env = np.exp(-np.linspace(0, 8, nsamp))
    noise = rng.choice([1.0, -1.0], size=nsamp)
    if kind >= 42:  # hi-hat: short bright tick
        env = np.exp(-np.linspace(0, 30, nsamp))
        return 0.35 * env * noise
    # lower GM note = deeper drum: hold noise samples longer
    hold = max(1, (50 - kind) // 4)
    deep = np.repeat(noise[:nsamp // hold + 1], hold)[:nsamp]
    return 0.5 * env * deep


def score_render(drv, hihat_rows, row_seconds):
    from score_gen import DRUM_MAP, DEFAULT_DRUM, TONE_PERC
    arps = {i: drv.arp_steps(i) for i in range(16)}
    total_rows = drv.row + 2
    n = int(total_rows * row_seconds * RATE)
    out = np.zeros(n + RATE)
    for ev in drv.events:
        if ev["type"] != "note":
            continue
        start = int(ev["row"] * row_seconds * RATE)
        nsamp = int(ev["dur"] * row_seconds * RATE)
        if ev.get("drum"):
            gm = DRUM_MAP.get((ev["note"], ev["inst"]), DEFAULT_DRUM)[0]
            sig = drum_burst(gm, nsamp)
        elif (ev["note"], ev["inst"]) in TONE_PERC:
            # tone-channel percussion (the C#6 clicks): a tick, not a pitch
            sig = drum_burst(TONE_PERC[(ev["note"], ev["inst"])][0], nsamp)
        else:
            base = MIDI_BASE + ev["note"] + ev["transpose"]
            steps = arps.get(ev["arp"], [0]) if ev["arp"] is not None else [0]
            midis = sorted({base + s for s in steps})
            sig = sum(square(midi_freq(m), nsamp, 0.28 / len(midis) ** 0.5)
                      for m in midis)
        out[start:start + nsamp] += sig
    hh = int(0.06 * RATE)
    for row in hihat_rows:
        start = int(row * row_seconds * RATE)
        out[start:start + hh] += drum_burst(42, hh)
    return out


def write_wav(path, sig):
    sig = sig / max(1e-9, np.abs(sig).max()) * 0.85
    data = (sig * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data.tobytes())
    print(f"wrote {path} ({len(sig)/RATE:.1f}s)")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--song", type=int, default=0)
    ap.add_argument("--chip", action="store_true")
    ap.add_argument("--score", action="store_true")
    args = ap.parse_args()

    if args.chip:
        drv = Driver(open("page_4.bin", "rb").read())
        drv.init(args.song)
        frames = []
        for _ in range(20000):
            drv.tick()
            frames.append(drv.frame())
            if not drv.playing:
                break
        write_wav(f"ninja_song{args.song}_chip.wav", ay_render(frames))

    if args.score:
        drv, hihat_rows = decode_song(args.song)
        speed = drv.mem[0xC0F9]
        write_wav(f"ninja_song{args.song}_score.wav",
                  score_render(drv, hihat_rows, speed / FRAME_HZ))


if __name__ == "__main__":
    main()
