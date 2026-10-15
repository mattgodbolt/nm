# The music driver

David Whittaker's music driver for Ninja Massacre, as the 128K version
keeps it in RAM bank 1 at &C000, and how the port runs it. The model is
`tools/music/dw_decode.py`, a Python port of the Z80 that matches the
captures in `music/` frame for frame; the port's driver is
`src/music.6502`, its data `src/data/music.6502` (`tools/mkmusic.py`).

## Entry points

| Address | | |
|---|---|---|
| &C000 → &C00E | init | A = song (0-6) |
| &C003 → &C0CD | tick | once a frame, from the game's interrupt |
| &C006 → &C19D | stop | silences the AY |
| &C009 → &C64B | effects | never called by the game (decision 2) |

## Its state

- **&C00C**: non-zero while a song plays. (&C00D is the effects'.)
- **Three voices** of &21 bytes at &C069, &C08A and &C0AB, reached
  through IX:

  | Offset | |
  |---|---|
  | +0 | flags: b0 the frame's parity, b1 drum, b2 portamento, b3 slide, b5 envelope running, b7 slide upwards |
  | +1/2 | the pattern's next byte |
  | +3/4, +5/6 | the pattern list, and the offset of its next entry |
  | +7/8 | the portamento's running sum |
  | +9/A, +B/C | the arpeggio's start and its next step |
  | +D, +E | the portamento's step (signed) and its delay in frames |
  | +F | frames for each of the envelope's steps (less one) |
  | +10, +11 | rows left of the note, and each note's rows |
  | +12, +13 | the note and the volume |
  | +14/15, +16/17 | the instrument, and the envelope's place in it |
  | +18, +19 | the envelope's volume, and frames to its next step |
  | +1A, +1B, +1C | the vibrato's depth, step and phase |
  | +1D | the vibrato: 0 off, &40 on, &C0 on alternate frames; b5 rising |
  | +1E | b0: this voice's notes set the noise's period |
  | +1F | the hi-hat: non-zero on, &FF at a row's start |
  | +20 | the voice's tone and noise bits in AY register 7 (&09, &12, &24) |

- **Self-modified operands**, which are variables in effect: the row
  countdown (&C0CC), the speed (&C0F9, frames a row), the noise's note
  (&C0D8), the noise's period this frame (&C125), the transpose (&C3A1),
  and the mixer's template (&C44A, the operand of `LD A,&38`).
- **Shadow AY registers** 0-11 at &C47F-&C48A, written to the AY at the
  end of each tick (&C161, from register 11 down).

## The data

- **The song table** (&C817): seven songs of seven bytes, a speed then a
  pattern list for each voice.
- **A pattern list**: pattern addresses, two bytes each. A 0 goes back
  to the list's start.
- **A pattern**: bytes,

  | Byte | |
  |---|---|
  | 00-7F | a note (0 is A#0); the row ends |
  | 80 | rest; the row ends |
  | 81, 82, 83 | vibrato off, on, on alternate frames |
  | 84 ss dd | portamento: a step added to the period each frame after dd frames |
  | 85, 86 | slide a semitone a row, down or up |
  | 87 | the pattern's end: the list's next |
  | 88 ss dd | the vibrato's step and depth |
  | 89 tt | transpose every note by tt |
  | 8A, 8B, 8C | the voice's tone only, noise only (its notes setting the noise's period), both |
  | 8D | drum: noise only on alternate frames, the period's bit 3 flipped |
  | 8E | the song stops |
  | 8F | tie: the note carries on; the row ends |
  | 90, 91 | hi-hat on, off: a frame of the shortest noise at each row's start |
  | B8-BF | speed 1-8 frames a row |
  | C0-CF | arpeggio |
  | D0-DF | instrument |
  | E0-FF | each note 1-32 rows |

  The commands go through a table of offsets at &C1B2 (&C366). Bytes
  92-B7 would jump through the table's neighbours; no song has one.
- **An instrument** (pointers at &C575): the byte before it is the step
  time; then a volume each step, until one with bit 7 set, where it holds.
- **An arpeggio** (offsets at &C558, each from its own address): semitones
  added to the note, a step a frame, the last with bit 7 set, then from
  the start. The offsets table is seven entries long: the first
  arpeggio's steps follow it.
- **The note table** (&C498): a 12-bit AY period per note.

The jingles (songs 1-6) don't end their voices: one voice reaches an &8E
and the song stops before the others run off the end of their patterns,
which would otherwise carry on into the next song's lists. So
`tools/mkmusic.py` finds the data by playing each song on `dw_decode.py`
and keeping the bytes it reads, not by walking the bytes.

## A frame (&C0CD)

1. The noise's period from the noise's note (&C0D7).
2. Every speed frames, a row for each voice (&C2AE). When its note's rows
   are done, it reads commands up to a note, a rest or a tie. A note
   starts the instrument's envelope. Otherwise a slide moves the note a
   semitone.
3. Each voice's frame (&C36E), in turn:
   - the envelope's next step, if its time has come;
   - the note, plus the transpose, plus the arpeggio's next step, looked
     up in the note table;
   - the vibrato: a triangle wave, its offset doubled once for each octave
     the note is below the table's top, so it is the same in cents;
   - the portamento's running sum;
   - its bits of register 7, from the template, or noise only on a drum's
     alternate frames; the hi-hat's noise at a row's start.
4. The periods, volumes and noise into the shadow registers, and those to
   the AY.

## How the port runs it

`src/music.6502` is a transcription, routine for routine. The voices keep
the original's offsets (`mv_flags` is `mu_voices + 0`, and so on), the
self-modified operands are variables in the workspace, and the shadow
registers are `mu_ay`. The data's pointers are labels, so baron places
it; the tables the driver indexes are split into low and high bytes. A
pattern list's entries are a byte each here, the pattern's number in a
table of their addresses (`mu_pat_lo`, `mu_pat_hi`), and a voice's
place in its list (`mv_next`) counts entries.

The VSync interrupt calls `music_tick`. After the driver's frame,
`mu_output` makes the SN76489's registers from `mu_ay` and writes those
that changed since it last wrote:

- the periods x 1155/1024 (decision 15), an octave up or two where they
  are past the SN's ten bits (decision 18);
- the volumes through ym2sn.py's table (decision 16);
- the noise on the SN's noise channel, as loud as the loudest voice it's
  mixed into (decision 17).

While the song is stopped it writes silence. While `mu_busy` is set it
writes nothing: the game's own writes hold it (`sound.6502`'s
`effect_start` to `effect_end`).

