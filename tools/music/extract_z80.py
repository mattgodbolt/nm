#!/usr/bin/env python3
"""Extract RAM pages from a .z80 snapshot (v2/v3, 128K).

Regenerates the page_N.bin files that ay_capture.py needs (the music
engine lives in page 4 = 128K RAM bank 1).
"""

import argparse
import struct
import sys

PAGE_SIZE = 16384

# .z80 page numbers for 128K snapshots: page N = RAM bank N-3
BANK_OF_PAGE = {p: p - 3 for p in range(3, 11)}


def decompress(data, expected=PAGE_SIZE):
    """Undo the .z80 ED ED <count> <byte> RLE encoding."""
    out = bytearray()
    i = 0
    while i < len(data) and len(out) < expected:
        if data[i] == 0xED and i + 3 < len(data) and data[i + 1] == 0xED:
            out.extend(data[i + 3:i + 4] * data[i + 2])
            i += 4
        else:
            out.append(data[i])
            i += 1
    if len(out) != expected:
        raise ValueError(f"decompressed to {len(out)} bytes, expected {expected}")
    return bytes(out)


def read_pages(path):
    """Yield (page_number, 16K data) for each memory block in the snapshot."""
    data = open(path, "rb").read()
    pc = struct.unpack_from("<H", data, 6)[0]
    if pc != 0:
        raise SystemExit("v1 .z80 snapshot - only v2/v3 supported")
    ext_len = struct.unpack_from("<H", data, 30)[0]
    version = {23: 2, 54: 3, 55: 3}.get(ext_len)
    hw_mode = data[34]
    port_7ffd = data[35]
    print(f"v{version} snapshot, hardware mode {hw_mode}, "
          f"last 0x7ffd write 0x{port_7ffd:02x}")
    pos = 32 + ext_len
    while pos < len(data):
        length, page = struct.unpack_from("<HB", data, pos)
        pos += 3
        if length == 0xFFFF:  # stored uncompressed
            yield page, data[pos:pos + PAGE_SIZE]
            pos += PAGE_SIZE
        else:
            yield page, decompress(data[pos:pos + length])
            pos += length


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", help=".z80 snapshot file")
    parser.add_argument("--all", action="store_true",
                        help="write every page, not just page 4")
    args = parser.parse_args()

    for page, content in read_pages(args.snapshot):
        bank = BANK_OF_PAGE.get(page)
        desc = f"RAM bank {bank}" if bank is not None else "ROM"
        print(f"page {page:2d} ({desc}): {len(content)} bytes")
        if args.all or page == 4:
            name = f"page_{page}.bin"
            with open(name, "wb") as f:
                f.write(content)
            print(f"  -> wrote {name}")


if __name__ == "__main__":
    main()
