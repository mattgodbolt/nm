# Ninja Massacre AY Music Extraction & BBC Micro Conversion

## Overview

Extracting AY-3-8910 music from the ZX Spectrum 128K game "Ninja Massacre"
(1989, Codemasters, written by Adam Waring) and converting it for playback
on the BBC Micro's SN76489 sound chip.

## Source Material

- **Game**: Ninja Massacre (1989)(Codemasters)[a][128K].z80
- **Format**: .z80 snapshot (v2, 128K mode, hw_mode=3)
- **Music engine**: Bespoke Codemasters engine in RAM bank 1

## Step 1: Parse the .z80 Snapshot

The .z80 file is a v2 extended format (23-byte extended header). Key fields:
- `hw_mode=3` → 128K Spectrum
- `last_7ffd=0x10` → ROM1 selected, bank 0 paged at 0xC000
- AY registers in the header confirm music was active at snapshot time
- 8 memory pages (banks 0-7) extracted as `page_3.bin` through `page_10.bin`

## Step 2: Locate the Music Engine

The music engine lives in **bank 1** (page 4 in .z80 format, loaded at
0xC000-0xFFFF when paged in).

### Engine Structure

Jump table at 0xC000:
| Address | Function | Description |
|---------|----------|-------------|
| 0xC000 → 0xC00E | Init | A = song number (0-6) |
| 0xC003 → 0xC0CD | Tick | Call once per frame (50Hz) |
| 0xC006 → 0xC19D | Stop | Silence all channels |
| 0xC009 → 0xC64B | SFX | Sound effects |

### Key Addresses
- **Song table**: 0xC817 (7 bytes per song: speed + 3x 2-byte order list pointers)
- **Frequency table**: 0xC498 (96 notes, 2 bytes each, C0-B7)
- **AY register buffer**: 0xC47F-0xC48A (regs 0-11)
- **Channel state**: 3 channels at IX=0xC069, 0xC08A, 0xC0AB (0x21 bytes each)
- **AY output routine**: 0xC161 (bulk write), 0xC175 (single reg), 0xC17F (silence)

### Songs
| Song | Speed | Duration | Description |
|------|-------|----------|-------------|
| 0 | 6 | 69.1s | Main game music |
| 1 | 6 | 2.9s | Jingle |
| 2 | 7 | 2.2s | Jingle |
| 3 | 6 | 1.8s | Jingle |
| 4 | 6 | 1.8s | Jingle |
| 5 | 6 | 1.8s | Jingle |
| 6 | 6 | 1.8s | Jingle |

## Step 3: Capture AY Register Writes

Rather than fully reverse-engineering the music data format, we wrote a
**minimal Z80 emulator** (`ay_capture.py`) that runs the actual music engine
code and captures AY register writes per frame.

```bash
# Extract memory pages from .z80 snapshot (done by the parser in ay_capture.py)
# Then capture each song:
python3 ay_capture.py --song 0 --frames 3500 --output song_0.psg --txt
```

This produces:
- `.psg` — PSG format (AY register dump, standard format)
- `.raw` — 14 bytes per frame (registers 0-13), easy to process
- `.txt` — Human-readable tracker-style output

### Verification
```bash
# Play with zxtune123:
/path/to/zxtune123 song_0.psg
```

## Step 4: Convert to YM Format

The `ym2sn.py` tool (from simondotm/ym2149f) converts AY music to SN76489,
but expects YM format input. We convert our raw captures to YM6 format:

```bash
python3 raw_to_ym.py
```

**Important**: The YM6 format must specify the correct AY clock (1773400 Hz
for Spectrum 128K, NOT the default 2000000 Hz for Atari ST). Getting this
wrong causes incorrect frequency mapping.

## Step 5: Convert AY → SN76489

```bash
python3 tools/ym2149f/ym2sn.py -c 4.0 -s 15 -b -o song_0_sn.vgm song_0.ym
```

Flags:
- `-c 4.0` — BBC Micro SN76489 clock (4 MHz)
- `-s 15` — BBC Micro LFSR bit (15-bit, vs 16-bit for Sega)
- `-b` — Enable software bass for frequencies below 122Hz

### Chip Differences
| Feature | AY-3-8910 (Spectrum) | SN76489 (BBC) |
|---------|---------------------|---------------|
| Tone channels | 3 | 3 |
| Frequency register | 12-bit | 10-bit |
| Min frequency | ~27 Hz | ~122 Hz (4MHz) |
| Hardware envelopes | Yes | No |
| Noise per-channel | Yes (mixer) | 1 shared channel |
| Volume | 0-15 (0=silent) | 0-15 (0=loud, 15=silent) |

This particular game doesn't use envelopes, so conversion is clean.

