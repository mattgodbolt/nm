# NINJA MASSACRE (BBC Micro port) — notes for Claude Code

A port of Codemasters' *Ninja Massacre* (ZX Spectrum 48K/128K, 1989) to
the BBC Micro, in 6502 assembly built with
[baron](https://github.com/waitingforvsync/baron) and tested in a headless
jsbeeb through its MCP server. The Spectrum original runs headless too, on
SkoolKit's Z80 simulator, so the two can be compared. Run the way the
Chuckie Egg 2 port (`../chuckie-egg-2-beeb`) was; its tools and docs are
the model.

- `docs/journal.md`: how it got here, in order. Add to it as you go.
- `docs/research.md`: what the original is and how it works (the reverse
  engineering). `disasm/*.ctl` holds the same as SkoolKit labels.
- `docs/decisions.md`: every call the port makes that the original
  didn't, numbered, with the reason. Nothing is changed from the original
  quietly.
- `docs/brief.md`: the brief the port started from (2026-10-15): the
  options and plan, as they were seen then.

## The rules (from kieranhj/beeb-port-kit)

1. **The original is the specification.** Find what the Spectrum code
   does and transcribe it: its tables, constants and logic. When the BBC
   forces a change, port the original's *decision*, not just its effect.
2. **Deviations are numbered decisions** in `docs/decisions.md`.
3. **One layer at a time**, working and visible in the emulator before the
   next one starts.
4. **Measure, don't recall.** Set the registers in jsbeeb, look, read
   memory back.

The 128K version is the specification (its AY music is the only thing it
adds; the game's code is the same on both machines).

## Commands

```sh
make            # assemble build/nm.ssd (+ build/nm.json, build/listing.txt)
make run        # boot it in jsbeeb, screenshot to shots/run.png
make check      # every check (MODEL=Master for a Master 128)
make fetch      # download the original into original/ (not committed)
make zx         # load the tape into build/nm128.z80 and build/nm48.z80
make disasm     # build/nm.skool from disasm/*.ctl
make venv       # .venv (uv sync): SkoolKit, Pillow, the music's libraries
make music      # the music driver against the original's, frame by frame
make music-disc # nm's music disc, ninja_music.ssd (tools/music/build.sh)
```

Baron 0.5.3 is expected at `../baron/build/src/baron` or on the PATH. CI
(`.github/workflows/check.yml`) builds it at the tag in `BARON_VERSION`
and runs `make check` on the B and the Master: move that pin with the
local one.

## Testing

- `node tools/play.mjs '<script>' shots/prefix_ [--disc build/nm.ssd]`:
  the BBC. Steps: a number waits seconds, `f10` frames, `SPACE:tap`,
  `LEFT:down`/`LEFT:up`, `!name` screenshots, `#name` dumps the screen,
  `?sym:n` peeks, `=sym:v1/v2` pokes, `@label` runs to a label. Symbols
  come from the disc's `.json`.
- `.venv/bin/python tools/zx.py '<script>' shots/zx_ [--snap build/nm128.z80]`:
  the Spectrum, same language (Spectrum key names, `>name` saves a
  snapshot, `--map FILE` logs executed addresses, `--ports FILE` the
  beeper, AY and paging writes). A 128K snapshot runs at 128K timing.
- `python3 tools/grid.py out.png cols a.png b.png ...` tiles screenshots.
- Run to a symbol after booting (`play.mjs --until`), never a guessed
  wait.
- `make passes` (`tools/passcheck.sh`): each scenario in
  `tests/scenarios.txt` on the original (`tools/passlog.py`, at `&C014`
  each pass) and the port (`tools/passlog.mjs`, at `pass_top`), compared
  by `tools/passcmp.py`: both variable blocks, the map, and every 50
  passes the screen. Add a scenario for anything that lands; a scenario
  `make fuzz` finds is copied in as it is.
- The original takes its random numbers from the port's generator in the
  checks (`tools/zx.py`'s `share_random`, decision 7).

## Transcribing

- The original's routines pass positions and map cells in registers; the
  transcription keeps the Z80's registers in zero page by name
  (`regs.6502`: rb, rc, rd, re, rh, rl, rhl), so a routine reads beside
  its original. Keep what a routine leaves in them too: the touch loop
  carries on from the BC a monster's death left (touch.6502).
- The original's variables are in its own layout (`vars_ba`, `vars_ff`,
  decision 10), named from `disasm/*.ctl` by `tools/mkvars.py`.
- Watch the flags: a `LDY #0` between a test and its branch sets Z; the
  Z80's `EX AF,AF'` and alternate registers keep values the 6502 must keep
  somewhere else (monsters.6502's trap doors, the chase's carry).
- `make music` (`tools/musiccheck.mjs`): every song on the 6502 driver
  against `tools/music/dw_decode.py`'s, frame by frame, and the SN76489's
  bytes against `tools/musicmodel.py`'s model of the conversion: change
  the conversion in both. `tools/mkmusic.py` makes `src/data/music.6502`
  from bank 1; the build never runs it, and its output is committed.
- The music plays from the VSync interrupt and writes the chip: a sound
  the game writes holds `mu_busy` throughout (`effect_start` and
  `effect_end`, sound.6502). The bass's timer interrupts (bass.6502)
  write it at any time, a byte at once: a tone's two bytes keep
  interrupts off between them.
- jsbeeb's sound capture stamps a write with the time of the write
  before it: take a write's time from the next entry's stamp
  (`tools/musiccheck.mjs`).
- Speed: `node tools/scrolltime.mjs [--against old.ssd]` times each
  direction's slide (and compares the screen at every step);
  `node tools/passtime.mjs [--against old.ssd]` gives each pass's busy
  cycles over scenarios. A drawing change must leave every pixel as it
  was.

## The screen

MODE 1's pixels with the CRTC narrowed to 256 x 192 (R1 = 64, R6 = 24)
from `screen` to the top of RAM: the Spectrum's geometry exactly. A
character row is 512 bytes, so row r starts at `screen + r * &200`. In a
byte, a pixel's high bit is in the top nibble and its low bit in the
bottom one: colour 1 = `&0F`, 2 = `&F0`, 3 = `&FF` for four pixels.

## Comments and docs: no numbers the assembler works out

Comments and docs say what something is and why. They never copy a figure
the build computes or one run measured: an address, a size, free bytes.
The source and the build own those (`SECTION` guards, `ASSERT`s, `PRINT`s,
the symbols). Name the symbol, or point at the decision that records the
measurement with its date. A number the port chooses is a named constant,
set once in the source. Immutable facts are fine as numbers: the
hardware's and the OS's addresses, the original's addresses, a format's
field widths. Every agent brief carries this rule.

## Commits

Never put a claude.ai session link or a `Claude-Session:` trailer in a
commit, PR, issue or anything that leaves the machine: commit messages end
at `Co-Authored-By:`. Subagent briefs carry the same rule.

## Baron gotchas (from Chuckie Egg 2)

- `--symbols` is format 2: read it through `loadSymbols` (tools/beeb.mjs).
- Workspace sections are `virtual = TRUE`. Virtual sections may overlap
  without a word: to carry on after one, reopen it.
- The build uses `--warn 2`, and `tools/asm.sh` fails on a warning.
- `ASSERT` is built in. `FOR n = 0..15` is inclusive.
- A zero-page array is `ZA_AUTO 8, name`, indexed with `ZA_INDEXEDBY`.
- The allocator follows both ways out of every branch: put
  `ZA_UNREACHABLE` after an always-taken branch.
- Long-lived state goes in fixed zero page or a fixed workspace section,
  never in baron's pool.

## Reading the original

- Z80 handlers that `PUSH AF`/`PUSH DE` and pop in the other order swap
  registers: read the pops, not the names.
- An `INC`, `DEC` or 8-bit `ADD` on a screen address's low byte wraps
  within a third of the screen, without carrying into the high byte.
- The game reads random numbers from the Z80's R register (`LD A,R`):
  both machines must take them from one shared generator to be compared
  (docs/brief.md, D5).
