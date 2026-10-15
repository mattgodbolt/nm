#!/bin/sh
# Replay every scenario in tests/scenarios.txt on the original and the port
# and compare them pass by pass, side by side (JOBS at a time, the CPUs by
# default). Exits non-zero if any differs. `tools/passcheck.sh --one N`
# runs the Nth alone. The logs go in PASSDIR; SCENARIOS names another
# scenarios file (tools/fuzz.py).
cd "$(dirname "$0")/.."
out=${PASSDIR:-build/passcheck}
export PASSDIR="$out"
# Not transcribed yet, so not compared (docs/journal.md): the menu's colour.
IGNORE=${IGNORE:-MenuColour}
# The screens compared too, every this many passes and on the last.
SCREENS=${SCREENS:-50}
export SCREENS
export IGNORE
scenarios() { grep -v "^#" "${SCENARIOS:-tests/scenarios.txt}" | grep -v "^[[:space:]]*$"; }

if [ "$1" = "--one" ]; then
    scenarios | sed -n "$2p" | while IFS='|' read -r name inputs passes flags; do
        name=$(echo $name); inputs=$(echo $inputs); passes=$(echo $passes)
        .venv/bin/python tools/passlog.py "$inputs" "$passes" --out "$out/zx_$name.json" --screens $SCREENS $flags > /dev/null || exit 1
        node tools/passlog.mjs "$inputs" "$passes" --out "$out/bbc_$name.json" --screens $SCREENS $flags > /dev/null || exit 1
        if result=$(python3 tools/passcmp.py "$out/zx_$name.json" "$out/bbc_$name.json" --ignore "$IGNORE"); then
            echo "$name: $result"
        else
            echo "$name: DIFFERS"; echo "$result"; exit 1
        fi
    done
    exit $?
fi

rm -rf "$out" && mkdir -p "$out"
n=$(scenarios | wc -l)
seq "$n" | xargs -P "${JOBS:-$(nproc)}" -I{} sh -c \
    'tools/passcheck.sh --one {} > "$PASSDIR/{}.txt" 2>&1 || touch "$PASSDIR/{}.failed"'
fail=0
for i in $(seq "$n"); do
    cat "$out/$i.txt"
    [ -e "$out/$i.failed" ] && fail=1
done
exit $fail