## Step 6: Pack for BBC Micro

```bash
python3 tools/vgm-packer/vgmpacker.py song_0_sn.vgm
```

Produces `.vgc` files (LZ4-compressed VGM) for use with the
[vgm-player-bbc](https://github.com/simondotm/vgm-player-bbc) 6502 player.

Song 0 compresses from ~48KB VGM to ~3.7KB VGC.

**Note**: The short jingles (songs 1-6) may be too small for the LZ4
compressor and might need to be handled differently.

## Tools Used

| Tool | Purpose | Source |
|------|---------|--------|
| `ay_capture.py` | Z80 emulator + AY register capture | Local (this repo) |
| `raw_to_ym.py` | Convert raw register dumps to YM6 format | Local (this repo) |
| `psg_to_vgm.py` | Convert PSG files to VGM format | Local (this repo) |
| `ym2sn.py` | Convert AY/YM to SN76489 VGM | [simondotm/ym2149f](https://github.com/simondotm/ym2149f) |
| `vgmpacker.py` | LZ4-compress VGM to VGC for 6502 | [simondotm/vgm-packer](https://github.com/simondotm/vgm-packer) |
| `vgm-player-bbc` | 6502 playback engine | [simondotm/vgm-player-bbc](https://github.com/simondotm/vgm-player-bbc) |
| `zxtune123` | Verification/playback | [zxtune.bitbucket.io](https://zxtune.bitbucket.io/) |
| `radare2` | Z80 disassembly | [rada.re](https://rada.re/) |

## Full Pipeline Summary

```
.z80 snapshot
    ↓ (ay_capture.py - parse snapshot, extract bank 1)
page_4.bin (music engine + data)
    ↓ (ay_capture.py - Z80 emulation, capture AY regs at 50Hz)
song_N.psg / song_N.raw
    ↓ (raw_to_ym.py - reformat with correct clock)
song_N.ym (YM6 format, 1773400 Hz clock)
    ↓ (ym2sn.py -c 4.0 -s 15 -b)
song_N_sn.vgm (SN76489 VGM, 4 MHz clock)
    ↓ (vgmpacker.py)
song_N_sn.vgc (LZ4-compressed for BBC 6502 playback)
```

## Step 7: Build BBC Micro Disc Image

The final step assembles a playable `.ssd` disc image using BeebASM and
the [vgm-player-bbc](https://github.com/simondotm/vgm-player-bbc) 6502
VGC player engine.

```bash
beebasm -i player.asm -do ninja_music.ssd -boot NMMusic
```

`player.asm` includes the VGC player library, the compressed music data,
and a minimal 6502 main loop that syncs to vsync (50Hz) and calls
`vgm_update()` each frame.

### Output
- `ninja_music.ssd` — 7.5KB DFS disc image, auto-boots
- 757 bytes player code + 3,745 bytes compressed music + 2KB decode buffers

### Playing It
- **JSBeeb** (easiest): Drag `ninja_music.ssd` onto https://bbc.godbolt.org/
- **b-em / BeebEm**: Load disc, it auto-boots
- **Real hardware**: Write SSD to floppy or use SD card (MMFS/GoSDC)

## Full Pipeline Summary

```
.z80 snapshot
    ↓ (ay_capture.py - parse snapshot, extract bank 1)
page_4.bin (music engine + data)
    ↓ (ay_capture.py - Z80 emulation, capture AY regs at 50Hz)
song_N.psg / song_N.raw
    ↓ (raw_to_ym.py - reformat with correct clock)
song_N.ym (YM6 format, 1773400 Hz clock)
    ↓ (ym2sn.py -c 4.0 -s 15 -b)
song_N_sn.vgm (SN76489 VGM, 4 MHz clock)
    ↓ (vgmpacker.py)
song_N_sn.vgc (LZ4-compressed for BBC 6502 playback)
    ↓ (beebasm -i player.asm -do ninja_music.ssd -boot NMMusic)
ninja_music.ssd (bootable BBC Micro DFS disc image)
```

## Notes

- The vgm-packer tools needed patching for Python 3 compatibility
  (bytes vs str issues in huffman.py, lz4enc.py, vgmparser.py)
- The music engine is NOT a known/documented format — it's a bespoke
  Codemasters engine. The Z80 emulation approach avoids needing to fully
  reverse-engineer the data format.
- Song 0 is the main game music (69s). Songs 1-6 are short jingles (~2s each).
  Only song 0 is included in the disc image — the jingles are too short for
  the LZ4 packer and would need a different approach (raw VGM or Exomizer).
- The tools (ym2149f, vgm-packer, vgm-player-bbc) are cloned into `tools/`
  and should ideally be converted to git submodules.
