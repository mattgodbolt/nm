# Journal

How the port got here, in order.

## 2026-10-15

### Where it started

This repository held the conversion of Ninja Massacre's music to the
BBC Micro (`music/README.md`). After the Chuckie Egg 2 port finished,
a brief (`docs/brief.md`) looked at porting the whole game the same way.
It found the game unusually easy to port: 7.4K of code, everything drawn
on the 8 x 8 grid with no masks or shifting, and all the data in clean
blocks. With 16K of sideways RAM it fits with room to spare, and a stock
B might read each level from disc at the "LEVEL nn" screen.

Matt asked for the repository to become that port, on a branch, with the
music as one part of it.

### Reorganised

The music's scripts went to `tools/music/` and their data to `music/`
(decision 3). `tools/music/build.sh` now works in `music/` and clones its
tools into `music/tools/`, so the top-level `tools/` can be the port's.
`ninja_music.ssd` stays at the top, because links point there.

### The skeleton

From Chuckie Egg 2: `tools/asm.sh`, `lint_labels.py`, `grid.py`,
`zx02.py`, the jsbeeb harness (`beeb.mjs`, `play.mjs`) and the Spectrum
harness (`zx.py`), and the Makefile's shape and CI.

- `make fetch` takes the tape and TOSEC's 128K snapshot from archive.org,
  since Spectrum Computing marks the tape "distribution denied", and the
  instructions, the map and a screen from Spectrum Computing.
- `tools/zx.py` now runs a 128K snapshot at 128K timing (70,908 T-states a
  frame), keeps the AY's registers (SkoolKit's snapshot writer wants them:
  without them `>name` failed on a 128K), and can log the beeper, AY and
  paging writes (`--ports`). The brief's research had made those changes
  in a copy; they're in the tool now.
- `make zx` loads the tape as a 128K and a 48K. The 128K reaches the menu
  and play, with the AY written every frame.
- The first layer, the screen: `src/main.6502` builds `build/nm.ssd`,
  whose `NINJA` sets MODE 1 on the narrowed CRTC in the hardware, takes
  IRQ1V for VSync and draws a test pattern (decision 1).

### Disassembly, in three parts

Three agents are taking the original apart in parallel, each with its own
range of the code and its own control file and notes: the core (start-up,
the main loop, levels, the view, printing, the menu), the players and
stars, and the monsters and items (`disasm/*.ctl`, `docs/research/`).

### The levels and the view

- `tools/mkgfx.py` takes the graphics and tables from the 48K load: the
  192 blocks, the font, the tiles' attributes, the passwords and the
  status panel, all one bit a pixel as the original keeps them.
- `tools/mklevels.py` transcribes the level decoder (&C418) in Python.
  `tools/levelcheck.py` runs the original's own decoder for every level in
  turn and compares: all 50 match, and the pointer ends in the same place.
  (A run's count is one less than the tiles it makes, and a count of 0
  makes 256, which the brief's script had one more of.) The maps it makes
  are packed with ZX02 (decision 4) into NDATA, which a loader puts in
  sideways RAM (decision 6).
- The port's first layers: a ZX02 unpacker (`unpack.6502`), the level's
  load and the original's pass over it (`level.6502`, &C39C), and the view
  (`view.6502`, &C54C/&C574/&C59A): 12 x 12 tiles, each a one-bit block
  coloured as it's drawn, its byte of pixels made two MODE 1 bytes by a
  table and masked with the colour.
- The random numbers: the original reads R in 13 places. The port has a
  generator of its own, and for the checks `tools/zx.py`'s `share_random`
  makes the original use the same one: each LD A,R becomes RST &10, which
  jumps to the generator, put in the publisher's mastering code that
  never runs (decision 7).
- `make views`: the original draws each level's first view
  (`tools/zxviews.py`: stop at the level's set-up, make it that level, run
  until the view is drawn), the port does the same in a test build that
  steps through the levels (`VIEWCHECK`, `tools/viewcheck.mjs`), and
  `tools/viewcmp.py` compares every pixel of the playfield in the port's
  colours (decision 5). At first 42 of the 50 matched. Tile &13, the
  spreading one, is the only tile with a paper that isn't black (green on
  magenta, flashing), so the drawing now takes a paper colour too, and the
  check's floor colour for level 50 was wrong. Now all 50 match.

### The music: Whittaker's driver on the 6502

Route (b) of the brief's D3 (decision 8): the original's driver
transcribed, on the original's song data.

- `tools/mkmusic.py` takes the songs from bank 1 into
  `src/data/music.6502`, every pointer a label. It finds what the driver
  reads by playing every song on `dw_decode.py`'s Driver and noting each
  byte read. A walk of the bytes from the song table was the first try,
  and failed: the jingles' voices have no end of their own (no &87 or
  &8E), their patterns running on into the next song's lists, and the
  song stops on one voice before the others reach that far. Played, the
  songs read only some of the instruments and arpeggios, and the note
  table only so far up; `mkmusic.py` writes out what they read.
- `src/music.6502` is the driver from the Z80 (&C00E init, &C0CD tick,
  &C2AE the row, &C36E the frame, &C19D stop), read alongside
  `dw_decode.py`: the voices' &21 bytes at the original's offsets, the
  self-modified operands (the speed, the noise, the transpose, the
  mixer's template) as variables, the commands through a table. The
  shadow AY registers are then converted for the SN76489 (decisions 9-12)
  and written where they changed, from the VSync interrupt. A game's
  write to the chip will hold `mu_busy`, as in Chuckie Egg 2.
- `make music`: a test build (`MUSICCHECK`) plays the songs one after
  another as fast as it goes, recording each frame's shadow registers;
  `tools/musicmodel.py` plays the same on `dw_decode.py`'s Driver (first
  checking that against the captures in `music/`), and
  `tools/musiccheck.mjs` compares. All seven songs matched every frame,
  for each capture's length rounded up to the check's chunks of frames,
  and the chip's bytes matched the model of the conversion. A change to
  the vibrato's octave scaling, made on purpose, showed up at once in
  song 1. Commands &83 (vibrato on alternate frames), &85 and &86 (the
  slides) appear in no song, so nothing checks them.
- The old `make music`, nm's music disc, is now `make music-disc`.
- How long a frame of the driver and the chip takes is in decision 8.
  That matters for a timer bass, whose interrupts would wait for it.
