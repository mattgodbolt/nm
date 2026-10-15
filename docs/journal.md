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

### The music: Whittaker's driver on the 6502

Route (b) of the brief's D3 (decision 14): the original's driver
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
  shadow AY registers are then converted for the SN76489 (decisions 15-18)
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
- How long a frame of the driver and the chip takes is in decision 14.
  That matters for a timer bass, whose interrupts would wait for it.

(The music was written on a branch beside the game's work and merged
after the players: its decisions, numbered 8-12 there, are 14-18.)

### The monsters, pass for pass

The monsters, trap doors and sparkles are transcribed (`monsters.6502`):
the quarter-view scan, the chase (the nearer player, or away under its
idol), the step tried diagonally then by column then by row, the hit on a
player, the trap doors' spawning and the sparkles' turning into monsters.
The scan's fixed delay per empty tile isn't: the pass clock paces the
pass (decision 12). Two things the transcription had to keep: the chase's
facing doubles in the Z80's alternate flags, so the compare's carry
survives it (here a PHP/PLP); and a monster's hit on player 1 is followed
by a test for player 2 on whatever A player 1's strength routine left,
so with player 1's heart at &72 player 2 is hit too.

`make passes` now replays `tests/scenarios.txt` on both machines side by
side (`tools/passcheck.sh`), and it's in `make check`. Five scenarios on
level 1 match pass for pass: standing, walking into walls, walking right
and up across the view's scroll, and up then right into the monsters (33
hits, a chest taken). The menu's flashing colour is the one thing not
compared yet.

### Stars, sounds, the smart bomb, and room

