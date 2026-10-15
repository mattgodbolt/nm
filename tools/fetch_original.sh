#!/bin/sh
# Fetch the Spectrum original and its reference material into original/,
# and check them against original/SHA256SUMS. Not committed: they are not
# ours to redistribute.
#
# Spectrum Computing marks the tape "distribution denied", so the tape and
# the 128K snapshot (the music's source, tools/music/build.sh) come from
# archive.org's TOSEC set, which serves single files from inside its zip.
# Spectrum Computing still serves the instructions, the map and a screen.
set -e
cd "$(dirname "$0")/../original"
SC=https://spectrumcomputing.co.uk/pub/sinclair
TOSEC="https://archive.org/download/zx_spectrum_tosec_set_september_2023/Games.zip/Games%2FNinja%20Massacre%2F"
get() { [ -f "$2" ] || curl -sfL "$1" -o "$2"; }
get "${TOSEC}Ninja%20Massacre%20%281989%29%28Code%20Masters%29%2848K-128K%29%5Ba%5D.tzx" "Ninja Massacre (1989)(Code Masters)(48K-128K)[a].tzx"
get "${TOSEC}Ninja%20Massacre%20%281989%29%28Code%20Masters%29%28128K%29.z80" "Ninja Massacre (1989)(Code Masters)(128K).z80"
get "$SC/games-info/n/NinjaMassacre.txt" NinjaMassacre.txt
get "$SC/games-maps/n/NinjaMassacre.png" NinjaMassacre.png
get "$SC/screens/in-game/n/NinjaMassacre.gif" NinjaMassacre.gif
sha256sum -c SHA256SUMS
