# The players, their controls and the stars

How the two ninjas read their controls, move, throw stars and fight in the
Spectrum original: the code at `&C632-&CE76` and the variables it uses.
The routines are labelled in `disasm/players.ctl`.

Tags, as in `docs/research.md`: **[measured]** = run on SkoolKit's
simulator (`tools/zx.py`, or its `Spectrum` class driven from Python, on
`build/nm128.z80` at 128K timing), with the experiment named;
**[source]** = read from the code; **[inferred]** = a reading to check. The
experiments' scripts lived in `build/pl/` and aren't kept: each one started
a one-player (`1`) or two-player (`2`) game, ran to the main loop's top
(`&C014`) a pass at a time, held keys and read memory back. When counting
passes, a break at `&C014` counts only with interrupts enabled: the 128K's
interrupt pages the music bank in at `&C000`, and its driver passes
through `&C014` too.

Notation: a **position** is (row, column) in character cells of the
64 x 64-cell map. A map tile (`&BC00`, 32 x 32) covers 2 x 2 cells, so a
cell's tile is (row/2, column/2) (`&D569`). The view's origin is
(`&BA4C`, `&BA4D`), in cells; the playfield is view rows 0-23 at screen
columns 8-31. A **pass** is one trip round the main loop (`&C014-&C05A`).

## 1. What runs, and when

- The main loop calls `&C168` (player 1) and `&C187` (player 2) every pass
  [source]. Each returns at once unless its bit in `&BA73` is set (bit 0
  player 1, bit 1 player 2: in the level; bits 2 and 3: left by the
  stairs).
- Each then calls `Player1Update` (`&C978`) or `Player2Update` (`&CC98`)
  and afterwards writes the player's code (`&71`, `&72`) into the map
  under its four cells (`&D1A2`). **The players live in the map** as the
  monsters do: that is how stars, monsters and the other player find them.
- `StarsUpdate` (`&C632`) runs every pass, after both players.
- A pass takes 1.1-1.3 frames while walking (74,000-95,000 T-states)
  [measured: 40 passes of each direction key, `e1`]. A player steps one
  cell (8 pixels) every two passes; a star flies one cell a pass.

## 2. The players' variables

Each player has a 15-byte record, `&BA4E` and `&BA5D`. The touch code
(`&D1BA`, in the monsters' and objects' range) reaches it through IX, so
the pick-ups are written by offset.

| Off | P1 | P2 | Name | Meaning | Written by | Read by |
|---|---|---|---|---|---|---|
| +0 | `&BA4E` | `&BA5D` | column | position: column (cells) | level start `&C3D2`; `&CACE`/`&CDF2`; pushed `&D4FE`/`&D4C8`; transporter `&D402` | everything here |
| +1 | `&BA4F` | `&BA5E` | row | position: row | as above | |
| +2/3 | `&BA50` | `&BA5F` | treasure | 16 bits, shown as 5 digits and a fixed 0 | `&DB3F`/`&DB59`; end of game `&C0E7` | panel |
| +4/5 | `&BA52` | `&BA61` | strength | 16 bits, shown as 5 digits and a fixed 0; negative = dead | `&DAE8`/`&DB33`; game start `&C30F` (1000); `&D2B9` (`&FF00`) | `&DAA6`/`&DAF4` |
| +6/7 | `&BA54` | `&BA63` | power | 16-bit counter; the high byte is the shot power | pick-up `&18` (`&D460`): low byte `&FF`, high byte + 1; a throw: - 1 (`&CA13`) | stars `&C6C1`, `&C6E4` |
| +8 | `&BA56` | `&BA65` | armour | pick-up `&19` sets 1: a quarter of strength changes are skipped (`&DAB1`) | `&D46C` | `&DAA6` |
| +9 | `&BA57` | `&BA66` | skull | pick-up `&1A` sets 255: the monsters run from this player while it counts down | `&D475`, `&C121` | monsters `&D024` |
| +A | `&BA58` | `&BA67` | heart | pick-up `&1B` sets 255: no strength changes at all, and the player blinks | `&D47E`, `&C121` | `&CAE3`, `&DAA6` |
| +B | `&BA59` | `&BA68` | keys | 0-9, shown as key icons | `&D2C2`, doors, chests | `&CB16` |
| +C | `&BA5A` | `&BA69` | magic | smart bombs, 0-9, shown as icons | `&D334`; the magic key | `&C99D`, `&CB21` |
| +D | `&BA5B` | `&BA6A` | bounces | each pick-up `&1C` adds one | `&D487` | throw `&CA20` |
| +E | `&BA5C` | `&BA6B` | freeze ring | pick-up `&12` sets it: this player's stars freeze the other player | `&D342` | `&C800`/`&C7EA` |

