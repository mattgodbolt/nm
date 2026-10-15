# Journal

How the port got here, in order.

## 2026-10-15

### Where it started

This repository held the conversion of Ninja Massacre's music to the
BBC Micro (`music/README.md`). After the Chuckie Egg 2 port finished,
a brief (`docs/brief.md`) looked at porting the whole game the same way.
It found the game unusually easy to port: 7.4K of code, everything drawn
on the 8 x 8 grid with no masks or shifting, and all the data in clean
blocks. With 16K of sideways RAM it fits with room to spare, and a stock
B might read each level from disc at the "LEVEL nn" screen.

Matt asked for the repository to become that port, on a branch, with the
music as one part of it.

### Reorganised

The music's scripts went to `tools/music/` and their data to `music/`
(decision 3). `tools/music/build.sh` now works in `music/` and clones its
tools into `music/tools/`, so the top-level `tools/` can be the port's.
`ninja_music.ssd` stays at the top, because links point there.

### The skeleton

From Chuckie Egg 2: `tools/asm.sh`, `lint_labels.py`, `grid.py`,
`zx02.py`, the jsbeeb harness (`beeb.mjs`, `play.mjs`) and the Spectrum
harness (`zx.py`), and the Makefile's shape and CI.

- `make fetch` takes the tape and TOSEC's 128K snapshot from archive.org,
  since Spectrum Computing marks the tape "distribution denied", and the
  instructions, the map and a screen from Spectrum Computing.
- `tools/zx.py` now runs a 128K snapshot at 128K timing (70,908 T-states a
  frame), keeps the AY's registers (SkoolKit's snapshot writer wants them:
  without them `>name` failed on a 128K), and can log the beeper, AY and
  paging writes (`--ports`). The brief's research had made those changes
  in a copy; they're in the tool now.
- `make zx` loads the tape as a 128K and a 48K. The 128K reaches the menu
  and play, with the AY written every frame.
- The first layer, the screen: `src/main.6502` builds `build/nm.ssd`,
  whose `NINJA` sets MODE 1 on the narrowed CRTC in the hardware, takes
  IRQ1V for VSync and draws a test pattern (decision 1).