- The stars are transcribed (`stars.6502`): the throw, the flight, the
  bounce off walls (one shared count), and every hit, with the original's
  quirks kept (a star's hits on a monster or a trap door use player 1's
  power whoever threw it; the trap door's 50 points are never paid). Three
  throwing scenarios match pass for pass.
- The beeper's effects play on the SN76489 (`sound.6502`, decision 19),
  each as long as the original's, holding `mu_busy` so the music stays
  off the chip. The smart bomb is transcribed (`bomb.6502`).
- Main RAM filled, so code that isn't in the inner loops runs from the
  sideways RAM bank, which is paged in for good, and the drawing's tables
  are made at start-up in OS workspace (decision 20). The panel's picture
  is packed with ZX02 and unpacked into the map's room at start-up.
- The pass logs now carry the screen every 50 passes, and `passcmp.py`
  compares them: the playfield in the port's colours, the panel by shape.
  That's because a bug only the screen showed got past the pass
  comparison: moving `print_char`'s glyph pointer into rl/rh broke
  `print_grid`, which counts in rl, and `draw_glyph` took the screen
  column from Y after `attr_colours` had used it. Both are fixed, and every
  scenario's screens now match.

### The front end

The menu, the password, the controls (redefining a player's keys), game
over, the high score and its name, the game's end with its tally, and
the keys in play (pause, quit, the music) are transcribed (`menu.6502`,
in the bank), with the gaps decision 21 lists. The release disc
(`build/nm.ssd`) now starts at the menu; the tools use `build/test.ssd`
(`-D DIRECT=1`), which goes straight into a one-player game.

The menu's flash: the original rewrites the attributes of rows 4-23
between yellow on blue and white on red twice a frame, for about 12.6 s.
Here the rows are repainted once so that their paper is logical colour 2
and their ink 3, and the flash swaps those two's physical colours.

More scenarios: the loggers take `--two` (a two-player game: on the port,
a byte the test disc's start reads), `--level n` and `--poke
pass:addr:value` (the original's addresses, set on both: so a scenario can
make a player leave by the exit without walking to one). Two-player play
with both fighting, a level change, and play on levels 10 and 37 all
match pass for pass, screens included.

### Fuzzing

`make fuzz` (`tools/fuzz.py`) writes random scenarios (a random level,
one or two players, random keys over random stretches, sometimes scrolls
for the smart bomb) and runs them through `tools/passcheck.sh`. The first
36 found three differences, each the original's own behaviour that the
transcription had smoothed over or got wrong:

- **A kill moves the touch.** `HitMonster` draws floor over a dead
  monster, and the drawing leaves the Z80's BC as its loops left it: (0,
  &20) for a whole picture, (0, &30) for half, or the floor's attribute
  and 0 off the view. The touch loop then carries on from that BC, so the
  cells touched after a kill are odd ones (row &FF, say), and the touch
  gate's count follows. The port now leaves rb/rc the same way.
- **The crumbling wall** mended the wall above at every stage: a
  `LDY #0` between the `AND` and the branch set the Z flag. A slip of
  mine.
- **A hell hole's sparkle**: the original keeps the trap door's code and
  the random number in A and A' (`EX AF,AF'`), and on one path reads back
  the random number for the sparkle's code: &41-&43, with no second
  random number. Transcribed.

They're in `tests/scenarios.txt` now. The panel's screen comparison also
needed the panel's own colour map: on a level whose floor is blue, the
logo's paper looked wrong to it.

Seven more seeds of fuzzing (84 scenarios) found one more: a door's run
didn't go with it, because `door_run` kept the door's code in `ra2`, which
the redraw uses as scratch; `push_rock` had the same hazard. Both have
their own variables now, and a scenario. Another checks a player's death
in a two-player game: GAME OVER, then play on with the other, screens and
all. The password route works on the release disc (SNOW starts level 5,
its password shown).

### Speed, and a scan past the map

Measured in jsbeeb (pass to pass, in cycles), walking took two of the
pass clock's ticks: the panel's figures and icons, reprinted on every
touch up to three times a pass, cost more than the rest. The panel now
keeps what each cell shows and skips a character already there (decision
22), and walking passes are 1.22 frames, as the original's median. A pass
with a scroll took 43 frames against the original's 18.6; the block moves
now copy sixteen bytes a group through addresses set once a shift and
stepped a page at a time, and it's 31.6. The shifts' screens were checked
every 5 passes on scrolls in all four directions.

The loggers now carry the random generator's state, and end a log when a
game ends (the original goes back to its menu). Ten 600-pass fuzz seeds
found one more: with the view at the bottom right, the original's
monster scan reads one tile past its map, which is its own code at &C000:
&31 there is a trap door to it. The port keeps that byte after its map
(decision 23); `map_cell` now adds the map's page instead of ORing it, so
the map needn't sit on a four-page boundary.

Eight more 600-pass fuzz seeds: games that ended now end both logs at
the same pass, and one difference turned up, mine: a pushed rock's old
cell was cleared through a Y the redraw had changed, leaving two rocks.
Fixed, with a scenario.

Matt booted the branch's disc on a phone and saw a blank playfield and a
red and white panel: the game was waiting for a key (the original's
first wait, on its loading screen, which the port doesn't keep), and the
start-up still loaded the screen's first test colours. At power-on the
menu now comes straight up (decision 21), and the start-up palette is a
level's.

### Docs, and the music still builds

A pass over the docs before merging to main: the README's links point at
main, the music's README says how its disc relates to the game's music,
and the conversion notes say where their commands run. `make music-disc`
rebuilds `ninja_music.ssd` byte for byte from the committed captures; and
from TOSEC's 128K snapshot (`make fetch`), the AY captures come out byte
for byte as committed.

### A round of optimisation

Four agents, each in its own worktree and with its own part of the code
(the game logic, the bank's code and data, the music and the effects,
the screen), looked for space and speed with the checks as the bar: no
change to anything the game does. Merged, everything still matches pass
for pass on the B and the Master.

- Main RAM's free space below the screen roughly trebled: the logic's
  shared tails, fall-throughs and table lookups; the shifts rewritten as
  one copier with an `LDA abs,Y : STA abs,Y` pair per character row;
  the music driver's commands dispatched through a table of offsets, its
  voices looped, and its entry points moved to the bank.
- The bank gained most from the levels: only the 30 x 30 inside of the
  border walls is packed, by columns or rows, whichever is smaller. The
  panel is packed as attributes and character cells, and the font stops
  at Z.
- The slide is about a quarter faster (decision 22 has the measurement);
  ordinary passes' drawing about an eighth. The blocks are stored as
  four planes of 8 x 8 quarters, so one index reads a line of each.
- Two new timing tools: `tools/scrolltime.mjs` and `tools/passtime.mjs`.
- 32 coverage scenarios, picked from random games on the original so
  that every touch, star and bomb handler runs at least three times: the
  old scenarios never reached a scroll's pickup, a chest's opening, the
  switch or the jackpot.
- Two fixes found on the way: `mul8` gave 0 for a length of 0 where the
  original's loop counts 256 (a noise segment went silent); and
  `make views` now depends on the 48K snapshot it reads.

### A second round

Three agents: the logic, the screen, and a fresh pair of eyes on the
whole program. The screen and the logic both rewrote the scroll, so the
logic's agent merged the two.

- The slide's attributes move once, at its end (`slide_attrs`), rather
  than at each of the eight steps: the pixels at every step and the
  attributes at the end are as before (`tools/scrolltime.mjs` checks
  both). Decision 22 has the new measurement.
- Passes are much faster: a sampler showed that reprinting the panel on
  every touch was a large share of a walking pass. `print5` now keeps
  each figure's digits and skips the ones already shown.
- The four scrolls are one `scroll`, with the direction in X, and the
  shifts are programs for `shift_by`.
- Start-up's run-once code sits in `panel_shown`'s bytes, which
  `draw_panel` fills only after it has run. `blocks` is page-aligned at
  the start of the code, with the copier after it.
- `read_key`'s 128-byte table became a list of the keys that matter.
- The views' rule depends on both snapshots, which `zxviews.py` reads.

### A third round

Two agents on what round 2 left. The music's frame is about a twentieth
cheaper (checked frame by frame on all seven songs, and every AY period
through `mu_period`, against the old driver in a simulator); the logic
gained `clear_cells`/`stamp_cells`, `add_rhl` for signed offsets, and the
jackpot as two `replace_codes` sweeps. A suspected clash over `ra2`
between the monsters and the redraws turned out not to be one: every use
sets and reads it with no call between. Both agents said what's left is
single bytes.