A new level (`&DBCA`) clears the bounces, the armour and the ring. Keys,
magic, power and the timers carry over; a new game (`&DBA2`) clears them
all [source].

The other variables:

| Address | Name | Meaning | Written by | Read by |
|---|---|---|---|---|
| `&BA47`, `&BA48` | P1Facing, P2Facing | bits 1-3 direction, bit 0 the step bit (section 4); the picture is `&30` + this | the key sites; `&C168`/`&C187`; the blocked path | `&CAEA`, the throw |
| `&BA49` | OldPos | the moving player's position at the start of its pass (column, row): what gets erased | `&C97C`, `&CC9C` | `&CA41`, `&CAD9`, `&CC75` |
| `&BA4B` | MapStamp | the code `&D1A2` writes into four cells: `&71`, `&72` or 0 | players, monsters, `&C890` | `&D1B5` |
| `&BA70`, `&BA71` | P1LastFacing, P2LastFacing | the facing at the last step attempt, to spot a turn | `&CA5A`, `&CD7E` | `&CA4D`, `&CD71` |
| `&BA85`, `&BA86` | StepV, StepH | the step being tried, vertical and horizontal (-1, 0, 1); pushes and transporters use it | `&CA38`, `&CD5B`; monsters `&D05E`; cleared by pushes | pushes `&D4B4`, boulders `&D34E`, transporters `&D3D1`, the slides |
| `&BA3B`, `&BA40` | Star1, Star2 | a star: row, column, drow, dcolumn, thrower (`&71`/`&72`; 0 = none) | throw `&C60E`; `&C660`; bounce; hits | `&C63D` |
| `&BA29` | StarPattern | the star, 8 x 8 | (data) | `&C660` |
| `&BA32` | FloorQuarter | a quarter of floor tile 0 (all four are the same), 8 x 8: erases a star | (data) | `&C652` |
| `&BA31`, `&BA3A` | | unused, never read | | |
| `&BA6D` | CreeperHits | star hits left before the next creeper tile goes | `&C7AB`, `&C7B4` | `&C7A7` |
| `&FF34` | StarDirs | 8 (drow, dcolumn) pairs, indexed by facing: right, left, up, down, up-right, up-left, down-right, down-left | (data) | `&C611` |
| `&FF44` | Bounces | bounces left, **shared by both stars**, set at each throw | `&CA23`, `&CD46`, `&C721` | `&C6B6` |
| `&FF45`, `&FF46` | P1Frozen, P2Frozen | passes the player stays frozen (255, or 0 when hit again) | `&C7EA`, `&C800`; counted down at `&C987`, `&CCA7` | the update's start |
| `&FF47` | StarInk | the star's ink, cycling 0-7 a cell drawn | `&C85F` | `&C859` |

Variables of the touch code (`&D1BA`, not in this range) that the players
rely on: `&FF2E`, a countdown from 10 that lets only every tenth touch of
a nonzero tile act (`&D287`); `&FF31` and `&FF32`, the treasure and
strength to add; `&FF33`, the last nonzero tile touched [source].

## 3. Controls

### Reading them

Each player has six sites, each its own `LD BC,port : IN A,(C) : CPL :
AND mask` [source]:

| | P1 site | P1 default | P2 site | P2 default |
|---|---|---|---|---|
| magic | `&C993` | ENTER | `&CCB6` | CAPS SHIFT |
| up | `P1Up` `&C9AF` | Q | `P2Up` `&CCD2` | 9 |
| down | `P1Down` `&C9C1` | A | `P2Down` `&CCE4` | 8 |
| right | `P1Right` `&C9D3` | P | `P2Right` `&CCF6` | 7 |
| left | `P1Left` `&C9E6` | O | `P2Left` `&CD09` | 6 |
| fire | `Fire1` `&C95E` | SPACE | `Fire2` `&CC6C` | 0 |

