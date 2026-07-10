#!/usr/bin/env python3
"""Generate a music score (MusicXML/MIDI) from the decoded Ninja Massacre
music data.

Uses dw_decode's driver simulation to obtain the written note events, then
maps them to notation:

  - one row = a sixteenth note (speed 6 at 50Hz = 125 bpm)
  - staves are *musical roles*, not chip channels: Whittaker moves parts
    between the three AY voices freely, so events are classified by the
    pattern they come from (patterns are his reusable musical objects)
  - arpeggio tables become block chords (that is what they emulate)
  - drum-mode notes (pitched noise), the per-row hi-hat noise burst, and
    the C#6 instrument-11 "click" pings go to a percussion staff
  - key signature is chosen per song by minimising accidentals over the
    duration-weighted pitch-class histogram (song 0 lands on three flats:
    the tune is Bb mixolydian with borrowed Db major chords)
  - driver note index 0 is A#0 (MIDI 22); sharps respelled as flats
"""

import argparse
from collections import Counter, defaultdict

from music21 import (chord, clef, instrument, key, metadata, meter, note,
                     pitch, stream, tempo)

from dw_decode import Driver

MIDI_BASE = 22  # driver note 0 = A#0

# Each (driver note, instrument) drum sound in the data, mapped to
# (GM percussion MIDI note, percussion-clef display position, notehead).
# Noise period = note & 0x1f (higher = deeper noise).
DRUM_MAP = {
    (63, 11): (36, "F4", "normal"),  # C#6, deep, sharp decay -> bass drum
    (31, 3): (41, "A4", "normal"),   # F3, deep, long decay   -> floor tom
    (35, 3): (38, "C5", "normal"),   # A3, bright, long decay -> snare
    (43, 3): (45, "D5", "normal"),   # F4, mid, long decay    -> low tom
    (47, 3): (48, "E5", "normal"),   # A4, mid, long decay    -> hi-mid tom
}
HIHAT = (42, "G5", "x")  # the one-frame period-1 noise burst each row
DEFAULT_DRUM = (38, "C5", "normal")
# tone-channel notes that are really percussion: the C#6 inst-11 ping
TONE_PERC = {(63, 11): (76, "A5", "x")}  # -> high woodblock

ROLES = ["lead", "chords", "riff", "bass"]

# Musical role of each pattern in song 0 (from per-pattern analysis).
# Patterns not listed fall back to a mean-pitch heuristic (the jingles).
SONG0_ROLES = {
    0xCA15: "lead", 0xCA50: "lead",
    0xCA06: "chords", 0xCA7B: "chords",
    0xC94C: "riff", 0xC967: "riff",
    0xC934: "bass", 0xC8E2: "bass", 0xC90C: "bass",
    0xC9AF: "bass", 0xC9D9: "bass",
}

# Key signature overrides (sharps count, negative = flats).
#
# Song 0 is Bb mixolydian, notated with the Bb MAJOR signature (two flats)
# and the modal Abs as accidentals -- per Rich Talbot-Watkins. The
# alternative "modal signature" (three flats, i.e. the mode's own pitch
# set) is a real convention, but its home is Irish/Scottish session books
# and early-music editions, where readers share the context to interpret
# it (and jazz occasionally: the So What lead sheet gives D dorian an
# empty signature). Outside those circles three flats resolving endlessly
# to Bb just reads as miswritten Eb major. The signature's job is to
# orient the reader to the tonic, and everything here says Bb: the bass
# pedal, the final, and the melody entering on F, the fifth.
SONG_KEY = {0: -2}

PART_STYLE = {  # name, abbreviation, clef, instrument
    "lead": ("Lead", "Ld.", clef.TrebleClef, instrument.ElectricGuitar),
    "chords": ("Chords", "Ch.", clef.TrebleClef, instrument.Piano),
    "riff": ("Riff", "Rf.", clef.BassClef, instrument.ElectricGuitar),
    "bass": ("Bass", "Bs.", clef.BassClef, instrument.ElectricBass),
}


