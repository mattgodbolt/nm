# The core: main loop, levels, view, printing and menu

The game's frame: start-up, the attract screen and menu, passwords, the
main loop and its pace, level set-up and the level format, the view and
the slide's screen shifts, tile drawing, printing, the status panel and the
key reading. The code is `&C000-&C631` and `&D972-&DCDB`; the data is the
font (`&F500`) and the tables in the `&FF00` page. SkoolKit entries for all
of it: `disasm/core.ctl`. The players' code is in `disasm/players.ctl` and
the monsters', objects' and front end's sub-screens in
`disasm/monsters.ctl`; their names are used here.

How each fact was checked:

- **[measured]**: run on SkoolKit's simulator (`tools/zx.py`'s `Spectrum`
  class, driven from Python: run to an address, call a routine with a
  sentinel return address, poke, peek, screenshot), or read from the
  disassembly. The experiment is named in brackets. Timings are in frames
  of the machine the run used: 69,888 T-states (48K) or 70,908 (128K).
- **[source]**: a published source, linked.
- **[inferred]**: a reading of the evidence, to check before relying on it.

One trap for the tools [measured]: on the 128K, a breakpoint anywhere in
`&C000-&FFFF` also fires inside the music driver, which runs from bank 1 at
`&C000` in the interrupt. A run to `&C014` stopped once with the stack
inside the music code. Logic experiments here use `build/nm48.z80`, which
has no paging and no interrupts.

## Summary

| Thing | Where | How it works |
|---|---|---|
| Start | `&C000` | stack, black border, reset, attract screen and menu, view, song 1, main loop |
| Main loop | `&C014-&C05A` | players, stars, monsters, status, timers, spreading tile, next level, EXTEND keys. No frame sync |
| Menu | `&C1E3-&C321` | 4 options read straight from the 1-5 half-row; colours that swap twice a frame for about 12.6 s |
| Passwords | `&FF62`, `&C322` | 8 words of 4 letters, each with a level; matched against `&FF2A` |
| Level set-up | `&C34F-&C415` | floor colour, LEVEL nn (and PASSWORD), a wait, decode, a pass over the map |
| Decoder | `&C418-&C486` | runs of `&80+t`, `n` give `n+1` tiles; the border is added |
| View | `&C54C`, `&C574` | 12 x 12 tiles from the 32 x 32 map at an origin in characters |
| Tiles | `&C59A-&C60D` | a 16 x 16 1-bit block at `&DD00 + 32n`, opaque, and one attribute from `&FF02` for its 2 x 2 cells |
| Slide shifts | `&DBE8-&DCDB` | the playfield moved two characters with LDIR or LDDR, pixels and attributes |
| Print | `&D995`, `&D999`, `&D9AA` | inline 0-terminated strings; no control codes; pixels only |
| Status | `&D9EC-&DBE7` | every 25 passes: strength drain, music restart, one-way tiles, the idle timers |
| Keys | `&D972` | any key, as ASCII through the ROM's key table |
| Smart bomb | `&C4B0-&C54A` | clears the view's monsters and generators; 6 times in 128, turns every monster in the map into a locked chest |

## 1. Start-up

### The loader and the 128K test [measured: disassembled; `&B8DE` read in both snapshots]

The tape's loader jumps to `&B9DD` (outside this file's area):

```
B9DD  DI; SP = &FFFF
      OUT (&7FFD),0 and OUT (&1FFD),0          ; ROM 0, bank 0 on a 128K
      &B8DE = (byte at address 1) - &AF          ; 0 on a 48K: its ROM has XOR A (&AF) there
      48K: JP &C000                              ; interrupts stay off for good
B9F6  128K: page bank 1 (&7FFD = &11), load the last tape block (&0B82 bytes) to &C000
      &7FFD = &10 (bank 0, ROM 1 = the 48K BASIC ROM); I = &FE, IM 2, EI; JP &C000
```

- `&B8DE` (`Is128K`) is `&52` in the 128K snapshot and 0 in the 48K one.
- During play, ROM 1 (48K BASIC) is paged in on the 128K too. That matters
  for `ReadKey`, which reads the ROM's key table (section 9).
- On a 48K, the interrupts are never enabled [measured: IFF = 0 at the
  menu].

### `Start`, `&C000` [measured]

```
C000  SP = &FFFF; border black
      ResetGame (&DBA2)          ; scores, strengths, the password typed, per-game counts
      Menu (&C1E3)               ; returns with a level set up
      DrawView (&C54C)
      song 1                     ; the opening jingle (on a 48K, the beeper: it blocks)
C014  MainLoop
```

