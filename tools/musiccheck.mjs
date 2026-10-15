#!/usr/bin/env node
// The music (src/music.6502, decision 8) against the original's driver.
//
// 1. build/musiccheck.ssd (MUSICCHECK: startup.6502's music_check) plays
//    every song on the 6502 driver, frame after frame, and records each
//    frame's shadow AY registers and mu_on; tools/musicmodel.py plays the
//    same on tools/music/dw_decode.py's Driver (itself checked against
//    the captures in music/). Every frame of every song must match, for at
//    least as many frames as the song's capture has.
// 2. The bytes the 6502 wrote to the SN76489 meanwhile must be those
//    musicmodel.py's model of the conversion writes (decisions 9-12).
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
const RECORD = 13;          // startup.6502's MC_RECORD: 12 registers, then mu_on
const hex = (a) => a.map((x) => x.toString(16).padStart(2, "0")).join(" ");
const snBytes = (log) => [...log.matchAll(/: 0x([0-9a-f]{2}) /g)].map((m) => parseInt(m[1], 16));

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

// 3: the game's build, the interrupt playing.
b = await startBeeb({ disc: "build/nm.ssd", symbols: "build/nm.json", bootUntil: "start.idle" });
try {
    const v0 = await b.peek("vsyncs");
    await b.call("start_sound_capture", { session_id: b.session_id });
    await b.frames(50);
    let writes = snBytes((await b.call("stop_sound_capture", { session_id: b.session_id, max_entries: 1e6 })).content[0].text);
    const frames = ((await b.peek("vsyncs")) - v0 + 256) & 255;
    if ((await b.peek("mu_on")) !== 1) fail("the game's build isn't playing song 0");
    if (writes.length === 0) fail(`the game's build: no bytes to the chip in ${frames} frames`);
    else console.log(`the game's build: song 0 from the interrupt, ${writes.length} bytes to the chip in ${frames} frames`);
    await b.write("mu_busy", [1]);
    await b.call("start_sound_capture", { session_id: b.session_id });
    await b.frames(50);
    writes = snBytes((await b.call("stop_sound_capture", { session_id: b.session_id, max_entries: 1e6 })).content[0].text);
    if (writes.length) fail(`with mu_busy set the interrupt wrote ${writes.length} bytes to the chip`);
    await b.write("mu_busy", [0]);
    await b.call("start_sound_capture", { session_id: b.session_id });
    await b.frames(10);
    writes = snBytes((await b.call("stop_sound_capture", { session_id: b.session_id, max_entries: 1e6 })).content[0].text);
    if (!writes.length) fail("after mu_busy the interrupt didn't write the chip again");
    else console.log("mu_busy: nothing to the chip while it's set, and the music's changes after");
} finally {
    await b.close();
}
process.exit(failed ? 1 : 0);
