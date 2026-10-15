; Ninja Massacre (ZX Spectrum, Codemasters 1989): the monsters, trap doors,
; the spreading tile, touching things (items, doors, chests, the exit, the
; other player), the map helpers, and the menus' key entry, game over and
; high score that share the range.
; SkoolKit control-file entries for docs/research/monsters.md. Code
; &CE77-&D971 and the variables and tables those routines own; the other
; .ctl files hold the rest. Positions are in characters (8 pixels): a map
; tile is 2 x 2 characters, B a row (0-63) and C a column (0-63).

; ---------------------------------------------------------------------------
; Variables and tables. #R$BA4B (the code #R$D1A2 writes), #R$BA85/#R$BA86
; (the step), #R$BA6E (the high score) and #R$FF4B are entries in core.ctl
; or players.ctl.

@ $BA6C label=FreezeTimer
g $BA6C Clock timer: monsters and trap doors stop while it is non-zero
D $BA6C Set to &FF by the clock (#R$D48F), counted down each pass by &C135.
@ $BA72 label=SparkleFrame
g $BA72 Spawning sparkle frame, 7 down to 0, one step a sweep
D $BA72 A spawning monster (&40-&5F) is drawn as block &28 + this, and becomes a monster when it is scanned while this is 0 (#R$D0DF).
@ $BA75 label=ScanQuarter
g $BA75 Which quarter of the view the monster scan visits this pass (0-3)
@ $BA77 label=MoveSweep
g $BA77 1 on sweeps in which monsters move; also their animation frame
D $BA77 Toggled each time #R$BA75 wraps, so monsters step once every eight passes.
B $BA77,1,1
i $BA78
@ $BA7F label=MonNewPos
g $BA7F A moving monster's new position (column, row)
B $BA7F,2,2
@ $BA81 label=MonOldPos
g $BA81 A moving monster's old position (column, row)
B $BA81,2,2
@ $BA83 label=MonCode
g $BA83 The code of the monster being moved
@ $BA84 label=MonFacing
g $BA84 The moving monster's facing: 0 right (or still), 2 left, 4 up, 6 down, 8 up-right, 10 up-left, 12 down-right, 14 down-left
@ $BA87 label=SpawnOffsets
b $BA87 The eight neighbours a trap door spawns into, as overlapping (row, column) steps
D $BA87 #R$D0AB reads a row step and a column step and then advances one byte, so each byte is a column step and then the next row step: up-left, up, left, up-right, down-right, down, right, down-left (in characters, 2 = one tile). &FF as a column step ends it.
B $BA87,9,9
i $BA90
@ $BA91 label=TrapPos
g $BA91 The trap door being run: its position (column, row)
B $BA91,2,2
i $BA93
@ $BA95 label=SpreadCursor
g $BA95 The spreading tile's cursor: column, then row
D $BA95 #R$D132 moves it one tile check a pass, over every tile of rows 1-30 in 960 passes.
B $BA95,2,2
@ $BA97 label=ScanPhase
g $BA97 The column phase (0-3) of the row being scanned
@ $BA98 label=HitFlag
g $BA98 Non-zero when a monster hit a player this pass: play the noise burst
i $BA99

@ $FF2E label=TouchCount
g $FF2E The touch gate's count: only every tenth contact with something acts
D $FF2E #R$D287 counts it down at each non-empty cell a player touches, and lets the contact through when it reaches 0.
i $FF2F
@ $FF30 label=TouchSpare
g $FF30 Cleared by #R$D1BA, never read
@ $FF31 label=TouchTreasure
g $FF31 Treasure this contact gained (the player's code adds it after #R$D1BA)
@ $FF32 label=TouchStrength
g $FF32 Strength this contact gained (food)
@ $FF33 label=TouchCode
g $FF33 The last non-empty code touched: non-zero blocks the move, &1E is the exit
@ $FF60 label=RepeatCount
g $FF60 Name entry: polls of a held key before it repeats (#R$D8E7)
W $FF60,2,2

; ---------------------------------------------------------------------------
; The monsters

@ $CE77 label=MonsterScan
c $CE77 Scan a quarter of the view: move monsters, run trap doors and sparkles
D $CE77 Called once a pass from the main loop. The area is the view and a one-tile margin (14 x 14 tiles; 12 rows when the view is at the bottom; no margin on the left or top at 0), from #R$CE58. A pass visits every fourth tile of each row, its columns shifted by two on alternate rows; the four quarters (#R$BA75) cover every tile once in four passes. A monster that moves lands on a tile the pass doesn't visit, so none moves twice.
D $CE77 Every tile that holds no monster costs the fixed delay #R$CF04 as well.
  $CE77 No player hit yet this pass.
  $CE7B Phase = quarter; C = 2 x quarter, the first column's offset in characters.
  $CE84 HL = the scan's first cell, B = its row count.
@ $CE87 label=ScanRow
  $CE87 C counts the columns left: 14 - phase.
@ $CE8F label=ScanTile
  $CE8F &80 and up is a monster's head: move it.
@ $CE9D label=ScanOther
  $CE9D Anything else: the delay, then &20-&3E are trap doors and &40-&5F spawning sparkles.
@ $CEB8 label=ScanNext
  $CEB8 Four tiles on.
  $CEC3 Next row: the phase moves by two, and HL to the next row's first tile.
  $CED1 Next quarter. When the sweep is complete, toggle the move flag and step the sparkle.
@ $CEED label=NoiseBurst
  $CEED A monster hit a player: 50 bursts of the beeper, each a length (C) and a level (bit 4) taken from R.
@ $CEF5 label=NoiseLoop
@ $CEFC label=NoiseOut

@ $CF04 label=TileDelay
c $CF04 The fixed delay for each tile scanned that holds no monster
D $CF04 Thirty LD C,(IX+&7B) (a read only): 993 T-states with the RET, 1,010 with the CALL. It paces the pass; a monster's turn costs more.
R $CF04 A Preserved

@ $CF0E label=MonsterMove
c $CF0E Move one monster and draw it
D $CF0E A monster is its code in the map: bit 7 set, bits 4-6 its kind (0-7), bits 2-3 its health (0-3), bits 0-1 a half-tile offset (bit 1 down, bit 0 right). The head cell holds the code and the other cells it covers hold &7F (#R$D1A2).
R $CF0E A The monster's code
R $CF0E HL Its head cell in the map
  $CF13 BC = its position: the tile's, plus the offset bits.
  $CF21 Keep the old position, then clear its cells.
  $CF30 Pick a step towards (or away from) a player.
  $CF37 Only on move sweeps: try the diagonal step, then the column step alone, then the row step alone (a player in the way is hit each time). Otherwise stay.
@ $CF5E label=MonStay
@ $CF62 label=MonPlace
  $CF62 Write &7F into its cells, then the code, with the new offset bits, into the head cell.
  $CF83 Block C = &40 + kind x 16 + facing + move flag; ink B = 4 + health.
  $CF9D If it moved, draw the floor block (0, in the floor's attribute) over the old position.
  $CFB2 Draw the monster at the new one.

@ $CFB9 label=DrawAt
c $CFB9 Draw block C in attribute B at a position, if on screen
D $CFB9 Within a character of the view on each side; the sprite drawer &C8D8 clips.
R $CFB9 B Attribute
R $CFB9 C Block number
R $CFB9 D Row (characters)
R $CFB9 E Column (characters)

@ $CFDF label=MonsterChase
c $CFDF Choose a monster's step: towards the nearer player, or away under an idol
D $CFDF With both players in, the target is the nearer by row distance plus column distance; a tie goes to player 2. The step is the sign of the difference on each axis, negated while the target's idol timer (+9 in its record) runs. Nothing happens while the clock (#R$BA6C) runs.
R $CFDF BC Position in; the stepped position out
  $CFF1 Distance to player 1 (A'), then to player 2 (H).
@ $D019 label=ChaseP2
@ $D021 label=ChaseP1
@ $D027 label=ChaseStep
  $D027 H = row step, E = facing so far: 0 level, 6 down, 4 up.
  $D03A L = column step; facing doubled for right, doubled plus 2 for left.
  $D04C Run away under the target's idol.
  $D058 Step, and keep the step (#R$BA85, column first) and the facing.

@ $D066 label=MonsterTry
c $D066 Test a monster's new position; hit a player who is in it
D $D066 Damage is the monster's kind + 1, from the player's strength (&DAA6, &DAF4), and sets #R$BA98 for the noise burst. Only the first non-empty cell found counts.
R $D066 BC Position
R $D066 O:F Z if the four cells are empty
  $D072 DE = -(kind + 1).

; ---------------------------------------------------------------------------
; Trap doors and spawning

@ $D08F label=TrapDoor
c $D08F Run a trap door (&20-&3E): maybe spawn a monster beside it
D $D08F A trap door is bits 0-2 a kind and bits 3-4 a health. A kind-7 one (the hell hole) spawns every time it is scanned, a random kind and health; the others one time in four (R), their own kind and health. The new monster starts as a sparkle (&40 + health x 8 + kind) in the first empty neighbour from #R$BA87.
R $D08F A Tile code
R $D08F HL Its cell
@ $D0A1 label=TrapSpawn
@ $D0AB label=TrapNeighbour
@ $D0C6 label=TrapPut
@ $D0D7 label=TrapRandom
  $D0D7 Hell hole: a random sparkle from R.

@ $D0DF label=Sparkle
c $D0DF Draw a spawning sparkle (&40-&5F); on frame 0 it becomes a monster
D $D0DF Drawn as block &28 + #R$BA72 in ink 4 + health. Scanned while #R$BA72 is 0, it becomes &80 + kind x 16 + health x 4.
R $D0DF A Tile code
R $D0DF HL Its cell

; ---------------------------------------------------------------------------
; The map

@ $D117 label=CellPos
c $D117 Map address to position
R $D117 HL A cell in the map (&BC00-&BFFF)
R $D117 O:B Row (characters): twice the map row
R $D117 O:C Column (characters): twice the map column

; ---------------------------------------------------------------------------
; The spreading tile

@ $D132 label=SpreadTick
c $D132 Check one tile for the spreading tile, and move the cursor on
D $D132 Called once a pass. The cursor (#R$BA95) checks every other tile of a row, the other half on the next row, from row 30 up to row 1, then again with the halves swapped: every tile of rows 1-30 once in 960 passes.

@ $D157 label=Spread
c $D157 If the tile is &13, spread it into the empty neighbours
D $D157 Left, right, below, then above: each that is empty (0) becomes &13 and is redrawn.
R $D157 B Row
R $D157 C Column
@ $D17F label=SpreadInto

@ $D181 label=RedrawCell
c $D181 Redraw the map tile at HL, if on screen
R $D181 HL A cell in the map

; ---------------------------------------------------------------------------
; Objects in the map: an object at (B, C) covers the cells of (B, C),
; (B+1, C), (B+1, C+1) and (B, C+1), which is one, two or four tiles.

@ $D18A label=CellsEmpty
c $D18A Are an object's four cells empty?
R $D18A BC Position (C comes back one more)
R $D18A O:A The first non-empty cell's code
R $D18A O:F Z if all four are empty
@ $D19A label=CellEmpty
c $D19A Is one cell empty? If not, return from #R$D18A
D $D19A The POP HL drops the return to #R$D18A, so the RET leaves #R$D18A with NZ.

@ $D1A2 label=FillCells
c $D1A2 Write #R$BA4B into an object's four cells
R $D1A2 BC Position (C comes back one more)
@ $D1B2 label=FillCell

; ---------------------------------------------------------------------------
; Touching things

@ $D1BA label=TouchAll
c $D1BA A player's four cells at a new position: touch what is in them
D $D1BA Called by the players' movement (&CB0C, &CE18) for each step tried. Afterwards the caller adds #R$FF31 to the treasure and #R$FF32 to the strength, and #R$FF33 decides: 0 moves, &1E leaves the level, anything else blocks.
R $D1BA BC The new position
R $D1BA IX The player's record (&BA4E or &BA5D)

@ $D1D7 label=Touch
c $D1D7 Touch one cell: dispatch on its code
D $D1D7 Every non-empty cell blocks the move (#R$FF33) but only every tenth acts (#R$D287). Monsters: &80 and up is a head, punched (&C86C, 5 treasure); &7F is a monster's other cell (&C8A4 finds the head). The other player is shoved. Codes &01-&07, &11, &13 and &1F are walls; &1E is the exit, handled by the caller.
R $D1D7 BC Position
R $D1D7 IX The player's record
  $D1E4 &7F: find the head. Above: punch it, 5 treasure.
@ $D1F7 label=TouchItem
  $D25E &20-&3F trap doors; &40 and up (sparkles and stray codes) just vanish.
@ $D265 label=TouchClear
@ $D267 label=RedrawTile
N $D267 Redraw the map tile at HL, at position BC, if on screen.

@ $D287 label=TouchGate
c $D287 The touch gate: let one contact in ten through
R $D287 A Code
R $D287 O:A Code, if let through
R $D287 O:F Z if let through

@ $D297 label=TouchTrapDoor
c $D297 Touch a trap door: one hit (5 treasure); a hell hole kills
D $D297 Each hit takes 8 from the code (a health point); below &20 the trap door is gone. The step is cleared.
@ $D2B9 label=HellHole
  $D2B9 Strength = &FF00: negative, so the next strength change kills.

@ $D2C2 label=TakeKey
c $D2C2 Key (&08): one more key, up to 9

@ $D2D0 label=OpenDoorV
c $D2D0 Vertical door (&09): spend a key to remove the door and its run up and down
@ $D2EF label=OpenDoorH
c $D2EF Horizontal door (&0A): spend a key to remove the door and its run left and right

@ $D30E label=OpenChest
c $D30E Locked chest (&0B): spend a key; it becomes a chest, tea, a scroll or a monster
D $D30E R AND 6 + &0C: &0C (chest), &0E (tea), &10 (scroll), or &12, which becomes &F0, a kind-7 monster (it can't be killed).

@ $D327 label=TakeChest
c $D327 Chest (&0C): 10 treasure

@ $D334 label=TakeScroll
c $D334 Scroll (&10): one more scroll, up to 9

@ $D342 label=TakeHorseshoe
c $D342 Horseshoe (&12): set the player's horseshoe flag (+&0E)

@ $D34A label=PushRock
c $D34A Rock (&14): push it one tile in the player's direction, if that tile is empty
D $D34A The direction is the players' #R$BA85 (row, then column), so a diagonal push moves it diagonally.

@ $D384 label=Teleport
c $D384 Teleporter (&15): to a random teleporter in view, one tile beyond it
@ $D389 label=PickTeleporter
c $D389 Find a random teleporter in the view
D $D389 Counts the &15 tiles in the 12 x 12 view, picks the ((R mod count) + 1)th in reading order. Found, it returns with Z and the alternate registers still in use, HL' the teleporter's cell; #R$D3CE switches back at #R$D3CC. Called by the stars too (&C7C0).
@ $D3CC label=TeleportDone
@ $D3CE label=TeleportLand
c $D3CE Land the player one tile beyond the chosen teleporter
D $D3CE Only if that tile is empty and at least two characters inside the view's edges (rows and columns 2-20 of it). Then the player's position is set and the step cleared.

@ $D410 label=TakeFood
c $D410 Food (&0D grapes, &0E tea, &0F rice): 25, 50 or 75 strength

@ $D423 label=TakeOneWay
c $D423 One-way tile (&16): it vanishes, and is remembered to become a wall
D $D423 With #R$FF4B full, nothing is taken; &DA59 is run to free entries.

@ $D441 label=TakeSwitch
c $D441 Switch (&17): it vanishes, and so does every &06 wall in the map

@ $D460 label=TakeDeathStar
c $D460 Death star (&18): +6 = &FF, +7 + 1 in the player's record
@ $D46C label=TakeShield
c $D46C Shield (&19): one strength change in four is ignored (&DAA6)
@ $D475 label=TakeIdol
c $D475 Idol (&1A): monsters chasing this player run away, for 255 passes
@ $D47E label=TakeHeart
c $D47E Heart (&1B): no strength changes for 255 passes
@ $D487 label=TakeBall
c $D487 Ball (&1C): one more ball (+&0D in the player's record)
@ $D48F label=TakeClock
c $D48F Clock (&1D): monsters and trap doors stop for 255 passes

@ $D499 label=DoorRun
c $D499 Remove the run of door cells with code A, stepping by DE
R $D499 A Door code
R $D499 DE Step: ±32 for a column, ±1 for a row
R $D499 HL The door cell touched

; ---------------------------------------------------------------------------
; The players: shoving, writing into the map, leaving the level

@ $D4AB label=ShoveP2
c $D4AB Player 1 touched player 2: shove player 2 one step, if there's room
D $D4AB The step is player 1's (#R$BA85). The shoved player's old position is drawn over (&CC79, which also clicks the beeper).
@ $D4CF label=ShoveP2Put
@ $D4E1 label=ShoveP1
c $D4E1 Player 2 touched player 1: shove player 1 one step, if there's room
@ $D505 label=ShoveP1Put

@ $D517 label=PutPlayer
c $D517 Write code A into a player's four cells
R $D517 A Code (0, &71 or &72)
R $D517 BC Position (kept)
R $D517 HL Kept

@ $D521 label=CellsFree
c $D521 Are the four cells at BC empty?
R $D521 O:F Z if all four are empty (BC kept then)

@ $D537 label=P1Exits
c $D537 Player 1 leaves the level
D $D537 Player 1 is out (bit 0 of &BA73) and through (bit 2). The two POPs drop the returns into its movement, so the main loop carries on after &C168. Song 6.
@ $D550 label=P2Exits
c $D550 Player 2 leaves the level (bits 1 and 3, song 5)

@ $D569 label=MapCell
c $D569 The map cell at a position, and what it holds
D $D569 Called for every cell any object tests or writes.
R $D569 B Row (characters)
R $D569 C Column (characters)
R $D569 O:HL &BC00 + (B / 2) x 32 + C / 2
R $D569 O:A The cell's code
R $D569 O:F Z if empty

; ---------------------------------------------------------------------------
; The menus' key entry, game over and the high score

@ $D58B label=EnterCode
c $D58B Menu 4: enter a password (four keys into &FF2A)
T $D596,11,10:n1
C $D5A1
  $D5A1 Wait for no key, then a key; keep it, print it, click.
@ $D5AD label=CodeKey

@ $D5C9 label=SelectControls
c $D5C9 Menu 3: select the controls
T $D5D9,23,22:n1
C $D5F0
T $D5F6,23,22:n1
C $D60D
T $D613,23,22:n1
C $D62A
T $D630,23,22:n1
@ $D647 label=ControlsKey
C $D647
  $D647 Wait for 1-4.
@ $D65F label=RedefineP1
  $D65F Redefine player 1: each key's port and mask go into the input code's LD BC and AND (self-modifying), and the CPLs are put back.
@ $D698 label=RedefineMagic1
  $D698 The magic (scroll) key is always a key.
@ $D6A2 label=KempstonP1
  $D6A2 Kempston for player 1: port &1F, NOP for each CPL, masks fire &10, up 8, down 4, left 2, right 1.
@ $D6E2 label=RedefineP2
@ $D71B label=RedefineMagic2
@ $D725 label=KempstonP2
  $D725 Kempston for player 2 (it writes the masks twice).

@ $D77E label=KempstonSelected
c $D77E Clear the screen in colour A and say KEMPSTON SELECTED
R $D77E O:BC &001F, the Kempston port
T $D787,19,18:n1
C $D79A

@ $D79E label=AskUp
c $D79E Ask for a key: UP, DOWN, LEFT, RIGHT, FIRE or MAGIC
D $D79E Each entry prints its word and joins #R$D7FC, which writes the key into the instruction at IX: its port at IX+1 and IX+2, its mask at IX+7.
R $D79E IX The key's LD BC,port : IN A,(C) : CPL : AND mask in a player's input code
T $D7A4,8,7:n1
C $D7AC
@ $D7AE label=AskDown
T $D7B4,8,7:n1
C $D7BC
@ $D7BE label=AskLeft
T $D7C4,8,7:n1
C $D7CC
@ $D7CE label=AskRight
T $D7D4,8,7:n1
C $D7DC
@ $D7DE label=AskFire
T $D7E4,8,7:n1
C $D7EC
@ $D7EE label=AskMagic
T $D7F4,8,7:n1
@ $D7FC label=ReadKeyFor
C $D7FC
  $D7FC Print KEY FOR, wait for a new key (not a shift), store it, show it.
T $D804,8,7:n1
C $D80C
@ $D838 label=KeyClick
  $D838 The key click: 256 half-waves of 666 T-states (170,509 in all).
@ $D83A label=KeyClickOut
@ $D848 label=ShowEnter
T $D84B,6,5:n1
C $D851
@ $D853 label=ShowSpace
T $D856,6,5:n1
C $D85C

@ $D85E label=GameOver
c $D85E A player's strength ran out: GAME OVER PLAYER n
D $D85E Waits five 65,536-step loops (&C08F, about 3 s). If the other player is still in, the view is redrawn and play goes on. Otherwise the better treasure (a tie to player 1) is offered to the high score and the game restarts.
R $D85E A '1' or '2'
R $D85E DE That player's treasure
T $D86D,18,17:n1
C $D87F
@ $D8B6 label=HighScoreCheck
c $D8B6 A new high score? Then YOUR NAME PLAYER n, and the name
D $D8B6 Not if the high score is at least DE. Entered from #R$D85E with carry set when player 2's treasure is the better, so a tie with the high score then counts as new.
R $D8B6 A '1' or '2'
R $D8B6 DE Treasure
T $D8CF,18,17:n1
C $D8E1
@ $D8E7 label=NameEntry
c $D8E7 Enter a name of up to 10 characters into the menu's text at &C2A7
D $D8E7 The name is written over the inline string the menu prints after the high score (self-modifying). A held key repeats after #R$FF60 polls. ENTER ends; CAPS SHIFT and 0 deletes.
@ $D8F9 label=NameKey
@ $D90B label=NameWait
@ $D940 label=NameDelete
T $D964,3,2:n1
C $D967
