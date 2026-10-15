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

### The panel, the title and text

- The status panel is drawn once from the loading screen's left columns
  (`panel.6502`), as the original keeps them, in colours that don't
  change with the level.
- The original's print writes a glyph and leaves the attribute: so the
  port keeps a copy of the attributes (decision 8) and prints in the
  cell's colours. The clear (&C487), print (&D995/&D9AA) and the
  two-digit number (&DB83) are transcribed, and with them the level's
  title screen (&C1A6, &C34F): NINJA MASSACRE, "LEVEL nn", and the pause,
  as a wait of the frames the original's loop took (decision 9).

A slip: that commit went in with `make check` failing, because the
command piped the check's output into `tail`, which succeeded. The test
build warned (the title code was unreachable in it), `tools/asm.sh` failed
the build after baron had written the disc, and the next run took that
disc as up to date. Now the Makefile has `.DELETE_ON_ERROR`, the check's
build runs each level's title too, and the check runs with its own exit
status read.

### The research, and the frame for the game

The three parts of the disassembly came back: `docs/research/core.md`,
`players.md` and `monsters.md`, with `disasm/*.ctl`, and `make disasm`
builds a labelled skool file from them (it's in `make check` now). They
corrected the brief in places: a run in the level data is one tile longer
than its count; the "random decorations" don't show (they're the trap
doors' hidden bits and the monsters' health); the slide's block moves are
`ShiftUp`/`ShiftDown`/`ShiftLeft`/`ShiftRight`. Two more of the R reads
only shape sounds (the hit noise and the burst), so they stay out of the
shared stream (decision 7).

The variables are all in &BA29-&BA9F and &FF2A-&FF61, with tables among
them, so the port keeps both blocks in the original's layout, from the
tape's bytes, named from the ctl files (`tools/mkvars.py`, decision 10).
The code now loads at &1900 and the loader copies it down to &0E00, and
the map and the attributes are in OS workspace (decision 11).

### The players walk, pass for pass

The players, touching and the status are transcribed: `player.6502` (the
two players' code is the same in the original apart from their variables,
keys and colours, so here it is once, for the player in `pl`), `touch.6502`
(every item, doors, chests, the teleporters, the shove, the exits, hitting
a monster), `status.6502` (strength, treasure, the panel's figures and
icons, the status tick, the idle timers, the one-way tiles), `shift.6502`
(the scroll's block moves) and `spread.6502`. The original's routines
pass positions and map cells in registers, so the transcription keeps
the Z80's registers in zero page by their names (`regs.6502`: rb, rc, rd,
re, rh, rl), and each routine reads beside its original. The parts not
yet transcribed are stubs (`stubs.6502`). The main loop runs at a pass
clock (decision 12); the keys are a table (decision 13).

`tools/passlog.py` plays the original pass by pass from the menu's 1,
with keys held over ranges of passes, and logs both variable blocks and
the map at the top of every pass; `tools/passlog.mjs` does the same on
the port, and `tools/passcmp.py` names what differs. On the first try,
walking right then down into the wall on level 1 matched every player
variable for 70 passes. What differs is the monsters' (not transcribed
yet): their scan's variables and the trap doors' sparkles in the map.
