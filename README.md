# Ninja Massacre on the BBC Micro

Ninja Massacre (1989, Codemasters) is a ZX Spectrum 128K game with a
brilliant, catchy soundtrack composed by David Whittaker. This project
extracts its music from the Spectrum and converts it to play on the BBC
Micro -- a machine with a completely different sound chip.

The main theme is a personal favourite: my friend
[Rich Talbot-Watkins](https://github.com/waitingforvsync) and I used to play
the game on my Spectrum +3, and the tune has been stuck in my head ever since.
This project was an excuse to finally get it running on the Beeb, with Claude
doing the heavy lifting.

## Listen to it

[Play it now in your browser](https://bbc.xania.org?autoboot&model=master&disc1=https://raw.githubusercontent.com/mattgodbolt/nm/main/ninja_music.ssd)
(runs in jsbeeb as a BBC Master).

You can also download `ninja_music.ssd` and use b-em, BeebEm, or real
hardware via floppy or SD card.

## The challenge

The Spectrum's **AY-3-8910** and the BBC's **SN76489** are quite different
sound chips:

| | AY-3-8910 (Spectrum) | SN76489 (BBC) |
|---|---|---|
| Tone frequency register | 12-bit | 10-bit |
| Lowest tone | ~27 Hz | ~122 Hz |
| Hardware envelopes | Yes | No |
| Noise | Per-channel mixer | 1 shared channel |
| Volume polarity | 0 = silent | 0 = loud |

The biggest problem is bass. Ninja Massacre uses bass *heavily* -- about 79%
of frames have at least one tone below the SN76489's 122 Hz minimum. Without
bass, the conversion sounds thin and wrong.

## How it works

### The pipeline

```
.z80 snapshot (Spectrum game state)
  |  ay_capture.py -- Z80 emulation, captures AY register writes at 50Hz
  v
.psg files (AY register dumps, one per song)
  |  raw_to_ym.py -- reformat with correct 1.7734 MHz clock
  v
.ym files (YM6 format)
  |  ym2sn.py -- frequency mapping, bass encoding
  v
_sn.vgm files (SN76489 VGM at 4 MHz, with software bass flags)
  |  vgmpacker.py -- LZ4 compression into 8 independent streams
  v
_sn.vgc files (compressed: 48 KB -> ~4 KB)
  |  beebasm + player.asm -- 6502 assembly, IRQ bass player
  v
ninja_music.ssd (bootable BBC Micro disc image)
```

### Extracting the music

The music engine is a bespoke Codemasters driver -- not a known/documented
format. Rather than reverse-engineering the data format, `ay_capture.py`
takes a different approach: it includes a **minimal Z80 CPU emulator**
(written in Python) that loads the Spectrum's memory banks and runs the
actual music engine code. It intercepts AY register writes via I/O port
trapping and records them at 50 Hz, producing standard PSG files.

The engine lives in Spectrum bank 1 with a jump table at 0xC000
(init/tick/stop/sfx) and supports 7 songs: the main theme plus 6 short
jingles.

### Solving the bass problem

The SN76489 at 4 MHz physically cannot produce tones below ~122 Hz. The
solution is **IRQ-driven volume toggling** using the BBC's 6522 VIA timers:

1. During conversion, `ym2sn.py -b` encodes sub-122 Hz tones with bit 6
   set in the SN76489 data byte (a normally-unused bit), and right-shifts
   the tone period to fit in 10 bits.
2. At playback, the bass-enhanced 6502 player detects bit 6 and:
   - Sets the SN76489 channel to period 1 (~125 kHz, effectively DC)
   - Programs a VIA timer to fire at the target bass frequency
   - The timer ISR toggles the channel volume on and off, synthesizing a
     square wave at the correct pitch
3. Three independent timers handle all three channels simultaneously
   (User VIA Timers 1 & 2, System VIA Timer 2).

This requires a BBC Master for 65C02 instructions (`stz`, `phx`/`phy`,
`bra`).

### Bug fix: LZ4 decoder

The bass-enhanced LZ4 decoder in `vgm-player-bbc` had a 16-bit decrement
bug: when a literal run crosses a 256-byte boundary, `dec zp_literal_cnt`
wraps from 0x00 to 0xFF without propagating the borrow to the high byte.
This desynchronises the entire LZ4 stream. The standard (non-bass) player
doesn't have this bug because it uses a proper `sec; sbc #1` sequence.

The fix is in `vgm-player-bbc-lz4fix.patch`.

## Building

### Prerequisites

- Python 3
- [BeebASM](https://github.com/stardot/beebasm) (`snap install beebasm`)
- git

### Build

```bash
./build.sh
```

This clones and patches the required tools, converts the included PSG files
through the full pipeline, and produces `ninja_music.ssd`.

The .z80 snapshot is not included (copyright), but the captured PSG register
dumps are, so the build works without it.

## Songs

| # | Duration | Description |
|---|----------|-------------|
| 0 | 69s | Main game music (included in disc image) |
| 1 | 2.9s | Jingle |
| 2 | 2.2s | Jingle |
| 3 | 1.8s | Jingle |
| 4 | 1.8s | Jingle |
| 5 | 1.8s | Jingle |
| 6 | 1.8s | Jingle |

Only song 0 is included in the disc image. The jingles are too short for
efficient LZ4 compression and would need a different packing approach.

## The sheet music

The other direction: from register dumps *up* to notation. Rather than
transcribing the captured AY output (which is smeared by vibrato, arpeggio
and portamento effects), `dw_decode.py` is a faithful Python port of David
Whittaker's actual Z80 music driver -- self-modifying code and all. It
interprets the original song data, so it recovers the *written* music:
notes, durations, volume-envelope instruments, chord (arpeggio) tables,
vibrato parameters and drum modes. The port also renders AY register
frames, verified **100% frame-exact** against all seven captured PSGs.

`score_gen.py` turns that into notation
([PDF](ninja_song0.pdf), [MusicXML](ninja_song0.musicxml),
[MIDI](ninja_song0.mid)). Staves are musical roles rather than chip
channels -- Whittaker moves the bass, riff and drum duties between the
three AY voices freely. Frame-rate arpeggio-table cycling (an unplayable
50 notes/sec) is notated as the block chords it emulates; row-rate runs
(playable sixteenths) stay written out. The main theme is B flat
mixolydian, notated with the B flat major signature and the modal A flats
as accidentals, as adjudicated by Rich Talbot-Watkins.

`audio_render.py` writes two WAVs for A/B listening: the exact chip
register frames through a small AY emulator, versus the notation played
straight -- the performance versus the page.

The score files are committed because regenerating them needs the music
engine from the .z80 snapshot, which is not distributable.

## Project structure

| File | Description |
|---|---|
| `ay_capture.py` | Z80 emulator + AY register capture from .z80 snapshots |
| `extract_z80.py` | Extract 128K RAM pages from a .z80 snapshot |
| `dw_decode.py` | Port of the Whittaker music driver; decoder + verifier |
| `score_gen.py` | Decoded music to notation (MusicXML/MIDI) |
| `audio_render.py` | A/B WAVs: chip emulation vs the score as written |
| `ninja_song0.pdf` | The main theme, engraved |
| `raw_to_ym.py` | Convert raw register dumps to YM6 format |
| `psg_to_vgm.py` | Convert PSG files to VGM format |
| `player.asm` | BBC Micro 6502 player (BeebASM source) |
| `build.sh` | Full build pipeline |
| `song_*.psg` | Captured AY register data (included) |
| `ninja_music.ssd` | Bootable BBC Micro disc image (included) |
| `CONVERSION.md` | Detailed technical notes on the conversion process |

## Credits

- **David Whittaker** -- original music
- **Adam Waring** -- original game (Codemasters, 1989)
- **[Simon Morris](https://github.com/simondotm)** --
  [ym2149f](https://github.com/simondotm/ym2149f) (AY-to-SN conversion),
  [vgm-packer](https://github.com/simondotm/vgm-packer) (VGM compression),
  [vgm-player-bbc](https://github.com/simondotm/vgm-player-bbc) (6502 playback engine)
- **[Rich Talbot-Watkins](https://github.com/waitingforvsync)** -- fellow
  Ninja Massacre enthusiast, and adjudicator of key signatures
- **Claude** (Anthropic) -- wrote the Z80 emulator, conversion scripts,
  6502 player integration, found the LZ4 decoder bug; later
  reverse-engineered the music driver and generated the score
