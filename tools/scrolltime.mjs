#!/usr/bin/env node
// The scroll's time, and its screens step by step. Plays a slide in each
// direction (keys held over main-loop passes, as tests/scenarios.txt's)
// and times each scroll from its entry (scroll_up and the rest) to its
// end (erase_old, or the pass's end when it stops at the map's edge), and
// the pass it's in (pass_top to main_loop's wait for the pass clock).
// Frames are the BBC's: 40,000 cycles.
//
//   node tools/scrolltime.mjs [--disc build/test.ssd] [--against old.ssd] [cases...]
//
// A case is one of CASES' names or keys/level (left:5-120,fire:30/37).
//
// With --against, the same slides on the other disc too: the screen is
// compared at every step (each shift's entry, and the scroll's end), and
// the attributes at the scroll's end (the port moves them once a slide:
// shift.6502's slide_attrs), and the times put side by side. The symbols
// are the .json beside each disc.
import { startBeeb } from "./beeb.mjs";

const FRAME = 40000;
const SCREEN_BYTES = 0x3000;
const KEYS = { up: "F", down: "C", left: "Z", right: "X", fire: "G", magic: "A" };
// name: [keys held over passes, as tests/scenarios.txt's; the level;
// pokes, [pass, symbol, value]]: each slides the view at least once. The
// sideways slides move player 1 in its record to beyond the view's
// columns (the map keeps it where it was: only the slide is measured).
const CASES = {
    down: ["down:5-200", 2],
    up: ["up:5-200", 31],
    across: ["", 1, [[10, "Player1", 22], [20, "Player1", 16]]],
};

const args = process.argv.slice(2);
const opt = (name, dflt) => { const i = args.indexOf(`--${name}`); if (i < 0) return dflt; const v = args[i + 1]; args.splice(i, 2); return v; };
const disc = opt("disc", "build/test.ssd");
const against = opt("against", null);
const cases = args.length ? args : Object.keys(CASES);
// The scroll's entry: one routine, or (on an older disc) one a direction.
// Every shift goes through shift_by.
const SCROLLS = ["scroll", "scroll_up", "scroll_down", "scroll_left", "scroll_right"];
const SHIFTS = ["shift_by"];

// A case of its own: keys/level (right:5-300,fire:20/41).
function parseCase(spec) {
    const [keys, level] = spec.split("/");
    return [keys, Number(level)];
}

// One case on one disc: each scroll's steps (screens) and times.
async function run(path, name) {
    const [keys, level, pokes = []] = CASES[name] ?? parseCase(name);
    const inputs = keys.split(",").filter(Boolean).map((part) => {
        const [k, rng] = part.split(":");
        const [a, b] = rng.split("-").map(Number);
        return { key: KEYS[k], a, b: b ?? a };
    });
    const last = Math.max(...inputs.map((i) => i.b), ...pokes.map((p) => p[0]));
    const beeb = await startBeeb({ disc: path, symbols: path.replace(/\.ssd$/, ".json"), bootUntil: "start" });
    const at = (s) => beeb.addr(s);
    const kinds = new Map([[at("pass_top"), "pass"], [at("main_loop"), "done"], [at("erase_old"), "erase"]]);
    const scrollSyms = SCROLLS.filter((s) => s in beeb.syms);
    for (const s of scrollSyms) kinds.set(at(s), "scroll");
    const names = new Map(scrollSyms.map((s) => [at(s), s]));
    for (const s of SHIFTS) kinds.set(at(s), "shift");
    const scrolls = [];
    try {
        await beeb.write("direct_level", [level - 1]);
        for (const pc of kinds.keys()) await beeb.breakpoint(pc);
        let pass = -1, passStart = 0, cur = null;
        const held = new Set();
        const screen = async () => [...(await beeb.read(0x5000, SCREEN_BYTES)), ...(await beeb.read("attrs", 768))];
        while (pass < last + 5) {
            const r = await beeb.cycles(40e6);
            if (r.stopped_reason !== "breakpoint" && r.stopped_reason !== "pending_breakpoint") throw new Error(`${name}: no pass for 20s`);
            const kind = kinds.get(r.registers.pc), t = r.registers.elapsed_cycles;
            if (kind === "done") {
                if (cur) {
                    if (cur.end === undefined) { cur.end = t; cur.steps.push(await screen()); }
                    cur.pass = t - passStart;
                    scrolls.push(cur); cur = null;
                }
            } else if (kind === "pass") {
                pass++; passStart = t;
                for (const [when, sym, value] of pokes) if (when === pass) await beeb.write(sym, [value]);
                for (const { key } of inputs) {
                    const want = inputs.some((i) => i.key === key && i.a <= pass && pass <= i.b);
                    if (want && !held.has(key)) { await beeb.keyDown(key); held.add(key); }
                    if (!want && held.has(key)) { await beeb.keyUp(key); held.delete(key); }
                }
            } else if (kind === "scroll") {
                cur = { at: pass, start: t, steps: [], which: names.get(r.registers.pc) };
            } else if (kind === "shift" && cur) {
                cur.steps.push(await screen());
            } else if (kind === "erase" && cur && cur.end === undefined) {
                cur.end = t; cur.steps.push(await screen());
            }
        }
    } finally {
        await beeb.close();
    }
    return scrolls;
}

const frames = (c) => (c / FRAME).toFixed(2);
let differs = false;
for (const name of cases) {
    const runs = await Promise.all([run(disc, name), ...(against ? [run(against, name)] : [])]);
    const [mine, theirs] = runs;
    if (!mine.length) { console.log(`${name}: no scroll`); differs = true; continue; }
    mine.forEach((s, i) => {
        let line = `${name} ${s.which} ${i + 1} (pass ${s.at}, ${s.steps.length - 1} steps): ${s.end - s.start} cycles, ${frames(s.end - s.start)} frames; its pass ${frames(s.pass)} frames`;
        const o = theirs?.[i];
        if (o) {
            line += `  [against: ${o.end - o.start} cycles, ${frames(o.end - o.start)} frames; pass ${frames(o.pass)}]`;
            const last = s.steps.length - 1;
            const bad = s.steps.findIndex((scr, k) => !o.steps[k] || scr.some((v, j) => (k === last || j < SCREEN_BYTES) && v !== o.steps[k][j]));
            if (o.at !== s.at || o.steps.length !== s.steps.length || bad >= 0) {
                line += `  DIFFERS${bad >= 0 ? ` at step ${bad}` : ""}`;
                differs = true;
            }
        }
        console.log(line);
    });
    if (theirs && theirs.length !== mine.length) { console.log(`${name}: ${mine.length} scrolls, against ${theirs.length}`); differs = true; }
}
process.exit(differs ? 1 : 0);
