# Ninja Massacre for the BBC Micro: a project brief

*Written on 2026-10-15, before the port began, and kept as it was. Its
research scripts (`nmscripts/` and the scratchpad files it names) lived in
a scratch directory and aren't kept; what the port needs of them is
rebuilt in `tools/` as it goes (docs/journal.md).*

A brief for porting *Ninja Massacre* (Codemasters, 1989) from the ZX
Spectrum to the BBC Micro, run the way *Chuckie Egg 2* was
(`chuckie-egg-2-beeb`, "CE2" below), and taking in the music conversion
already done in `mattgodbolt/nm` ("nm" below).

How to read the tags:

- **[measured]**: I ran it or read the bytes myself on 2026-10-15. The
  tools and files are named.
- **[source]**: a published source says so. The link is given.
- **[inferred]**: my reading of the evidence. Check it before relying on it.

Addresses are the Spectrum's, in `&` hex. Bank 1 is the 128K music bank;
everything else is the 48K map (bank 5, 2 and 0 on a 128K).

---

## 1. What the original is

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
  - a byte with bit 7 set is a run of `byte & &7F`, and the next byte is
    the count;
  - otherwise the byte is a single tile.
- **The decoder supplies the border.** The packed data holds the 30 x 30
  inside, and the decoder adds the walls around it.
- **The decorations are random.** After decoding, wall and decoration
  tiles get random variants from the Z80's refresh register, `LD A,R`
  (`&C3AE`, `&C3C3`).
- **The start is marked.** `&7F` marks the start. It sets the players'
  position and the view (`&C3CD`).
