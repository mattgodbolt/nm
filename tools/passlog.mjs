#!/usr/bin/env node
// Play the BBC port pass by pass and log its state each pass: the
// counterpart of tools/passlog.py (same inputs, same output), compared by
// tools/passcmp.py.
//
//   node tools/passlog.mjs '<inputs>' passes [--out build/bbc_passes.json] [--disc build/nm.ssd]
//
// Pass 0 is the first time pass_top (the main loop's) is reached; keys are
// set at the top of a pass, before the game reads them. Each pass logs the
// original's variables in the port's copies of the blocks (vars_ba,
// vars_ff: decision 10) and the map, as hex.
import { writeFileSync } from "fs";
import { startBeeb } from "./beeb.mjs";

// The Spectrum's keys (tools/passlog.py) as the port's (src/keys.6502).
const KEYS = {
    up: "Q", down: "A", left: "O", right: "P", fire: "SPACE", magic: "RETURN",
    p2up: "K9", p2down: "K8", p2left: "K6", p2right: "K7", p2fire: "K0", p2magic: "SHIFT",
};

const args = process.argv.slice(2);
const option = (name, dflt) => { const i = args.indexOf(name); return i >= 0 ? args.splice(i, 2)[1] : dflt; };
const out = option("--out", "build/bbc_passes.json");
const disc = option("--disc", "build/nm.ssd");
const inputs = (args[0] ?? "").split(",").filter(Boolean).map((part) => {
    const [name, rng] = part.split(":");
    const [a, b] = rng.split("-").map(Number);
    return { key: KEYS[name], a, b: b ?? a };
});
const passes = parseInt(args[1] ?? "100");
const hex = (bytes) => bytes.map((b) => b.toString(16).padStart(2, "0")).join("");

const beeb = await startBeeb({ disc, symbols: disc.replace(/\.ssd$/, ".json") });
const log = [];
try {
    await beeb.breakpoint("pass_top");
    const held = new Set();
    for (let n = 0; n < passes; n++) {
        const r = await beeb.run(60);
        if (!JSON.stringify(r).includes("breakpoint")) throw new Error(`pass ${n}: pass_top not reached (${JSON.stringify(r)})`);
        for (const { key, a, b } of inputs) {
            const want = a <= n && n <= b;
            if (want && !held.has(key)) { await beeb.keyDown(key); held.add(key); }
            if (!want && held.has(key) && !inputs.some((i) => i.key === key && i.a <= n && n <= i.b)) {
                await beeb.keyUp(key); held.delete(key);
            }
        }
        log.push({
            pass: n,
            ba: hex(await beeb.read("vars_ba", 0xBAA0 - 0xBA29)),
            ff: hex(await beeb.read("vars_ff", 0xFF62 - 0xFF2A)),
            map: hex(await beeb.read("map", 1024)),
        });
    }
} finally {
    await beeb.close();
}
writeFileSync(out, JSON.stringify(log));
console.log(`${out}: ${log.length} passes`);
process.exit(0);