- **The keys are redefined by rewriting the code** (`&D647-&D779`, the
  controls menu, in the core's range) [source; measured]:
  - *Redefine player one / two* asks UP, DOWN, LEFT, RIGHT, FIRE, MAGIC.
    Each answer's half-row port goes into the site's `LD BC` and its
    key bits (all the keys held in that half-row) into the `AND`. The CPL
    goes back to `&2F`. Measured: keys 1, 2, 3, 4, 5, K made the sites
    read port `&F7FE` with masks 1, 2, 4 (left), 8 (right), `&10`, and
    `&BFFE` mask 4.
  - *Kempston player one / two* writes port `&001F` into all five
    direction and fire sites, makes each CPL a NOP (the Kempston reads
    active high) and sets the masks: up 8, down 4, left 2, right 1, fire
    `&10`. It still asks for the magic key from the keyboard. Measured:
    after choosing it, KR moved player 1 and P didn't, and KF threw.
  - Player 2's Kempston writes its masks twice (`&D74E-&D764`, then
    `&D767-&D779`), the same both times.
- **Sinclair joysticks are keys.** Player 2's defaults, 6-0, are the
  Sinclair joystick on 6-0 (6 left, 7 right, 8 down, 9 up, 0 fire). The
  other Sinclair joystick (1-5) needs player 1 redefined.
- **Two players at once** just works: each player's sites read their own
  ports, every pass. Two Kempston players would read the same joystick.
- The order inside a pass is magic, up, down, right, left, then fire. A
  later direction's facing overwrites an earlier one's, so with both held
  **down beats up and left beats right** [source].

### The magic key

