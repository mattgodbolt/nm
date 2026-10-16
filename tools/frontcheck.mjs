#!/usr/bin/env node
// The front end on the release disc (menu.6502, decisions 13 and 21),
// driven with keys: power-on to the menu; 1 and 2; the passwords; Select
// Controls, a player's keys redefined (the punctuation by name) and then
// used in play; the menu's seed (decision 7); game over with a new high
// score and its name, shown on the menu; CTRL-SHIFT-Q; and the end of the
// game after the last level. Exits non-zero if a check fails.
//
//   node tools/frontcheck.mjs [--disc build/nm.ssd]
//
// Each step runs to the label that means it's done. A key is held until
// the routine that takes it is reached, then let go: the front end polls
// between waits and can miss a tap. What's on the screen is read back by
// matching each cell's pixels against the font (rowText).
import { readFileSync } from "fs";
import { startBeeb } from "./beeb.mjs";

const args = process.argv.slice(2);
const option = (name, dflt) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : dflt; };
const disc = option("--disc", "build/nm.ssd");
const b = await startBeeb({ disc, symbols: disc.replace(/\.ssd$/, ".json"), bootUntil: "main_menu" });
const S = (name) => b.addr(name);

let failed = false;
const check = (ok, what) => {
    console.log(`${ok ? "ok  " : "FAIL"} ${what}`);
    if (!ok) failed = true;
};

// How long a run to a label goes, in emulated seconds, before the label
// is called missed: far longer than any step here takes.
const LABEL_SECS = 30;
const reach = async (label, secs = LABEL_SECS) => (await b.runUntil(label, secs)).stopped_reason === "breakpoint";
// Hold a key until the label that takes it, then let go; and, given the
// label where the routine has seen it let go, run to that, so the next
// key isn't taken for this one still held.
const press = async (key, label, released) => {
    await b.keyDown(key);
    const ok = await reach(label);
    await b.keyUp(key);
    return ok && (!released || (await reach(released)));
};
// Where new_key (the password's and the controls' keys) and the name's
// entry have seen the last key let go and wait for the next.
const NEW_KEY = "new_key.down";
const NAME_KEY = "name_entry.wait";
// A routine that ends by way of `menu` (&C1E3) waits for a key and its
// release before the menu: SPACE, then the menu waiting for 1-4.
const toMenu = async () => {
    await press("SPACE", "menu.release");
    return reach("main_menu.keys");
};
// Run n of the main loop's passes; false if the game left the loop.
const passes = async (n) => {
    await b.breakpoint("pass_top");
    let ok = true;
    for (let i = 0; i < n && ok; i++) ok = (await b.run(LABEL_SECS)).stopped_reason === "breakpoint";
    await b.clearBreakpoints();
    return ok;
};
// Does running a few frames reach the label? (For what must not happen.)
const NOT_FRAMES = 25;
const reachedSoon = async (label) => {
    await b.breakpoint(label);
    const r = await b.frames(NOT_FRAMES);
    await b.clearBreakpoints();
    return r.stopped_reason === "breakpoint";
};
const word = async (sym) => b.peekw(sym);
const setWord = (sym, v) => b.write(sym, [v & 0xff, v >> 8]);
const str = async (sym, n) => String.fromCharCode(...(await b.read(sym, n)));

// The text in a row of the playfield. A cell's pixels in MODE 1 (16 bytes:
// its left four pixels' eight lines, then its right four's) are matched
// against each glyph of the font: a glyph matches when the cell's colour
// follows its bits, whatever the two colours are (the menu's rows flash
// in logical colours 2 and 3). A cell of one colour is a space.
const font = readFileSync("src/data/font.bin");
const FONT_FIRST = S("FONT_FIRST");
const ROW_BYTES = S("ROW_BYTES");
// The glyphs tried first: the font has pictures where some punctuation is.
const PREFER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.!";
const glyphOrder = [...PREFER].map((c) => c.charCodeAt(0) - FONT_FIRST)
    .concat([...Array(font.length / 8).keys()].filter((g) => !PREFER.includes(String.fromCharCode(g + FONT_FIRST))));