EXTEND+Q and the end of a game come back to `&C000` [measured: code].

## 2. The main loop and its pace

### Order [measured: disassembled]

```
C014  Player1Pass (&C168)    ; if bit 0 of InPlay: move (&C978), then stamp &71 into the map
      Player2Pass (&C187)    ; if bit 1: move (&CC98), then stamp &72
      StarsUpdate (&C632)
      MonsterScan (&CE77)
      StatusTick (&D9EC)     ; does something every 25th pass
      Timers (&C121)         ; P1Skull, P2Skull, FreezeTimer, P1Heart, P2Heart: -1 each if not 0
      SpreadTick (&D132)
      InPlay AND 3 = 0? -> NextLevel (&C153)
      EXTEND (CAPS SHIFT + SYMBOL SHIFT) held?
          T: MusicToggle  (once a press: MusicKeyHeld re-arms when EXTEND is seen without T)
          Q: JP Start
          P: Pause (wait for P up, down, up)
      JR C014
```

- Each player's code is called every pass and returns at once if the
  player isn't in play. The players move one character every second pass
  [measured: `Player1`'s column while holding P: 2, 3, 3, 4, 4 ...]. That
  comes from the players' code, not from the loop.
- A player in play stamps its tile (`&71` or `&72`) into the map cells
  under it every pass (`&D1A2` with `MapStamp`): the map holds the players
  as well as the monsters.

### No frame sync [measured]

Nothing in the loop waits for the frame. A pass costs what its code costs:

| Pass (level 1, start) | Frames | Machine |
|---|---|---|
| idle | 0.755 median (0.754-0.866) | 48K, 100 passes |
| walking right | 1.115 median (1.056-1.712) | 48K, 30 passes |
| idle | about 0.8 (56,000-63,000 T) | 128K, 40 passes, with the music's interrupt |

[t2.py, t14.py.] On the 128K, an idle pass broke down as about 3,700
T-states for player 1, 50 for player 2, 130 for the stars, 48,000-54,000
for the monster scan (mostly its padding: monsters.ctl), and a few hundred
for the rest; the music interrupt adds about 4,600 when it falls in a pass.
The status tick (every 25 passes) came round every 21.1 frames idle on the
48K [t9.py]. docs/research.md has the figures for random play.

Things that stop the loop for a while, all inside one pass:

- a slide: up to 8 steps (section 6);
- the smart bomb: about 69 frames (section 8);
- the beeper's sounds, and on a 48K every song (the beeper player blocks).

## 3. The attract screen and the menu [measured: screenshots, t3.py]

`Menu`, `&C1E3`:

1. **The attract screen.** Wait for any key (`ReadKey`), then for it to be
   released. Until then the loading screen stays up: its right part is the
   legend of items and nasties.
2. **The menu.** `ClearPlayfield` (`&C1A6`) clears columns 8-31 to white
   on black and prints the title. The title is two rows of custom glyphs:
   row 1 `&2B &3A &3B-&40 &3A &2B` (dots, star, NINJA, star, dots) and row
   2 `&2A &24 &25 &26 &26 &25 &27 &28 &29 &2A` (block, MASSACRE, block). Its
   colours are copied from `TitleAttrs` (`&FF8A`, 10 cells a row). Then:

   ```
   (7,9)   WRITTEN BY ADAM WARING
   (8,11)  TAG COMPUTER GAMES
   (11,11) 1  ONE PLAYER GAME
   (13,11) 2  TWO PLAYER GAME
   (15,11) 3  SELECT CONTROLS
   (17,11) 4  ENTER  PASSWORD
   (21,9)  nnnnn0  BY  <name>       ; HighScore, 5 digits and a 0; the name is HighName
   ```

   (Row, column in characters.)
3. **The music stops, and interrupts go off** (`DI` at `&C2B5`).
4. **The key loop** (`MenuKeys`, `&C2B9`) reads the 1-5 half-row
   directly: 1 one player, 2 two players, 3 `SelectControls` (`&D5C9`), 4
   `EnterCode` (`&D58B`).
5. **The flash.** While a count of 1,280 runs, each loop also swaps rows
   4-23's colour between `&0E` (yellow on blue) and `&17` (white on red)
   (`MenuFlash`, `MenuColour`). A swap takes 0.49 frames, so both colours
   are on screen at once, in bands that roll. The count runs out after
   about 630 frames (12.6 s) on the 128K and 639 on the 48K. Then:
   - 128K: interrupts on, and song 0, the main theme, plays in the menu.
   - 48K: song 0 plays on the beeper, and the menu waits until a key is
     pressed [t15.py: it returned only when SPACE was pressed].
   - The colour stays as it was (1,280 swaps is even: `&0E`).

### Starting a game (`NewGame`, `&C30C`)

- Strength is 1,000 each (the panel shows 010000: section 7). With 1,
  `InPlay` = 1; with 2, `InPlay` = 3 and player 2 gets strength too.
- **T, A and G held** while choosing: `NewGame` returns at once, without
  setting a level up, so the game plays whatever map is at `&BC00` with
  the variables as they are. On the tape that is a leftover map, with
  white floor and `Level` = `&FF` (the next level is then level 1). A
  developer's test [measured: t11.py, screenshot].
- Otherwise, `FindPassword` (`&C322`): the level pointer is reset to the
  first level (`&5B20`), the typed password is compared with the 8 in
  `Passwords`, and on a match the levels before it are decoded only to move
  the pointer on. No match: level 0.

### Passwords [measured: dumped; t10.py]

`Passwords` (`&FF62`): 8 entries of 4 letters and the level, from 0.

| Word | Level byte | LEVEL screen shows |
|---|---|---|
| SNOW | 4 | 05 |
| EASY | 9 | 10 |
| RACK | 14 | 15 |
| BLUE | 19 | 20 |
| STAG | 24 | 25 |
| HULL | 29 | 30 |
| BEER | 34 | 35 |
| CARD | 39 | 40 |

- The word is shown on the LEVEL screen of the level it starts:
  "PASSWORD..SNOW" under "LEVEL 05" [t10.py screenshot].
- `EnterCode` (`&D58B`, monsters.ctl) prints ENTER CODE, reads 4 keys
  with `ReadKey` into `PasswordTyped` (`&FF2A`), and goes back to `Menu`.
  The attract-screen wait comes round again, so a key is needed before the
  menu shows. Typing `SNOW` then 1 started level index 4 [t10.py].
- `ResetGame` zeroes `PasswordTyped`, and `Start` calls it before the
  menu, so a password lasts only until the game it starts ends. The tape
  has "TAG!" there, which matches nothing.
- Keys are stored as `ReadKey`'s characters: CAPS SHIFT would store `&E3`.

### Select controls

`SelectControls` (`&D5C9`, monsters.ctl) offers REDEFINE or KEMPSTON for
each player. Redefining writes the half-row port and bit masks into the
players' own key-reading code (`P1Keys` `&C978`... and `P2Keys`), and the
`CPL` that inverts a key's bits is written over with `NOP` for a Kempston
[measured: disassembled `&D647-&D77C`]. So the players' key reading is
self-modifying: a port must keep the chosen keys as data instead.

## 4. The level: set-up and format

### `StartLevel`, `&C34F` [measured: t7.py, t10.py]

With A = the level (from 0) and `LevelPtr` (`&FF5E`) at its data:

1. `Level` = A. If it's 50, the game is complete (`GameComplete`,
   section 10).
