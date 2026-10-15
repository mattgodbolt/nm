; Ninja Massacre (ZX Spectrum, Codemasters 1989): the core.
; SkoolKit control-file entries for docs/research/core.md: the main loop,
; start-up, the menu, level set-up and decoding, the view and its drawing,
; printing, the status panel, the key reading and the four screen shifts
; of the slide. Code &C000-&C631 and &D972-&DCDB, the variables those use,
; the font (&F500) and the tables in the &FF00 page.
;
; Rows and columns are characters (8 x 8 pixels) throughout: the map's
; tiles are 2 x 2 characters, so a position in characters halves to a map
; tile. Text is 0-terminated and inline after CALL #R$D995 or #R$D999.

; ---------------------------------------------------------------------------
; The music flags (the three music hooks between them are not in this file)

@ $B8DE label=Is128K
b $B8DE Non-zero on a 128K
D $B8DE Set once by the loader at &B9DD: the byte at address 1 with ROM 0 paged, less &AF. A 48K's ROM has &AF there (the XOR A after DI), so 0 means a 48K. The music hooks, the menu's EI at #R$C2F4 and the interrupt test it.
B $B8DE,1,1
@ $B8DF label=MusicOff
b $B8DF Non-zero when EXTEND+T has turned the music off
B $B8DF,1,1
@ $B8E0 label=MusicKeyHeld
b $B8E0 &FF from EXTEND+T until EXTEND is seen without T: one toggle a press
B $B8E0,1,1
i $B8E1

; ---------------------------------------------------------------------------
; Start-up and the main loop