const pixel = (cell, x, y) => {
    const byte = cell[(x >> 2) * 8 + y], bit = 3 - (x & 3);
    return (((byte >> (bit + 4)) & 1) << 1) | ((byte >> bit) & 1);
};
const cellChar = (cell) => {
    const cols = [];
    for (let y = 0; y < 8; y++) for (let x = 0; x < 8; x++) cols.push(pixel(cell, x, y));
    if (cols.every((c) => c === cols[0])) return " ";
    for (const g of glyphOrder) {
        const seen = [undefined, undefined];
        let ok = true;
        for (let i = 0; i < 64 && ok; i++) {
            const bit = (font[g * 8 + (i >> 3)] >> (7 - (i & 7))) & 1;
            if (seen[bit] === undefined) seen[bit] = cols[i];
            else ok = seen[bit] === cols[i];
        }
        if (ok && seen[0] !== undefined && seen[1] !== undefined && seen[0] !== seen[1]) return String.fromCharCode(g + FONT_FIRST);
    }
    return "?";
};
const rowText = async (row) => {
    const bytes = await b.read(S("screen") + row * ROW_BYTES, ROW_BYTES);
    let text = "";
    for (let col = S("VIEW_LEFT"); col < S("SCREEN_COLS"); col++) text += cellChar(bytes.slice(col * 16, col * 16 + 16));
    return text;
};
const screenText = async () => {
    const rows = [];
    for (let row = 0; row < S("SCREEN_ROWS"); row++) rows.push(await rowText(row));
    return rows;
};
const shows = async (text) => (await screenText()).some((r) => r.includes(text));
// A check on the screen's text, which prints the screen if it fails.
const checkShows = async (texts, what) => {
    const rows = await screenText();
    const ok = [].concat(texts).every((t) => rows.some((r) => r.includes(t)));
    check(ok, what);
    if (!ok) console.log(rows.map((r) => `     |${r}|`).join("\n"));
};

// The players' records (touch.6502's R_ fields) and the controls' order
// (player.6502's C_ constants).
const R_COL = S("R_COL");
const CONTROLS = S("CONTROLS");
const keyNum = (k) => S(`K_${k}`);
const hex = (bytes) => bytes.map((x) => x.toString(16).padStart(2, "0")).join(" ");