`make music` checks it: every frame of every song, the shadow registers
against `dw_decode.py`'s, and the SN's bytes against a Python model of
`mu_output` (`tools/musicmodel.py`).

## The bass, later

The SN's lowest note is 122Hz and the main theme's bass is below it
nearly all the time. nm's player (`tools/music/player.asm`, from Simon
Morris's `vgcplayer_bass.asm`) plays such notes at their pitch: the
channel's period is set to 1, which the ear hears as silence, and a VIA
timer toggles its volume at the note's frequency, a square wave made by
hand. What the port would need for it:

- **Three timers**, one a channel: the User VIA's T1 (free-running), its
  T2 and the System VIA's T2 (both one-shot, reloaded in the interrupt).
  The System VIA's T1 is the brief's choice for the pace of a pass (D4),
  so it isn't one of them. Each timer's count is half the note's period
  in microseconds: the AY's period P is 16P / 1.7734MHz long, so a half
  is about 4.51P microseconds, which fits a timer's 16 bits for every
  note. `mu_bass,X` says which channels need it; `mu_ay` has the period.
- **The interrupt** dispatching the timers as well as VSync, with
  start-up (`start`, startup.6502) enabling them.
- **The chip shared at a finer grain.** The bass interrupts write
  volumes many times a frame. A two-byte tone write anywhere (the music's
  or the game's) must keep them off between its bytes, or a volume's
  latch byte lands between and the data byte goes to the volume. So
  `mu_write`'s callers, the music's and the effects', would hold interrupts off (SEI)
  across each pair, rather than `mu_busy` alone.
- **Latency.** While `music_tick` runs, interrupts wait, and it takes up
  to a few thousand cycles (decision 14): a bass edge would be late by
  that much once a frame, a click at 50Hz. Either the VSync handler
  re-enables interrupts once it has acknowledged VSync (and guards
  against running twice), or the driver's frame is split so that each
  part is short.
- **A Model B's 6502.** nm says its player needs a Master. Upstream's
  `vgcplayer_bass.asm` has an `IF MASTER ... ELSE` path for every 65C02
  instruction it uses (`stz`, `inc a`, `bra`, `bit #`); the only `phx`
  and `phy` are in an `IF 0` block. So it should assemble for a B with
  `MASTER` false, untested. The port's own would be plain 6502 anyway.
- **The game's sounds** taking a channel would stop its timer as well as
  its writes (docs/brief.md, D3), and the disc's NMIs (a later edition)
  would delay the timers.
