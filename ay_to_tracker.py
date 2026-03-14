#!/usr/bin/env python3
"""Convert AY register captures to a tracker-style format.

Reads the 14-byte-per-frame .raw files from ay_capture.py and converts
to a simplified tracker representation, identifying notes, instruments,
and patterns suitable for conversion to BBC Micro SN76489.
"""

import struct
import sys
import math

# AY-3-8910 clock on Spectrum 128K
AY_CLOCK = 1773400

# SN76489 clock on BBC Micro
SN_CLOCK = 4000000

# Standard note frequency table (A4 = 440Hz)
NOTE_NAMES = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']


def ay_period_to_freq(period):
    """Convert AY tone period to frequency in Hz."""
    if period == 0:
        return 0
    return AY_CLOCK / (16 * period)


def freq_to_note(freq):
    """Convert frequency to closest MIDI note number and name."""
    if freq <= 0:
        return None, "---"
    # MIDI note: A4 = 69 = 440Hz
    midi = 69 + 12 * math.log2(freq / 440.0)
    midi_rounded = round(midi)
    if midi_rounded < 0 or midi_rounded > 127:
        return None, "---"
    octave = (midi_rounded // 12) - 1
    note = midi_rounded % 12
    cents_off = round((midi - midi_rounded) * 100)
    name = f"{NOTE_NAMES[note]}{octave}"
    if abs(cents_off) > 5:
        name += f"({cents_off:+d}c)"
    return midi_rounded, name


def freq_to_sn_period(freq):
    """Convert frequency to SN76489 tone period."""
    if freq <= 0:
        return 0
    period = round(SN_CLOCK / (32 * freq))
    return max(1, min(1023, period))  # SN76489 has 10-bit period


def ay_vol_to_sn_atten(ay_vol):
    """Convert AY volume (0-15, 0=silent) to SN76489 attenuation (0-15, 15=silent).

    AY: 0=silent, 15=loudest (roughly 2dB per step)
    SN: 0=loudest, 15=silent (2dB per step)
    """
    if ay_vol == 0:
        return 15
    return 15 - ay_vol


def detect_loop_point(frames, min_loop=48, max_check=None):
    """Try to detect where the music loops by looking for repeated sequences."""
    if max_check is None:
        max_check = len(frames) // 2

    # Compare beginning of song with later portions
    for start in range(min_loop, max_check):
        match_len = 0
        for i in range(min(200, len(frames) - start)):
            if frames[i] == frames[start + i]:
                match_len += 1
            else:
                break
        if match_len >= 48:  # At least ~1 second of matching
            return start
    return len(frames)


def analyze_song(raw_file, song_num=0):
    """Analyze a raw AY register dump and convert to tracker format."""
    with open(raw_file, "rb") as f:
        data = f.read()

    num_frames = len(data) // 14
    frames = []
    for i in range(num_frames):
        regs = list(data[i*14:(i+1)*14])
        frames.append(regs)

    print(f"\n{'='*70}")
    print(f"Song {song_num} - {num_frames} frames ({num_frames/50:.1f}s)")
    print(f"{'='*70}")

    # Find loop point
    loop_point = detect_loop_point(frames)
    if loop_point < num_frames:
        print(f"Loop detected at frame {loop_point} ({loop_point/50:.1f}s)")
        frames = frames[:loop_point]
        num_frames = len(frames)

    # Convert to tracker rows
    # The music engine runs at 50Hz but advances notes every N ticks (speed)
    # We'll detect note changes to figure out the effective row rate

    rows = []
    for fr in frames:
        tone_a = fr[0] | ((fr[1] & 0x0F) << 8)
        tone_b = fr[2] | ((fr[3] & 0x0F) << 8)
        tone_c = fr[4] | ((fr[5] & 0x0F) << 8)
        noise = fr[6] & 0x1F
        mixer = fr[7]
        vol_a = fr[8] & 0x0F  # Ignore envelope bit for now
        vol_b = fr[9] & 0x0F
        vol_c = fr[10] & 0x0F
        env_a = fr[8] & 0x10
        env_b = fr[9] & 0x10
        env_c = fr[10] & 0x10

        freq_a = ay_period_to_freq(tone_a) if not (mixer & 0x01) else 0
        freq_b = ay_period_to_freq(tone_b) if not (mixer & 0x02) else 0
        freq_c = ay_period_to_freq(tone_c) if not (mixer & 0x04) else 0

        noise_a = not (mixer & 0x08)
        noise_b = not (mixer & 0x10)
        noise_c = not (mixer & 0x20)

        rows.append({
            'freq_a': freq_a, 'freq_b': freq_b, 'freq_c': freq_c,
            'vol_a': vol_a, 'vol_b': vol_b, 'vol_c': vol_c,
            'noise': noise, 'noise_a': noise_a, 'noise_b': noise_b, 'noise_c': noise_c,
            'tone_a': tone_a, 'tone_b': tone_b, 'tone_c': tone_c,
            'env_a': env_a, 'env_b': env_b, 'env_c': env_c,
        })

    # Output tracker-style display (every tick, since effects change per-tick)
    # But also identify "note events" (significant pitch changes)

    print(f"\nTracker output ({num_frames} rows at 50Hz):")
    print(f"{'Row':>5} {'Ch1':>10} {'V1':>3} {'Ch2':>10} {'V2':>3} {'Ch3':>10} {'V3':>3} {'Noise':>5}")
    print("-" * 60)

    prev_note = [None, None, None]
    note_events = []

    for i, row in enumerate(rows):
        freqs = [row['freq_a'], row['freq_b'], row['freq_c']]
        vols = [row['vol_a'], row['vol_b'], row['vol_c']]
        notes = []
        is_event = False

        for ch in range(3):
            midi, name = freq_to_note(freqs[ch])
            notes.append(name)
            if midi != prev_note[ch] and vols[ch] > 0:
                is_event = True
            prev_note[ch] = midi

        if is_event or i < 5 or i % 50 == 0:
            noise_str = ""
            if row['noise_a'] or row['noise_b'] or row['noise_c']:
                noise_str = f"N{row['noise']:02d}"
            print(f"{i:5d} {notes[0]:>10} {vols[0]:3d} {notes[1]:>10} {vols[1]:3d} {notes[2]:>10} {vols[2]:3d} {noise_str:>5}")
            if is_event:
                note_events.append(i)

    # Compute SN76489 conversion for the note events
    print(f"\n\nSN76489 Conversion Summary:")
    print(f"{'Row':>5} {'Ch1 Note':>10} {'SN Per':>7} {'Ch2 Note':>10} {'SN Per':>7} {'Ch3 Note':>10} {'SN Per':>7}")
    print("-" * 65)

    for i in note_events[:50]:
        row = rows[i]
        freqs = [row['freq_a'], row['freq_b'], row['freq_c']]
        parts = []
        for ch in range(3):
            _, name = freq_to_note(freqs[ch])
            sn_per = freq_to_sn_period(freqs[ch])
            parts.append(f"{name:>10} {sn_per:7d}")
        print(f"{i:5d} {'  '.join(parts)}")

    return frames, rows, note_events


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Convert AY captures to tracker format")
    parser.add_argument("--song", type=int, default=None, help="Song number (default: all)")
    args = parser.parse_args()

    songs = [args.song] if args.song is not None else range(7)

    for song in songs:
        raw_file = f"song_{song}.raw"
        try:
            analyze_song(raw_file, song)
        except FileNotFoundError:
            print(f"Song {song}: {raw_file} not found, skipping")


if __name__ == "__main__":
    main()