2. **The floor colour**: `((level + 1) AND 3) + 1`: red, magenta, green,
   blue, red ... It is written into `TileAttrs` for tiles `&00` (floor),
   `&16` (one-way) and `&1E` (exit).
3. `ClearPlayfield` in white; "LEVEL nn" at row 10, column 16, `nn` from
   1; for a password's level, "PASSWORD.." and the word at row 13, column 13.
4. A wait of two `Delay`s of 65,536 loops: 63.8 frames [measured]. The
   music plays on through it on a 128K.
5. `DecodeLevel`: 1.4 frames [measured, level 1].
6. A pass over the map (`SetUpMap`, `&C390`): 0.8 frames.
7. Back in `Start` or `NextLevel`: `DrawView`.

### The format and `DecodeLevel`, `&C418` [measured: the original's routine against a Python model, all 50 levels, t4.py]

- The map is 32 x 32 tiles at `&BC00`, a row of 32 bytes.
- The level data holds rows 1-30, columns 1-30: 900 tiles, in order, with
  no break at the end of a row.
- **A byte below `&80` is one tile.**
- **A byte `&80 + t` starts a run**: the next byte `n` gives `n + 1` tiles
  `t`, and `n = 0` gives 256. (The run routine writes `n`, counting a 0 as
  255, and the main loop writes one more.) docs/research.md's "the next
  byte is the count" is short by one.
- Runs carry on across rows. Stepping to the next cell (`DecodeStep`,
  `&C474`) writes the side walls when it reaches column 31.
- The 50 levels sit one after another from `&5B20`. Each decode leaves
  `LevelPtr` at the next; the last ends at `&B8DD`. They are 44 to 786
  bytes. A level can only be reached by decoding all before it: so
  `FindPassword` decodes the levels it skips.