def flatten(p):
    """Respell sharps as flats (the song lives on the flat side)."""
    if p.accidental and p.accidental.alter == 1:
        return p.getEnharmonic()
    return p


def decode_song(song, max_frames=20000):
    drv = Driver(open("page_4.bin", "rb").read())
    drv.init(song)
    hihat_rows = set()
    last_row = -1
    for _ in range(max_frames):
        drv.tick()
        if not drv.playing:
            break
        if drv.row != last_row:
            last_row = drv.row
            if any(v[0x1F] for v in drv.voices):
                hihat_rows.add(drv.row - 1)
    return drv, hihat_rows


def sounding_midis(ev, arps):
    base = MIDI_BASE + ev["note"] + ev["transpose"]
    steps = arps.get(ev["arp"], [0]) if ev["arp"] is not None else [0]
    return sorted({base + s for s in steps})


def classify_patterns(drv, arps, song):
    """Map pattern address -> role. Explicit table for song 0, heuristic
    (chord fraction, then mean pitch) for anything else."""
    stats = defaultdict(lambda: dict(midis=[], chords=0, notes=0))
    cur = {}
    for ev in drv.events:
        if ev["type"] == "pattern":
            cur[ev["voice"]] = ev["addr"]
        elif ev["type"] == "note" and not ev.get("drum"):
            s = stats[cur[ev["voice"]]]
            s["notes"] += 1
            s["midis"] += sounding_midis(ev, arps)
            if ev["arp"] not in (0, None):
                s["chords"] += 1

    roles = {}
    for addr, s in stats.items():
        if song == 0 and addr in SONG0_ROLES:
            roles[addr] = SONG0_ROLES[addr]
            continue
        if not s["notes"]:
            roles[addr] = "bass"
            continue
        mean = sum(s["midis"]) / len(s["midis"])
        if s["chords"] / s["notes"] > 0.3:
            roles[addr] = "chords"
        elif mean >= 55:
            roles[addr] = "lead"
        elif mean >= 42:
            roles[addr] = "riff"
        else:
            roles[addr] = "bass"
    return roles


def pattern_rhythms(drv):
    """Rhythm signature per pattern: tone-note (relative row, duration)
    pairs. Two patterns with equal signatures are octave/unison doublings
    of each other; anything else that happens to coincide is two separate
    musical lines and must not be merged into chords."""
    sigs = defaultdict(list)
    cur, start = {}, {}
    for ev in drv.events:
        if ev["type"] == "pattern":
            cur[ev["voice"]] = ev["addr"]
            start[ev["voice"]] = ev["row"]
        elif ev["type"] == "note" and not ev.get("drum"):
            vi = ev["voice"]
            key = (cur[vi], ev["row"] - start[vi])
            sigs[cur[vi]].append((ev["row"] - start[vi], ev["dur"]))
    # keep only the first occurrence's worth: signatures repeat per play
    out = {}
    for addr, pairs in sigs.items():
        seen = set()
        sig = []
        for rel, dur in pairs:
            if rel in seen:
                break
            seen.add(rel)
            sig.append((rel, dur))
        out[addr] = tuple(sig)
    return out


def pick_key(drv, arps):
    """Choose the signature minimising duration-weighted accidentals."""
    pcs = Counter()
    for ev in drv.events:
        if ev["type"] != "note" or ev.get("drum"):
            continue
        for m in sounding_midis(ev, arps):
            pcs[m % 12] += ev["dur"]
    counts = {}
    for sharps in range(-6, 7):
        tonic = (sharps * 7) % 12
        diat = {(tonic + s) % 12 for s in (0, 2, 4, 5, 7, 9, 11)}
        counts[sharps] = sum(n for pc, n in pcs.items() if pc not in diat)
    least = min(counts.values())
    # among near-minimal candidates (within 15%), prefer the shortest
    # signature: flats on borrowed chords read better than naturals
    # cancelling the signature all over the melody
    near = [s for s, n in counts.items() if n <= least * 1.15]
    return min(near, key=abs)