@ $C000 label=Start
c $C000 Start a game: the menu, then the main loop
D $C000 The loader jumps here (&BA1B on a 128K, &B9F3 on a 48K), and so do EXTEND+Q and the end of a game. There is no frame sync anywhere: the main loop runs as fast as its code.
  $C000 Reset the stack; black border.
  $C006 Zero the scores, strengths and per-game state.
  $C009 The attract screen and the menu; returns once a level is set up.
  $C00C Draw the view, then start song 1 (the game's opening jingle).
N $C014 The main loop. Each call returns at once if it has nothing to do.
@ $C014 label=MainLoop
  $C014 Player 1, then player 2 (each does nothing unless in play).
  $C01A The two stars.
  $C01D The monsters (a quarter of the view and its margin a pass).
  $C020 Every 25th pass: strength, music restart, the idle timers.
  $C023 Count down the five per-pass timers.
  $C026 The spreading tile (&13).
  $C029 No player in play (bits 0-1 of #R$BA73)? Then the next level.
  $C031 EXTEND MODE is CAPS SHIFT and SYMBOL SHIFT together; without it, loop.
  $C041 EXTEND+T toggles the music; EXTEND+Q quits to #R$C000.
  $C04D EXTEND+P pauses.
  $C056 EXTEND without T re-arms the music toggle.
@ $C05C label=MusicToggle
  $C05C Ignore T until it has been seen released (#R$B8E0).
  $C066 Flip #R$B8DF. Music on: start song 0 (A is 0 here).
  $C076 Music off: stop it. On a 48K this is a bug: #R$B92E calls &C006 with no music bank paged in, which is #R$C000's CALL #R$DBA2 and CALL #R$C1E3 here, so the scores are zeroed and the game drops back to the attract screen with the stack 12 bytes deep [measured].

@ $C07B label=Pause
c $C07B Pause until P is released, pressed and released again
@ $C086 label=WaitPUp
  $C086 Wait until P is up.

@ $C08F label=Delay
c $C08F Wait BC loops of 34 T-states (BC = 0 means 65,536)
R $C08F BC Loops

; ---------------------------------------------------------------------------
; The end of the game

@ $C097 label=GameComplete
c $C097 Level 50 reached: WELL DONE, then strength into treasure
D $C097 Reached from #R$C34F with A = 50, from the next level's set-up. The remaining strength of each player is counted down into treasure, one unit at a time. Then it falls into #R$C121 and returns to #R$C15A, so the main loop resumes on the old map with both strengths at 0: the players die at the next status tick (#R$DAA6), which leads to the name entry [measured].
  $C097 Clear the playfield in yellow on black.
T $C0A2,21,20:n1
C $C0B7 Both players left the last level (bits 2 and 3 of #R$BA73)? Then MAN! becomes MEN!
T $C0C6,5,4:n1
@ $C0CB label=Tally
C $C0CB Player 1's strength: note whether it is 0, in the operand at #R$C11D.
  $C0D5 Strength - 1, printed; treasure + 1, printed.
  $C0F4 The same for player 2.
@ $C11C label=TallyMore
  $C11C Self-modified (#R$C0D0): non-zero while player 1 has strength left. Loop until both are 0, then fall into #R$C121.

@ $C121 label=Timers
c $C121 Count down the five per-pass timers that are not zero
D $C121 Called once a pass. Players 1 and 2 have one each at &BA57 and &BA66, and another each at &BA58 and &BA67 (while that one runs, the player's strength doesn't change: #R$DAA6, #R$DAF4); &BA6C is shared. The players' and monsters' code sets them.

@ $C153 label=NextLevel
c $C153 Next level: both players are out of play
D $C153 Bits 2 and 3 of #R$BA73 (left by an exit) become bits 0 and 1 (in play): a player who died stays out.
  $C162 Reset the per-level state, then draw the view.

@ $C168 label=Player1Pass
c $C168 Player 1's pass, if in play
D $C168 #R$C978 moves player 1. Then the player's tile, &71, is stamped into the map cells under the player (#R$D1A2), where the monsters and the stars see it.
@ $C187 label=Player2Pass
c $C187 Player 2's pass, if in play
D $C187 As #R$C168, with #R$CC98 and the tile &72.

; ---------------------------------------------------------------------------
; The menu

@ $C1A6 label=ClearPlayfield
c $C1A6 Clear the playfield to colour A and print the title
D $C1A6 The playfield is columns 8-31; the panel (columns 0-7, the loading screen's) is never touched. The title is two rows of custom glyphs from the font: '* NINJA *' and 'MASSACRE', coloured from #R$FF8A.
R $C1A6 A Attribute for the cleared playfield
  $C1AB Row 1: &2B (dots), &3A (star), &3B-&40 (NINJA), &3A, &2B.
B $C1B1,11,11
C $C1BC Row 2: &2A (block), &24-&29 (M A S S A C R E), &2A.
B $C1C2,11,11
C $C1CD The title's colours: 10 cells on each row.

@ $C1E3 label=Menu
c $C1E3 The attract screen and the menu
D $C1E3 Waits for a key, then its release: until then the loading screen (the legend of items and nasties) stays up. Then the menu. Returns, with a level set up, by RET from #R$C34F (or #R$C321).
  $C1E3 Wait for a key, then for it to be released.
  $C1ED White on black.
T $C1F8,23,22:n1
C $C20F
T $C215,19,18:n1
C $C228
T $C22E,19,18:n1
C $C241
T $C247,19,18:n1
C $C25A
T $C260,19,18:n1
C $C273
T $C279,19,18:n1
C $C28C The high score (5 digits; the 0 after them is in the string) and its name. The name is these bytes themselves: the name entry (&D8F5) writes over &C2A7-&C2B0.
T $C29C,8,7:n1
C $C2A4
@ $C2A7 label=HighName
T $C2A7,11,10:n1
C $C2B2 Stop the music; interrupts off (so no music) while the menu colours flash.
  $C2B6 1,280 flashes before the menu settles.
@ $C2B9 label=MenuKeys
  $C2B9 Each player starts with 1,000 strength.
  $C2BC Keys 1-4 (half-row &F7): 1 one player, 2 two players, 3 select controls (#R$D5C9), 4 enter password (#R$D58B).
  $C2D2 Flash, unless the count has run out.
@ $C2D9 label=MenuFlash
  $C2D9 Swap the colour of rows 4-23: &0E (yellow on blue) and &17 (white on red). A swap takes about half a frame, so both colours show at once in bands [measured].
  $C2F0 After the last flash: interrupts on (128K), and the main theme, song 0. BC = 0 stops the flashing.
@ $C303 label=MenuTwo
  $C303 Two players: bits 0 and 1 of #R$BA73, and player 2's strength.
@ $C30A label=MenuOne
  $C30A One player.
@ $C30C label=NewGame
  $C30C Players in play, and player 1's strength.
  $C312 T, A and G held: return without setting a level up, so the game plays whatever map is at &BC00 (a developer's test; on the tape it is a leftover map) [measured].
@ $C322 label=FindPassword
  $C322 The first level's data.
  $C328 Does the password typed (#R$FF2A) match one of the 8 in #R$FF62?
  $C33A Yes: its level number, from 0. Decode that many levels to move the pointer past them, then set that level up.
  $C347 No: try the next.
  $C34E None: level 0.

; ---------------------------------------------------------------------------
; Level set-up and the decoder

@ $C34F label=StartLevel
c $C34F Set up level A (from 0): the LEVEL screen, the map, the start
R $C34F A Level, 0-49 (50 is the end of the game)
D $C34F Expects #R$FF5E to point at this level's data: the levels are decoded in order, each leaving the pointer at the next.
  $C352 50: the game is complete.
  $C357 The floor's colour: ((level + 1) AND 3) + 1, red, magenta, green, blue in turn. It is also the colour of tiles &16 and &1E (the exit).
  $C366 LEVEL nn, nn from 1.
T $C371,7,6:n1
C $C378
  $C37D Is it a password's level (the 5th byte of each entry in #R$FF62)? Then show the password too.
@ $C390 label=SetUpMap
  $C390 Wait two DELAYs of 65,536 loops (about 64 frames) on the LEVEL screen, then decode the map.
N $C39C Then a pass over the map. Tiles below &20 and &27 stay as they are.
@ $C39F label=SetUpCell
  $C3A4 &7F: the start.
  $C3AE &20-&26 (the generators): random bits 3-4, which the drawing ignores (#R$C59A).
@ $C3BB label=SetUpMonster
  $C3BB &28-&2F (a monster of type 0-7): swap the nibbles, so &8t-&Ft with the type in bits 4-6; random bits 2-3; bits 0-1 (the half-tile offsets of a monster's position) clear.
@ $C3CD label=SetUpStart
  $C3CD The start: floor, and both players there.
  $C3DA The view's origin: 10 characters up and left of the start, kept within 0-40.
@ $C3EA label=ClampOrigin
  $C3EA A - 10, kept within 0-40.
@ $C3F6 label=ShowPassword
  $C3F6 PASSWORD.. and the four letters at IX.
T $C3FC,11,10:n1

@ $C418 label=DecodeLevel
c $C418 Decode the level at (#R$FF5E) into the map at &BC00
D $C418 The map is 32 x 32 tiles, a row of 32 bytes. The data holds rows 1-30, columns 1-30; this routine adds the border. A byte below &80 is one tile. A byte &80+t is a run: the next byte n gives n+1 tiles t (n = 0 gives 256). Rows don't end a run. All 50 levels decode with it, ending at &B8DD [measured: the original's routine against a Python model].
D $C418 The border: columns 0 and 31 are tile 5, row 31 is tile 4, and row 0 is tile 4, or 5 above a wall (tiles 1-5 and &11).
  $C418 Row 1, column 0 is the border.
@ $C422 label=DecodeNext
  $C437 Leave the pointer at the next level's data.
  $C43B Row 31: tile 4.
  $C443 Row 0: tile 4, or 5 above tiles 1-5 and &11.
@ $C462 label=DecodeRun
c $C462 Write a run of n tiles; return the tile in A for one more
R $C462 A &80 + tile
R $C462 DE The run byte; n follows it
@ $C474 label=DecodeStep
c $C474 Next cell: at column 31, write the side walls and go to the next row's column 1
D $C474 L is stepped alone: it never passes &FF here, because column 31 (L AND &1F = &1F) moves on with INC HL.
@ $C480 label=SideWalls

@ $C487 label=WipePlayfield
c $C487 Clear the playfield's pixels and set its attributes to A
D $C487 Columns 8-31 of every row. #R$C49F, the attribute half, is also called on its own.
R $C487 A Attribute
@ $C49F label=FillAttrs
  $C49F Fill attribute cells with B from HL to the end of the screen, skipping columns 0-7.

; ---------------------------------------------------------------------------
; The smart bomb

@ $C4B0 label=SmartBomb
c $C4B0 The smart bomb: clear the view's monsters and generators
D $C4B0 Called when a player uses one (&C9A8, &CCCB) or a star hits tile &10 (&C794). Two outcomes, chosen by R [measured: both run with R forced]:
D $C4B0 - R >= 6 (122 times in 128): every monster in the view and a margin of a tile is removed, and every generator (&20-&3E: not &27) and the players' tiles become floor.
D $C4B0 - R < 6: across the whole map, every monster becomes a locked chest (&0C), and everything else from &20 up (the generators, the players' tiles) becomes &0E.
D $C4B0 Then the floor flashes through 8 colours, with a sound for each: about 69 frames in all [measured].
  $C4B0 Random: R.
  $C4B6 The view and its margin: HL its top-left in the map, B its rows (#R$CE58).
@ $C4BB label=BombRow
  $C4BB 14 tiles a row.
  $C4C6 Tile &27 (and anything ending in 7) survives.
  $C4D2 The next row.
@ $C4D8 label=BombFlash
  $C4D8 Eight times: the floor's paper colour + 1, redraw the view, sound.
  $C4EC The floor back to its own colour.
@ $C4F5 label=BombSound
c $C4F5 The smart bomb's sound: two sweeps of 128 clicks on the beeper
D $C4F5 The first with the gap between clicks growing, the second with it shrinking. The border stays black.
@ $C515 label=BombMonster
c $C515 Remove the monster whose tile HL holds
D $C515 Bits 1 and 0 of the tile say whether the monster stands a character down and right of the tile: so its four cells are found, and cleared (#R$D1A2 with &BA4B = 0).
@ $C531 label=BombJackpot
c $C531 R < 6: every monster in the map a locked chest, everything else from &20 a &0E
  $C541 Redraw the cell if it is in view.

; ---------------------------------------------------------------------------
; The view and the tiles

@ $C54C label=DrawView
c $C54C Draw the view: 12 x 12 tiles from the map at the origin
D $C54C The view is columns 8-31, rows 0-23 of the screen. Tiles from &40 up (monsters and players) are drawn as floor here: they draw themselves. About 4.6 frames [measured].
@ $C574 label=ViewCell
c $C574 The map address of the view's cell (B, C) characters from the origin
R $C574 B Rows down from the origin (#R$BA4C)
R $C574 C Columns across from the origin (#R$BA4D)
R $C574 O:HL The map cell: &BC00 + 32 * ((row) / 2) + (column) / 2
  $C574 32 * ((BA4C + B) / 2): A is below 64, so the shifts lose nothing.
  $C58E Column / 2, kept within the row.
@ $C59A label=DrawTile
c $C59A Draw the tile at HL in the screen's character (D, E)
R $C59A HL The map cell
R $C59A D Screen row (characters)
R $C59A E Screen column (characters)
  $C59A From &40 up: floor.
  $C5A0 &20-&3F: drop bits 3-4 (the generators' random bits).
  $C5A6 The attributes, then the pixels.
@ $C5B1 label=BlitBlock
c $C5B1 Copy a 16 x 16 block from HL to the screen at DE, opaque
D $C5B1 C = &FF so that the LDIs (which decrement BC) never touch the line count in B. #R$C946 moves DE down a pixel line, and ends the loop at the bottom of the screen.
@ $C5C0 label=ColourTile
c $C5C0 Colour a tile's 2 x 2 cells; then HL = its graphics, DE = its screen address
D $C5C0 Each tile type has one attribute in #R$FF02: an ink on black paper, but for tile &13. The graphics block is &DD00 + 32 * A.
R $C5C0 A Tile (graphics block)
R $C5C0 D Screen row (characters)
R $C5C0 E Screen column (characters)
R $C5C0 O:HL The block's graphics
R $C5C0 O:DE The screen address
  $C5C0 The attribute.
  $C5CC HL = &5800 + 32 * D + E.
@ $C5EE label=BlockAddr
  $C5EE HL = &DD00 + 32 * A: the 192 blocks, 32 bytes each.
@ $C5FF label=CharAddr
  $C5FF DE = the screen address of the top line of character (D, E).

@ $C60E label=LaunchStar
c $C60E Throw a star
D $C60E Called from the players' code (&CA26, &CD49). The star moves two characters a step in one of 8 directions (#R$FF34). Then on into the stars' code at &C659.
R $C60E IX The star's record (&BA3B or &BA40): row, column, row step, column step, tile
R $C60E H The star's tile
R $C60E L Direction in bits 1-3
R $C60E D Thrower's row (characters)
R $C60E E Thrower's column (characters)
i $C632

; ---------------------------------------------------------------------------
; Keys and printing

@ $D972 label=ReadKey
c $D972 Read the keyboard: Z if no key; else the key's character in D
D $D972 The half-rows are read from &FEFE to &7FFE; the first with a key down wins, and in it the lowest bit. The character comes from the 48K ROM's key table at &0205 (ROM 1 is paged in on a 128K during play): letters, digits, space and ENTER (&0D) as ASCII, SYMBOL SHIFT &0E, and CAPS SHIFT &E3, the byte after the table [measured: every key].
R $D972 O:A The half-row's keys (bit set = down), 0 and Z if none
R $D972 O:D The character
  $D97E E counts down from &34 a half-row, so &0200 + E - 8 * (bit + 1) is the key's entry.

@ $D995 label=PrintAt
c $D995 Print the string after the CALL at row D, column E
D $D995 The string is 0-terminated, and execution continues after it. There are no control codes: every other byte is a glyph (#R$D9AA). AF and HL are kept.
R $D995 D Row (characters)
R $D995 E Column (characters)
@ $D999 label=Print
c $D999 Print the string after the CALL at the print position
  $D9A0 #R$D9AA uses the main registers.

@ $D9AA label=PrintChar
c $D9AA Print character A at the print position and move it on
D $D9AA Writes the glyph's pixels only: the text takes the cell's colour. The font is #R$F500, from character &20 (so &F400 + 8 * A). At column 32 the position moves to the next row's column 0, and past row 23 to (0, 0).
R $D9AA A Character
  $D9AA HL = &F400 + 8 * A.

; ---------------------------------------------------------------------------
; The status panel

@ $D9EC label=StatusTick
c $D9EC Every 25th pass: music, strength, respawns and the idle timers
D $D9EC The status panel only changes when something calls #R$DB71: there is no regular redraw. Each tick:
D $D9EC - restart song 0 if the last song has ended (128K);
D $D9EC - each player in play loses 1 strength;
D $D9EC - #R$DA59 closes the one-way tiles walked through;
D $D9EC - #R$FF49 counts down. At 0 (100 ticks after the last treasure, about 42 seconds of idle play [measured]), every key, door and chest (&08-&0B) vanishes, and #R$FF48 counts down. When that reaches 0, every border wall (tiles 4 and 5) becomes an exit (&1E) [measured].
D $D9EC Nothing resets #R$FF48 and #R$FF49 at a level's start: only treasure does (#R$DB3F, #R$DB59).
  $D9EC Every 25 passes.
  $D9F9 Song 0 again if the music has stopped.
  $D9FC Drain: DE = -1.
  $DA12 The one-way tiles.
  $DA15 The idle timer.
  $DA1D Keys, doors and chests (&08-&0B) vanish, and are redrawn as floor.
  $DA34 100 ticks to the next.
  $DA39 The fourth time: every border wall (4 and 5) becomes an exit (&1E). Then this counter is &FF, so it won't come round again.

@ $DA59 label=CloseOneWays
c $DA59 Turn each one-way tile walked through into &07, once its cell is empty
D $DA59 #R$FF4B lists up to 8 map addresses, high byte first (0 = none), filled when a player walks over a one-way tile (&16, &D423: see monsters.ctl). When the cell holds 0 again, the entry is cleared, &07 is written there and the cell is redrawn.

@ $DA7E label=PrintGrid
c $DA7E Print up to 9 icons in a 3 x 3 grid: L of character A, then spaces
D $DA7E The panel's inventories: keys held (glyph &22) at row 5, column 1, and magics (&23) at row 5, column 4, for player 1 (&CB16), and the same at row 13 for player 2.
R $DA7E A Character
R $DA7E L How many
R $DA7E D Top row
R $DA7E E Left column
@ $DA9C label=PrintNumberAt
c $DA9C Print A as 2 digits at (D, E) (never called)

@ $DAA6 label=P1AddStrength
c $DAA6 Add DE to player 1's strength; below 0, player 1 dies
D $DAA6 Called with DE = -1 by #R$D9EC, with the food's value (&CB3B), and with a hit's cost (&D084). No change while the timer at &BA58 runs. While &BA56 is set, a change is ignored when R AND &0C is 0 (1 time in 4).
D $DAA6 Death: player 1 leaves play (bits 0 and 2 of #R$BA73), the player's tile is cleared from the map, strength shows 0, song 2 plays, and on to the name entry at &D85E with '1' and the treasure.
R $DAA6 DE Change
  $DAB1 Random: R.
@ $DAB6 label=P1ApplyStrength
@ $DAE8 label=P1SetStrength
  $DAE8 Store HL as player 1's strength, and print it at row 2, column 1.
@ $DAF4 label=P2AddStrength
c $DAF4 Add DE to player 2's strength; below 0, player 2 dies
D $DAF4 As #R$DAA6, with &BA67, &BA65, bits 1 and 3 of #R$BA73, and '2'. Strength is printed at row 10, column 1.
  $DAFF Random: R.
@ $DB04 label=P2ApplyStrength
@ $DB33 label=P2SetStrength

@ $DB3F label=P1AddTreasure
c $DB3F Add DE to player 1's treasure and print it; reset the idle timers
D $DB3F Treasure is printed at row 4, column 1. The idle timers (#R$FF49, #R$FF48) start again: 100 ticks, 4 stages.
R $DB3F DE Amount
@ $DB59 label=P2AddTreasure
c $DB59 Add DE to player 2's treasure and print it; reset the idle timers
D $DB59 Treasure is printed at row 12, column 1.
R $DB59 DE Amount

@ $DB71 label=Print5Digits
c $DB71 Print HL as 5 digits at the print position
D $DB71 The panel's figures have a sixth digit, a 0 that is part of the loading screen: so strength and treasure show 10 times their value. Returns A = 0.
R $DB71 HL Number (0-65535)
@ $DB83 label=Print2Digits
  $DB83 Entry: the last 2 digits of HL.
@ $DB91 label=PrintDigit
c $DB91 Print HL / DE as a digit, leaving HL = HL mod DE

@ $DBA2 label=ResetGame
c $DBA2 Zero the per-game state
D $DBA2 Strength, treasure, the password typed (#R$FF2A) and the players' counts (keys, magics and others), then #R$DBCA.
@ $DBCA label=ResetLevel
c $DBCA Zero the per-level state
D $DBCA The players' per-level counts and the one-way tiles' list (#R$FF4B).

; ---------------------------------------------------------------------------
; The slide's screen shifts
;
; The slide (&CB4C-&CC69) moves the view up to 8 tiles in steps of one: each
; step shifts the playfield two characters with one of these, moves the
; origin, and draws the new strip of 12 tiles (#R$C574, #R$C59A).

@ $DBE8 label=ShiftLeft
c $DBE8 Shift the playfield 16 pixels left (the view moves right)
D $DBE8 Columns 10-31 move to 8-29, pixels and attributes; columns 30-31 are left for the new strip. About 1.8 frames [measured].
@ $DC17 label=ShiftRight
c $DC17 Shift the playfield 16 pixels right (the view moves left)
D $DC17 Columns 8-29 move to 10-31, with LDDR. About 1.8 frames [measured].
@ $DC48 label=ShiftUp
c $DC48 Shift the playfield 16 pixels up (the view moves down)
D $DC48 Lines 16-191 move to 0-175 in columns 8-31, and attribute rows 2-23 to 0-21. About 1.8 frames [measured].
@ $DC7F label=ShiftDown
c $DC7F Shift the playfield 16 pixels down (the view moves up)
D $DC7F Lines 0-175 move to 16-191, from the bottom up, and attribute rows 0-21 to 2-23. About 1.8 frames [measured].
@ $DCB7 label=LineDown
c $DCB7 HL = the screen address a pixel line down
@ $DCC7 label=LineUp
c $DCC7 HL = the screen address a pixel line up
i $DCDC

; ---------------------------------------------------------------------------
; Variables in &BA29-&BBBA used here (the players' blocks are &BA4E and
; &BA5D, 15 bytes each; most of their fields belong to players.ctl)

@ $BA45 label=PrintPos
b $BA45 The print position: column, then row
B $BA45,2,1
i $BA47
@ $BA4C label=ViewOrigin
b $BA4C The view's origin in the map: row, then column, in characters (0-40, even)
B $BA4C,2,1
i $BA4E
@ $BA73 label=InPlay
b $BA73 Which players are in play
D $BA73 Bit 0 player 1 in play, bit 1 player 2; bit 2 player 1 has left by an exit, bit 3 player 2. When bits 0-1 are both clear, #R$C153 moves bits 2-3 down and starts the next level.
B $BA73,1,1
@ $BA74 label=Level
b $BA74 The level, from 0
B $BA74,1,1
i $BA75
@ $BA76 label=MenuColour
b $BA76 The menu's colour while it flashes (&0E or &17)
B $BA76,1,1
i $BA77

; ---------------------------------------------------------------------------
; Data

@ $F500 label=Font
b $F500 The font: 8 x 8 glyphs from character &20
D $F500 Indexed from &F400 (#R$D9AA). &20 space, &21 !, &22 a key and &23 a magic (the panel's inventories), &24-&29 M A S C R E for the title, &2A a block, &2B dots, &2C-&2F , . . , (&2E is the full stop used), &30-&39 digits, &3A a star, &3B-&40 the title's NINJA, &41-&5A A-Z, &5B-&5C blank. Glyph &5D has only 6 bytes before the beeper player at &F6EE, and is never printed.
B $F500,494,8
i $F6EE

@ $FF02 label=TileAttrs
b $FF02 Each tile type's attribute, &00-&27
D $FF02 Ink on black paper, but &13 (&9C: green on magenta, flashing). #R$C34F sets &00 (the floor), &16 and &1E (the exit) to the level's floor colour; #R$C4D8 changes &00's paper while it flashes.
B $FF02,40,8
@ $FF2A label=PasswordTyped
b $FF2A The password typed at the menu (&D58B); zeroed by #R$DBA2
T $FF2A,4,4
i $FF2E
@ $FF48 label=IdleStage
b $FF48 How many more idle periods until the walls become exits (#R$D9EC)
B $FF48,1,1
@ $FF49 label=IdleTicks
b $FF49 Status ticks left in this idle period (#R$D9EC)
B $FF49,1,1
@ $FF4A label=StatusPasses
b $FF4A Passes left until the next status tick (#R$D9EC)
B $FF4A,1,1
i $FF4B
u $FF5B Unused
B $FF5B,3,1
@ $FF5E label=LevelPtr
b $FF5E The next level's packed data (#R$C418)
W $FF5E,2
i $FF60
@ $FF62 label=Passwords
b $FF62 The 8 passwords: 4 letters, then the level (from 0) they start
D $FF62 Levels 5, 10 ... 40 as the LEVEL screen numbers them, which shows the password when it starts one.
T $FF62,40,4:n1
@ $FF8A label=TitleAttrs
b $FF8A The title's colours: 10 cells of row 1, then 10 of row 2
B $FF8A,20,10
u $FF9E Unused
i $FFA0
