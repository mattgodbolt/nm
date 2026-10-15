# Monsters, trap doors, the creeper and touching things

How the Spectrum original runs its monsters, trap doors and spreading
tile, and what happens when a player touches something: the code at
`&CE77-&D971` and the variables it uses. That range also holds the menus'
key entry (password, controls, the high score's name) and game over,
covered briefly at the end. The routines are labelled in
`disasm/monsters.ctl`.

Tags, as in `docs/research.md`: **[measured]** = run on SkoolKit's
simulator (`tools/zx.py`'s `Spectrum` class driven from Python, on a
one-player game started from `build/nm128.z80` at 128K timing unless
48K is said), with the experiment named; **[source]** = read from the
code; **[inferred]** = a reading to check. The experiments' scripts are in
`build/mon/` (not kept): each starts from a snapshot taken at the main
loop's top (`&C014`) in level 1, pokes tiles into the map beside player 1
(at position (60, 2), view origin (40, 0)), holds keys and reads memory
back a pass at a time. A stop at `&C014` counts as a pass only with
interrupts enabled, since the 128K's music driver passes `&C014` too.

Notation, as in `players.md`: a **position** is (row, column) in
character cells of the 64 x 64-cell map; a map tile (`&BC00`, 32 x 32)
covers 2 x 2 cells. A **pass** is one trip round the main loop. A
**sweep** is four passes: the time the monster scan takes to visit every
tile once. Player record fields are given as offsets from the record
(`&BA4E` player 1, `&BA5D` player 2: IX in the touch code), with the labels
`players.ctl` gives them.

## 1. Tile codes

Everything in the level lives in the 32 x 32 map, one byte a tile
[source: `&D569`, the touch dispatch `&D1D7`, the scan `&CE77`]. The names
are the loading screen's legend [measured: screenshot, and the blocks
drawn out].

