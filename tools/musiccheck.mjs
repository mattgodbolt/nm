#!/usr/bin/env node
// The music (src/music.6502, decision 14) against the original's driver.
//
// 1. build/musiccheck.ssd (MUSICCHECK: startup.6502's music_check) plays
//    every song on the 6502 driver, frame after frame, and records each
//    frame's shadow AY registers and mu_on; tools/musicmodel.py plays the
//    same on tools/music/dw_decode.py's Driver (itself checked against
//    the captures in music/). Every frame of every song must match, for at
//    least as many frames as the song's capture has.
// 2. The bytes the 6502 wrote to the SN76489 meanwhile must be those
//    musicmodel.py's model of the conversion writes (decisions 15-18).
// 3. The game's build: the interrupt plays song 0, and while mu_busy is
//    set it writes nothing to the chip.
//
//   node tools/musiccheck.mjs
//
// Exits non-zero on a difference.
import { execFileSync } from "child_process";
import { mkdirSync, writeFileSync } from "fs";
import { startBeeb } from "./beeb.mjs";

const PYTHON = process.env.PYTHON || ".venv/bin/python";
mkdirSync("build/music", { recursive: true });
const model = JSON.parse(execFileSync(PYTHON, ["tools/musicmodel.py"], { maxBuffer: 1 << 28 }).toString());
const RECORD = 19;          // startup.6502's MC_RECORD: 12 registers, mu_on, the bass's half-cycles
const hex = (a) => a.map((x) => x.toString(16).padStart(2, "0")).join(" ");
const snBytes = (log) => [...log.matchAll(/: 0x([0-9a-f]{2}) /g)].map((m) => parseInt(m[1], 16));

// The bass check: frames to wait for a channel's bass and to watch it, how
// close its half-cycles must be on average, and the latest an edge may be
// (an interrupt waits while another runs or interrupts are off).
const BASS_WAIT = 3000;
const BASS_FRAMES = 25;
const BASS_MEAN_US = 1;
const BASS_LATE_US = 100;

let failed = false;
const fail = (msg) => { console.log(`DIFFERS: ${msg}`); failed = true; };

// 1 and 2: every song.
let b = await startBeeb({ disc: "build/musiccheck.ssd", symbols: "build/musiccheck.json", bootUntil: "music_check" });
try {
    if (b.addr("MC_FRAMES") !== model.mc_frames || b.addr("MC_RECORD") !== RECORD)
        throw new Error("startup.6502's MC_FRAMES or MC_RECORD isn't musicmodel.py's");
    await b.call("start_sound_capture", { session_id: b.session_id });
    await b.breakpoint("mc_full");
    const got = [];
    for (const song of model.songs) {
        const records = [];
        for (let c = 0; c < song.chunks; c++) {
            const r = await b.run(60);
            if (!JSON.stringify(r).includes("breakpoint")) throw new Error(`song ${song.song}: never reached mc_full`);
            const buf = await b.read("mc_buf", model.mc_frames * RECORD);
            for (let f = 0; f < model.mc_frames; f++) records.push(buf.slice(f * RECORD, (f + 1) * RECORD));
            if (c === song.chunks - 1 && song.song + 1 < model.songs.length) await b.write("mc_next", [song.song + 1]);
        }
        got.push(records);
    }
    const log = (await b.call("stop_sound_capture", { session_id: b.session_id, max_entries: 1e7 })).content[0].text;
    await b.clearBreakpoints();

    for (const [i, song] of model.songs.entries()) {
        const want = song.records;
        let first = -1, same = 0;
        for (let f = 0; f < want.length; f++) {
            if (hex(got[i][f]) === hex(want[f])) same++;
            else if (first < 0) first = f;
        }
        if (first >= 0) {
            fail(`song ${song.song}: ${same}/${want.length} frames match; the first that doesn't, frame ${first}:\n` +
                 `  6502   ${hex(got[i][first])}\n  Python ${hex(want[first])}`);
        } else {
            console.log(`song ${song.song}: ${want.length} frames (its capture ${song.captured}): the shadow AY registers match`);
        }
    }
    writeFileSync("build/music/bbc.json", JSON.stringify(got));

    const sn = snBytes(log);
    const want = model.sn;
    let at = 0;
    while (at < sn.length && at < want.length && sn[at] === want[at]) at++;
    if (at < sn.length || at < want.length)
        fail(`the SN76489's bytes: ${sn.length} written, the model's ${want.length}; the first difference at ${at}:\n` +
             `  6502  ${hex(sn.slice(at, at + 12))}\n  model ${hex(want.slice(at, at + 12))}`);
    else console.log(`the SN76489: ${sn.length} bytes, as the model writes them`);
} finally {
    await b.close();
}

