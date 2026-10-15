#!/usr/bin/env node
// Every level's first view as the BBC draws it: boots build/viewcheck.ssd
// (src/startup.6502's view_check) and dumps the screen each time it
// reaches view_done, to build/views/bbc_NN.bin. tools/viewcmp.py compares
// them with the original's (tools/zxviews.py).
import { startBeeb } from "./beeb.mjs";
import { mkdirSync, writeFileSync } from "fs";

const LEVELS = 50;
mkdirSync("build/views", { recursive: true });
const beeb = await startBeeb({ disc: "build/viewcheck.ssd", symbols: "build/viewcheck.json" });
try {
    await beeb.breakpoint("view_done");
    for (let n = 1; n <= LEVELS; n++) {
        const r = await beeb.run(60);
        if (r.stopped_reason === undefined && !r.breakpoint_hit && !JSON.stringify(r).includes("breakpoint"))
            throw new Error(`level ${n}: never reached view_done (${JSON.stringify(r)})`);
        writeFileSync(`build/views/bbc_${String(n).padStart(2, "0")}.bin`, Buffer.from(await beeb.dump()));
    }
    console.log(`build/views: ${LEVELS} BBC views`);
} finally {
    await beeb.close();
}
process.exit(0);
