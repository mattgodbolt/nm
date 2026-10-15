# Research: the original

What *Ninja Massacre* is and how it works, from its bytes. It starts from
the brief's research (2026-10-15, `docs/brief.md` section 1) and grows as
the disassembly does (`disasm/*.ctl`, `make disasm`).

Tags: **[measured]** = run or read from the bytes, with the tool named;
**[source]** = a published source, linked; **[inferred]** = a reading of the
evidence, to check before relying on it. Addresses are the Spectrum's, in
`&` hex. Bank 1 is the 128K music bank; everything else is the 48K map.

The details, routine by routine, are in `docs/research/`:
`core.md` (start-up, the main loop, levels, the view, printing, the menu
and the status), `players.md` (the players, their controls and the stars)
and `monsters.md` (the monsters, trap doors, touching and items), with
`disasm/*.ctl` labelling the same routines for `make disasm`.

## What the original is

### Facts

| | |
|---|---|
| Title | *Ninja Massacre*, Code Masters, 1989, £2.99 [source: [Spectrum Computing 9384](https://spectrumcomputing.co.uk/entry/9384)] |
| Who | Coding and graphics Adam Waring; graphics Neil Adamson; music and effects David Whittaker; project leader Tim Miller; production Mike Clark and Stew Regan; design and illustration Nigel Fletcher [source: the [instructions](https://spectrumcomputing.co.uk/pub/sinclair/games-info/n/NinjaMassacre.txt)]. The menu says "WRITTEN BY ADAM WARING / TAG COMPUTER GAMES" [measured: screenshot] |
| Machine | 48K/128K, one tape for both [source, and measured below] |
| Kind | A Gauntlet clone, seen from above: 50 levels, one or two players at once, throwing stars and hand-to-hand fighting, keys for doors and chests, food for strength, "trap doors" that spawn monsters, a password every fifth level [source: instructions] |
| Other machines | Amstrad CPC and C64 [source: Spectrum Computing]. No Acorn version found |
| Reception | Crash 45%, Your Sinclair 2/10 [source: Spectrum Computing] |
| Existing work | No disassembly, published source, remake or BBC/Electron port found (web, GitHub code search, Spectrum Computing; 2026-10-15). The only BBC work is nm, the music. Spectrum Computing has a full map of the 50 levels (Ladderman, 2005), the instructions and the IBSA inlay text |

### Getting the original

- Spectrum Computing, World of Spectrum and ZXArt mark the tape
  "distribution denied" [source]. CE2's `make fetch` won't work as it is.
- **archive.org's TOSEC set has it**, in
  [`zx_spectrum_tosec_set_september_2023`](https://archive.org/details/zx_spectrum_tosec_set_september_2023)
  → `Games.zip` → `Games/Ninja Massacre/`. Only an `[a]` (alternate) tape
  is there:
  - `Ninja Massacre (1989)(Code Masters)(48K-128K)[a].tzx`, 59,179 bytes,
    SHA-256 `1f606851726fa51e22530b9ffb45dea4e6feab579912a30909c63c8af7442e75`
  - the same as `.tap`, and `(128K).z80`, `(128K)[a].z80` and other
    snapshots, plus Russian hacks.
- **Three copies agree** [measured]: a SkoolKit load of the TOSEC tape, the
  TOSEC `(128K).z80`, and nm's `Ninja Massacre (1989)(Codemasters)[a][128K].z80`
  match in every byte of code and data. They differ only in a few bytes of
  state (the stack, the music driver's counters, `&BA52`, `&FF2A`). So
  nm's snapshot is a tape load taken just after start, and dw_decode.py
  verifies all seven songs frame for frame against the tape's bank.

### The tape, and what it loads [measured]

`tapinfo.py`, then `tap2sna.py -c machine=48|128 -s 49152` (both work)
from CE2's `.venv` (SkoolKit 10.1). The blocks are:

1. BASIC `ninja`
2. `loader`: 64 bytes at `&FFA0`
3. 49,056 bytes at `&4000-&FF9F` (the whole 48K, screen area included)
4. a 6,912-byte screen at `&4000` (the loading screen, over block 3's
   first part)
5. 2,946 bytes: the AY music driver and songs. The game loads this itself
   into bank 1 at `&C000`, on 128K only

The loader then jumps to `&B9DD`. That pages ROM 0 and reads address 1:
`&AF` means a 48K ROM. The answer goes in a flag at `&B8DE`. On a 128K, it
loads block 5 into bank 1, sets IM 2 (`I` = `&FE`, every vector `&BBBB`),
and jumps to `&C000`. There's no protection.

### What 128K adds

**Only the AY music** [measured]. The sound effects are on the beeper in
both versions.

- The interrupt (`&BBBB`) does nothing on a 48K. On a 128K it pages bank
  1 and calls the driver's tick (`&C003`) every frame.
- The game calls the music only through three hooks:
  - `&B8E1`: start song A
  - `&B907`: restart song 0 when it has finished; the main loop calls it
    every pass
  - `&B929`: stop
- Bank 1 is paged only there and in the interrupt. **The driver's own
  sound-effect entry (`&C009`) is never called.**
- The songs are used like this [measured: the seven calls of `&B8E1`, and
  the value in A before each; the roles are partly inferred]:
  - **0**: the main theme, all through play, started after the "LEVEL nn"
    screen
  - **1**: at the start of a game
  - **6 and 5**: when player 1 or player 2 leaves the level
  - **2**: two call sites, `&DADC` and `&DB27`
  - **3 and 4**: no call site found
- On a 48K, the same hook plays songs 1-6 on the beeper instead. The
  player is at `&F6EE`, with its data to `&FDFC` (1,807 bytes together).
  It is a three-voice beeper player that waits on HALT under its own IM 2
  handler, so the game stops while a tune plays. There's no music in play.
- EXTEND MODE (CAPS SHIFT with SYMBOL SHIFT) with T toggles the music
  (`&B8DF`). With Q it quits, and with P it pauses (main loop, `&C031-&C05A`).
- **So: take the 128K version as the specification**, the music included.
  The rest of the game is the same code on both machines.

### The memory map [measured]

| Range | Bytes | What | Evidence |
|---|---|---|---|
| `&5B20-&B8DD` | 23,998 | the 50 levels, run-length packed | decoded (below): all 50 decode cleanly, end exactly at `&B8DD`, and match the published map |
| `&B8DE-&B941` | 100 | the 128K and music flags, the three music hooks | disassembled |
| `&B942-&BA28` | ~230 | the publisher's mastering code (saves the game to tape, reloads banks 6 and 7). Never run | disassembled |
| `&BA29-&BBBA` | ~400 | variables: players, view, counters | watched in play |
| `&BBBB-&BBE3` | 41 | the interrupt handler | disassembled |
| `&BC00-&BFFF` | 1,024 | the level being played: 32 x 32 tiles | `&C418` |
| `&C000-&DCDB` | 7,388 | **all the game's code**, with its text inline after each print call | execution maps of 48K and 128K runs; nothing executes elsewhere except the music |
| `&DD00-&F4FF` | 6,144 | **192 graphics blocks**, 16 x 16 at 1 bit a pixel (32 bytes each) | the drawer: `H = &DD + n/8` (`&C5FC`) |
| `&F500-&F6ED` | ~496 | the font, 8 x 8, indexed from `&F400` | the print routine `&D9AA` |
| `&F6EE-&FDFC` | 1,807 | the 48K beeper tune player and its data | disassembled |
| `&FE00-&FF00` | 257 | the IM 2 vector table | |
| `&FF02-&FF29` | 40 | each tile type's attribute | `&C5C0` |
| `&FF62-&FF89` | 40 | 8 passwords, for levels 5, 10 ... 40 | `&C32A` |
| bank 1 `&C000-&CB81` | 2,946 | the AY driver (`&C000-&C816`, its unused effects code included) and the song data (`&C817-&CB81`, 875 bytes) | nm's CONVERSION.md and dw_decode.py, checked here |

The status panel (the left 64 pixels) is never drawn by the game. The
game keeps the loading screen's left 8 columns: the 1 and 2 boxes, the
frame and the Codemasters logo. The rest of the loading screen is a
legend of the items and "nasties". It stays up as the attract screen until
a key is pressed [measured: screenshots; `&C487` clears only columns 8-31].

### How the engine works

#### The screen, tiles and sprites

**Everything sits on the 8 x 8 character grid** [measured]. Colour clash
can't happen. It's the easiest kind of Spectrum game to port.

- **The playfield** is columns 8-31: 24 x 24 characters, which is 12 x 12
  tiles of 16 x 16 pixels.
- **Tiles are drawn opaque**: two `LDI`s a line (`&C5B1`). Each tile also
  sets its 2 x 2 attribute cells to one ink on black paper (`&C5C0`).
- **There are no masks and no pixel shifting.** Players and monsters are
  16 x 16 too, drawn the same way, but they move in 8-pixel steps on both
  axes [measured: player 1 at x = 41 is drawn in columns 17-18, and at
  y = 43 in rows 3-4].
- **The 192 graphics blocks** [measured: drawn out]:
  - 40 tile types (`&00-&27`): floor, walls, items, doors, chests and the
    trap doors
  - 8 star frames (`&28-&2F`)
  - 144 character frames (`&30-&BF`): 9 sets of 16, which is the ninja
    and 8 "nasties" [inferred from the legend]
- **What could be packed** [measured]:
  - 30 of the character frames are mirror images of others (960 bytes)
  - there are 208 blank lines (416 bytes)
  - no two blocks are identical

#### Levels

- **Each level is a 32 x 32 tile map**, packed as runs (`&C418`):
  - a byte with bit 7 set is a run of tile `byte & &7F`, and the next
    byte, n, makes it n + 1 tiles long (256 if n is 0) [measured:
    `tools/levelcheck.py` against the original's decoder; the brief had
    it one short];
  - otherwise the byte is a single tile.
- **The decoder supplies the border.** The packed data holds the 30 x 30
  inside, and the decoder adds the walls around it.
- **Random bits that don't show.** After decoding, `&C3AE` sets random
  bits 3-4 on trap doors (`&20-&26`), which the drawing masks off, and
  `&C3C3` swaps the nibbles of monsters (`&28-&2F` in the data, becoming
  `&8x-&Fx`) and gives them random bits 2-3: their health
  (docs/research/core.md, docs/research/monsters.md).
- **The start is marked.** `&7F` marks the start. It sets the players'
  position and the view (`&C3CD`).
- **The sizes** [measured]:
  - 44 to 786 bytes a level, mean 479
  - 49 tile codes in use
  - ZX02 packs the 50 decoded maps, each on its own, into about 10.7K,
    against the original's 23,998 (decision 4)
- **The floor colour cycles** red, magenta, green, blue by level:
  `((level + 1) AND 3) + 1`, also used for tiles `&16` and `&1E` (`&C357`).
- **Tile `&13` flashes.** Its attribute is `&9C`: green on magenta, with
  FLASH. It spreads into empty neighbouring cells (`&D157`, run every
  pass). The BBC's own flashing green/magenta colour is that pair
  [inferred].

#### The view

**The view scrolls by pushing** [measured]. When a player nears an edge,
the whole view slides 8 tiles in 8 steps of one tile (16 pixels). Each step
takes 2-3 frames, about 20 frames in all, and play stops while it slides.

- It all happens inside one main-loop pass: one pass measured 19.7-20
  frames.
- The view's origin is `&BA4C` and `&BA4D`, in characters (0-40).
- The slide moves the screen with block copies (`ShiftUp`/`ShiftDown`/
  `ShiftLeft`/`ShiftRight`, `&DBE8-&DCB6`, about 1.8 frames each), then
  draws the new strip.
- The whole view is redrawn by `&C54C`: 144 tiles from the map.

#### The main loop

The main loop is `&C014-&C05A` [measured: disassembled; the roles are
inferred]. It runs:

1. player 1 (`&C168`) and player 2 (`&C187`), every other pass
2. the stars (`&C632`)
3. the monsters (`&CE77`)
4. status and music restart (`&D9EC`)
5. timers (`&C121`)
6. the spreading tile (`&D132`)
7. next level when both players are out (`&C153` → `&C34F`)
8. the EXTEND-mode keys

#### Monsters

**Monsters live in the map itself**, as tile codes `&80` and up [measured:
`&CE8F`]. Each pass, `&CE77` scans a quarter of the view and its margin
(`&BA75` cycles 0-3).

- If a tile in the scan holds a monster, it moves the monster (`&CF0E`).
- If not, it burns a fixed delay (`&CF04`: 30 × `LD C,(IX+n)`).
- So a pass costs about the same however many monsters there are
  [inferred purpose].
- **That delay is 36% of all the time in play** [measured: PC sampled
  every 3,547 T-states over 60 s of random play].

#### No frame sync

**Nothing waits for the frame** [measured]. The only HALT is in the 48K
beeper player, and the interrupt only plays music. The main loop runs as
fast as its code, padded as above.

| Pass | Median | 10-90% | n |
|---|---|---|---|
| no beeper sound | **1.22 frames** | 0.89-1.82 | 1,683 |
| with a beeper sound | 1.37 frames | 1.21-1.76 (max 4.55) | 1,317 |
| scroll | ~20 frames (8 steps) | | |

*(Random play from level 1 under SkoolKit, 128K timing, frames of 70,908
T-states.)* A player moves one character every two passes [measured].

#### Objects, sound and randomness

- **Touching things**: `&D1D7` dispatches on the tile touched (keys,
  food, chests, the exit and the other tiles `&08-&1D`; players `&71` and
  `&72`; monsters `&80`+).
- **Score**: STRENGTH, which drains over time and with hits, and
  TREASURE, 6 digits each per player [measured: screenshots; source:
  instructions].
- **Sound effects**: seven beeper sites besides the border's
  (`&C4FB`, `&C50A`, `&C8CA`, `&CC8F`, `&CC93`, `&CEFC`, `&D83A`). One is a
  burst of random noise from `LD A,R`. They block the game while they
  play [measured].
- **Randomness**: 13 `LD A,R` reads in the code [measured]. These are the
  level decorations, the noise, and choices in the monsters' and items'
  code. R counts instruction fetches, so the original is deterministic
  under SkoolKit, but a 6502 can't reproduce it (D5).
- **Text** is printed by `&D995`, with the string inline after the call.
  There's little text: the menu, "LEVEL nn", "PASSWORD..", the ending's
  "WELL DONE YOUNG MAN!" [measured].

#### Controls

[measured: tried in play; source: instructions]

- The default keys are Q, A, O and P to move, and SPACE to throw a star.
- The menu offers: 1 one player, 2 two players, 3 select controls (redefine
  either player, or Kempston for either), and 4 enter password.
- Sinclair joysticks work too.

### The screen and colour [measured]

- **The playfield's paper is always black** (every cell sampled). Bright is
  used only in the panel.
- **What was measured**: every lit playfield pixel by its ink, over all 50
  levels, 30 s of random play each, every 10th frame. Each level was
  started by breaking at `&C34F` and setting the level number and the
  level pointer. Script: `the brief's colour scan`.
- **The lit pixels by ink**:
  - yellow 69.9% (walls)
  - green 8.0%, blue 5.5%, white 5.3%, cyan 5.2%, red 3.4%, magenta 2.7%
- **Players, monsters and items**: 17.5% of lit pixels are neither yellow
  nor that level's floor colour. Of those: white 30%, cyan 30%, green 24%,
  blue 13%. Player 1 is cyan and player 2 green.
- **Inks per character row of the playfield**: 1-3 in 73% of rows, 4 in
  27%, and up to 5 in a few. With the panel included, 64% of rows need no
  more than 3.
- **The panel needs** yellow, white, cyan, green and blue (the logo),
  normal and bright.

### Rights (only what is public)

- The instructions say the program, code, graphics, music and artwork are
  "the copyright of CodeMasters Software Co. Ltd" [source: instructions].
  Codemasters has been part of Electronic Arts since 2021 [source:
  Wikipedia, as the Dizzy brief notes].
- Spectrum Computing, World of Spectrum and ZXArt mark the tape
  distribution denied. Those sites do that when a rights holder asks
  [source].
- nm commits the AY register captures, the converted music, its disc and
  a score made from the music. It keeps the snapshot and the memory banks
  out of the repository (`.gitignore`, and its README says so) [measured].
  nm's README links its disc to play in jsbeeb, and jsbeeb's disc list
  includes it [measured: `gh search code`].
- The tools nm uses:
  - Simon Morris's `vgm-player-bbc` and `ym2149f` are MIT [measured: `gh
    api`].
  - `vgm-packer` has no licence GitHub recognises [measured].
- As with CE2, the port's own code could be MIT, with the original's
  content credited and fetched rather than committed. Weigh the
  distribution-denied flag before publishing a disc.

