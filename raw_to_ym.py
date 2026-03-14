#!/usr/bin/env python3
"""Convert raw AY register dumps (.raw) to YM6 format for use with ym2sn.py.

YM6 format: header with clock/rate info, then 16 * num_frames bytes interleaved,
followed by title/author/comment strings and "LeOnArD!" end marker.
"""

import os
import sys
import glob
import struct


AY_CLOCK = 1773400  # Spectrum 128K AY clock


def raw_to_ym(raw_file, ym_file, title="", author=""):
    """Convert a 14-bytes-per-frame raw file to YM6 format."""
    with open(raw_file, "rb") as f:
        data = f.read()

    num_frames = len(data) // 14
    if num_frames == 0:
        print(f"  {raw_file}: no frames, skipping")
        return False

    # Strip trailing silent frames
    last_active = num_frames - 1
    while last_active > 0:
        offset = last_active * 14
        regs = data[offset:offset + 14]
        vol_a = regs[8] & 0x1F
        vol_b = regs[9] & 0x1F
        vol_c = regs[10] & 0x1F
        if vol_a > 0 or vol_b > 0 or vol_c > 0:
            break
        last_active -= 1

    # Keep a small tail of silence (10 frames = 0.2s)
    active_frames = min(last_active + 10, num_frames)

    # Build YM6 file
    # YM6 header: "YM6!" + "LeOnArD!" check + fields
    song_attributes = 1  # bit 0 = interleaved
    nb_digidrums = 0
    chip_clock = AY_CLOCK
    frames_rate = 50
    loop_frame = 0
    extra_data = 0

    # Build interleaved data: 16 registers per frame (pad regs 14-15 with 0)
    ym_data = bytearray()
    for reg in range(16):
        for frame in range(active_frames):
            if reg < 14:
                ym_data.append(data[frame * 14 + reg])
            else:
                ym_data.append(0)

    if not title:
        title = os.path.splitext(os.path.basename(raw_file))[0]
    if not author:
        author = "Ninja Massacre (Codemasters)"
    comment = "Extracted from ZX Spectrum 128K"

    with open(ym_file, "wb") as f:
        f.write(b"YM6!")
        f.write(b"LeOnArD!")
        f.write(struct.pack(">I", active_frames))  # nb_frames
        f.write(struct.pack(">I", song_attributes))  # attributes
        f.write(struct.pack(">H", nb_digidrums))  # nb_digidrums
        f.write(struct.pack(">I", chip_clock))  # chip_clock
        f.write(struct.pack(">H", frames_rate))  # frames_rate
        f.write(struct.pack(">I", loop_frame))  # loop_frame
        f.write(struct.pack(">H", extra_data))  # extra_data
        # No digi drum samples
        # ym2sn.py expects strings BEFORE interleaved data
        f.write(title.encode('ascii') + b'\x00')
        f.write(author.encode('ascii') + b'\x00')
        f.write(comment.encode('ascii') + b'\x00')
        # Interleaved register data
        f.write(ym_data)
        f.write(b"LeOnArD!")  # End marker

    print(f"  {raw_file} -> {ym_file} ({active_frames} frames, {active_frames/50:.1f}s, clock={chip_clock}Hz)")
    return True


def main():
    files = sys.argv[1:] if len(sys.argv) > 1 else sorted(glob.glob("song_*.raw"))

    if not files:
        print("No raw files found")
        return

    for raw_file in files:
        base = os.path.splitext(raw_file)[0]
        ym_file = base + ".ym"
        raw_to_ym(raw_file, ym_file)


if __name__ == "__main__":
    main()