def fill_rests(sc):
    """Pad every measure (and every voice within one) with explicit rests:
    neither music21's makeNotation nor Verovio fills gaps or empty bars."""
    for part in sc.parts:
        for m in part.getElementsByClass("Measure"):
            targets = list(m.voices) or [m]
            for t in targets:
                t.makeRests(refStreamOrTimeRange=(0, m.barDuration.quarterLength),
                            fillGaps=True, inPlace=True, hideRests=False)
    return sc


def fix_voices(sc):
    """Renumber measure voices 1-based (MusicXML convention: Verovio drops
    'voice 0' content out of its layer, rendering it sequentially) and
    prune voices that contain no notes, keeping a bar rest if needed."""
    from music21 import note as m21note
    for part in sc.parts:
        for m in part.getElementsByClass("Measure"):
            voices = list(m.voices)
            if not voices:
                continue
            keep = [v for v in voices if len(v.notes)]
            for v in voices:
                if v not in keep:
                    m.remove(v)
            if not keep:
                r = m21note.Rest()
                r.quarterLength = m.barDuration.quarterLength
                m.insert(0, r)
            for i, v in enumerate(keep):
                v.id = str(i + 1)
    return sc


def fix_naturals(sc):
    """Remove spurious courtesy naturals music21's makeAccidentals leaves
    behind: a displayed natural is kept only if the key signature alters
    that step, or an earlier accidental in this or the previous measure
    actually needs cancelling."""
    for part in sc.parts:
        sig_steps = set()
        prev_altered = set()
        for m in part.getElementsByClass("Measure"):
            ks = m.keySignature
            if ks is not None:
                sig_steps = {p.step for p in ks.alteredPitches}
            altered = set()
            for n in sorted(m.flatten().notes, key=lambda x: x.offset):
                if not hasattr(n, "pitch") and not n.isChord:
                    continue  # Unpitched percussion
                for q in (n.pitches if n.isChord else [n.pitch]):
                    acc = q.accidental
                    if acc is None:
                        continue
                    if acc.name == "natural" and acc.displayStatus:
                        if (q.step not in sig_steps
                                and q.step not in altered
                                and q.step not in prev_altered):
                            acc.displayStatus = False
                    elif acc.name != "natural":
                        altered.add(q.step)
            prev_altered = altered
    return sc


def drum_note(spec, ql, notation):
    """A percussion hit: Unpitched for notation, GM pitch for MIDI."""
    midi, display, head = spec
    if notation:
        n = note.Unpitched(displayName=display)
        if head != "normal":
            n.notehead = head
    else:
        n = note.Note(midi)
    n.quarterLength = ql
    return n