While held, and while the player has any magic (`&BA5A`), each pass sets
off a smart bomb (`&C4B0`, the core's) and redraws the view (`&C54C`).
There is no debounce: holding the key spends one a pass. One bomb takes
about 73 frames, 2,048 beeper writes [measured: `e6`, 4 bombs in 4 passes
with ENTER held].

`&C4B0` [source, outside this range]: with R below 6 (6 in 128) every
tile `&20` and up in the whole map changes, monsters and markers into
treasure `&0C` and trap doors into food `&0E`. Otherwise every monster,
and every trap door other than kind 7, in the view and a tile's margin
(`ViewMapPtr` `&CE58`) is removed, with no reward. Then the floor colour
flashes 8 times with a beep.

## 4. Movement

### A pass of `Player1Update` (`&C978`)

1. Save the position in `OldPos` (`&BA49`).
2. **Frozen** (`&FF45` nonzero): count it down and skip to step 7 with no
   control read.
3. Read the magic key, then the four directions into D (horizontal) and E
   (vertical), setting the facing as they go (below).
4. **Fire held**: if the player's star isn't flying, throw (section 5).
   Either way the player doesn't move this pass. Holding fire throws again
   as soon as the star lands [measured: `e2`, a second throw on the next
   pass after the first star hit the wall].
5. **No direction**: no move; the facing and step bit stay.
6. **Move**:
   - Store the step as `StepV`/`StepH` (`&BA85`, `&BA86`).
   - Lift the player out of the map (write 0 under its old cells), so it
     can't touch itself.
   - If the facing (without bit 0) differs from the last attempt's
     (`&BA70`), clear the step bit.
   - **If the step bit is set, step**: column += horizontal, row +=
     vertical. Either way, toggle the step bit.
   - Touch the four cells at the new position (`P1Touch`, `&CB0C`). If
     anything there blocks, set the step bit and try the horizontal step
     alone from the old position, then the vertical alone; if all three
     are blocked, stay.
7. `P1Place` (`&CAAA`): scroll the view if needed, else store the position;
   if it changed, erase the old picture (with the click, section 8); draw.

So **a player steps once every two passes** while a direction is held,
and **a turn costs a pass**: the first pass in a new direction only turns.
Measured (`e1`): holding P from rest, the column went 2, 3, 3, 4, 4, 5 ...
over passes; on reversing to O, one pass turned and the next stepped; the
same up and down. Sliding along a wall with a diagonal held keeps the step
bit set, so the next pass tries again at once.

### Blocking

**Every nonzero tile blocks** [source: `&D1D7` sets `&FF33` from any
nonzero tile; measured]. Floor is tile 0, the only thing a player walks
on. The touch also acts on what it finds, but only on every tenth touch
of anything nonzero, counted by `&FF2E` across both players and all tiles
(walls included) [source: `&D287`]. So:

- **Picking up** an item blocks the player until the touch acts; then the
  item is gone and a slide attempt in the same pass steps into its place.
  Measured (`e5`, a key `&08` placed ahead): 1-3 passes of pushing,
  depending on the shared count.
- **The staircase** (`&1E`) acts at once, not on the tenth touch: the
  player leaves the level (`&D537`: `&BA73` bit 2 set, bit 0 cleared, song
  6) [measured: `&BA73` = 4 on the first touch].
- **Tile `&27`** (a pit; a shot wall `&1F` becomes one) is trap-door kind
  7: touching it sets strength to `&FF00`, and the strength update in the
  same touch (`&DAA6`) finds it negative: game over [measured: walked into
  a `&27`, "GAME OVER PLAYER 1"].
- **The other player** is pushed one step along `StepV`/`StepH` if its
  cells there are free (`&D4E1`, `&D4AB`) [source]. In a two-player game
  both players start on the same cells [measured].

The player's position is any cell, so it can straddle tiles: at an odd
row or column it covers, and is blocked by, two or four tiles [source].

### Facing and pictures

`&BA47` / `&BA48`: bits 1-3 the direction, bit 0 the step bit. Up sets 4,
down 6, right 0, left 2. With right or left, `Diagonal` (`&C967`) adds 8
if up is also held (E = -1) or 12 if down (E = 1) [source; measured].

| Facing | 0 | 2 | 4 | 6 | 8 | 10 | 12 | 14 |
|---|---|---|---|---|---|---|---|---|
| Direction | right | left | up | down | up-right | up-left | down-right | down-left |

The picture is graphics block `&30` + facing, step bit included: two
frames a direction, alternating with each step attempt [measured: blocks
`&30-&3F` drawn out]. Player 1 is drawn bright cyan on black (`&45`),
player 2 bright green (`&44`). `DrawFrame` (`&CAF1`) draws it, opaque, 16
x 16 (`DrawSpriteA`, `&C8E8`) every pass.

**The heart** (`&BA58`): while it counts down (one a pass), on even
counts the player is drawn as floor instead: a blink every pass [source;
measured: the count falls one a pass].

### The view

`P1Place` keeps the player in view rows and columns 2-20 [source;
measured]. A step outside them scrolls instead:

- The view slides 8 tiles, a tile (2 cells) a step (`ScrollUp` `&CB4C`,
  `ScrollDown` `&CB93`, `ScrollLeft` `&CBD5`, `ScrollRight` `&CC23`), each
  step a block move of the screen (core, `&DBE8-&DCB6`) and a new strip.
- The player's position isn't stored that pass; the old picture is
  redrawn with a click. The step happens on the next pass. Measured
  (`e7`): column 20 to 21 with the view at column 0 slid the view to 16
  in one pass of 18.6 frames.
- The slide stops early at the map's edges (origin 0 and 40). Then it
  returns Z without redrawing the player [source].
- **With both players in the level** (`&BA73` = 3), the slide goes only
  as far as keeps the other player inside view rows or columns 2-20;
  if that's no distance, the mover simply can't go on [measured: with
  player 2 at column 2, player 1 stopped at column 20 for good]. Scrolling
  up or left, the limit is 9 - ceil((other - 2 - origin) / 2) steps, so it
  can be 9 [source].

## 5. Throwing stars

### The throw

[source; measured: `e2`, all four directions and up-right]

- Each player has one star (`&BA3B`, `&BA40`). Fire does nothing while
  it's flying.
- A throw takes one off the power counter (`&BA54`, 16 bits, if nonzero)
  and copies the player's bounces to `&FF44`.
- `&C60E` (core's range) sets the star's direction from `StarDirs`
  (`&FF34`) by the facing, and its cell to the player's + 2 x the
  direction. The doubling is `RLCA`, which leaves `&FF` as `&FF`: so the
  star starts just outside the player's 2 x 2 cells on every side (2
  ahead going right or down, 1 going left or up).
- The star looks at its first cell at once (and can hit something
  there), then `StarsUpdate` moves it on in the same pass.
- The throw chirp `&C508` plays (section 8), and the player doesn't move
  that pass.
- Measured: thrown right from column 3, the star was at column 6 after the
  pass, then 7, 8, 9 ...; thrown up from row 59, at row 57, then 56, 55 ...

### The flight (`StarMove`, `&C63D`)

Every pass, for each star with a thrower:

1. Erase its cell by drawing `FloorQuarter` (`&BA32`) in the floor's
   colour (`StarCell` `&C816`). If the cell isn't inside the view (rows and
   columns 1-22 of it), the star is gone.
