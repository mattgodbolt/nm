# NINJA MASSACRE — BBC Micro port
#
#   make          assemble build/nm.ssd (+ build/nm.json, build/listing.txt)
#   make run      boot it in jsbeeb and grab a screenshot (shots/run.png)
#   make check    every check (MODEL=Master to run them on a Master 128;
#                 default B-DFS1.2)
#   make views    every level's first view, against the original's
#   make passes   tests/scenarios.txt on both, compared pass by pass
#   make music    the music's 6502 driver against the original's, every
#                 song frame by frame, and the sound chip's bytes
#   make fetch    download the Spectrum original into original/
#   make zx       load the original's tape into build/nm128.z80 and
#                 build/nm48.z80 (SkoolKit)
#   make disasm   the original's disassembly with the research's labels,
#                 build/nm.skool (from disasm/*.ctl)
#   make venv     the Python tools' environment (.venv: SkoolKit, Pillow,
#                 and the music tools' music21 and numpy)
#   make music-disc  nm's music disc, ninja_music.ssd (tools/music/build.sh)

BARON   ?= $(firstword $(wildcard ../baron/build/src/baron) baron)
# Baron, failing on a warning too.
ASM      = BARON=$(BARON) tools/asm.sh
# The jsbeeb model the test tools use (tools/beeb.mjs reads NM_MODEL).
MODEL   ?= B-DFS1.2
export NM_MODEL = $(MODEL)
PYTHON  ?= .venv/bin/python
TARGET   = build/nm.ssd
SOURCES  = $(wildcard src/*.6502 src/data/*)
TAPE     = original/Ninja Massacre (1989)(Code Masters)(48K-128K)[a].tzx
# Stamped into !BOOT, so a disc says what it is: UTC build time and the
# commit, with + if the tree had changes.
BUILD   := $(shell date -u '+%Y-%m-%d %H:%M UTC') $(shell git rev-parse --short HEAD 2>/dev/null || echo NOGIT)$(shell git diff --quiet HEAD -- . 2>/dev/null || echo +)

# A failed step leaves no half-made target behind (asm.sh fails on a
# warning after baron has written the disc).
.DELETE_ON_ERROR:

.PHONY: all run check views passes music fetch zx disasm venv music-disc clean

all: $(TARGET) $(TEST)

$(TARGET): $(SOURCES) | build
	@python3 tools/lint_labels.py > /dev/null || python3 tools/lint_labels.py
	$(ASM) -D 'BUILD="$(BUILD)"' -o $@ --title NINJA --opt 3 --warn 2 --symbols $(@:.ssd=.json) -v -log0 build/listing.txt src/main.6502

build:
	mkdir -p build

# The tests' disc: -D DIRECT=1 goes straight into a one-player game, so the
# tools reach the main loop without the menu.
TEST = build/test.ssd
$(TEST): $(SOURCES) | build
	$(ASM) -D DIRECT=1 -D 'BUILD="$(BUILD) test"' -o $@ --title NINJA --opt 3 --warn 2 --symbols $(@:.ssd=.json) src/main.6502

# The view check's disc: every level's first view in turn (VIEWCHECK).
build/viewcheck.ssd: $(SOURCES) | build
	$(ASM) -D VIEWCHECK=1 -D 'BUILD="$(BUILD) viewcheck"' -o $@ --title NINJA --opt 3 --warn 2 --symbols $(@:.ssd=.json) src/main.6502

# tests/scenarios.txt on both machines, compared pass by pass.
passes: $(TEST) build/nm48.z80
	PASSDIR=build/passes-$(MODEL) tools/passcheck.sh

# Every level's first view, against the original's (tools/zxviews.py).
views: build/viewcheck.ssd build/views/zx_50.scr
	node tools/viewcheck.mjs
	$(PYTHON) tools/viewcmp.py

build/views/zx_50.scr: build/nm128.z80 tools/zxviews.py tools/zx.py tools/mklevels.py
	$(PYTHON) tools/zxviews.py

# The music check's disc: every song on the driver, as fast as it goes
# (MUSICCHECK).
build/musiccheck.ssd: $(SOURCES) | build
	$(ASM) -D MUSICCHECK=1 -D 'BUILD="$(BUILD) musiccheck"' -o $@ --title NINJA --opt 3 --warn 2 --symbols $(@:.ssd=.json) src/main.6502

# The music against tools/music/dw_decode.py's driver (tools/musicmodel.py).
music: $(TARGET) build/musiccheck.ssd build/nm128.z80 $(TEST)
	node tools/musiccheck.mjs

run: $(TARGET)
	node tools/play.mjs '1,!run' shots/ --disc $(TARGET)

check: $(TARGET) $(TEST) views disasm music passes

fetch:
	tools/fetch_original.sh

zx: build/nm128.z80 build/nm48.z80

# The tape loaded as each machine would (the game's start, &C000): the
# 128K has the AY music, which the port takes as the specification.
build/nm128.z80: | build
	@[ -f "$(TAPE)" ] || tools/fetch_original.sh
	$(PYTHON) .venv/bin/tap2sna.py -c machine=128 -s 49152 "$(TAPE)" $@ > /dev/null
build/nm48.z80: | build
	@[ -f "$(TAPE)" ] || tools/fetch_original.sh
	$(PYTHON) .venv/bin/tap2sna.py -c machine=48 -s 49152 "$(TAPE)" $@ > /dev/null

disasm: build/nm.skool

build/nm.skool: build/nm48.z80 $(wildcard disasm/*.ctl)
	rm -rf build/ctl && mkdir -p build/ctl
	cp disasm/*.ctl build/ctl/
	.venv/bin/sna2skool.py -H -c build/ctl build/nm48.z80 > $@

venv:
	uv sync

music-disc:
	tools/music/build.sh

clean:
	rm -rf build
