# Ninja Massacre on the BBC Micro

A port of Codemasters' *Ninja Massacre* (ZX Spectrum, 1989; code and
graphics by Adam Waring, music by David Whittaker) to the BBC Micro, in
6502 assembly built with [baron](https://github.com/waitingforvsync/baron).
It is run the way the
[Chuckie Egg 2 port](https://github.com/mattgodbolt/chuckie-egg-2-beeb)
was: the Spectrum original is the specification, it runs headless as an
oracle, and the port is checked against it in a headless
[jsbeeb](https://github.com/mattgodbolt/jsbeeb).

Where it has got to (`docs/journal.md` has the story):

- The whole game is transcribed: the levels and the view, the players,
  touching and every item, the monsters, trap doors and the spreading
  tile, the stars, the smart bomb, the status, the menu, the password,
  the controls, game over, the high score and the game's end.
- It plays the same as the original, pass for pass: `make passes` replays
  scripted games on both and compares every variable, the map and the
  screen; `make fuzz` does the same with random ones.
- The music is David Whittaker's own driver, transcribed to 6502 and
  playing the original's songs on the SN76489 (from the 128K version,
  which is the specification for sound); the beeper's effects are played
  on the SN76489 too.
- It needs 16K of sideways RAM (or a Master). A stock-B edition is
  considered in `docs/streaming.md`.
- The colours are a first attempt (decisions 5 and 21 in
  `docs/decisions.md`), to be looked at, and the scroll's slide is slower
  than the original's (decision 22).

## Playing

[Play it in jsbeeb](https://bbc.xania.org/?autoboot&disc1=https://raw.githubusercontent.com/mattgodbolt/nm/main/ninja-massacre.ssd)
(a Model B with sideways RAM), or write `ninja-massacre.ssd` to a disc and
SHIFT-BREAK: it starts at the menu (1 one player, 2 two, 3 the controls,
4 a password). The keys, as the original's where the BBC has them
(decision 13):

| | Player 1 | Player 2 |
|---|---|---|
| up, down | Q, A | 9, 8 |
| left, right | O, P | 6, 7 |
| fire | SPACE | 0 |
| magic (a smart bomb) | RETURN | SHIFT |

The menu's 3 redefines them. In play, with CTRL and SHIFT held (the
Spectrum's EXTEND MODE): T turns the music off or on, P pauses, Q quits.

The project began as a conversion of the game's music alone, which is
still here: [`music/README.md`](music/README.md) tells that story, and
`ninja_music.ssd`
[plays in jsbeeb](https://bbc.xania.org?autoboot&model=master&disc1=https://raw.githubusercontent.com/mattgodbolt/nm/main/ninja_music.ssd).

## Building

You need [baron](https://github.com/waitingforvsync/baron) 0.5.3 (at
`../baron/build/src/baron`, or on the PATH), Node.js, Python 3 and
[uv](https://github.com/astral-sh/uv).

```sh
npm ci          # the jsbeeb test harness
make venv       # .venv: SkoolKit, Pillow, and the music tools' libraries
make fetch      # the Spectrum original, into original/ (not committed)
make            # build/nm.ssd
make run        # boot it in jsbeeb, screenshot to shots/run.png
make check      # every check: the views, the music, the pass-by-pass scenarios
make fuzz       # random scenarios on both (SEED=n COUNT=n)
```

## Where things are

| Path | What |
|---|---|
| `src/` | the port, in 6502 assembly (`main.6502` is the build file) |
| `tools/` | the build's and the checks' tools: the jsbeeb harness (`beeb.mjs`, `play.mjs`), the Spectrum harness (`zx.py`) |
| `tools/music/` | the music conversion's scripts |
| `music/` | the converted music, the captured AY registers and the score |
| `disasm/` | SkoolKit control files: the original's disassembly, as far as it's understood |
| `docs/` | the journal, the decisions, the research on the original, and the brief the port started from |
| `original/` | where `make fetch` puts the original |

## Credits

- **Adam Waring** (TAG Computer Games): the original game. Graphics also
  by Neil Adamson; music and effects by **David Whittaker**; published by
  Codemasters, whose copyright it is.
- **[Simon Morris](https://github.com/simondotm)**: the tools the music
  conversion uses.
- **[Rich Talbot-Watkins](https://github.com/waitingforvsync)**: baron,
  and fellow Ninja Massacre enthusiast.
- **Claude** (Anthropic): the port and the music conversion.
