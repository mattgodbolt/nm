# The original

`make fetch` (`tools/fetch_original.sh`) downloads the Spectrum original
here and checks it against `SHA256SUMS`. None of it is committed: it is
not ours to redistribute.

- `Ninja Massacre (1989)(Code Masters)(48K-128K)[a].tzx`: the tape, from
  archive.org's TOSEC set (Spectrum Computing marks it "distribution
  denied"). The only tape TOSEC has is this `[a]` (alternate) one; its
  code and data match two independent 128K snapshots byte for byte
  (docs/research.md).
- `Ninja Massacre (1989)(Code Masters)(128K).z80`: TOSEC's 128K
  snapshot, the music conversion's input (`tools/music/build.sh`).
- `NinjaMassacre.txt`: the instructions (Spectrum Computing).
- `NinjaMassacre.png`: the map of all 50 levels (Spectrum Computing).
- `NinjaMassacre.gif`: an in-game screen (Spectrum Computing).