- **The sizes** [measured]:
  - 44 to 786 bytes a level, mean 479
  - 49 tile codes in use
  - ZX02 (CE2's `tools/zx02.py`) packs all 50 decoded maps into 9,837
    bytes, or 9,617 as one stream, against the original's 23,998
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
- The slide moves the screen with block copies (`&DC86-&DCB6`, `LDIR` and
  `LDDR`), then draws the new strip.
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
  level pointer. Script: `nmscripts/levelscan2.py`.
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

---

## 2. The process carried over from CE2

**Section 3 of the Magicland Dizzy brief applies as written.** It covers the
rules, the repository's shape, the toolchain, the BBC and Spectrum tools,
CI, the reusable code in CE2's `src/` and `docs/optimising.md`. Only what
differs is listed here.

### Easier than CE2, or than Dizzy

- **Everything is on the character grid.** The drawing is copies of 1-bit
  blocks coloured as they go: no shifting, masking or clash. CE2's 2bpp
  colour lookup (`sprite.6502`) is most of what's needed.
- **The code is small.** It is 7,388 bytes in one block, with the data in
  clean blocks beside it. A complete disassembly is within reach,
  unlike Magicland's [inferred].
- **No separate front end is needed.** CE2 needed `MENU` for saves and
  high scores. This game has neither: it has passwords, and its menu is
  part of the game. Transcribe the menu with the rest. A loader picks the
  edition (CE2 decision 29's test for sideways RAM) [inferred].

### Adapt

- **`tools/fetch_original.sh`**: the archive.org TOSEC path above, hash
  checked. Fetch Spectrum Computing's map and instructions too.
- **`tools/zx.py`** needs four changes. All but the last are made in this
  brief's `nmscripts/nmzx.py` [measured]:
  - **Saving a snapshot fails on a 128K machine.** `>name` stops with
    `'Spectrum' object has no attribute 'ay'`: SkoolKit's `get_state` wants
    the tracer to keep the AY's registers. Keep them, with the selected
    register.
  - **Count 128K frames.** Use 70,908 T-states a frame, not the 48K's
    69,888.
  - **Log the AY and beeper writes** with their T-states. That is the
    oracle for `make sound` and `make music`.
  - **Hook every `LD A,R`.** Stop at each of the 13 sites, set A from the
    shared generator, and step past (D5).
- **`passlog`/`passcmp`**: log at `&C014`, the top of the main loop. Log
  the players (`&BA49-&BA4F`, `&BA5D`), the view, the strength and
  treasure, and the map's monster tiles in the scanned quarter. Compare pass
  by pass, as CE2 does. A scroll is one pass, so log its eight steps
  separately (`&DC86`).
- **`zxrooms.py` and `roomcmp.py` become `zxlevels`**. Decode each level
  with the original's `&C418`, with the shared random numbers. Keep the
  32 x 32 map, then draw views with `&C54C` at chosen origins. Compare maps
  byte for byte and views pixel for pixel.
- **`mkrooms.py` and `packrooms.py` become `mklevels.py`.** This brief's
  `nmscripts/levels.py` already decodes all 50 levels. Repack them with
  ZX02, or keep the original's runs (D2).
- **`mkgfx.py`**: the 192 blocks, colour-free. It could drop the 30
  mirrored frames and the blank lines (CE2 decision 26's method).
- **`mkmusic.py`** isn't used: CE2's takes MIDI. The music comes from the
  original's driver instead (D3), with nm's `dw_decode.py` as the model and
  its PSG captures as fixtures.
- **`colourstats.py`**: this brief's `levelscan2.py` is a first version
  (D1).

---

## 3. Decisions to make first

These are numbered for discussion, not for `decisions.md` yet.

### D1. Screen mode and colour

Geometry is CE2's either way: 256 x 192, with the CRTC narrowed (R1 = 64,
R6 = 24) and 12K at the top of RAM. The playfield and the panel share every
scan line, so a palette split (CE2 decision 15) can't give the panel its
own colours.

The colour figures are the share of lit playfield pixels shown in their own
hue [measured: section 1]. They count walls and floor, which are most
pixels. The question is really what the players, monsters and items lose:
that 17.5%.

| Option | Detail kept | Colour kept |
|---|---|---|
| **A. MODE 1, one palette per level** | every pixel | |
|  - black, yellow, the level's floor colour, cyan | | 87.7% |
|  - black and the level's 3 commonest inks | | mean 92.9%, worst level 73.9% |
| A + a split per character row for the 4th colour | every pixel | 97.5%; rows still short in 27% of cases |
| **B. MODE 2, 8 colours, 128 x 192** | half the width: **45% of the graphics' lit pixels** sit in a pair with an unlit one, and each pair becomes one pixel [measured over all 192 blocks] | 100% |

**Recommendation: A, with one palette per level, chosen offline from the
oracle (CE2 decision 2's method).**

- B would halve the bricks, the ninjas and the font, and they are this
  game's look.
- Per-row splits would need an interrupt every 8 lines. Sprites move a row
  at a time, so the splits would also change colour from pass to pass.
  They aren't worth it to begin with.
- Three things to decide with figures in hand:
  - **The 4th colour.** Cyan keeps player 1 in its colour. In a
    two-player game, player 2 (green) then needs a stand-in.
  - **The panel.** It needs yellow, white, cyan, green and blue, from the
    level's four. One idea is to give each player's box the player's
    colour, but that's only possible if both are in the palette.
  - **Tile `&13`'s flash.** The BBC's hardware flash could carry it, but
    it would take one of the four logical colours, so use it only where
    it fits.

### D2. Memory and editions

The game needs about 42K of code and data on the Spectrum: 7.4K of
code, 6.1K of graphics, 24K of levels, and the rest small. Add 2.9K of
music on 128K. A Model B has about 19-20K free beside a 12K screen once
the game owns the machine (CE2 decision 3, `memory-map.md`).

| Item | Spectrum [measured] | BBC [inferred] |
|---|---|---|
| Code and inline text | 7,388 | 7.5-10K (6502 code is seldom smaller) |
| Variables, the interrupt | ~450 | in zero page and LowState |
| Graphics | 6,144 | 6.1K, or about 4.8K with the mirrored frames and blank lines dropped |
| Font | ~496 | 0.5K |
| Tables (tile colours, passwords) | ~160 | 0.2K |
| The level being played | 1,024 | 1K |
| All 50 levels | 23,998 | 9.8K with ZX02 [measured] |
| One level | up to 786 | up to 786, or less packed |
| Panel art | none (the loading screen) | none, if the loader draws it once |
| 2bpp lookup tables | none | a few hundred bytes |
| Music | 2,946 (the driver and 875 bytes of songs) | about 2.5-3K as a 6502 driver (D3), or 6.5K by nm's route for song 0 alone |
| Disc reader | none | CE2S's, about 0.3K |

Options:

1. **A Model B with 16K of sideways RAM, or a Master.** The bank holds the
   packed levels (9.8K) and the music. Everything else is in main RAM. It
   fits with room to spare, and needs no disc access in play, so MMFS
   works.
2. **A stock 32K Model B, reading each level from disc as it starts.** This
   is far easier than CE2S:
   - one read a level, of under 800 bytes;
   - at the "LEVEL nn" screen, where the original already waits about a
     second (`&C390`: two 65,536-step delay loops);
   - no cache and no reading ahead.

   CE2's NMI reader (`disc.6502`) carries over. What's resident comes to
   about 16-20K without music, so it fits. With music it's about 18.5-23K,
   right at the edge.
3. All levels resident on a stock B: 9.8K of levels on top of about 18K.
   It doesn't fit.

**Recommendation:** build edition 1 first, on the B and the Master, with
the music. Design the level loading so that edition 2 is a change of where
one level's bytes come from, as CE2's records did for CE2S.

Then decide edition 2's music once the 6502 code's size is known. Matt
made nm because of the tune, so leaving the music out of an edition is a
question for Matt, not a default. Support the Master from the start:
CE2 paid for adding it late (decisions 14, 16 and 33).

### D3. Music and sound

**The sound effects**: the original's beeper effects on the SN76489,
written directly, as CE2 decision 12 did. Each effect's length is
measured from the original and kept as a wait, because the beeper stops
the game while it sounds (D4).

**The music has two routes:**

- **(a) nm's pipeline as it is.** It records the AY registers, converts
  them to SN76489 data offline (`ym2sn.py -b`), and packs them with LZ4
  (VGC). Simon Morris's bass player plays the result.
  - Song 0 is 3,745 bytes of data, plus 757 bytes of player and 2K of
    decode buffers.
  - The jingles need another format: nm's README says they are too short
    for the packer.
  - It plays what the chip did, but it's a recording of the original, not
    the original's logic.
- **(b) Transcribe Whittaker's driver to 6502.** Keep the original's song
  data (875 bytes, plus about 0.4K of tables). Convert the AY registers to
  the SN76489 as each frame is played.
  - **Periods**: the SN's period is the AY's times about 1.128 (4 MHz/32
    against 1.7734 MHz/16). Use nm's bass flag above the SN's range.
  - **Volumes**: map the AY's steps to the SN's.
  - **Noise**: map it to the SN's noise channel.
  - **The model is `dw_decode.py`.** It is a faithful Python port of the
    driver: 3,500/3,500 frames of song 0 and every jingle match the
    captures [measured here, against the tape's bank].
  - It would be tested as CE2's `make music` is: the 6502 driver's shadow
    AY registers against `dw_decode.py`'s, frame for frame.

**Recommendation: (b).** It is rule 1 applied to the music, and it plays
all seven songs, the jingles included. It is about a third of (a)'s memory
for song 0 alone. Keep nm's disc as the listening reference.

Whichever route, nm's bass technique comes too. The SN can't go below
about 122 Hz, and about 79% of frames have a lower tone (nm's README). How
it works:

- The channel is set to period 1, which is almost DC.
- A VIA timer interrupt toggles the channel's volume at the bass note's
  frequency, to make the square wave.
- Channel 0 uses the User VIA's T1, channel 1 the User VIA's T2, and
  channel 2 the System VIA's T2.

What that means here:

- **The timers.** CE2 used the User VIA's T1 for its palette bands and
  T2 for sound timing. With one palette per level (D1) and the effects
  timed some other way, all three timers are free for the bass. Keep it
  that way, or give the bass up on one channel.
- **The B's 6502.** nm says its player needs 65C02 instructions (`stz`,
  `phx`, `bra`). The upstream file has `IF MASTER ... ELSE` paths at some
  of those [measured: read `vgcplayer_bass.asm`]. Whether it assembles and
  plays on a B is untested.
- **When it runs.** nm's player runs from a foreground loop that polls
  VSync, with `SEI` around its update. A game needs it in the VSync
  interrupt (CE2's `music.6502`), where the bass interrupts are held off
  until the update ends: up to an update's length, once a frame. Either
  re-enable interrupts in the VSync handler after acknowledging it, or keep
  the update short (route (b) is a short update). Measure the jitter.
- **The bass interrupt writes the chip too.** It writes port A, then
  strobes the latch, from the interrupt. On the Spectrum, the music (AY)
  and the effects (beeper) are separate devices, so they never meet. Here
  they share four channels. The pieces:
  - **Every write from outside the interrupts holds them off**, with `SEI`
    or CE2's `mu_busy` (decision 46), across the port A write and the
    strobe. A two-byte tone write needs both bytes covered: a volume write
    from the interrupt between them would latch another register, and the
    second byte would land there.
  - **Who owns each channel.** An effect takes a channel, as CE2's
    movement tick does. The music stops writing it **and its bass timer
    stops**, or the interrupt keeps toggling the effect's volume. When the
    effect ends, the music's note comes back.
  - **The noise channel.** The music's drums use noise, and so do the
    effects (the noise burst). Decide which wins, as CE2 decision 48 did
    for the train.
- **The disc reads** (edition 2) are NMIs. They delay the bass interrupts
  during a level's read. The original plays music then (song 0 starts
  after the LEVEL screen). Mute the bass during the read, or accept a
  rough note (compare CE2 decision 50).

### D4. The pace of a pass

The original doesn't sync to the frame (section 1). It keeps its speed
by padding: each tile the monsters' scan finds empty costs a fixed delay.
**Port the decision, not the loop:** a pass takes a fixed time on the BBC.

Options:

- **A timer at the original's measured pass length**: about 1.22 frames,
  24.4 ms, or a figure per kind of pass. The System VIA's T1 is free once
  the OS's 100 Hz tick is stopped.
- **VSync counts**: 1 frame (about 20% fast), 2 (about 60% slow), or 1
  and 2 alternately (1.5, about 20% slow).

**Recommendation:** the timer, with its period a numbered decision that
records the measurement and its date. Beeper effects add their measured
length to the pass, as on the Spectrum. The slide's eight steps keep the
original's time per step. Pass-by-pass comparison (CE2's `make passes`)
doesn't depend on the pace, so this can be settled late.

Estimate for the slide [inferred]:

- Copying the 24 x 24 playfield in MODE 1 is 9,216 bytes.
- At about 9 cycles a byte that is about 2.1 frames, plus about 0.5 for the
  new strip of tiles.
- So about 2.6 frames a step, against the Spectrum's 2-3.

The CRTC's hardware scroll would be faster, but it moves the panel too.
Keep it in reserve.

### D5. Random numbers

The original takes them from R, and a 6502 has no R.

- **On the BBC:** one generator, a small LFSR, called at each of the 13
  sites.
- **In the oracle:** the same generator, fed in by the `LD A,R` hook (Adapt
  above), so the two machines get the same numbers in the same order.

Pass-by-pass comparison, and drawing a level's walls the same way,
depend on this.

### D6. Input and two players

- **The keys.** Defaults Q, A, O, P and SPACE for player 1, which are all
  on the BBC. Player 2's defaults come from the redefine table. Transcribe
  the redefine screen.
- **EXTEND MODE (quit, pause, music).** It needs a BBC combination, such as
  SHIFT+CTRL with the same letter. That's a decision.
- **Joysticks.** None at first (CE2 decision 17). Kempston isn't on the
  BBC. The BBC's two analogue joysticks would suit the two players later.
- **Two players on one keyboard** means 4-6 keys held at once. Test for
  ghosting on real hardware early (Risks).

---

## 4. Risks and unknowns

- **No disassembly yet.** The code is small and in one block, but
  self-modifying code and inline strings need care. The music driver is
  self-modifying (dw_decode.py's notes).
- **Timing** (D4): the original runs free. Pass-by-pass comparison is
  fine, but how the game feels depends on choosing the pace well. Measure
  what makes passes longer: monsters on screen, two players, effects.
- **Random numbers** (D5): without the shared hook, no comparison past the
  first random choice will match.
- **Colour** (D1): one palette a level loses colour on players, monsters
  and items, and the panel can't keep all its colours. That needs Matt's
  eye, on screenshots side by side.
- **The music on the SN76489** (D3): the bass interrupts, the shared chip
  and the jitter. nm has played in jsbeeb as a Master. Whether its bass
  sounds right on real hardware is an open question, and so is jsbeeb's
  fidelity there.
- **Keyboard ghosting** with two players [inferred]: the BBC's matrix may
  report phantom keys with three or more held. Test it on the B and the
  Master.
- **Memory on a stock B with music** (D2): right at the edge.
- **The slide's speed** in 2bpp (D4): estimated, not measured.
- **The tape's provenance.** Only an `[a]` tape is in TOSEC. Its code and
  data match two independent snapshots, so the risk is small.
- **Rights**: distribution denied (section 1).
- **jsbeeb is kind.** Raster timing, NMIs and interrupt-driven bass all
  need checking on b2 and on Matt's Master.

---

## 5. A plan in layers

Each layer is visible in jsbeeb and checked against the original before the
next starts. Sizes are by what each touches.

0. **Skeleton.**
   - The repo from CE2's shape, `make fetch` (archive.org TOSEC, hash
     checked), `make venv` and `make zx` (48K and 128K snapshots).
   - `tools/zx.py` with the 128K changes and the R hook.
   - CI building an empty disc.
   - *Check*: the oracle reaches play and saves a 128K snapshot.
1. **Disassembly** (`disasm/*.ctl`, `docs/research.md`). Starting points
   are in section 1:
   - the main loop `&C014`, the level decoder `&C418` and the view
     `&C54C`;
   - the slide `&DC86`, the tile drawer `&C59A` and the players
     `&D4AB`/`&D4E1`;
   - the monsters `&CE77`/`&CF0E`, the touch dispatch `&D1D7` and the
     printing `&D995`;
   - the music hooks `&B8E1`-`&B929`, the 13 `LD A,R` sites and the 7
     beeper sites.

   Then the exact budget, and D2.

   *Check*: `make disasm` builds, and the regions add up.
2. **The screen.** MODE 1 at 256 x 192, the panel from the loading screen,
   the font, and drawing a block in a colour. *Check*: a test pattern and
   the panel, read back from screen memory.
3. **Levels.**
   - The decoder, with the shared generator.
   - The oracle decodes all 50 levels, and the maps are compared byte for
     byte.
   - The view drawn at chosen origins, compared pixel for pixel.
4. **Colour.** The per-level palettes and the panel (D1). *Check*: own-hue
   figures per level recorded in a decision, and screenshots side by side.
5. **The players and the view.** Movement, walls, the slide and the pace
   (D4). *Check*: scenarios compared pass by pass, and the slide step by
   step.
6. **Monsters, trap doors and stars.** The quarter-view scan, the
   monsters' moves, throwing, hits and the spreading tile. *Check*: a
   scenario for every outcome.
7. **Items and the game around them.** Keys and doors, chests, food,
   strength, treasure, exits, the next level, passwords, two players and
   game over. *Check*: scenarios, with the passwords reaching levels 5-40.
8. **Sound effects** on the SN76489. *Check*: the chip's bytes against the
   original's beeper timings, as `make sound` does.
9. **Music** (D3):
   - the 6502 driver, with all seven songs;
   - the AY-to-SN mapping and the bass;
   - sharing the chip with the effects;
   - EXTEND+T.

   *Check*: the shadow registers frame for frame against `dw_decode.py`.
   Then the chip's bytes, as CE2's `make music` does. Then by ear against
   nm.
10. **The front end and the loader.** The legend as the attract screen,
    the menu, redefining keys, the password, finding sideways RAM, the
    Master, BREAK. *Check*: `make check` on the B and the Master in CI.
11. **The stock-B edition**, with each level read from disc (D2).
12. **Real hardware**: the bass, the disc and the keyboard.

---

## 6. First concrete steps

1. Make the repo from CE2's skeleton: `Makefile`, `tools/`, `docs/`, CI and
   `CLAUDE.md` with the rules. Include the attribution and session-link
   rules, and the rule on numbers the build works out.
2. `tools/fetch_original.sh`: the TOSEC TZX by the path in section 1, its
   SHA-256 in `original/SHA256SUMS`, plus Spectrum Computing's map and
   instructions.
3. `make zx`: `tap2sna.py -c machine=128 -s 49152` to `build/nm128.z80`, and
   `machine=48` to `build/nm48.z80`. Both worked here.
4. Bring `tools/zx.py` up to 128K (`nmscripts/nmzx.py` shows what's
   needed). Add the `LD A,R` hook. Take an execution map over a long
   scripted game.
5. The first `.ctl`: the regions in section 1's table, the routines named
   in layer 1, and the music bank labelled from `dw_decode.py`'s
   docstring.
6. `mklevels.py` from `nmscripts/levels.py`, and the levels oracle. Then
   the first view on the BBC.
7. Put D1-D6 to Matt with these figures, and `docs/research.md` with the
   budget.

---

## 7. Magicland Dizzy's music: is it the same driver?

**No** [measured]. Magicland's 128K music is credited to David Whittaker,
but it uses a different player and a different data format. nm's
`dw_decode.py` and the route in D3 (b) won't carry it.

### The evidence

The files:

- Ninja Massacre's music bank: the tape's last block, 2,946 bytes at
  `&C000`.
- Magicland's bank 3: its tape's last block, 16,384 bytes; the music runs
  `&C000-&EA52`.
- The Spectrum Computing AY rips of both Dizzy games.

What was found:

- **Shared bytes**: only 33 of Ninja Massacre's 2,946 bytes appear in
  Magicland's bank in runs of 10 or more (46 at runs of 6). The runs are
  part of a period table and a few bytes of effects code.
- **Fantasy World Dizzy (Dizzy III, 1989), by contrast, uses Ninja
  Massacre's driver.**
  - 675 bytes are shared in runs of 10 or more (765 at 6): the row
    advance, the renderer, the commands and the period table.
  - FWD has the same entry table at `&C000`: init, tick, stop and effects,
    with the tick at `&C0CD` in both.
  - It has 7 songs, like Ninja Massacre.
- **Different note tables.**
  - Ninja Massacre's starts 3832, 3600, 3424 (`&C498`).
  - Magicland's starts 3625, 3421, 3228 (`&C4FB`), which is closer to
    equal temperament.
- **A different player design.**
  - Magicland's player keeps a list of patterns ending in `&FFFF`, and
    patterns of 64 rows (`AND &3F`).
  - It processes four 10-byte track records each tick (`&C082-&C0AE`).
  - Its init sets pointers rather than reading a song table.
  - Ninja Massacre's has a song table of speeds and three pattern lists,
    with a command set in the stream.
- **Two copies.** Magicland's bank holds the player twice: at `&C000`
  (data `&C5BE`) and `&D300` (data `&D8D1`). The rip's two songs use them
  (song 0: interrupt `&C033`; song 1: init `&D300`, interrupt `&D333`).
  The code is the same apart from addresses [measured for the entry code;
  inferred for the rest].
- **dw_decode.py on Magicland's bank** gives nonsense: pattern address 0,
  then notes "A#0" lasting 35, 221 and 197 rows. On Ninja Massacre's bank,
  as a control, it matches 3,500/3,500 frames of song 0 and every jingle.

### What would carry Magicland's music

- **nm's capture route is independent of the driver** [inferred].
  - Run Magicland's tick (`&C033` or `&D333`) once a frame under SkoolKit,
    as `ay_capture.py` does with Ninja Massacre's.
  - Record the AY registers, and convert them with `ym2sn.py`.
  - The bass technique and the chip-sharing points in D3 apply as they
    are.
- **A transcription like D3 (b)** would mean disassembling Magicland's
  player first.
- **Fantasy World Dizzy's music** could be read by `dw_decode.py` with its
  table addresses moved [inferred].

---

*Measurements and scripts for this brief are in this scratchpad:*

- *`nmscripts/`:*
  - *`nmzx.py`: zx.py with AY state, port log and execution map*
  - *`levels.py`, `lvpack.py`: the level decoder, and ZX02 sizes*
  - *`levelscan2.py`, `colrandom.py`, `attrstats.py`: colour*
  - *`passlen2.py`, `passlen3.py`, `pcprof.py`: pass timing and profile*
  - *`blocks.py`: the graphics*
  - *`match.py`, `ayinfo.py`: the driver comparison*
  - *`dis.py`, `banks.py`*
- *`nm/`: the tape blocks, snapshots, banks, disassembly and logs*
- *`mld/`: Magicland's blocks and banks*
- *`shots/`: screenshots, the graphics sheet `nm_blocks.png` and the level
  sheet `nm_levels.png`*

*The downloads are in `dl-nm-tosec/` and `dl-nm-sc/`, and a copy of nm's
snapshot is in `nm-snap/`.*
