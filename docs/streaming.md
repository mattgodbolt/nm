# A stock Model B: streaming, and what it would take

The port runs on a Model B with 16K of sideways RAM, or a Master
(decision 6). This note is about a second edition for a stock 32K Model B,
the way Chuckie Egg 2's CE2S does it: what would have to move, and what
the disc would carry. Nothing here is built yet.

## Where things are now

- **Main RAM**, from `CODE_BASE` up to the screen: the game's code that
  runs every pass (the players, touching, the monsters, the stars, the
  sprite drawer, the shifts, the status), the music's driver, the 192
  graphics blocks, and the original's two variable blocks.
- **OS workspace** below `CODE_BASE` (decision 11): the map, the
  attributes, the drawing's tables (made at start-up, decision 20).
- **The sideways RAM bank** (`NDATA`): the 50 levels, packed (decision 4),
  the songs, the panel (packed), the font, and the code that needn't be in
  main RAM: the level's set-up, text, the colours, the front end
  (decision 20).

The build's `PRINT`s say how full each is. Both are close to full.

## What a stock B would need

The levels are the easy part, as the brief found: a level is needed only
at its start, during the "LEVEL nn" screen, where the original already
waits about a second and a quarter (`LEVEL_PAUSE`). One packed level is a
few hundred bytes: read it from the disc into a buffer, then unpack it
into the map as now. Chuckie Egg 2's NMI disc reader (`disc.6502` there,
for the 8271 and the 1770) reads a sector at a time with the game's
interrupts still running, and would carry over; each level would start on
a sector of its own in a file of levels, its sector and length in a table.

The hard part is everything else in the bank. On a stock B it all has to
fit in main RAM, beside the code that's there now, and it doesn't. The
ways to make room, roughly in the order they'd pay:

1. **The front end as an overlay**: the menu, the controls, the password,
   game over, the high score and the name are only needed between games
   (and at game over). Chuckie Egg 2 made its front end a separate program
   (`MENU`); here it could be read from the disc into the map's room, since
   no level is in play then, and the game's state kept where both see it.
2. **The panel drawn by the loader**, not the game: it's drawn once.
3. **The music** only where it fits: Chuckie Egg 2's streaming edition
   has none. The driver and the songs together are the largest single
   thing that could go.
4. **The mirrored ninja frames**: 30 of the character frames are mirror
   images of others (docs/research.md). Drawing them flipped needs a
   reversing table, which needs a page of its own, so this saves less than
   it looks.
5. **Smaller code**: the transcription keeps the Z80's registers in zero
   page by name (`regs.6502`), which is clear but not small.

The order to try them: the overlay first, as it frees the most and keeps
everything the game does; then measure. If the music still doesn't fit,
the stock-B edition goes without it, as CE2S does, unless Matt prefers
something else.

## Real hardware

As with Chuckie Egg 2, jsbeeb is kinder than a real drive: the disc reader
would need checking on a real 8271 and 1770, with a mechanical drive.
