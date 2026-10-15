#!/usr/bin/env python3
"""Convert PSG (AY register dump) files to VGM format.

VGM is a standard chip music format that records register writes with timing.
This produces VGM files targeting the AY-3-8910 at 1773400 Hz (Spectrum 128K),
which can then be converted to SN76489 using ym2sn.py or vgm-converter.

VGM spec: https://vgmrips.net/wiki/VGM_Specification
"""

import struct
import sys
import os


# VGM header constants
VGM_MAGIC = 0x206D6756  # "Vgm "
VGM_VERSION = 0x00000161  # Version 1.61
AY_CLOCK = 1773400  # Spectrum 128K AY clock
SAMPLES_PER_FRAME = 882  # 44100 / 50 = 882 samples per frame at 50Hz


def psg_to_vgm(psg_file, vgm_file):
    """Convert a PSG file to VGM format."""
    with open(psg_file, "rb") as f:
        data = f.read()

    # Parse PSG header
    if data[:3] != b"PSG" or data[3] != 0x1A:
        print(f"Error: {psg_file} is not a valid PSG file")
        return False

    # PSG data starts after 16-byte header
    offset = 16

    # Build VGM data commands
    vgm_data = bytearray()
    total_samples = 0

    while offset < len(data):
        byte = data[offset]
        offset += 1

        if byte == 0xFF:
            # End of frame - wait one frame (882 samples at 44100Hz)
            vgm_data.append(0x63)  # Wait 882 samples (1/50 second PAL)
            total_samples += SAMPLES_PER_FRAME
        elif byte == 0xFE:
            # Multiple frame wait (PSG extension)
            if offset < len(data):
                count = data[offset] * 4
                offset += 1
                for _ in range(count):
                    vgm_data.append(0x63)
                    total_samples += SAMPLES_PER_FRAME
        elif byte < 0x10:
            # AY register write: byte = register, next byte = value
            if offset < len(data):
                value = data[offset]
                offset += 1
                # VGM command 0xA0 = AY8910 write
                vgm_data.append(0xA0)
                vgm_data.append(byte)  # register
                vgm_data.append(value)  # value
        else:
            # Unknown byte, skip
            pass

    # End of data
    vgm_data.append(0x66)

    # Build VGM header (256 bytes, mostly zeros)
    header = bytearray(256)

    # Magic
    struct.pack_into("<I", header, 0x00, VGM_MAGIC)
    # EOF offset (relative to offset 0x04)
    eof_offset = len(header) + len(vgm_data) - 4
    struct.pack_into("<I", header, 0x04, eof_offset)
    # Version
    struct.pack_into("<I", header, 0x08, VGM_VERSION)
    # AY8910 clock
    struct.pack_into("<I", header, 0x74, AY_CLOCK)
    # AY8910 chip type (0 = AY8910)
    header[0x78] = 0x00
    # AY8910 flags
    header[0x79] = 0x00
    # Total samples
    struct.pack_into("<I", header, 0x18, total_samples)
    # Rate (50Hz for PAL)
    struct.pack_into("<I", header, 0x24, 50)
    # VGM data offset (relative to 0x34)
    # Data starts at offset 256, so relative to 0x34: 256 - 0x34 = 204
    struct.pack_into("<I", header, 0x34, len(header) - 0x34)

    with open(vgm_file, "wb") as f:
        f.write(header)
        f.write(vgm_data)

    duration = total_samples / 44100
    print(f"  {psg_file} -> {vgm_file} ({duration:.1f}s, {len(header)+len(vgm_data)} bytes)")
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Convert PSG files to VGM format")
    parser.add_argument("files", nargs="*", help="PSG files to convert (default: song_*.psg)")
    parser.add_argument("--output-dir", default=".", help="Output directory")
    args = parser.parse_args()

    files = args.files
    if not files:
        import glob
        files = sorted(glob.glob("song_*.psg"))

    if not files:
        print("No PSG files found")
        return

    os.makedirs(args.output_dir, exist_ok=True)

    for psg_file in files:
        base = os.path.splitext(os.path.basename(psg_file))[0]
        vgm_file = os.path.join(args.output_dir, base + ".vgm")
        psg_to_vgm(psg_file, vgm_file)


if __name__ == "__main__":
    main()