- **The border**:
  - columns 0 and 31 of rows 1-30: tile 5;
  - row 31: tile 4;
  - row 0: tile 4, or 5 above a wall (a tile 1-5 or `&11` in row 1).

What the 50 decoded maps hold [measured, t4.py]:

| Codes | Count in all 50 | What [from the tiles drawn out, and the other files] |
|---|---|---|
| `&00` | 24,793 | floor |
| `&01-&06`, `&11` | ... | walls: `&04` and `&05` the border's; `&11` and `&01-&03` crumble when hit (players.ctl) |
| `&07-&1F` | ... | keys, doors, chests, food, the items of the legend, `&13` the creeper, `&16` one-way, `&1E` exit |
| `&20-&27` | 1,483 | trap doors, 8 kinds |
| `&28-&2F` | 1,718 | monsters, 8 kinds (the 8 nasties), before set-up |
| `&7F` | 50 | the start, one a level |

### `SetUpMap`: the random bits and the start [measured: t7.py]

After decoding, one pass over the map:

- **Below `&20`, and `&27`**: left alone.
- **`&20-&26`** (trap doors): `OR (R AND &18)`: random bits 3-4. The
  drawing drops them (`DrawTile` ANDs `&27`), so they don't change the
  picture; they are state for the monsters' code (monsters.ctl). Level 1
  gave `&20` -> `&38` 11 times, `&30` 7 times, `&28` twice.
- **`&28-&2F`** (monsters): the nibbles swap, so `&2t` becomes `&8t`-`&Ft`:
  bit 7 marks a monster, and bits 4-6 hold its kind. Then `OR (R AND &0C)`,
  `AND &FC`: random bits 2-3, and bits 0-1 clear. Bits 0-1 are the
  monster's half-tile offsets (it stands a character down or right of the
  tile: `BombMonster` reads them that way). Level 1: `&28` -> `&84`, `&88`,
  `&8C`.
- **`&7F`** (the start): becomes floor. Both players' positions are set to
  it, in characters (`Player1`, `Player2`: column, row = tile * 2). The
  view's origin is 10 characters up and left of it, kept within 0-40
  (`ClampOrigin`). Level 1: the start at row 30, column 1 gives the
  players (2, 60) and the origin row 40, column 0.

So the decorations aren't random: the drawing never shows the random bits.
What R decides at set-up is the trap doors' hidden bits and the monsters'
initial bits 2-3 [inferred: their meaning is the monsters' code's].

## 5. Tiles and drawing

### `DrawTile`, `&C59A` [measured: disassembled; t12.py]

With HL a map cell and D, E a screen character (row, column):

1. A = the cell. From `&40` up (monsters, players): draw floor instead.
   They draw themselves (`DrawSprite`, players.ctl). From `&20` to `&3F`:
   `AND &27`, so the trap doors' random bits go.
2. `ColourTile` (`&C5C0`): the attribute `TileAttrs[A]` (`&FF02 + A`) goes
   in the four cells at `&5800 + 32 * D + E`.
3. `BlockAddr` (`&C5EE`): **block n is at `&DD00 + 32 * n`**: H = `&DD +
   n / 8`, L = `(n AND 7) * 32`. The 192 blocks are 16 x 16 at 1 bit a
   pixel, two bytes a line, top line first.
4. `CharAddr` (`&C5FF`): DE = the screen address of character (D, E).
5. `BlitBlock` (`&C5B1`): 16 lines of two `LDI`s, opaque. C is set to
   `&FF` so that the `LDI`s, which decrement BC, never reach B, the line
   count. `NextLineDown` (`&C946`, players.ctl) steps DE a pixel line down,
   and at the bottom of the screen it sets B = 1 so the loop ends: a block
   is clipped there.

One tile takes 2,161 T-states [measured].

### `TileAttrs`, `&FF02` [measured: dumped and drawn out]

Each of the 40 tile types has one attribute: an ink on black paper, but
`&13` (`&9C`: green ink on magenta paper, flashing). The floor's entry
(`&00`), `&16` and `&1E` are set per level (section 4). The other inks,
in tile order from `&01`:

```
01-07  6 6 6 6 6 6 4        08-0F  6 5 5 2 2 2 6 3
10-17  7 6 1 9C 7 5 - 5     18-1F  6 4 1 2 7 6 - 7
20-27  7 1 1 5 2 1 7 1
```

(`-` = the floor colour.) The smart bomb's flash adds 8 to the floor's
entry eight times, cycling its paper (section 8).

## 6. The view and the slide

### The origin [measured: disassembled; t7.py]

