# Ninja Massacre on the BBC Micro

A port of Codemasters' *Ninja Massacre* (ZX Spectrum, 1989; code and
graphics by Adam Waring, music by David Whittaker) to the BBC Micro, in
6502 assembly built with [baron](https://github.com/waitingforvsync/baron).
It is run the way the
[Chuckie Egg 2 port](https://github.com/mattgodbolt/chuckie-egg-2-beeb)
was: the Spectrum original is the specification, it runs headless as an
oracle, and the port is checked against it in a headless
[jsbeeb](https://github.com/mattgodbolt/jsbeeb).

It's at an early stage: `docs/journal.md` says where it has got to.

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
make check      # every check
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