def build_score(drv, hihat_rows, song, notation=True):
    speed = drv.mem[0xC0F9]
    bpm = round(50 * 60 / speed / 4)
    arps = {i: drv.arp_steps(i) for i in range(16)}
    roles = classify_patterns(drv, arps, song)
    rhythms = pattern_rhythms(drv)
    sharps = SONG_KEY.get(song, pick_key(drv, arps))

    sc = stream.Score()
    sc.metadata = metadata.Metadata()
    sc.metadata.title = ("Ninja Massacre" if song == 0
                         else f"Ninja Massacre - jingle {song}")
    sc.metadata.composer = "David Whittaker, 1989"

    parts = {}
    for role in ROLES:
        name, abbr, clef_cls, inst_cls = PART_STYLE[role]
        p = stream.Part(id=role)
        p.partName, p.partAbbreviation = name, abbr
        p.insert(0, inst_cls())
        p.insert(0, clef_cls())
        p.insert(0, meter.TimeSignature("4/4"))
        p.insert(0, key.KeySignature(sharps))
        parts[role] = p
    drums = stream.Part(id="drums")
    drums.partName, drums.partAbbreviation = "Drums", "Dr."
    perc = instrument.UnpitchedPercussion()
    perc.midiChannel = 9
    drums.insert(0, perc)
    drums.insert(0, clef.PercussionClef())
    drums.insert(0, meter.TimeSignature("4/4"))
    parts["lead"].insert(0, tempo.MetronomeMark(number=bpm))

    cur_pattern = {}
    last_note = [None, None, None]  # per chip voice, for ties
    at = {}  # (role, offset) -> inserted note, to merge octave doublings

    for ev in drv.events:
        if ev["type"] == "pattern":
            cur_pattern[ev["voice"]] = ev["addr"]
            continue
        if ev["type"] not in ("note", "tie"):
            continue
        vi = ev["voice"]
        off = ev["row"] * 0.25
        ql = ev["dur"] * 0.25

        if ev["type"] == "tie":
            if last_note[vi] is not None:
                last_note[vi].quarterLength += ql
            continue

        drum_spec = None
        if ev.get("drum"):
            drum_spec = DRUM_MAP.get((ev["note"], ev["inst"]), DEFAULT_DRUM)
        elif (ev["note"], ev["inst"]) in TONE_PERC:
            drum_spec = TONE_PERC[(ev["note"], ev["inst"])]
        if drum_spec:
            n = drum_note(drum_spec, ql, notation)
            n.stemDirection = "up"
            drums.insert(off, n)
            last_note[vi] = None
            continue

        midis = sounding_midis(ev, arps)
        pat = cur_pattern.get(vi)
        role = roles.get(pat, "bass")
        prev = at.get((role, off))
        if prev is not None:
            prev_n, prev_pat = prev
            # merge only genuine doublings: the other chip voice must be
            # playing a rhythm-identical pattern (octave/unison copy) with
            # a chord-sized span. Coinciding hits from rhythmically
            # different lines stay separate voices on the staff.
            twins = (prev_pat == pat
                     or rhythms.get(prev_pat) == rhythms.get(pat))
            if twins and prev_n.quarterLength == ql:
                combined = sorted(({p.midi for p in prev_n.pitches}
                                   if prev_n.isChord else {prev_n.pitch.midi})
                                  | set(midis))
                if combined[-1] - combined[0] <= 12:
                    midis = combined
                    parts[role].remove(prev_n)
        # NB: Pitch(midi=...), not Note(int): the int constructors attach
        # explicit natural accidentals that makeAccidentals then displays
        ps = [flatten(pitch.Pitch(midi=m)) for m in midis]
        n = note.Note(ps[0]) if len(ps) == 1 else chord.Chord(ps)
        n.quarterLength = ql
        parts[role].insert(off, n)
        at[(role, off)] = (n, pat)
        last_note[vi] = n

    # hi-hat: one sixteenth per row while armed
    for row in sorted(hihat_rows):
        n = drum_note(HIHAT, 0.25, notation)
        n.stemDirection = "down"
        drums.insert(row * 0.25, n)

    for role in ROLES:
        sc.insert(0, parts[role])
    sc.insert(0, drums)
    return sc


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--song", type=int, default=0)
    ap.add_argument("--out", default=None, help="output basename")
    ap.add_argument("--midi", action="store_true", help="also write MIDI")
    args = ap.parse_args()

    drv, hihat_rows = decode_song(args.song)
    print(f"song {args.song}: {drv.row} rows, "
          f"{sum(1 for e in drv.events if e['type'] == 'note')} notes, "
          f"{len(hihat_rows)} hi-hat rows")

    base = args.out or f"ninja_song{args.song}"
    sc = build_score(drv, hihat_rows, args.song).makeNotation(inPlace=False)
    fix_naturals(sc)
    fill_rests(sc)
    fix_voices(sc)
    xml = f"{base}.musicxml"
    sc.write("musicxml", fp=xml)
    print(f"wrote {xml}")

    if args.midi:
        drv, hihat_rows = decode_song(args.song)
        msc = build_score(drv, hihat_rows, args.song, notation=False)
        mid = f"{base}.mid"
        msc.write("midi", fp=mid)
        print(f"wrote {mid}")


if __name__ == "__main__":
    main()
