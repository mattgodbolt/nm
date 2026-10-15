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

- the periods x 1155/1024 (decision 15); one past the SN's ten bits is
  played as bass (decision 18, below), its period 1;
- the volumes through ym2sn.py's table (decision 16);
- the noise on the SN's noise channel, as loud as the loudest voice it's
  mixed into (decision 17).

While the song is stopped it writes silence. While `mu_busy` is set it
writes nothing: the game's own writes hold it (`sound.6502`'s
`effect_start` to `effect_end`).

`make music` checks it: every frame of every song, the shadow registers
and the bass's half-cycles against `dw_decode.py`'s, and the SN's bytes
against a Python model of `mu_output` (`tools/musicmodel.py`); then, in
the game, each channel's bass edges' spacing.

## The bass

The SN's lowest note is 122Hz and the main theme's bass is below it
nearly all the time. nm's player (`tools/music/player.asm`, from Simon
Morris's `vgcplayer_bass.asm`) plays such notes at their pitch: the
channel's period is set to 1, which the ear hears as silence, and a VIA
timer toggles its volume at the note's frequency, a square wave made by
hand. The port does the same (`bass.6502`, decision 18):

- **Three timers**, one a channel: the User VIA's T1 (free-running), its
  T2 and the System VIA's T2 (one-shot, started again at each edge). The
  System VIA's T1 is the pass clock, so it isn't one of them. A
  half-cycle in microseconds is four SN periods: `mu_period` keeps the
  period before it went up in `mu_h`, and `bass_play` takes four times
  it, which fits a timer's 16 bits for every note. A one-shot counts on
  past 0, so adding its count when the edge reads it takes off however
  late the interrupt was, and the pitch doesn't drift.
- **`mu_output` decides** each frame which channels play bass (a period
  too low, and heard), and at what volume: `bass_play` starts a channel's
  timer or changes its half-cycle; `bass_stop` turns its interrupt off.
  Each edge writes one byte, the channel's volume or silence.
- **The chip shared at a finer grain.** A two-byte tone write anywhere
  (the music's or the effects') keeps interrupts off between its bytes,
  or an edge's volume byte lands between and the data byte goes to the
  volume. `mu_write` keeps them off for its own byte too, since an edge
  sets port A up itself and puts it back after.
- **Latency.** `irq_handler` turns interrupts back on once it has
  acknowledged VSync, so the driver's frame doesn't hold the edges back;
  only `mu_output`'s writes do. (A nested interrupt's entry overwrites
  the OS's copy of A at &FC, so the handler keeps its own.)
- **The effects** take channel 1 and the User VIA's T2 (`wait_us`), so
  `effect_start` stops channel 1's bass; the other channels' edges go on.
- **Plain 6502**, so it runs on a B as well as a Master.

The edges' spacing is checked in jsbeeb (`make music`); real hardware is
untested. The disc's NMIs, for a later edition that reads the disc in
play, would delay the edges.
