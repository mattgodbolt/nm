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