2. Look at the map tile under the next cell (`StarLook` `&C659`). Empty,
   or the thrower's own code: move there and draw the star, its ink the
   next of 0-7 (`&FF47`), so it changes colour every cell (and is black,
   unseen, one cell in eight).
3. Otherwise it's a hit, by tile (`StarHit` `&C66E`):

| Tile | What the star does | Stops? |
|---|---|---|
| `&01-&03` crumbling wall | next stage; after `&03` it's gone, and a wall end above (`&05` → `&04`, `&11` → `&01`) is mended (`&C770`) | yes |
| `&11` wall | becomes crumbling `&02` | yes |
| `&0E` food, `&14` boulder | destroyed | yes |
| `&10` magic scroll | destroyed, and it goes off as a smart bomb (`&C4B0`) | yes |
| `&13` creeper | destroyed on every Nth hit, N random 1-32 (`&BA6D`, shared by all creeper tiles) | yes |
| `&15` transporter | the star comes out by a random transporter in the view (`&D389`) and flies on | no |
| `&1F` wall | becomes `&27`, the pit | yes |
| `&20-&3F` trap door | power + 1 times, 8 off the tile; below `&20` it's gone. Kind 7 (bits 0-2) can't be hurt | yes |
| `&7F` monster's marker | hits the monster that owns it (`HitMarker` `&C8A4`) | yes |
| `&71`, `&72` the other player | freezes or unfreezes it (section 6) | yes |
| `&80+` monster | power + 1 hits (`HitMonster` `&C86C`), then 2 treasure | yes |
| `&40-&5F` | passes over; none exist after a level loads (`&C39F`) | no |
| anything else (walls `&04`-`&06`, items, doors, stairs) | bounces if `&FF44` lasts, else stops | |

- **A trap door's hits**: bits 3-4 are hits left, so 1-4 hits at power 0.
  Destroying one pays nothing: the code checks the thrower against `&F1`
  and `&F2` for its 50 points, and the thrower is `&71` or `&72`
  [measured: `&28` took two stars, treasure stayed 0].
- **A monster**: measured (`e4`), `&84` (health 1) took two stars and
  paid 2 treasure each; each hit plays the hit noise.
- **Bounce** (`StarBounce` `&C720`): one off `&FF44`, then each axis whose
  next cell isn't empty is reversed and the star steps back along it, not
  drawn this pass. Measured (`e9`, 2 bounces, thrown left at the wall):
  columns 3, 2, then 3 (undrawn), 4 ... 17, back to 16 at the far wall
  ... until it went out of view. The star passes over its own thrower on
  the way back.
- **`&FF44` is shared**: a throw by either player sets it from that
  player's bounces, and both stars use it up [source].

## 6. Hits on players

A star that hits a player (`&C7DB`) stops. If the *other* player holds
the freeze ring (`&BA6B` for a hit on player 1, `&BA5C` on player 2) it
toggles the hit player's frozen count between 255 and 0 [source; measured,
`e8`: player 2 with the ring threw at player 1: `&FF45` = 255, counting
down, and P did nothing]. The star's thrower isn't checked, so a player's
own bounced star freezes it too if the other player has a ring [source].
A star does no damage.

## 7. Hand-to-hand fighting

Walking into a monster is a touch like any other (`&D1D7`, the touch code)
[source; measured, `e5`]:

- It blocks, and on every tenth touch (`&FF2E`) the monster takes one hit
  (`HitMonster`, with the hit noise) and the player gets 5 treasure.
- With a monster ahead, each pass touches it four times (the step and the
  horizontal slide, two cells each), so a hit lands every 2-3 passes.
  Measured: `&8C` (health 3) took four hits, at passes 6, 8, 11 and 13,
  for 20 treasure; then the player walked on.
- Shot power doesn't count by hand.
- Through a monster's marker (`&7F`) the monster is hit but no treasure
  is paid (`&D1E8` jumps straight to `HitMarker`).
- A trap door touched by hand loses 8 (one hit) and pays 5, and the step
  is cancelled (`&D297`).
- What monsters do to the player (strength) is in the monsters' code
  (`&D066`: strength - (kind + 1)).

`HitMonster` (`&C86C`) [source]: a monster tile is bit 7 set, bits 4-6 its
kind, bits 2-3 its health, bits 0-1 its offset in the tile (column, row).
Kind 7 (`&F0-&FF`; a chest can produce one, `&D30E`) can't be hurt. A hit
takes 4 off; below 0 health the monster dies: its four cells are cleared
and floor is drawn over it.

