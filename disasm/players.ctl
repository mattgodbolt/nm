; Ninja Massacre, ZX Spectrum: the players, their controls and the throwing stars.
; SkoolKit control-file entries for &C632-&CE76 and the variables that code uses;
; see docs/research/players.md. `make disasm` reads every disasm/*.ctl.
;
; Coordinates: a position is (row, column) in character cells of the 64 x 64-cell
; map; a map tile (#R$BC00, 32 x 32) is 2 x 2 cells, so tile = (row/2, col/2).
; The view's origin is (#R$BA4C, #R$BA4D); the playfield is view rows 0-23 at
; screen columns 8-31.
;
; ---------------------------------------------------------------- the stars
@ $C632 label=StarsUpdate
c $C632 Move both throwing stars one cell
D $C632 Called every main-loop pass (#R$C01A). Player 1's star is the record at #R$BA3B, player 2's at #R$BA40.
@ $C63D label=StarMove
c $C63D Move one star (IX) one cell along its direction
D $C63D Erases the star's cell with the floor pattern, then looks at the map tile under its next cell: an empty tile, or one holding the thrower, lets it move; anything else is a hit, dispatched on the tile.
R $C63D IX Star record: +0 row, +1 column, +2 drow, +3 dcolumn, +4 thrower (&71 or &72; 0 = no star)
N $C63D A star out of the view's inside is killed by #R$C816.
@ $C659 label=StarLook
c $C659 Look at the tile under the star's new cell (B, C)
D $C659 Entered from #R$C63D, from #R$C60E when a star is thrown, and after a transporter (#R$C7C0).
R $C659 B New row
R $C659 C New column
@ $C660 label=StarAdvance
N $C660 Store the new cell and draw the star there (#R$BA29).
@ $C66E label=StarHit
N $C66E The tile dispatch. In order: the thrower's own tile passes; &01-&03 crumbling wall; &11 wall; &0E food and &14 boulder are destroyed; &10 magic sets itself off; &13 creeper; &15 transporter; &1F wall; &20-&3F trap doors; &7F a monster's marker; &70-&7E players; &80+ monsters; &40-&5F pass; everything else is a wall.
C $C6AF,4 Tiles &40-&5F: no level holds them after loading (#R$C39F), so this pass-through is never taken.
C $C6B6,4 A wall: bounce while #R$FF44 lasts, otherwise the star stops.
@ $C6C1 label=StarHitMonster
c $C6C1 Star hits a monster: up to power + 1 hits, then 2 points of treasure to the thrower
D $C6C1 Power is the high byte of the thrower's power counter (#R$BA54). Each hit is #R$C86C, with its noise; the loop stops once the monster dies or can't be hurt.
@ $C6E4 label=StarHitTrapDoor
c $C6E4 Star hits a trap door (&20-&3F): power + 1 hits of 8 off the tile, destroyed below &20
D $C6E4 Bits 3-4 of a trap door are its hits left, bits 0-2 its kind; kind 7 (&27, &2F, &37, &3F) can't be hurt.
N $C702 The 50-point reward compares the thrower with &F1 and &F2, but the thrower byte is &71 or &72, so it is never paid [measured: no treasure for a destroyed trap door].
@ $C712 label=StarStop
@ $C717 label=StarHitWall1F
c $C717 Star hits wall &1F: it becomes &27, the pit
@ $C720 label=StarBounce
c $C720 Bounce a star off a wall, one axis at a time
D $C720 Uses up one of #R$FF44. Each axis whose next cell is not empty is reversed, and the star steps back along it without being drawn this pass.
@ $C762 label=StarHitCrumble
c $C762 Star hits a crumbling wall (&01-&03): the next stage, and gone after &03
@ $C770 label=CrumbleAbove
c $C770 When a crumbling wall goes, mend the wall tile above it
D $C770 A vertical wall end (&05) above becomes &04; a wall &11 above becomes &01.
R $C770 HL The tile that went
@ $C78E label=StarHitMagic
c $C78E Star hits a magic scroll (&10): it goes off as a smart bomb (#R$C4B0) and the view is redrawn
@ $C79A label=StarHitWall11
c $C79A Star hits wall &11: it becomes crumbling wall &02
@ $C7A3 label=StarHitCreeper
c $C7A3 Star hits the creeper (&13): destroyed only on every Nth hit, N random from 1 to 32
D $C7A3 The count is #R$BA6D, shared by every creeper tile.
C $C7AF,2 Random: the hits until the next creeper tile goes.
@ $C7B7 label=StarDestroy
c $C7B7 Star destroys the tile it hit (food &0E, boulder &14, creeper &13)
@ $C7C0 label=StarTransport
c $C7C0 Star hits a transporter (&15): it comes out of a random transporter in view and flies on
@ $C7DB label=StarHitPlayer
c $C7DB Star hits a player: toggles that player frozen if the other player holds the freeze ring
@ $C7EA label=StarFreeze1
c $C7EA Freeze or unfreeze player 1 (#R$FF45) when player 2 has the ring (#R$BA6B)
@ $C800 label=StarFreeze2
c $C800 Freeze or unfreeze player 2 (#R$FF46) when player 1 has the ring (#R$BA5C)
@ $C816 label=StarCell
c $C816 Draw an 8 x 8 pattern at a map cell, for a star
D $C816 The ink is the floor's (#R$FF02) for the erasing pattern, whose first byte is 0, and the next of the star's cycling inks (#R$FF47) for the star.
R $C816 D Row
R $C816 E Column
R $C816 HL Pattern: #R$BA29 (star) or #R$BA32 (floor)
R $C816 IX Star record, cleared if the cell is outside view rows and columns 1-22
R $C816 O:F Z drawn, NZ outside the view
@ $C865 label=StarOffView
;
; ---------------------------------------------------------------- hitting monsters
@ $C86C label=HitMonster
c $C86C Hit the monster in tile HL once: noise, one point of health off, and remove it when it dies
D $C86C A monster tile is bits 0-1 its offset in the tile (column, row), bits 2-3 its health, bits 4-6 its kind, bit 7 set. Kind 7 (&F0-&FF) can't be hurt. Health below 0 kills: its four cells are cleared and its picture is drawn over with floor. Used by stars (#R$C6C1) and by hand-to-hand fighting (&D1EB).
R $C86C B Row of a cell in the tile
R $C86C C Column of a cell in the tile
R $C86C HL Map tile
R $C86C O:F Z when the monster died or can't be hurt, NZ when it lives on
@ $C8A4 label=HitMarker
c $C8A4 A star or a player touched a monster's marker (&7F): find the monster to the left, up-left or up, and hit it
R $C8A4 B Row of the cell touched
R $C8A4 C Column of the cell touched
@ $C8C4 label=HitNoise
c $C8C4 Beeper: a burst of noise, D segments of random level and length
D $C8C4 Each segment sets the speaker to bit 4 of R and holds it for R x 24 T-states (R = 0 holds 256 x 24). Called with D = 50: 72,000-82,000 T-states a hit [measured]. The border goes black.
R $C8C4 D Segments
C $C8C6,2 Random (sound only): the speaker level.
C $C8CC,2 Random (sound only): the segment's length.
;
; ---------------------------------------------------------------- drawing 16 x 16 pictures
@ $C8D8 label=DrawSprite
c $C8D8 Draw a 16 x 16 picture with attribute B
D $C8D8 The monsters' entry (#R$CFB9).
R $C8D8 B Attribute
R $C8D8 HL Picture (#R$C5EE)
R $C8D8 DE Screen address of the top line (#R$C5FF)
@ $C8E8 label=DrawSpriteA
c $C8E8 Draw a 16 x 16 picture with attribute A', clipped at the playfield's left and right edges
D $C8E8 Opaque: two bytes a line, then two attribute cells a row. A picture whose left byte is in screen column 7 (the panel) draws only its right byte; one at column 31 only its left. Clipping above and below relies on the Spectrum: a picture at view row -1 (the monsters', #R$CFB9) starts at &38xx, in the ROM, where its writes are lost, and its attribute row is moved to screen row 0 (#R$C93C); one at row 23 stops at the bottom (#R$C946) but writes its second attribute row to &5B00-&5B1F.
R $C8E8 A' Attribute
R $C8E8 BC &1040: B counts the 16 lines, C absorbs the LDIs' count
R $C8E8 HL Picture
R $C8E8 DE Screen address of the top line
@ $C902 label=DrawSpriteRight
c $C902 Draw only the right byte of each line (the picture's left half is in the panel)
@ $C917 label=DrawSpriteLeft
c $C917 Draw only the left byte of each line (screen column 31)
@ $C92A label=SpriteAttr
c $C92A Attribute address of screen address DE, and the step to the next attribute row
R $C92A DE Screen address of the top line
R $C92A O:HL Attribute address
R $C92A O:DE &20, or 0 when DE is above the screen (both rows then go to the top row)
@ $C93C label=SpriteAttrTop
@ $C946 label=NextLineDown
c $C946 Move screen address DE down one pixel line; B = 1 below the bottom, to end the loop
;
; ---------------------------------------------------------------- controls
@ $C95E label=Fire1
c $C95E Read player 1's fire (self-modified)
D $C95E Port and mask are set by the controls menu (&D680, &D6B7): SPACE by default, or the Kempston port &1F with the CPL made a NOP.
R $C95E O:A Nonzero when fire is held
R $C95E O:F NZ when fire is held
@ $C967 label=Diagonal
c $C967 Turn a left or right facing into a diagonal: +8 when going up, +12 when going down
R $C967 E Vertical step: -1 up, 1 down, 0 neither
R $C967 HL Facing byte (#R$BA47 or #R$BA48)
;
; ---------------------------------------------------------------- player 1
@ $C978 label=Player1Update
c $C978 Player 1's pass: read the controls, throw or move, scroll the view, draw
D $C978 Called from #R$C168 every pass while player 1 is in the level. Returns NZ when the player was drawn; Z (no drawing, the view couldn't scroll) makes #R$C168 set the step bit, so the next pass tries again.
N $C980 Frozen by player 2's freeze ring (#R$FF45): no control is read until it runs out.
@ $C98D label=P1Keys
N $C98D The magic key (ENTER by default): a smart bomb (#R$C4B0) while there are any (#R$BA5A), one a pass while held.
C $C993,3 Port, self-modified by the controls menu.
C $C999,2 Mask, self-modified.
@ $C9AF label=P1Up
N $C9AF Up (Q by default): E = -1, facing 4. Each of the four direction sites below has its port in the LD BC, its CPL (a NOP for Kempston) and its mask self-modified by the controls menu (&D664-&D6DD). A later site's facing overrides an earlier one's: down beats up and left beats right.
@ $C9C1 label=P1Down
N $C9C1 Down (A): E = 1, facing 6.
@ $C9D3 label=P1Right
N $C9D3 Right (P): D = 1, facing 0, made diagonal by #R$C967.
@ $C9E6 label=P1Left
N $C9E6 Left (O): D = -1, facing 2, made diagonal by #R$C967.
@ $C9FC label=P1Fire
N $C9FC Fire: throw a star in the facing's direction if player 1's star (#R$BA3B) isn't flying. Holding fire throws again as soon as it lands. A throw uses one of the power counter (#R$BA54), plays the throw chirp (#R$C508) and doesn't move the player.
C $CA20,6 The star's bounces are copied to #R$FF44, which both stars share.
@ $CA31 label=P1Move
N $CA31 Move: lift player 1 out of the map, then step on every other pass.
C $CA38,4 #R$BA85 = vertical step, #R$BA86 = horizontal step.
C $CA4D,12 A new facing (bit 0 ignored) clears the step bit, so a turn takes a pass before the first step.
C $CA5D,24 Step only when the step bit (bit 0) was set; then toggle it.
C $CA75,3 Blocked by anything in the new cells?
N $CA7A Blocked: set the step bit (so the next pass tries again) and slide, first along the horizontal step alone, then the vertical.
@ $CAA6 label=P1Stay
N $CAA6 Not moving: keep the position.
@ $CAAA label=P1Place
c $CAAA Player 1 at DE: scroll the view if it is near an edge, else store the position and draw
D $CAAA Within the view, rows and columns 2-20 are allowed. Outside them the view slides (#R$CB4C, #R$CB93, #R$CBD5, #R$CC23) and the position isn't stored this pass. The picture is frame &30 + facing (#R$BA47) in bright cyan (&45).
R $CAAA DE New position (D row, E column)
C $CAD2,17 Moved: erase the old picture, with a click (#R$CC75).
C $CAE3,7 Invulnerable (#R$BA58): blink.
@ $CAF1 label=DrawFrame
c $CAF1 Draw picture A at view cell DE with attribute C; returns NZ
R $CAF1 A Picture number (#R$C5EE)
R $CAF1 C Attribute
R $CAF1 D View row
R $CAF1 E Screen column
@ $CAFF label=Blink
c $CAFF While invulnerable, draw floor instead of the player on even counts, and return from the player's routine
R $CAFF A Invulnerability count (#R$BA58 or #R$BA67)
@ $CB0C label=P1Touch
c $CB0C Player 1 touches the four cells at DE: act on what's there, update the panel; NZ if blocked
D $CB0C #R$D1BA does the touching and leaves the treasure (&FF31) and strength (&FF32) to add and the last tile touched (&FF33). Every nonzero tile blocks. The staircase (&1E) leaves the level (&D537). The keys and magic icons, treasure and strength are reprinted on every call.
R $CB0C DE Position (D row, E column)
R $CB0C O:F NZ when blocked
;
; ---------------------------------------------------------------- scrolling
@ $CB4C label=ScrollUp
c $CB4C Slide the view up 8 tile rows, a tile row a step
D $CB4C With both players in the level, it slides only as far as keeps the other player (H = row) in view rows up to 20; if that is no distance it returns Z and the mover stays put. Stops early at the map's edge (returns Z). Then the mover is redrawn, with a click (#R$CC75).
R $CB4C H Other player's row
R $CB4C L Other player's column
@ $CB67 label=ScrollUpStep
@ $CB93 label=ScrollDown
c $CB93 Slide the view down 8 tile rows (as #R$CB4C)
@ $CBA8 label=ScrollDownStep
@ $CBD5 label=ScrollLeft
c $CBD5 Slide the view left 8 tile columns (as #R$CB4C, with L the other player's column)
@ $CBF0 label=ScrollLeftStep
@ $CC23 label=ScrollRight
c $CC23 Slide the view right 8 tile columns (as #R$CBD5)
@ $CC38 label=ScrollRightStep
@ $CC6C label=Fire2
c $CC6C Read player 2's fire (self-modified; 0 by default, the Sinclair joystick's fire)
R $CC6C O:F NZ when fire is held
@ $CC75 label=EraseOld
c $CC75 Erase the moving player's picture at its old position (#R$BA49), with a click
@ $CC79 label=EraseAt
c $CC79 Draw floor at map position DE, with a click on the beeper
D $CC79 The click is the speaker on for the 18 T-states between two OUTs, once a step.
R $CC79 DE Position (D row, E column)
C $CC8D,8 The click.
;
; ---------------------------------------------------------------- player 2
@ $CC98 label=Player2Update
c $CC98 Player 2's pass (as #R$C978, with player 2's variables and keys)
D $CC98 Called from #R$C187. The default keys are the Sinclair joystick on 6-0 (6 left, 7 right, 8 down, 9 up, 0 fire) and CAPS SHIFT for magic.
@ $CCB0 label=P2Keys
C $CCB6,3 Magic port, self-modified (&D71B).
@ $CCD2 label=P2Up
N $CCD2 Up (9). As for player 1, each site's port, CPL and mask are self-modified (&D6E7-&D779).
@ $CCE4 label=P2Down
N $CCE4 Down (8).
@ $CCF6 label=P2Right
N $CCF6 Right (7).
@ $CD09 label=P2Left
N $CD09 Left (6).
@ $CD1F label=P2Fire
@ $CD54 label=P2Move
@ $CDCA label=P2Stay
@ $CDCE label=P2Place
c $CDCE Player 2 at DE (as #R$CAAA); drawn in bright green (&44)
@ $CE18 label=P2Touch
c $CE18 Player 2 touches the four cells at DE (as #R$CB0C)
;
@ $CE58 label=ViewMapPtr
c $CE58 Map address of the smart bomb's area: the view and a tile's margin
D $CE58 Used by #R$C4B0: 14 tiles a row; 14 rows, or 12 when the view is at the map's bottom. The columns aren't clamped, so with the view at the right edge the area wraps into the next row.
R $CE58 C Column offset (0)
R $CE58 O:HL Map address
R $CE58 O:B Rows
;
; ---------------------------------------------------------------- data
@ $BA29 label=StarPattern
b $BA29 The star, 8 x 8
@ $BA31 label=Unused_BA31
u $BA31 Unused
@ $BA32 label=FloorQuarter
b $BA32 A quarter of the floor tile, 8 x 8: what erases a star
@ $BA3A label=Unused_BA3A
u $BA3A Unused
@ $BA3B label=Star1
g $BA3B Player 1's star: row, column, drow, dcolumn, thrower (0 = none)
B $BA3B,5,1
@ $BA40 label=Star2
g $BA40 Player 2's star (as #R$BA3B)
B $BA40,5,1
@ $BA47 label=P1Facing
g $BA47 Player 1's facing: bits 1-3 direction (0 right, 2 left, 4 up, 6 down, 8 up-right, 10 up-left, 12 down-right, 14 down-left), bit 0 the step bit; the picture is &30 + this
@ $BA48 label=P2Facing
g $BA48 Player 2's facing (as #R$BA47)
@ $BA49 label=OldPos
g $BA49 The moving player's position at the start of its pass (column, row), for the erase
B $BA49,2,1
@ $BA4B label=MapStamp
g $BA4B Code written into the map's four cells by #R$D1A2: &71, &72 or 0 (also the monsters')
@ $BA4E label=Player1
g $BA4E Player 1's record (IX in #R$D1BA): column, row, treasure (2), strength (2), power counter (2; the high byte is the shot power), armour, skull timer, heart timer, keys, magic, bounces, freeze ring
B $BA4E,2,1
W $BA50,6,2
B $BA56,7,1
@ $BA50 label=P1Treasure
@ $BA52 label=P1Strength
@ $BA54 label=P1Power
@ $BA56 label=P1Armour
@ $BA57 label=P1Skull
@ $BA58 label=P1Heart
@ $BA59 label=P1Keys
@ $BA5A label=P1Magic
@ $BA5B label=P1Bounces
@ $BA5C label=P1Ring
@ $BA5D label=Player2
g $BA5D Player 2's record (as #R$BA4E)
B $BA5D,2,1
W $BA5F,6,2
B $BA65,7,1
@ $BA5F label=P2Treasure
@ $BA61 label=P2Strength
@ $BA63 label=P2Power
@ $BA65 label=P2Armour
@ $BA66 label=P2Skull
@ $BA67 label=P2Heart
@ $BA68 label=P2Keys
@ $BA69 label=P2Magic
@ $BA6A label=P2Bounces
@ $BA6B label=P2Ring
@ $BA6D label=CreeperHits
g $BA6D Star hits left before the next creeper tile (&13) is destroyed
@ $BA70 label=P1LastFacing
g $BA70 Player 1's facing on the previous step attempt, to spot a turn
@ $BA71 label=P2LastFacing
g $BA71 Player 2's facing on the previous step attempt
@ $BA85 label=StepV
g $BA85 The step being tried: vertical (-1, 0, 1); the monsters use it too
@ $BA86 label=StepH
g $BA86 The step being tried: horizontal (-1, 0, 1)
@ $FF34 label=StarDirs
b $FF34 A star's (drow, dcolumn) for each facing / 2: right, left, up, down, up-right, up-left, down-right, down-left
B $FF34,16,2
@ $FF44 label=Bounces
g $FF44 Bounces left for the stars in flight; set at each throw and shared by both stars
@ $FF45 label=P1Frozen
g $FF45 Passes player 1 stays frozen (255 when hit)
@ $FF46 label=P2Frozen
g $FF46 Passes player 2 stays frozen
@ $FF47 label=StarInk
g $FF47 The star's ink, cycling 0-7 a cell