// 3: the game's build, the interrupt playing: in play, after the opening
// jingle (song 1), the status tick starts the main theme.
b = await startBeeb({ disc: "build/test.ssd", symbols: "build/test.json", bootUntil: "pass_top" });
try {
    await b.frames(250);
    const v0 = await b.peek("vsyncs");
    await b.call("start_sound_capture", { session_id: b.session_id });
    await b.frames(50);
    let writes = snBytes((await b.call("stop_sound_capture", { session_id: b.session_id, max_entries: 1e6 })).content[0].text);
    const frames = ((await b.peek("vsyncs")) - v0 + 256) & 255;
    if ((await b.peek("mu_on")) !== 1) fail("the game's build isn't playing a song");
    if (writes.length === 0) fail(`the game's build: no bytes to the chip in ${frames} frames`);
    else console.log(`the game's build: the music from the interrupt, ${writes.length} bytes to the chip in ${frames} frames`);
    // Each channel's bass (bass.6502), each when it next plays: with
    // mu_busy set the music's frame writes nothing, and the bass's edges go
    // on at the half-cycles it left, each channel's volume switching
    // between its level and silence, every half-cycle on average (an edge
    // is as late as the interrupt, but the next is timed from when it was
    // due). Nothing else reaches the chip.
    const seen = new Set();
    for (let want = 0; want < 3; want++) {
        if (seen.has(want)) continue;
        let halves = [];
        for (let f = 0; f < BASS_WAIT; f++) {
            const h = await b.read("mu_half_lo", 6);
            halves = [0, 1, 2].map((c) => h[c] | (h[c + 3] << 8));
            if (halves[want]) break;
            await b.frames(1);
        }
        if (!halves[want]) { fail(`channel ${want}: no bass in ${BASS_WAIT} frames, to check`); continue; }
        await b.write("mu_busy", [1]);
        const lvl = await b.read("mu_bass_lvl", 3);
        await b.call("start_sound_capture", { session_id: b.session_id });
        await b.frames(BASS_FRAMES);
        const busyLog = (await b.call("stop_sound_capture", { session_id: b.session_id, max_entries: 1e6 })).content[0].text;
        await b.write("mu_busy", [0]);
        const entries = [...busyLog.matchAll(/^(\d+): 0x([0-9a-f]{2}) /gm)].map((m) => [Number(m[1]), parseInt(m[2], 16)]);
        const ours = (v, c) => halves[c] && (v & 0xF0) === (lvl[c] & 0xF0);
        for (const [c, half] of halves.entries()) {
            if (!half) continue;
            seen.add(c);
            const mine = entries.filter(([, v]) => ours(v, c));
            let alternate = mine.every(([, v]) => v === lvl[c] || v === (lvl[c] | 15));
            for (let i = 1; i < mine.length; i++) if (mine[i][1] === mine[i - 1][1]) alternate = false;
            const gaps = mine.slice(1).map(([t], i) => (t - mine[i][0]) / 2);   // microseconds
            const mean = gaps.length ? (mine[mine.length - 1][0] - mine[0][0]) / 2 / gaps.length : 0;
            const worst = Math.max(...gaps.map((g) => Math.abs(g - half)));
            console.log(`channel ${c}: bass at a half-cycle of ${half}us: ${gaps.length} edges, ` +
                        `${mean.toFixed(2)}us apart on average, the furthest out by ${worst.toFixed(1)}us`);
            if (!alternate) fail(`channel ${c}: its edges don't switch between &${lvl[c].toString(16)} and silence`);
            if (gaps.length < 2 || Math.abs(mean - half) > BASS_MEAN_US) fail(`channel ${c}: its half-cycles aren't ${half}us`);
            if (worst > BASS_LATE_US) fail(`channel ${c}: an edge ${worst.toFixed(1)}us out`);
        }
        const others = entries.filter(([, v]) => ![0, 1, 2].some((c) => ours(v, c)));
        if (others.length) fail(`with mu_busy set the chip got ${others.length} bytes that aren't the bass's`);
    }
    await b.call("start_sound_capture", { session_id: b.session_id });
    await b.frames(10);
    writes = snBytes((await b.call("stop_sound_capture", { session_id: b.session_id, max_entries: 1e6 })).content[0].text);
    if (!writes.length) fail("after mu_busy the interrupt didn't write the chip again");
    else console.log("mu_busy: nothing but the bass's edges to the chip while it's set, and the music's changes after");
} finally {
    await b.close();
}
process.exit(failed ? 1 : 0);