| Code | What | Touched (section 6) |
|---|---|---|
| `&00` | floor | |
| `&01-&07` | walls; `&06` is the one the switch removes, `&07` what one-way tiles become | blocks |
| `&08` | key | taken |
| `&09`, `&0A` | door, up-down and side-to-side | needs a key |
| `&0B` | locked chest | needs a key |
| `&0C` | chest | 10 treasure |
| `&0D`, `&0E`, `&0F` | grapes, tea, rice | 25, 50, 75 strength |
| `&10` | scroll (the "magic" smart bomb) | taken |
| `&11`, `&1F` | walls | block |
| `&12` | horseshoe (`players.ctl`'s "ring") | taken |
| `&13` | the creeper, the spreading tile (green on magenta, flashing) | blocks |
| `&14` | rock | pushed |
| `&15` | teleporter | teleports |
| `&16` | one-way tile, in the floor's colour | vanishes, later a wall |
| `&17` | switch | removes every `&06` |
| `&18` | death star | taken |
| `&19` | shield | taken |
| `&1A` | idol | taken |
| `&1B` | heart | taken |
| `&1C` | ball | taken |
| `&1D` | clock | taken |
| `&1E` | the exit (stairs) | leaves the level |
| `&20-&3E` | trap door: bits 0-2 a kind, bits 3-4 a health. Kind 7 (`&27`) is the **hell hole** | hit; the hell hole kills |
| `&40-&5F` | a spawning monster (the sparkle): bits 0-2 kind, bits 3-4 health | vanishes |
| `&71`, `&72` | player 1, player 2 | shoved |
| `&7F` | a monster's cells other than its head | punched (via the head) |
| `&80-&FF` | a monster's head | punched |

- A trap door is drawn with block `&20 + (code AND 7)`: the tile drawer
  (`&C59A`) ANDs codes `&20-&3F` with `&27` [source]. The level decoder
  gives `&20-&26` a random health (`R AND &18`) and leaves `&27` alone
  (`&C3A8`) [source].
- Monsters in the level data get a random health at the start too
  (`&C3C3`, `R AND &0C`) [source]. Level 1 holds kind-0 monsters and
  kind-0 trap doors [measured: the decoded map].

### Objects cover one, two or four tiles

An object at position (B, C) covers the four cells (B, C), (B+1, C),
(B+1, C+1) and (B, C+1) [source: `&D1A2`, `&D18A`, `&D1BA`, `&D521`]. On
even (B, C) those are one tile; on an odd row or column they straddle two
or four. Players and monsters move a cell (8 pixels) at a time, so they
occupy every tile they overlap. `&D1A2` writes one code (`&BA4B`) into all
four; for a monster the head cell then gets the monster's code and the
others keep `&7F` [source: `&CF62`].

## 2. Monsters

### The code

`&80 + kind x 16 + health x 4 + offset` [source: `&CF0E`; measured:
`e2_move`]:

- **bits 4-6, kind** (0-7). The picture is block
  `&40 + kind x 16 + facing + frame`: nine sets of 16 frames, the ninja's
  at `&30`, the eight nasties' at `&40-&BF`.
- **bits 2-3, health** (0-3). The ink is `4 + health`: green, cyan,
  yellow, white [measured: `e12_colour`, attributes `&04-&07` for
  `&A0`, `&A4`, `&A8`, `&AC`].
- **bits 0-1, the half-tile offset**: bit 1 one cell down, bit 0 one cell
  right of the head cell's tile.

### The quarter scan (`MonsterScan`, `&CE77`)

Called once a pass [source: main loop `&C01D`].

- **The area** is the view and a one-tile margin, from `ViewMapPtr`
  (`&CE58`, in `players.ctl`'s range): 14 x 14 tiles starting a tile above
  and left of the view; no margin above or left when the origin is 0; 12
  rows when the view is at the bottom (origin row 40) [source; measured:
  `e1_scan`, origin (40, 0): rows 19-30, columns 0-13, 168 tiles].
- **The pattern.** Each pass visits every fourth tile of each row, and
  the next row's columns are shifted by two tiles, so a pass is a sparse
  checkerboard of 42 or 49 tiles. `&BA75` (0-3) picks the quarter; the
  four quarters visit every tile of the area exactly once [measured:
  `e1_scan`, every tile once in 4 passes, repeated].
- **No double moves.** A monster steps at most one cell; its new head
  tile is never one the same pass still has to visit [source: the column
  shift of 2 against a step of at most 1 tile].
- **At the right edge** (origin column 40) the area's last column is
  "column 32", which is the next row's column 0, the border wall: harmless
  [measured: `e17_misc`].
- **Each tile**: `&80` and up → `MonsterMove` (`&CF0E`). Anything else →
  the fixed delay `TileDelay` (`&CF04`), then `&20-&3E` → `TrapDoor`
  (`&D08F`) and `&40-&5F` → `Sparkle` (`&D0DF`) [source].
- **At the end of a sweep** (`&BA75` wraps to 0): `MoveSweep` (`&BA77`)
  toggles 0/1 and `SparkleFrame` (`&BA72`) steps 7, 6 ... 0, 7 [source;
  measured: `e2_move`].
- **Then the noise burst**, if a monster hit a player during the pass
  (`HitFlag`, `&BA98`): section 8.

### The delay (`TileDelay`, `&CF04`)

Thirty `LD C,(IX+&7B)`: 993 T-states, 1,010 with the call [measured:
`e13_cost`, 48K timing]. It pads the pass but doesn't make it even: a
monster's turn (erase, chase, draw) costs several times more.

| Monsters in the scanned area | The scan, T-states a pass [measured: `e13_cost`, 8 passes each] |
|---|---|
| none | 48,180-52,391 |
| 12, frozen (clock) | 55,855-83,192 |
| 12, moving | 52,291-118,534 |

### A monster's turn (`MonsterMove`, `&CF0E`)

1. Position = head tile + offset bits; keep it (`MonOldPos`, `&BA81`);
   clear its cells (code 0) [source].
2. `MonsterChase` (`&CFDF`) picks the step and the facing.
3. **Only on move sweeps** (`MoveSweep` = 1), try in turn: the diagonal
   step, the column step alone, the row step alone (`MonsterTry`,
   `&D066`). The first whose four cells are all empty is taken. Otherwise,
   and on every other sweep, it stays [source; measured: `e2_move`].
4. Write `&7F` into the new cells and the code, with the new offset bits,
   into the head cell.
5. Draw: if it moved, the floor block (0, in the floor's attribute
   `&FF02`) over the old position, then the monster at the new one, every
   visit [source: `&CF9D-&CFB6`].

**So a monster steps one cell every 8 passes** (once a sweep, on
alternate sweeps), about 10 frames: a quarter of a walking player's speed
(a cell every 2 passes) [measured: `e2_move`, a kind-2 monster placed at
(50, 12) moved (51, 11), (52, 10), (53, 9) ... at passes 4, 11, 13, 20,
26, 29, 35, 42: every 8 passes give or take where its tile falls in the
quarters]. Its animation frame is `MoveSweep` too.

### Choosing the step (`MonsterChase`, `&CFDF`)

- **While the clock runs** (`FreezeTimer`, `&BA6C`, non-zero) it returns
  at once: no step, and the facing (`MonFacing`, `&BA84`) isn't
  recomputed, so frozen monsters are all drawn with the facing of the last
  monster that chose a step [source].
- **The target** [source]: only player 1 in (`&BA73` bits 0-1 = 1) →
  player 1; only player 2 → player 2; both → the nearer by row distance
  plus column distance, a tie to player 2.
- **The step** is the sign of the difference on each axis (-1, 0, +1).
  **Under the target's idol** (its timer at +9, `players.ctl`'s "skull",
  non-zero) the step is negated: the monster runs away, still facing the
  player [source; measured: `e17_misc`, the monster went (50, 12),
  (49, 13), (48, 14) ... away from (60, 2)].
- **The facing** (0-14, even) [source]: 0 right or still, 2 left, 4 up,
  6 down, 8 up-right, 10 up-left, 12 down-right, 14 down-left.
- The step goes into `&BA85`/`&BA86` **column first, then row**: the
  opposite of the players, who write row then column there. The
  touch code reads them the players' way. The monsters only read their own
  step back within the same turn, so the two never mix [source].
- **No randomness**: a monster's move is fixed by the positions.

### Hitting a player (`MonsterTry`, `&D066`)

- The four cells at the new position are tested in the order above; the
  **first non-empty one** decides (`CellsEmpty`, `&D18A`) [source].
- If it is `&71` or `&72`, that player loses **kind + 1 strength**
  (`&DAA6`/`&DAF4`, core's) and `HitFlag` is set. The move is blocked
  either way [source; measured: `e3b_hits`, a kind-2 monster takes 3].
- Each of the three tries can hit, so **a monster beside a player on its
  row or column hits twice a visit** (the diagonal and the column step
  both land on the player) [measured: `e3b_hits`: beside, -6 every 8
  passes; above or diagonal, -3].
- With the player standing still, a hit comes once every 8 passes per
  monster [measured: `e3b_hits`].

### Punching a monster

The players' touch (section 6) on a monster's head runs `HitMonster`
(`&C86C`, `players.ctl`) and adds **5 treasure**; a `&7F` cell runs
`HitMarker` (`&C8A4`) to find the head, and gives no treasure itself
[source]. Each punch takes a health point; the punch after health 0 kills
it (cells cleared, erased) [measured: `e9_punch`, `&AC` (health 3) went
`&A8`, `&A4`, `&A0`, gone, at 5 treasure each]. **Kind 7 can't be hurt**,
but every punch still pays 5 treasure [measured: `e9_punch`, `&F0` and
`&FC` 16 punches, 80 treasure]. Each punch is also gated by the touch
counter (section 6).

## 3. Trap doors and spawning

### `TrapDoor` (`&D08F`)

Run when the scan visits a trap door (`&20-&3E`; `&3F` is skipped by the
scan) [source]:

- Nothing while the clock runs.
- **An ordinary trap door spawns one time in four** (`R AND 3` = 0). **A
  hell hole** (kind 7) spawns on every visit [source; measured: `e6_trap`:
  a `&3A` spawned at passes 36, 48, 64, 72, 76; a `&27` at 4, 8, 12, 16,
  20 ...].
- **Where**: the first empty neighbour tile in the order up-left, up,
  left, up-right, down-right, down, right, down-left (`SpawnOffsets`,
  `&BA87`). The table is nine bytes read as overlapping pairs: each step
  reads a row step and a column step and then advances one byte [source;
  measured: `e6_trap`, first up-left, then up]. No empty neighbour, no
  spawn.
- **What**: a sparkle, `&40 + (code AND &1F)`: the trap door's own kind
  and its *current* health. A hell hole's is `&40 + (R AND &1F)`: a random
  kind and health [source; measured: `e6_trap`, `&3A` gave `&5A`; `&27`
  gave `&40-&43`].

### The sparkle (`Sparkle`, `&D0DF`)

- Drawn as block `&28 + SparkleFrame` (the eight "star" blocks) in ink
  4 + health, each time it is scanned [source].
- **When it is scanned with `SparkleFrame` = 0 it becomes a monster**:
  `&80 + kind x 16 + health x 4`, offset 0 [source; measured: `e6_trap`,
  `&5A` became `&AC`]. All sparkles change on the same sweep, so a sparkle
  lasts 0-7 sweeps.
- A player touching a sparkle removes it, for nothing [source:
  `&D265`].

### Hitting trap doors (`TouchTrapDoor`, `&D297`)

A player touching a trap door (through the gate, section 6) takes 8 off
its code, a health point, and gets **5 treasure**; below `&20` it is gone
[source; measured: `e4_items`, `&20` gone at the first hit, 5 treasure].
Stars hit trap doors too (`players.ctl`).

**Touching a hell hole kills**: it sets the player's strength to `&FF00`,
negative, and the next strength change (`&DAA6`, run at once after the
touch with a change of 0) ends the player [source; measured: `e5_keys`,
strength 0 and the player out (`&BA73` = 0) two passes after walking into
`&27`]. Under the heart (section 7) strength changes are skipped, so the
end waits for the heart to run out [inferred].

## 4. The creeper, the spreading tile (`SpreadTick`, `&D132`)

- Called once a pass [source: main loop `&C026`]. It checks one tile
  (`Spread`, `&D157`): if it is `&13`, each empty neighbour, in the order
  left, right, below, above, becomes `&13` and is redrawn if on screen
  [source; measured: `e7_spread`].
- **The cursor** (`SpreadCursor`, `&BA95`: column, row, in cells)
  advances two tiles a pass along a row; at the end of a row it goes up a
  row and switches to the other half of the columns; past row 1 it starts
  again at row 30 with the halves swapped [source]. **It checks every tile
  of rows 1-30 once every 960 passes** [measured: `e7_spread`, the model
  matched the original for 1,100 passes; its period is 960 with 960
  distinct tiles].
- So one creeper grows by one tile in each direction about every 960
  passes, wherever it is in the map, on screen or not.
- It only spreads into floor (0). Stars wear creepers down
  (`CreeperHits`, `&BA6D`, `players.ctl`).

## 5. Map helpers (called very often)

- **`MapCell` (`&D569`)**: (B, C) in cells → HL = `&BC00 + (B/2) x 32 +
  C/2`, A = the code, Z if empty. Every object test and write goes through
  it [source].
- **`CellPos` (`&D117`)**: HL in the map → B = 2 x row, C = 2 x column
  [source].
- **`FillCells` (`&D1A2`)**: write `&BA4B` into an object's four cells.
  **`CellsEmpty` (`&D18A`)**: Z if all four are empty; otherwise A is the
  first non-empty code. The early exit is `CellEmpty` (`&D19A`) popping
  `CellsEmpty`'s return address before its RET [source].
- **`CellsFree` (`&D521`)**: the same test, with B and C restored on Z.
- **`PutPlayer` (`&D517`)**: write A into a player's four cells, keeping
  BC and HL.
- **`RedrawTile` (`&D267`)** and **`RedrawCell` (`&D181`)**: redraw a map
  tile if it is in the view. **`DrawAt` (`&CFB9`)**: draw a block at a
  position if it is within a cell of the view (the sprite drawer `&C8D8`
  clips).

## 6. Touching things (`TouchAll`, `&D1BA`, and `Touch`, `&D1D7`)

The players' movement (`&CB0C`, `&CE18`) calls `TouchAll` for each step
it tries, with the player's record in IX [source]. It clears the
results (`&FF30-&FF33`) and touches the four cells. Afterwards the
movement code adds `TouchTreasure` (`&FF31`) to the treasure and
`TouchStrength` (`&FF32`) to the strength, then looks at `TouchCode`
(`&FF33`), the last non-empty code touched: 0 moves, `&1E` leaves the
level, anything else blocks the step [source; `players.ctl`].

### The touch gate (`TouchGate`, `&D287`)

**Only every tenth contact does anything.** Each non-empty cell touched,
by either player, walls included, counts `TouchCount` (`&FF2E`) down; only
the contact that brings it to 0 runs the handler, and the count goes back
to 10 [source; measured: `e15_gate`, a key was taken on the tenth
contact]. Every contact still blocks the step. A player makes several
contacts a pass (up to three steps tried, each up to four cells), so an
item usually goes within two passes of walking into it [measured:
`e4_items`, every item at the second pass] — but punches, trap-door hits
and shoves come at a tenth of the contact rate.

### What each code does

[source; measured: `e4_items` walks player 1 into each code, `e5_keys`
gives it keys first, `e16_switch`, `e11_teleport`, `e8_shove`]

| Code | Handler | Effect |
|---|---|---|
| `&80`+ | `HitMonster` | punch (section 2), 5 treasure |
| `&7F` | `HitMarker` | finds the head and punches it |
| `&71`, `&72` | `ShoveP1`, `ShoveP2` (`&D4E1`, `&D4AB`) | the other player is moved one step the toucher's way (`&BA85`, row then column) if its four cells there are free; its old picture is erased with a click (`&CC79`). The toucher stays [measured: `e8_shove`, player 2 moved one cell a shove, about one shove every 3-4 passes] |
| `&08` key | `TakeKey` | keys (+&0B) + 1, up to 9 |
| `&09` door | `OpenDoorV` | with a key: spend it; the door and the unbroken run of `&09` above and below it go (`DoorRun`, `&D499`) [measured: a 4-tile column, one key] |
| `&0A` door | `OpenDoorH` | the same, along the row |
| `&0B` locked chest | `OpenChest` | with a key: spend it; it becomes `(R AND 6) + &0C`: a chest `&0C`, tea `&0E`, a scroll `&10`, or (`&12`) a kind-7 monster `&F0` [measured: 24 openings gave 5, 11, 4 and 4] |
| `&0C` chest | `TakeChest` | 10 treasure |
| `&0D`-`&0F` food | `TakeFood` | `(code AND 3) x 25` strength: 25, 50, 75 |
| `&10` scroll | `TakeScroll` | scrolls (+&0C, "magic") + 1, up to 9 |
| `&12` horseshoe | `TakeHorseshoe` | +&0E = `&12`: while it is set, a star hitting the other player freezes or unfreezes that player (`&C7EA`, `&C800`, `players.ctl`) |
| `&14` rock | `PushRock` | moves one tile the player's way if that tile is empty (diagonally on a diagonal step); then the player walks into the space [measured: against a wall it stays] |
| `&15` teleporter | `Teleport` | section 6.1 |
| `&16` one-way | `TakeOneWay` | goes, and its address is remembered in `RESPAWNS` (`&FF4B`, 8 places). Every 25 passes core's `RESPAWN` (`&DA59`) puts a wall `&07` back at each remembered place that is empty [measured: `e16_switch`, a wall behind the player 11 passes later]. With all 8 places used, it stays and `RESPAWN` runs |
| `&17` switch | `TakeSwitch` | goes, and every `&06` in the map goes (redrawn if in view) [measured: 4 placed, none left] |
| `&18` death star | `TakeDeathStar` | +6 = `&FF`, +7 + 1: the 16-bit "power" counter (+6/+7) becomes 256 x (old high byte + 1) + 255 [measured: 0 → 511] |
| `&19` shield | `TakeShield` | +8 = 1: one strength change in four is skipped (section 7) |
| `&1A` idol | `TakeIdol` | +9 = `&FF`: monsters chasing this player run away, for 255 passes |
| `&1B` heart | `TakeHeart` | +&0A = `&FF`: no strength changes, for 255 passes; the player flashes |
| `&1C` ball | `TakeBall` | +&0D + 1 ("bounces" for the stars) |
| `&1D` clock | `TakeClock` | `FreezeTimer` = `&FF`: monsters and trap doors stop for 255 passes |
| `&1E` exit | (the caller) | section 6.2 |
| `&20-&3E` | `TouchTrapDoor` | hit (5 treasure); a hell hole kills (section 3) |
| `&40` up, but `&7F`, `&80`+ | `TouchClear` | goes, for nothing |
| `&01-&07`, `&11`, `&13`, `&1F` | | block |

The timers (+9, +&0A, `FreezeTimer`) count down once a pass (`&C121`,
core's) [source]. Every handler that removes a tile redraws it
(`RedrawTile`).

#### 6.1 Teleporters (`Teleport`, `&D384`)

- `PickTeleporter` (`&D389`) counts the `&15` tiles in the 12 x 12 view
  and picks the `(R mod count) + 1`th in reading order [source]. It may
  pick the one touched.
- `TeleportLand` (`&D3CE`): the player goes to the tile one beyond the
  chosen teleporter in the player's step direction, if that tile is empty
  and at least two cells inside the view's edge (rows and columns 2-20 of
  the view). Otherwise nothing happens [source]. The new position is
  tile-aligned.
- [measured: `e11_teleport`, with teleporters at tiles (30, 2) and
  (25, 5) and the player walking right into the first: 16 runs from
  different R gave (60, 6) six times and (50, 12) ten times. A teleporter
  whose landing tile was beyond view column 20 was never used.]
- `PickTeleporter` returns with the **alternate register set still
  selected** when it finds one (`EXX` at the start, `RET Z` inside the
  loop); `TeleportLand` works in that set and switches back at
  `TeleportDone` (`&D3CC`) [source]. The stars call it too (`&C7C0`).
- If no teleporter were in view the `R mod count` loop would never end;
  every caller has one in view [source].

#### 6.2 The exit and leaving the level

- A step whose last non-empty cell is `&1E` runs `P1Exits` (`&D537`) or
  `P2Exits` (`&D550`) from the movement code (`&CB46`, `&CE52`) [source].
  The gate doesn't apply: the exit works on any contact. If a wall is
  touched after it in the same step (cell order (B, C), (B+1, C),
  (B+1, C+1), (B, C+1)), the step is just blocked [source].
- The player's picture is erased (with a click), its "in" bit in `&BA73`
  cleared and its "left" bit set (bit 2 for player 1, bit 3 for player 2).
  Two POPs drop the returns into its movement code, so the main loop goes
  straight on. Song 6 (player 1) or 5 (player 2) [source].
- The exit tile stays: in a two-player game the other can use it.
- When neither player is in, the main loop's `&C153` moves the "left"
  bits down to "in" and starts the next level: a player who died stays out
  [source: `&C153`; measured: `e4_items`, after the exit the next level
  started with player 1 at (2, 2)].

## 7. Strength and treasure: every change in this range

| Change | Amount | Where |
|---|---|---|
| a monster hits | -(kind + 1), up to twice a visit | `MonsterTry` → `&DAA6`/`&DAF4` |
| food | +25, +50, +75 | `TakeFood` → `&FF32` |
| the hell hole | strength := `&FF00`, then dead | `HellHole` (`&D2B9`) |
| punch a monster's head | +5 treasure (kind 7 too) | `&D1EB` → `&FF31` |
| hit a trap door | +5 treasure | `TouchTrapDoor` |
| a chest (`&0C`) | +10 treasure | `TakeChest` |

- Strength also drains by 1 every 25 passes (`&D9EC`, core's) [measured:
  `e2_move`, -1 at passes 11 and 36].
- **The shield and the heart apply to every strength change**, food and
  the drain included, since all go through `&DAA6`/`&DAF4`: the heart skips
  them all while it runs, the shield skips one in four (`R AND &0C` = 0)
  [source; measured: `e17_misc`, under the heart a monster beside the
  player for 40 passes took nothing, and neither did the drain].
- `TouchTreasure` and `TouchStrength` are bytes [source].

## 8. Beeper effects in this range

Both block the game while they sound [source: busy loops].

| Site | What | Length |
|---|---|---|
| `NoiseBurst`, `&CEED-&CF03` (OUT at `&CEFC`) | **the noise burst**, once at the end of a pass in which any monster hit a player. 50 segments; each takes its length (1-256 loops of 27 T-states) and its level (bit 4) from R | 161,201-171,866 T-states (2.31-2.46 frames) over every starting R of 0-127, 48K timing, interrupts off; 151,761-170,060 (2.14-2.40 128K frames) in play, 12 hits [measured: `e14_burst48`, `e3_burst`] |
| `KeyClick`, `&D838` (OUT at `&D83A`) | **the key click** in the menus (password, controls, name): 256 half-waves of 666 T-states, about 2.6 kHz | 170,509 T-states (2.44 frames) at 48K timing; 182,258 with the 128K's music interrupt running [measured: `e10_click`] |

- R's bit 7 is 0 throughout: nothing loads R, and the snapshots have it
  clear [measured: R in `nm48.z80`, `nm128.z80` and the play snapshot;
  source: no `LD R,A`]. With bit 7 set the burst would be longer (up to
  344,666 T-states) [measured: `e14_burst48`].
- The punch's noise (`HitNoise`, `&C8C4`) and the shove's click
  (`&CC79`) are `players.ctl`'s.

## 9. Randomness: the `LD A,R` sites in this range

Five of the game's thirteen [source]:

| Site | Routine | What it decides |
|---|---|---|
| `&CEF5` | `NoiseBurst` | each segment's length and level |
| `&D095` | `TrapDoor` | whether an ordinary trap door spawns this visit (`AND 3` = 0: one in four) |
| `&D0D7` | `TrapRandom` | a hell hole's sparkle: kind and health (`AND &1F`) |
| `&D317` | `OpenChest` | the locked chest's contents (`AND 6`: chest, tea, scroll or monster) |
| `&D3AD` | `PickTeleporter` | which teleporter in view (R mod count) |

The monsters' movement uses none.

## 10. The menus' key entry, game over and the high score

[source, with the strings read from the bytes]

- **`EnterCode` (`&D58B`)**, menu 4: "ENTER CODE"; four keys into
  `PASSWORD_TYPED` (`&FF2A`), each shown and clicked; then the menu.
- **`SelectControls` (`&D5C9`)**, menu 3: "1 REDEFINE PLAYER ONE",
  "2 REDEFINE PLAYER TWO", "3 KEMPSTON PLAYER ONE", "4 KEMPSTON PLAYER
  TWO".
  - **Redefining writes into the players' input code.** Each control is
    an `LD BC,port : IN A,(C) : CPL : AND mask` in the player's movement
    code; `ReadKeyFor` (`&D7FC`) stores the key's port at IX+1/IX+2 and
    its mask at IX+7, and the CPLs are rewritten (`&2F`) after. Player 1's
    are at `&C9AF` (up), `&C9C1` (down), `&C9E6` (left), `&C9D3` (right),
    `&C95E` (fire) and `&C993` (magic); player 2's at `&CCD2`, `&CCE4`,
    `&CD09`, `&CCF6`, `&CC6C`, `&CCB6`.
  - Prompts: "KEY FOR UP.....", "DOWN...", "LEFT...", "RIGHT..",
    "FIRE...", "MAGIC.."; ENTER and SPACE are shown as words; a shift
    (key code `&E3` or `&0E`) is refused.
  - **Kempston** writes port `&001F`, NOP over each CPL, and masks fire
    `&10`, up 8, down 4, left 2, right 1; "KEMPSTON SELECTED". The magic
    key is still asked for on the keyboard. Player 2's Kempston routine
    writes the masks twice.
- **`GameOver` (`&D85E`)**, from core's strength routines when a player's
  strength goes negative: "GAME OVER PLAYER n" in the player's colour, then
  five 65,536-step delays (about 11.1 million T-states, 3.2 s). If the
  other player is still in, the view is redrawn and play goes on.
  Otherwise the better treasure (a tie to player 1) goes to
  `HighScoreCheck` and the game restarts at `&C000`.
- **`HighScoreCheck` (`&D8B6`)**: a new high score if it beats
  `HI_SCORE` (`&BA6E`). When player 2's treasure is the one offered, the
  carry from the comparison is still set, so a tie with the high score
  also counts as new. "YOUR NAME PLAYER n".
- **`NameEntry` (`&D8E7`)**: up to 10 characters, **written over the
  menu's own inline text at `&C2A7`** (the string printed after the high
  score; "TAG GAMES!" at first). A new key acts at once; a held one
  repeats after `RepeatCount` (`&FF60`, `&1000`) polls. ENTER ends; CAPS
  SHIFT with 0 deletes; codes `&80` and up are ignored.

## 11. Variables

| Address | Name | Meaning | Written by | Read by |
|---|---|---|---|---|
| `&BA4B` | `MapStamp` (players) | code `FillCells` writes | players, monsters, `PutPlayer`, core | `FillCells` |
| `&BA6C` | `FreezeTimer` | the clock: monsters and trap doors stop while non-zero | `TakeClock` (`&FF`), `&C121` (-1 a pass) | `MonsterChase`, `TrapDoor` |
| `&BA6E` | `HI_SCORE` (core) | the high score | `HighScoreCheck` | it, the menu (`&C293`) |
| `&BA72` | `SparkleFrame` | 7 → 0, a step a sweep | `MonsterScan` | `Sparkle` |
| `&BA75` | `ScanQuarter` | the quarter scanned this pass, 0-3 | `MonsterScan` | `MonsterScan` |
| `&BA77` | `MoveSweep` | 1 on sweeps when monsters move; their frame | `MonsterScan` | `MonsterMove` |
| `&BA7F`/`&BA80` | `MonNewPos` | a moving monster's new position (column, row) | `MonsterMove` | `MonsterMove` |
| `&BA81`/`&BA82` | `MonOldPos` | its old position | `MonsterMove` | `MonsterMove` |
| `&BA83` | `MonCode` | its code | `MonsterMove` | `MonsterTry` (the damage) |
| `&BA84` | `MonFacing` | its facing, 0-14 | `MonsterChase` | `MonsterMove` |
| `&BA85`/`&BA86` | `StepV`/`StepH` (players) | the step: players write (row, column), monsters (column, row) | players' movement, `MonsterChase`, the touch handlers (cleared) | players, `MonsterMove`, `PushRock`, `TeleportLand`, the shoves |
| `&BA87-&BA8F` | `SpawnOffsets` | the spawn neighbours, overlapping pairs | (constant) | `TrapDoor` |
| `&BA91`/`&BA92` | `TrapPos` | the trap door being run (column, row) | `TrapDoor` | `TrapDoor` |
| `&BA95`/`&BA96` | `SpreadCursor` | the creeper cursor (column, row) | `SpreadTick` | `SpreadTick` |
| `&BA97` | `ScanPhase` | the column phase of the row being scanned | `MonsterScan` | `MonsterScan` |
| `&BA98` | `HitFlag` | a monster hit a player this pass | `MonsterScan` (0), `MonsterTry` | `MonsterScan` |
| `&FF2E` | `TouchCount` | the touch gate's count, 10 → 1 | `TouchGate` | `TouchGate` |
| `&FF30` | `TouchSpare` | cleared, never read | `TouchAll` | |
| `&FF31` | `TouchTreasure` | treasure this step gained | `TouchAll` (0), punches, `TouchTrapDoor`, `TakeChest` | the players' movement (`&CB2C`, `&CE38`) |
| `&FF32` | `TouchStrength` | strength this step gained | `TouchAll` (0), `TakeFood` | the players' movement (`&CB35`, `&CE41`) |
| `&FF33` | `TouchCode` | the last non-empty code touched | `TouchAll` (0), `Touch` | the players' movement (`&CB3F`, `&CE4B`) |
| `&FF4B-&FF5A` | `RESPAWNS` (core) | one-way tiles to turn into walls | `TakeOneWay`, `RESPAWN`, `&DBCA` (cleared each level) | `RESPAWN` |
| `&FF60`/`&FF61` | `RepeatCount` | name entry's key repeat | `NameEntry` | `NameEntry` |
| `&C2A7-&C2B0` | (core's menu text) | the high score's name | `NameEntry` | the menu |
| player +8, +9, +&0A, +&0B-&0E | (players) | shield, idol, heart; keys, scrolls, balls, horseshoe | the `Take` handlers, `OpenDoor`/`OpenChest` (keys -1) | `&DAA6`, `MonsterChase`, players |

`&BA78-&BA7E`, `&BA90`, `&BA93`/`&BA94` and `&FF2F` are never read or
written by the code [source: no references].

## 12. For the port

- **R** (D5): five sites here. The monsters' movement needs none, so
  pass-by-pass comparison of monsters holds until a trap door's spawn
  check, a hell hole, a chest or a teleporter. The burst's length comes
  from R too; a fixed length near 2.4 frames (section 8) is the decision
  to record.
- **Timing**: `TileDelay` is 1,010 T-states for every non-monster tile
  visited (42-49 a pass) and is most of a quiet pass's scan. Monsters step
  once every 8 passes; sparkles turn on one sweep in eight; the creeper's
  cycle is 960 passes; the one-way walls come back on core's 25-pass tick.
  These are counts of passes, so they carry over whatever the pass length.
- **Self-modifying code**: redefining the controls rewrites the players'
  input instructions (`LD BC` operand, `AND` operand, CPL or NOP); the
  name entry rewrites the menu's inline text. Both want tables on the BBC.
- **Register tricks**: `CellEmpty` pops its caller's return address;
  `PickTeleporter` returns in the alternate register set; `P1Exits` and
  `P2Exits` drop two return addresses; `SpawnOffsets` is read as
  overlapping pairs.
- **`&BA85`/`&BA86`** mean (row, column) to the players and the touch
  code, (column, row) to the monsters.
- **The touch gate** is one count for both players and every contact,
  walls included: transcribe it as it is, or punches, shoves and trap-door
  hits change rate.
- **Double hits**: a monster's three tries can each hit the player.
- **Frozen monsters' facing** is whatever the last moving monster chose.
- **The scan reads past the map's right edge** into the next row's
  column 0 when the view is at the right; at the bottom it stops at 12
  rows, so it never reads past `&BFFF`.
