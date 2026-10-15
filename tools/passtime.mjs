#!/usr/bin/env node
// A pass's time: the cycles from pass_top to the main loop's wait for the
// pass clock (main_loop), each pass of scenarios from tests/scenarios.txt,
// interrupts included. Passes with a scroll are left out
// (tools/scrolltime.mjs has those), and so are the sounds' waits
// (wait_us: YX microseconds, two cycles each), which take the original's
// time whatever the code does. Frames are the BBC's: 40,000 cycles; the pass clock's tick is
// PASS_TICK (irq.6502).
//
//   node tools/passtime.mjs [--disc build/test.ssd] [--against old.ssd] [scenarios...]
//
// Scenarios by name (all but the scrolling ones by default).
import { readFileSync } from "fs";
import { startBeeb } from "./beeb.mjs";

const KEYS = {
    up: "Q", down: "A", left: "O", right: "P", fire: "SPACE", magic: "RETURN",
    p2up: "K9", p2down: "K8", p2left: "K6", p2right: "K7", p2fire: "K0", p2magic: "SHIFT",
};
// The scroll's entry: one routine, or (on an older disc) one a direction.
const SCROLLS = ["scroll", "scroll_up", "scroll_down", "scroll_left", "scroll_right"];

const args = process.argv.slice(2);
const opt = (name, dflt) => { const i = args.indexOf(`--${name}`); if (i < 0) return dflt; const v = args[i + 1]; args.splice(i, 2); return v; };
const disc = opt("disc", "build/test.ssd");
const against = opt("against", null);
const all = readFileSync("tests/scenarios.txt", "utf8").split("\n")
    .filter((l) => l.trim() && !l.startsWith("#"))
    .map((l) => l.split("|").map((f) => f.trim()));
const wanted = args.length ? all.filter((s) => args.includes(s[0])) : all.filter((s) => !s[0].startsWith("scroll"));

// The busy cycles of each pass of a scenario on a disc, the sounds' waits
// taken out; null for a pass with a scroll.
async function run(path, [name, keys, passes, flags = ""]) {
    const beeb = await startBeeb({ disc: path, symbols: path.replace(/\.ssd$/, ".json"), bootUntil: "start" });
    const inputs = keys.split(",").filter(Boolean).map((part) => {
        const [k, rng] = part.split(":");
        const [a, b] = rng.split("-").map(Number);
        return { key: KEYS[k], a, b: b ?? a };
    });
    const flag = (f) => { const m = flags.match(new RegExp(`--${f}\\s+(\\S+)`)); return m && m[1]; };
    const pokes = (flag("poke") ?? "").split(",").filter(Boolean).map((p) => p.split(":").map((v) => parseInt(v.replace("&", "0x"))));
    const out = [];
    try {
        if (flags.includes("--two")) await beeb.write("direct_players", [3]);
        await beeb.write("direct_level", [Number(flag("level") ?? 1) - 1]);
        const at = (s) => beeb.addr(s);
        const kinds = new Map([[at("pass_top"), "top"], [at("main_loop"), "end"], [at("wait_us"), "wait"]]);
        for (const s of SCROLLS) if (s in beeb.syms) kinds.set(at(s), "scroll");
        for (const pc of kinds.keys()) await beeb.breakpoint(pc);
        const held = new Set();
        let pass = -1, start = null, scrolled = false;
        while (pass < Number(passes) - 1) {
            const r = await beeb.cycles(40e6);
            if (!r.registers) break;            // the game ended
            const kind = kinds.get(r.registers.pc), t = r.registers.elapsed_cycles;
            if (kind === "scroll") scrolled = true;
            else if (kind === "wait") start += 2 * (r.registers.y * 256 + r.registers.x);
            else if (kind === "end" && start !== null) {
                out.push(scrolled ? null : t - start);
                start = null;
            } else if (kind === "top") {
                pass++; start = t; scrolled = false;
                for (const [when, addr, value] of pokes) {
                    if (when !== pass) continue;
                    const a = addr >= 0xFF2A ? at("vars_ff") + addr - 0xFF2A : at("vars_ba") + addr - 0xBA29;
                    await beeb.write(a, [value]);
                }
                for (const { key } of inputs) {
                    const want = inputs.some((i) => i.key === key && i.a <= pass && pass <= i.b);
                    if (want && !held.has(key)) { await beeb.keyDown(key); held.add(key); }
                    if (!want && held.has(key)) { await beeb.keyUp(key); held.delete(key); }
                }
            }
        }
    } finally {
        await beeb.close();
    }
    return out;
}

const sum = (xs) => xs.reduce((a, b) => a + b, 0);
let tot = [0, 0];
for (const s of wanted) {
    const runs = await Promise.all([run(disc, s), ...(against ? [run(against, s)] : [])]);
    const [mine, theirs] = runs;
    // Only passes both count (neither scrolled), so the sums compare.
    const both = mine.map((c, i) => c !== null && (!theirs || (theirs[i] !== undefined && theirs[i] !== null)));
    const m = mine.filter((_, i) => both[i]), o = theirs ? theirs.filter((_, i) => both[i]) : [];
    tot[0] += sum(m); tot[1] += sum(o);
    let line = `${s[0]}: ${m.length} passes, mean ${Math.round(sum(m) / m.length)}, max ${Math.max(...m)} cycles`;
    if (theirs) line += `  [against: mean ${Math.round(sum(o) / o.length)}, max ${Math.max(...o)}; ${(100 * (sum(m) - sum(o)) / sum(o)).toFixed(1)}%]`;
    console.log(line);
}
if (against) console.log(`all: ${tot[0]} cycles against ${tot[1]}, ${(100 * (tot[0] - tot[1]) / tot[1]).toFixed(1)}%`);
process.exit(0);