- `ViewOrigin` (`&BA4C`, `&BA4D`): the view's top-left in the map, **row
  then column, in characters**, 0-40. The map is 64 x 64 characters and
  the view 24 x 24. The origin is always even: it starts as a player's
  position (even) less 10, and the slide moves it by 2.
- `ViewCell` (`&C574`): the map cell of the view's character (B, C), as
  `&BC00 + 32 * ((row + B) / 2) + (column + C) / 2`.
- `DrawView` (`&C54C`): all 144 tiles, into rows 0-23, columns 8-31. 4.6
  frames [measured].

### How the slide works [measured: disassembled `&CB4C-&CC69` (players.ctl's ScrollUp... ScrollRight); timed t12.py]

When a player nears the edge of the view, the slide moves the view up to
8 tiles, one tile a step. Each step:

1. shifts the playfield 2 characters (16 pixels), pixels and attributes,
   with one of four routines here;
2. moves the origin by 2;
3. draws the strip that came into view: 12 tiles along the new edge, with
   `ViewCell` and `DrawTile`.

It stops early at the map's edge (origin 0 or 40). In a two-player game
the number of steps is cut to keep the other player in view [inferred
from `&CB4E-&CB66`: players.ctl].

| Routine | View moves | Copy | Time |
|---|---|---|---|
| `ShiftLeft` `&DBE8` | right | columns 10-31 to 8-29, LDIR, 192 lines; attributes the same | 1.80 frames |
| `ShiftRight` `&DC17` | left | columns 8-29 to 10-31, LDDR from the bottom | 1.82 |
| `ShiftUp` `&DC48` | down | lines 16-191 to 0-175 (176 lines of 24 bytes); attribute rows 2-23 to 0-21 | 1.82 |
| `ShiftDown` `&DC7F` | up | lines 0-175 to 16-191, from the bottom up; attribute rows 0-21 to 2-23 | 1.82 |

[measured: each run on a screen of random bytes and checked byte for
byte: the shifted area matches, and the rest is unchanged.] `LineDown`
(`&DCB7`) and `LineUp` (`&DCC7`) step HL a pixel line on the Spectrum's
screen. A step is about 1.8 frames of shift and 12 x 2,161 T-states of
strip, about 2.2 frames: 8 steps about 18 frames, against the ~20
docs/research.md measured for a whole slide.

docs/research.md calls the slide `&DC86`: that address is inside
`ShiftDown`'s loop.

## 7. Printing and the panel

### The print routines [measured: disassembled; every string in the area listed by a script]

- `PrintAt` (`&D995`): DE = row (D), column (E) into `PrintPos` (`&BA45`:
  column, then row), then `Print`.
- `Print` (`&D999`): the string follows the `CALL`. It prints bytes until
  0 and returns after the 0. AF and HL are kept; each character is
  printed with `EXX` around it.
- `PrintChar` (`&D9AA`): character A, with the glyph at `&F400 + 8 * A`
  (the font starts at `&F500` with character `&20`), into the screen at
  `PrintPos`. Then the column + 1: at 32, column 0 of the next row; past
  row 23, back to (0, 0).
- **There are no control codes.** Every byte but 0 is a glyph. Position is
  set only by `PrintAt`, or by writing `PrintPos`.
- **Only pixels are written.** Text takes the colour already in its
  cells: `ClearPlayfield` sets it first.
- Numbers: `Print5Digits` (`&DB71`) prints HL as 5 digits, `Print2Digits`
  (`&DB83`) the last 2, both by repeated subtraction (`PrintDigit`,
  `&DB91`). `PrintNumberAt` (`&DA9C`) is never called.

### The font, `&F500` [measured: drawn out]

8 x 8, from character `&20`:

- `&20` space, `&21` !, `&2C-&2F` , . . , and `&30-&39` digits.
- `&41-&5A` A-Z. There is no lower case.
- Custom glyphs: `&22` a key and `&23` a magic (the panel's inventories),
  `&24-&29` the title's M A S C R E, `&2A` a block, `&2B` dots, `&3A` a
  star, `&3B-&40` the title's NINJA.
- `&5B-&5C` are blank. `&5D` has only 6 bytes before the beeper player at
  `&F6EE` begins, and is never printed.

### The panel

- The panel (columns 0-7) is the loading screen's, and the game only
  prints figures and icons into it.
- **Each figure has a sixth digit**: a 0 drawn on the loading screen. So
  strength 1,000 shows as 010000, and the high score and treasure show 10
  times their value [measured: screenshots].
- Where things go (row, column):
  - player 1: strength (2,1), treasure (4,1), keys (5,1), magic (5,4);
  - player 2: the same at rows 10, 12 and 13.
  - `PrintGrid` (`&DA7E`) prints keys and magic as up to 9 icons in a
    3 x 3 grid: L copies of the glyph, then spaces.
- The panel isn't redrawn regularly: a figure changes only when the code
  that changes it calls `Print5Digits`.

## 8. The status tick and the smart bomb

### `StatusTick`, `&D9EC` [measured: t9.py, 180 s idle on level 1]

Every 25th pass (`StatusPasses`, `&FF4A`):

1. `&B907`: on a 128K, start song 0 again if the last song has ended.
2. **Strength drain**: each player in play gets -1 (`P1AddStrength`,
   `P2AddStrength`): 1,000 fell to 574 in 9,000 frames (180 s) idle on
   the 48K.
3. `CloseOneWays` (`&DA59`): each one-way tile a player walked over
   (`OneWayTable`, `&FF4B`, 8 entries) becomes `&07` once its cell is empty
   (monsters.ctl has the tile's side).
4. **The idle timers.** `IdleTicks` (`&FF49`) counts down each tick:
   - At 0: every key, door and chest (`&08-&0B`) vanishes; `IdleTicks` =
     100 (about 42 s idle on the 48K); `IdleStage` (`&FF48`) - 1.
   - When `IdleStage` reaches 0: every tile 4 and 5 (the border walls)
     becomes an exit (`&1E`). Then `IdleStage` is `&FF`, so it won't come
     round again.
   - Treasure resets both: `IdleTicks` = 100, `IdleStage` = 4
     (`P1AddTreasure`, `P2AddTreasure`).
   - **Nothing else resets them**: not a new level, not a new game. The
     tape has `IdleTicks` = 25 and `IdleStage` = 4, so in the first game,
     level 1 lost its 16 keys, doors and chests 520 frames (10 s) in
     unless treasure was taken first. The walls became exits at 6,867
     frames (137 s).

So a player who stops scoring is helped out of the level: doors open,
then every outer wall is an exit [inferred: the purpose].

### Strength and death (`P1AddStrength`, `&DAA6`) [measured: disassembled; t10.py]

Strength changes go through `P1AddStrength` / `P2AddStrength` with DE: -1
from the tick, the food's value (players.ctl), a hit's cost (monsters.ctl).

- While `P1Heart` (`&BA58`) runs, strength doesn't change.
- While `P1Armour` (`&BA56`) is set, a change is skipped when `R AND &0C`
  is 0: 1 in 4.
- Below 0, the player dies: out of play (bits 0 and 2 of `InPlay`), its
  tile cleared from the map, strength 0 printed, song 2, and on to
  `GameOver` (`&D85E`) with the player's number and treasure: the name
  entry, if it is a high score.

### `SmartBomb`, `&C4B0` [measured: t8.py, R forced to each side]

Called when a player uses a magic (`&C9A8`, `&CCCB`) or a star hits tile
`&10` (`&C794`). R chooses:

- **R ≥ 6** (122 times in 128): over the view and a margin of one tile
  (14 x 14, or 14 x 12 at the bottom: `&CE58`), every monster is removed
  (all its four cells: `BombMonster` reads bits 0-1 for its offset), and
  every other code from `&20` with low bits not 7 becomes floor: the trap
  doors but `&27`, and the players' own tiles (stamped back next pass).
- **R < 6**: over the whole map, every monster becomes a locked chest
  (`&0C`), and every other code from `&20` becomes `&0E`: every trap door,
  `&27` too, and the players' tiles.
- Then `BombFlash`: 8 times, the floor's paper colour + 1, `DrawView`,
  and `BombSound` (two sweeps of 128 clicks). About 69 frames.

## 9. Keys: `ReadKey`, `&D972` [measured: every key pressed in turn, t6.py]

- Reads the half-rows from `&FEFE` (CAPS SHIFT-V) to `&7FFE` (SPACE-B).
  The first with a key down wins, and in it the lowest bit.
- Returns Z and A = 0 if no key. Otherwise A = that half-row's keys (bits
  set) and D = the key's character, read from the 48K ROM's key table: E
  counts from `&34` down a half-row, and the entry is `&0200 + E - 8 *
  (bit + 1)`.
- The characters: A-Z and 0-9 as ASCII, SPACE `&20`, ENTER `&0D`, SYMBOL
  SHIFT `&0E`, and CAPS SHIFT `&E3`, which is the byte after the table
  (the name entry uses `&E3` to spot CAPS SHIFT for delete).
- Q and A together gave `A`: the A half-row (`&FDFE`) is read before Q's
  (`&FBFE`).
- The 128K reads ROM 1 there, which is the same 48K ROM.

Users: the attract screen's wait, `EnterCode`, the name entry and
`SelectControls` (as "any key" and for the character). In play the keys
are read by the players' own self-modified code (section 3), and the
menu reads 1-4 with its own `IN`.

### EXTEND MODE keys [measured: disassembled; t13.py]

CAPS SHIFT and SYMBOL SHIFT together, then:

- **T**: toggle the music (`MusicOff`). One toggle a press: `MusicKeyHeld`
  is set by the toggle, and cleared only when EXTEND is held without T.
- **Q**: back to `Start`.
- **P**: pause until P is released, pressed and released.
- **A 48K bug**: turning the music off calls `&B92E`, which pages bank 1 and
  calls `&C006`, the driver's stop. A 48K has no bank 1, so `&C006` is the
  game's own `CALL ResetGame : CALL Menu`. EXTEND+T in play on a 48K
  zeroed the treasure and dropped to the attract screen's wait, with the
  stack 12 bytes deep [t13.py]. On the 128K it stopped the music and
  play went on.

## 10. The end of a level, and of the game

- **`NextLevel`** (`&C153`) runs when neither player is in play (bits 0-1
  of `InPlay`). It sets up `Level` + 1, then moves bits 2-3 (left by an
  exit: `P1Exits`, `P2Exits` in monsters.ctl) down to bits 0-1, so only the
  players who got out play on. Then `ResetLevel` and `DrawView`.
- **`GameComplete`** (`&C097`) runs instead when that level would be 50
  [t10.py: `Level` poked to 49, `InPlay` to 4]:
  - "WELL DONE YOUNG MAN!" at row 6, column 10, in yellow. When both
    players got out of the last level, "MEN!" is printed over "MAN!".
  - `Tally`: each player's strength is counted down into treasure, one
    unit at a time, each change printed.
  - Then it falls into `Timers` and returns into `NextLevel`, which moves
    the exit bits down and goes back to the main loop on the last map,
    with strength 0. At the next status tick the players die of it, which
    leads to the name entry ("YOUR NAME PLAYER 1" was on screen 300 frames
    later). So the game's end is two deaths.

## 11. Random numbers: the `LD A,R` sites [measured: disassembled]

13 sites in the game's code (and one more at `&B991`, in the mastering
code, which never runs). Five are in this file's area:

| Site | Routine | What R decides |
|---|---|---|
| `&C3AE` | `SetUpMap` | a trap door's hidden bits 3-4 (`AND &18`), at each level's set-up |
| `&C3C3` | `SetUpMonster` | a monster's bits 2-3 (`AND &0C`), at set-up |
| `&C4B0` | `SmartBomb` | which outcome: R < 6 turns every monster into a chest |
| `&DAB1` | `P1AddStrength` | with `P1Armour`: skip the change when `R AND &0C` = 0 |
| `&DAFF` | `P2AddStrength` | the same for player 2 |

The other eight are in players.ctl and monsters.ctl: `&C7AF`, `&C8C6`,
`&C8CC`, `&CEF5`, `&D095`, `&D0D7`, `&D317`, `&D3AD`.

R's low 7 bits count instruction fetches, so a value depends on the
exact path the code took since the last read. `SetUpMap`'s reads come once
a cell in a fixed loop: on a given run, set-up's bits follow from R at the
start of the pass. For the port this is D5 of docs/brief.md: one shared
generator, called at each site.

## 12. Variables

Names are core.ctl's, or the other files' where they own the variable.

| Address | Name | Meaning | Written | Read |
|---|---|---|---|---|
| `&B8DE` | `Is128K` | non-zero on a 128K | loader `&B9F0` | music hooks, `&BBCD`, `MenuFlash` |
| `&B8DF` | `MusicOff` | EXTEND+T turned the music off | `MusicToggle` | `MusicToggle`, `&B8E8`, `&B90C` |
| `&B8E0` | `MusicKeyHeld` | EXTEND+T seen; cleared by EXTEND without T | `MainLoop` | `MusicToggle` |
| `&BA45` | `PrintPos` | column, row of the next character | `PrintAt`, `PrintChar`, callers | `PrintChar` |
| `&BA4B` | `MapStamp` (players.ctl) | the code `&D1A2` writes into four cells | `Player1Pass`, `Player2Pass`, `BombMonster`, deaths | `&D1B2` |
| `&BA4C` | `ViewOrigin` | the view's row, column in the map, in characters, 0-40 | `SetUpStart`, the slide | `ViewCell`, `&CE58`, sprites |
| `&BA4E` | `Player1` (players.ctl) | player 1's column, row in characters | `SetUpStart`, players' code | `Player1Pass`, many |
| `&BA50` | `P1Treasure` | | `P1AddTreasure`, `Tally`, `ResetGame` | high score check |
| `&BA52` | `P1Strength` | 1,000 at the start | `NewGame`, `P1SetStrength`, `Tally`, `ResetGame` | `P1AddStrength`, `Tally` |
| `&BA56` | `P1Armour` | skips 1 strength change in 4 | players' code; `ResetLevel` | `P1AddStrength` |
| `&BA57`, `&BA58` | `P1Skull`, `P1Heart` | timers; strength holds while `P1Heart` runs | players' code; `Timers` | players' code, `P1AddStrength` |
| `&BA59`, `&BA5A` | `P1Keys`, `P1Magic` | shown by `PrintGrid` | players' code; `ResetGame` | players' code |
| `&BA5D-&BA6B` | `Player2` ... | player 2's record, as player 1's | | |
| `&BA6C` | `FreezeTimer` (monsters.ctl) | the clock | monsters' code; `Timers` | monsters' code |
| `&BA6E` | `HighScore` (monsters.ctl) | shown by `Menu` with a 0 after it | `&D8BC` | `Menu`, `&D8B6` |
| `&BA73` | `InPlay` | bit 0 P1 in play, 1 P2; bit 2 P1 got out, 3 P2 | `NewGame`, `NextLevel`, deaths, exits | `MainLoop`, players, slide, status |
| `&BA74` | `Level` | from 0 | `StartLevel` | `NextLevel` |
| `&BA76` | `MenuColour` | `&0E` or `&17` | `MenuFlash` | `MenuFlash` |
| `&C11D` | (in `TallyMore`) | self-modified: player 1 has strength left | `Tally` | `TallyMore` |
| `&C2A7` | `HighName` | the high score's name: 10 characters of the menu's own inline string | `NameEntry` (`&D8F5`) | `Menu` |
| `&FF02` | `TileAttrs` | each tile's attribute | `StartLevel` (3 entries), `BombFlash` | `ColourTile`, sprites |
| `&FF2A` | `PasswordTyped` | 4 characters | `EnterCode`, `ResetGame` | `FindPassword` |
| `&FF34` | `StarDirs` (players.ctl) | 8 steps (row, column) | | `LaunchStar` |
| `&FF48` | `IdleStage` | idle periods left until the walls are exits | `StatusTick`, treasure | `StatusTick` |
| `&FF49` | `IdleTicks` | ticks left in this idle period | `StatusTick`, treasure | `StatusTick` |
| `&FF4A` | `StatusPasses` | passes to the next status tick (25) | `StatusTick` | `StatusTick` |
| `&FF4B` | `OneWayTable` (monsters.ctl) | 8 map addresses | `&D423`; `ResetLevel` | `CloseOneWays` |
| `&FF5E` | `LevelPtr` | the next level's data | `FindPassword`, `DecodeLevel` | `DecodeLevel` |
| `&FF62` | `Passwords` | 8 x (4 letters, level) | | `FindPassword`, `StartLevel` |
| `&FF8A` | `TitleAttrs` | 20 colours | | `ClearPlayfield` |
| `&FF5B-&FF5D`, `&FF9E-&FF9F` | | never used | | |

