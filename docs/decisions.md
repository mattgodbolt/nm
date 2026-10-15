# Decisions

Every call the port makes that the original didn't, numbered, with the
reason. The original is the specification; nothing changes quietly.

| # | Date | Decision | Why |
|---|---|---|---|
| 1 | 2026-10-15 | **The screen is MODE 1's pixels on a CRTC narrowed to 256 x 192**, as Chuckie Egg 2's port does: the Spectrum's geometry exactly, 12K at the top of RAM, four colours | The game draws 16 x 16 one-bit blocks on the 8 x 8 grid, and its look is the fine detail of the bricks, the ninjas and the font. MODE 2's eight colours would halve that detail (45% of the graphics' lit pixels pair with an unlit one: docs/brief.md, D1). The colours are chosen per level (to come). |
| 2 | 2026-10-15 | **The 128K version is the specification** | The 128K adds only the AY music (and the driver's own effects entry is never called); everything else is the same code on both machines (docs/research.md). The music is why this project exists. |
| 3 | 2026-10-15 | **The repository is reorganised around the port.** The music conversion's scripts move to `tools/music/` and its data to `music/`; `ninja_music.ssd` stays at the top | Matt asked for it to be a game port first. The music disc stays where it was because the README's jsbeeb link and jsbeeb's own disc list point at that path on `main`. |