try {
    // 1. Power-on: the menu, with the tape's high score and name.
    check(await reach("main_menu.keys"), "power-on reaches the menu");
    await checkShows(["1  ONE PLAYER GAME", "2  TWO PLAYER GAME", "3  SELECT CONTROLS", "4  ENTER  PASSWORD"], "... its four choices");
    const tapeHigh = await word("HighScore");
    await checkShows(`${String(tapeHigh).padStart(5, "0")}0  BY  TAG GAMES!`, "... and the tape's high score and name");
    const menuState = await b.saveState("menu");

    // 2 and 6. 1 and 2 start games, each seeded from the VSyncs the menu
    // waited (decision 7): two different waits, two different seeds.
    const startAfter = async (key, frames) => {
        await b.restoreState(menuState);
        if (frames) await b.frames(frames);
        const ok = await press(key, "new_game");
        return { ok, seed: await b.peek("seed"), vsyncs: await b.peek("vsyncs") };
    };
    const [WAIT_A, WAIT_B] = [10, 37];
    const a = await startAfter("K1", WAIT_A);
    const c = await startAfter("K1", WAIT_B);
    check(a.ok && c.ok && a.seed !== c.seed && a.seed === (a.vsyncs || 1) && c.seed === (c.vsyncs || 1),
        `the seed comes from the VSyncs: ${WAIT_A} frames at the menu seed ${a.seed}, ${WAIT_B} seed ${c.seed}`);

    let ok = (await startAfter("K1", 0)).ok && (await passes(1));
    let inPlay = await b.peek("InPlay"), level = await b.peek("Level");
    check(ok && inPlay === 1 && level === 0 && (await word("P1Strength")) === S("START_STRENGTH"),
        `1: a one-player game (InPlay ${inPlay}, level ${level + 1})`);
    // In play, CTRL and SHIFT with Q: a new game, by way of the menu.
    await b.keyDown("CTRL"); await b.keyDown("SHIFT");
    ok = await press("Q", "start_game");
    await b.keyUp("SHIFT"); await b.keyUp("CTRL");
    check(ok && (await toMenu()), "... CTRL-SHIFT-Q: back to the menu");

    ok = (await startAfter("K2", 0)).ok && (await passes(1));
    inPlay = await b.peek("InPlay"); level = await b.peek("Level");
    check(ok && inPlay === 3 && level === 0 && (await word("P1Strength")) === S("START_STRENGTH")
        && (await word("P2Strength")) === S("START_STRENGTH"), `2: a two-player game (InPlay ${inPlay}, level ${level + 1})`);

    // 3. Each password, typed after 4, starts its level, whose title screen
    // shows it; a wrong one starts level 1.
    const PASSWORD_LEN = S("PASSWORD_LEN");
    const pw = readFileSync("src/data/passwords.bin");
    const codes = [];
    for (let i = 0; i < pw.length; i += PASSWORD_LEN + 1) codes.push([pw.subarray(i, i + PASSWORD_LEN).toString("latin1"), pw[i + PASSWORD_LEN]]);
    codes.push(["ABCD", 0]);
    for (const [code, want] of codes) {
        await b.restoreState(menuState);
        ok = await press("K4", "enter_code", NEW_KEY);
        if (code === codes[0][0]) await checkShows("ENTER CODE", "4: ENTER CODE");
        for (const ch of code.slice(0, -1)) ok = ok && (await press(ch, "key_click", NEW_KEY));
        ok = ok && (await press(code.at(-1), "key_click"));
        const typed = await str("PasswordTyped", PASSWORD_LEN);
        ok = ok && typed === code && (await toMenu()) && (await press("K1", "new_game"));
        ok = ok && (await reach("level_intro.pause_start"));
        const title = (await screenText()).join("|");
        const titleOk = title.includes(`LEVEL ${String(want + 1).padStart(2, "0")}`)
            && (want === 0 || title.includes(`PASSWORD..${code}`));
        ok = ok && (await passes(1));
        level = await b.peek("Level");
        check(ok && titleOk && level === want, `password ${code} (typed ${typed}): level ${level + 1}${titleOk ? "" : ", but not on its title"}`);
    }

    // 4. Select Controls: only 1 and 2 (no Kempston); player 1's keys
    // redefined, SHIFT refused, the punctuation shown by name.
    await b.restoreState(menuState);
    check(await press("K3", "select_controls"), "3: Select Controls");
    await reach("select_controls.key");
    const rows = await screenText();
    const offered = rows.filter((r) => /\d  /.test(r)).map((r) => r.trim());
    check(JSON.stringify(offered) === JSON.stringify(["1  REDEFINE PLAYER ONE", "2  REDEFINE PLAYER TWO"]),
        `... offers 1 and 2 only (${offered.join(", ")})`);
    await b.keyDown("K3");
    check(!(await reachedSoon("select_controls.redefine")), "... and 3 does nothing");
    await b.keyUp("K3");
    check(await press("K1", "select_controls.redefine", NEW_KEY), "... 1: redefine player one");
    const before = await b.read("controls", 2 * CONTROLS);
    await b.keyDown("SHIFT");
    check(!(await reachedSoon("key_click")), "... SHIFT is refused");
    await b.keyUp("SHIFT");
    await reach(NEW_KEY);
    // In the order asked: up, down, left, right, fire, magic.
    const NEW_KEYS = [
        ["SEMICOLON_PLUS", "SEMI", "UP....."], ["SLASH", "SLASH", "DOWN..."], ["COMMA", "COMMA", "LEFT..."],
        ["PERIOD", "STOP", "RIGHT.."], ["SPACE", "SPACE", "FIRE..."], ["COLON_STAR", "COLON", "MAGIC.."],
    ];
    for (const [key, name, ask] of NEW_KEYS) {
        ok = await press(key, "key_click", key === NEW_KEYS.at(-1)[0] ? undefined : NEW_KEY);
        await checkShows(`KEY FOR ${ask}${name}`, `... ${ask.replace(/\.+$/, "").toLowerCase()}: ${key}, shown as ${name}`);
        check(ok, `... ${key} taken`);
    }
    // The table is in C_ order: magic, up, down, right, left, fire.
    const want = ["COLON", "SEMI", "SLASH", "STOP", "COMMA", "SPACE"].map(keyNum);
    const after = await b.read("controls", 2 * CONTROLS);
    check(hex(after.slice(0, CONTROLS)) === hex(want), `... player 1's controls: ${hex(after.slice(0, CONTROLS))}`);
    check(hex(after.slice(CONTROLS)) === hex(before.slice(CONTROLS)), "... player 2's unchanged");
    check(await toMenu(), "... and back to the menu");

    // The new right key moves the ninja; the old one doesn't.
    ok = (await press("K1", "new_game")) && (await passes(1));
    const col = async () => b.peek(S("Player1") + R_COL);
    const MOVE_PASSES = 40;
    const start = await col();
    await b.keyDown("X");
    ok = ok && (await passes(MOVE_PASSES));
    await b.keyUp("X");
    const afterOld = await col();
    await b.keyDown("PERIOD");
    ok = ok && (await passes(MOVE_PASSES));
    await b.keyUp("PERIOD");
    const afterNew = await col();
    check(ok && afterOld === start && afterNew > start, `in play: X no longer moves the ninja (column ${start} to ${afterOld}), full stop does (to ${afterNew})`);

    // 5. Game over with a new high score: the name, with DELETE and a held
    // key's repeat, then the menu shows it. (Strength 0 runs out at the
    // next status tick, as passlog's --poke does it.)
    const gameOver = async (players) => {
        await b.restoreState(menuState);
        return (await press(players === 1 ? "K1" : "K2", "new_game")) && (await passes(1));
    };
    ok = await gameOver(1);
    const NEW_HIGH = 1234;          // (shown as ten times this)
    const treasure = tapeHigh + NEW_HIGH;
    await setWord("P1Treasure", treasure);
    await setWord("P1Strength", 0);
    ok = ok && (await reach("game_over")) && (await reach("wait_frames"));
    await checkShows("GAME OVER PLAYER 1", "strength out: GAME OVER PLAYER 1");
    ok = ok && (await reach("name_entry"));
    check(ok && (await word("HighScore")) === treasure, `... a new high score (${treasure}0)`);
    await checkShows("YOUR NAME PLAYER 1", "... YOUR NAME PLAYER 1");
    for (const k of ["M", "A", "T", "T", "DELETE"]) ok = ok && (await press(k, "key_click", NAME_KEY));
    const deleted = await str("high_name", S("NAME_LEN"));
    check(deleted === "MAT       " && (await shows("MAT       ")), `... DELETE deletes ("${deleted}")`);
    // Z held: taken, then taken again when it repeats.
    await b.keyDown("Z");
    ok = ok && (await reach("key_click")) && (await reach("key_click"));
    await b.keyUp("Z");
    ok = ok && (await reach(NAME_KEY));
    ok = ok && (await press("RETURN", "start_game"));
    const name = await str("high_name", S("NAME_LEN"));
    check(ok && name === "MATZZ     ", `... a held key repeats, RETURN ends it: "${name}"`);
    check(await toMenu(), "... then the menu");
    await checkShows(`${String(treasure).padStart(5, "0")}0  BY  MATZZ`, "... which shows the new high score and name");

    // 7. The game's end: leaving level 50 (InPlay's exit bits, Level the
    // last), WELL DONE, the strength counted into the treasure, and then
    // game over when the strength, now 0, runs out: the better treasure,
    // over the tape's high score, asks for its player's name.
    const LAST = S("LEVELS_END") - 1;
    const STRENGTH_LEFT = [20, 30];
    for (const players of [1, 2]) {
        ok = await gameOver(players);
        await b.write("Level", [LAST]);
        await b.write("InPlay", [players === 1 ? 4 : 0x0c]);   // (left by the exit: bits 2 and 3)
        await setWord("P1Strength", STRENGTH_LEFT[0]);
        await setWord("P2Strength", players === 2 ? STRENGTH_LEFT[1] : 0);
        const t0 = [await word("P1Treasure"), await word("P2Treasure")];
        ok = ok && (await reach("game_complete")) && (await reach("timers"));
        await checkShows(`WELL DONE YOUNG ${players === 1 ? "MAN" : "MEN"}!`, `${players} player${players === 1 ? "" : "s"} past level ${LAST + 1}: WELL DONE YOUNG ${players === 1 ? "MAN" : "MEN"}!`);
        const t1 = [await word("P1Treasure"), await word("P2Treasure")];
        const s1 = [await word("P1Strength"), await word("P2Strength")];
        check(ok && s1[0] === 0 && s1[1] === 0 && t1[0] === t0[0] + STRENGTH_LEFT[0]
            && t1[1] === t0[1] + (players === 2 ? STRENGTH_LEFT[1] : 0),
            `... the strength counted into the treasure (${t1.join(", ")})`);
        ok = ok && (await reach("name_entry"));
        const best = t1[1] > t1[0] ? 2 : 1;
        check(ok && (await word("HighScore")) === Math.max(...t1), `... and game over: player ${best}'s treasure the high score`);
        await checkShows(`YOUR NAME PLAYER ${best}`, `... YOUR NAME PLAYER ${best}`);
    }
} finally {
    await b.close();
}
console.log(failed ? "front end: FAILED" : "front end: all checks pass");
process.exit(failed ? 1 : 0);