## 8. Strength and treasure

- **Strength** starts at 1000, shown x 10 ("010000") [source: `&C30F`;
  measured, `993` showed as "009930"].
- It drains one every 25 passes (`&D9EC`) [measured: 10 in 250 passes].
- Food adds 25, 50 or 75 (`&0D`, `&0E`, `&0F`); monsters take it.
- Armour skips 1 in 4 changes, up or down, by `LD A,R AND &0C`; the heart
  skips all of them.
- Below 0, the player is out (`&DAA6`): "GAME OVER PLAYER n".
- **Treasure**: 2 a star hit on a monster, 5 a hand hit on a monster or
  trap door, 10 a chest `&0C`; after level 50 the strength left is added to
  it, one by one (`&C0CB`) [source].
- Both are reprinted on every touch call (`P1Touch` `&CB0C`), with the
  key and magic icons (3 x 3 cells of `&22` and `&23`, `&DA7E`): up to
  three times a pass. That printing is a good share of a pass [inferred
  from the pass times: blocked passes take 115,000-130,000 T-states
  against 80,000 walking].

## 9. Beeper effects

All block the game while they play. The border goes black with each.

| Site | Routine | Sound | Length | When |
|---|---|---|---|---|
| `&C8CA` | `HitNoise` `&C8C4` | noise: 50 segments, each a random level (R bit 4) held R x 24 T-states | 72,000-82,000 T-states, ~1.1 frames [measured, `e10`: 4 hits] | every hit on a monster, by star or hand |
| `&CC8F`, `&CC93` | `EraseAt` `&CC79` | a click: speaker on for the 18 T-states between two OUTs | 18 T-states [measured: the beeper writes logged in `e5`, every step] | every step, every scroll, a pushed player, leaving by the stairs |
| `&C50A` (core's range) | `&C508`, called from the throw | a rising chirp: 60 half-cycles, the delay falling from 60 x 16 T-states to 16 | 31,082 T-states [measured, `e10`: 10 throws; 35,000 when an interrupt falls inside] | every throw |

`HitNoise`'s length per segment is 48 + 24 x C T-states, C = R (0 counts
as 256).

## 10. Random numbers (`LD A,R`) in this range

| Site | What | Affects the game? |
|---|---|---|
| `&C7AF` | the creeper's next hit count: (R AND `&1F`) + 1 | yes |
| `&C8C6` | `HitNoise`: the speaker level, bit 4 | no: sound only |
| `&C8CC` | `HitNoise`: a segment's length | no state, but the pass's length |

`HitNoise` reads R 100 times a hit. If the shared generator (brief, D5)
replaces every `LD A,R`, the port must draw as many numbers there or the
streams part; leaving `&C8C6`/`&C8CC` out of the shared stream is simpler.

Reached from this range but outside it: `&C4B0` (the smart bomb's 6-in-128
chance), `&D3AD` (which transporter), `&DAB1`/`&DAFF` (armour).

## 11. For the port

- **Self-modifying code**: the twelve control sites (ports, CPL/NOP,
  masks) are rewritten by the controls menu. Port the decision: a table
  of key or joystick bits per player per control.
- **Clipping by the Spectrum's memory map** (`DrawSpriteA`): a picture at
  view row -1 (the monsters' `&CFB9` allows it) starts drawing at `&38xx`,
  in the ROM, where the writes are lost; its attributes go to screen row 0.
  One at view row 23 writes its second attribute row to `&5B00-&5B1F`. On
  the BBC both would land in RAM: clip instead.
- **Timing**: nothing waits for the frame. The player steps every other
  pass and the star every pass, so the speeds are the pass rate's. The
  beeper effects, the panel's reprinting and the scroll's 18 frames are
  all inside passes.
- **Quirks to keep** (they are the game): the shared bounce counter
  `&FF44`; the trap door's unpaid 50 points; the touch countdown `&FF2E`
  shared by both players and all tiles; down beats up, left beats right;
  the magic key's repeat; the power counter's 16-bit decrement (a power
  level lasts 256 throws, then the low byte is left at `&FF`); the
  undrawn bounce step; the star's erase always drawing floor, which
  wipes a quarter of the thrower until the next pass if the star
  bounces back onto it.
- **Draw order**: players draw before stars each pass, and collisions
  read the map, not the screen.