## 13. For the port

- **Self-modifying code** in this area: the operand at `&C11D` (`Tally`'s
  loop test) and the high-score name, which is the menu's inline string
  at `&C2A7`. Outside it, but met here: the players' key reading, which
  `SelectControls` rewrites. Keep each as a variable.
- **R** is read at five sites here (section 11); D5's shared generator
  covers them. The level's set-up reads it once per trap door and monster
  in map order: the comparison tools must feed the same numbers in the
  same order.
- **Pace**: no frame sync anywhere. The level screen's wait is a fixed
  65,536 x 2 loop (63.8 frames), the menu's flash a fixed loop too (0.49
  frames a swap), and the smart bomb's flash about 69 frames. Each is
  CPU-bound on the Spectrum: the port needs each as a measured time.
- **The menu's flash** shows both colours at once in rolling bands,
  because a swap takes half a frame. Copying the effect, not the loop, is
  a decision.
- **The idle timers carry over** between levels and games (section 8):
  that is the original's behaviour, quirk or not.
- **The 48K's EXTEND+T bug** (section 9) is a 48K artefact: the 128K is
  the specification, and there it works.
- **The panel's sixth digit** is the loading screen's: the port's panel
  must have it.
- **T+A+G** at the menu plays the map in memory: a developer's test,
  probably not worth porting, but a decision either way.
