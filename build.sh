#!/bin/bash
# Build script for Ninja Massacre BBC Micro music conversion
# Reproduces the full pipeline from .z80 snapshot to bootable BBC disc image.
#
# Prerequisites:
#   - Python 3
#   - BeebASM (snap install beebasm, or https://github.com/stardot/beebasm)
#   - git (for cloning tools)
#
# The .z80 snapshot is not included in the repo (too large / copyright).
# The PSG files (captured AY register dumps) ARE included, so you can
# skip straight to the conversion step if you don't have the snapshot.

set -euo pipefail
cd "$(dirname "$0")"

# --- Clone and patch tools if needed ---

if [ ! -d tools/ym2149f ]; then
    echo "=== Cloning ym2149f ==="
    git clone https://github.com/simondotm/ym2149f.git tools/ym2149f
fi

if [ ! -d tools/vgm-packer ]; then
    echo "=== Cloning and patching vgm-packer ==="
    git clone https://github.com/simondotm/vgm-packer.git tools/vgm-packer
    cd tools/vgm-packer
    git apply ../../vgm-packer-py3.patch
    cd ../..
fi

if [ ! -d tools/vgm-player-bbc ]; then
    echo "=== Cloning vgm-player-bbc ==="
    git clone https://github.com/simondotm/vgm-player-bbc.git tools/vgm-player-bbc
fi

# --- Step 1: Capture AY registers from .z80 snapshot (optional) ---
# Only needed if you have the snapshot and want to regenerate the PSG files.

Z80_FILE="Ninja Massacre (1989)(Codemasters)[a][128K].z80"
if [ -f "$Z80_FILE" ] && [ ! -f song_0.psg ]; then
    echo "=== Extracting AY music from .z80 snapshot ==="
    # Lengths determined by finding where each song's active flag goes to 0
    python3 ay_capture.py --song 0 --frames 3500 --output song_0.psg
    python3 ay_capture.py --song 1 --frames 180  --output song_1.psg
    python3 ay_capture.py --song 2 --frames 150  --output song_2.psg
    python3 ay_capture.py --song 3 --frames 120  --output song_3.psg
    python3 ay_capture.py --song 4 --frames 120  --output song_4.psg
    python3 ay_capture.py --song 5 --frames 120  --output song_5.psg
    python3 ay_capture.py --song 6 --frames 120  --output song_6.psg
fi

# --- Step 2: PSG -> raw -> YM6 ---

echo "=== Converting PSG to raw and YM6 ==="
# ay_capture.py also writes .raw files; regenerate from PSG if needed
for song in 0 1 2 3 4 5 6; do
    if [ ! -f "song_${song}.raw" ]; then
        # Re-extract raw from the snapshot if available, otherwise skip
        echo "  song_${song}.raw missing - re-run ay_capture.py with the .z80 snapshot"
    fi
done
python3 raw_to_ym.py

# --- Step 3: YM6 -> SN76489 VGM ---

echo "=== Converting YM to SN76489 VGM ==="
python3 tools/ym2149f/ym2sn.py -c 4.0 -s 15 -b -o song_0_sn.vgm song_0.ym

# --- Step 4: VGM -> VGC (LZ4 compressed) ---

echo "=== Packing VGM to VGC ==="
python3 tools/vgm-packer/vgmpacker.py song_0_sn.vgm

# --- Step 5: Assemble BBC Micro disc image ---

echo "=== Building BBC Micro disc image ==="
beebasm -i player.asm -do ninja_music.ssd -boot NMMusic

echo ""
echo "Done! ninja_music.ssd is ready."
echo "Play on JSBeeb (BBC Master): https://bbc.godbolt.org/"
echo "Or on real hardware via SD card / floppy."
