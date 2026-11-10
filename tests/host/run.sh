#!/bin/sh
# Host tests for the Bubblegum Brawl core. Usage: tests/host/run.sh
# Output goes to build/test-host (override with BRAWL_TEST_OUT); only a summary is printed.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
OUT=${BRAWL_TEST_OUT:-$ROOT/build/test-host}
mkdir -p "$OUT"
CC="nice -n 19 clang -I $ROOT/build -std=c99 -Wall -Wextra -Werror -pedantic"
SRC="$ROOT/src/core/rng.c $ROOT/src/core/game.c $ROOT/src/core/hiscore.c $ROOT/src/core/nameentry.c $ROOT/src/core/flow.c $ROOT/src/core/obstacle_view.c $ROOT/src/core/bg_scroll.c $ROOT/src/core/vram_queue.c $ROOT/src/core/obj_pool.c $ROOT/src/core/sound_queue.c $ROOT/src/core/sound_events.c $ROOT/src/core/flier.c $ROOT/src/core/stage.c $ROOT/src/core/island_layout.c $ROOT/src/core/ai.c $ROOT/src/core/flier_view.c $ROOT/src/core/sprite_budget.c $ROOT/src/core/camera.c"
fail=0
# test_flier_view reads the generated Sootling tables
(cd "$ROOT" && gmake -s build/gen/sootling_tables.h build/gen/city_tables.h build/gen/island_tables.h build/gen/fix_font.h >"$OUT/gen.log" 2>&1) || { echo "[ERROR] gen sootling_tables.h failed"; tail -n 5 "$OUT/gen.log"; exit 1; }

$CC -o "$OUT/test_core" "$HERE/test_core.c" $SRC >"$OUT/build.log" 2>&1 || { echo "[ERROR] build failed"; tail -n 20 "$OUT/build.log"; exit 1; }
nice -n 19 "$OUT/test_core" >"$OUT/test_core.log" 2>&1 || fail=1
tail -n 1 "$OUT/test_core.log"; grep FAIL "$OUT/test_core.log" | head -n 10

$CC -o "$OUT/test_flow" "$HERE/test_flow.c" $SRC >"$OUT/build.log" 2>&1 || { echo "[ERROR] flow build failed"; tail -n 20 "$OUT/build.log"; exit 1; }
nice -n 19 "$OUT/test_flow" >"$OUT/test_flow.log" 2>&1 || fail=1
tail -n 1 "$OUT/test_flow.log"; grep FAIL "$OUT/test_flow.log" | head -n 10

$CC -o "$OUT/test_bg" "$HERE/test_bg.c" $SRC >"$OUT/build.log" 2>&1 || { echo "[ERROR] bg build failed"; tail -n 20 "$OUT/build.log"; exit 1; }
nice -n 19 "$OUT/test_bg" >"$OUT/test_bg.log" 2>&1 || fail=1
tail -n 1 "$OUT/test_bg.log"; grep FAIL "$OUT/test_bg.log" | head -n 10

$CC -o "$OUT/test_sound_queue" "$HERE/test_sound_queue.c" $SRC >"$OUT/build.log" 2>&1 || { echo "[ERROR] sound_queue build failed"; tail -n 20 "$OUT/build.log"; exit 1; }
nice -n 19 "$OUT/test_sound_queue" >"$OUT/test_sound_queue.log" 2>&1 || fail=1
tail -n 1 "$OUT/test_sound_queue.log"; grep FAIL "$OUT/test_sound_queue.log" | head -n 10

$CC -o "$OUT/test_vram_queue" "$HERE/test_vram_queue.c" $SRC >"$OUT/build.log" 2>&1 || { echo "[ERROR] vram_queue build failed"; tail -n 20 "$OUT/build.log"; exit 1; }
nice -n 19 "$OUT/test_vram_queue" >"$OUT/test_vram_queue.log" 2>&1 || fail=1
tail -n 1 "$OUT/test_vram_queue.log"; grep FAIL "$OUT/test_vram_queue.log" | head -n 10

$CC -o "$OUT/test_flier_view" "$HERE/test_flier_view.c" $SRC >"$OUT/build.log" 2>&1 || { echo "[ERROR] flier_view build failed"; tail -n 20 "$OUT/build.log"; exit 1; }
nice -n 19 "$OUT/test_flier_view" >"$OUT/test_flier_view.log" 2>&1 || fail=1
tail -n 1 "$OUT/test_flier_view.log"; grep FAIL "$OUT/test_flier_view.log" | head -n 10

$CC -o "$OUT/test_sprite_budget" "$HERE/test_sprite_budget.c" $SRC >"$OUT/build.log" 2>&1 || { echo "[ERROR] sprite_budget build failed"; tail -n 20 "$OUT/build.log"; exit 1; }
nice -n 19 "$OUT/test_sprite_budget" >"$OUT/test_sprite_budget.log" 2>&1 || fail=1
tail -n 1 "$OUT/test_sprite_budget.log"; grep FAIL "$OUT/test_sprite_budget.log" | head -n 10

$CC -o "$OUT/test_obj_pool" "$HERE/test_obj_pool.c" $SRC >"$OUT/build.log" 2>&1 || { echo "[ERROR] obj_pool build failed"; tail -n 20 "$OUT/build.log"; exit 1; }
nice -n 19 "$OUT/test_obj_pool" >"$OUT/test_obj_pool.log" 2>&1 || fail=1
tail -n 1 "$OUT/test_obj_pool.log"; grep FAIL "$OUT/test_obj_pool.log" | head -n 10

$CC -o "$OUT/test_flier" "$HERE/test_flier.c" $SRC -lm >"$OUT/build.log" 2>&1 || { echo "[ERROR] flier build failed"; tail -n 20 "$OUT/build.log"; exit 1; }
nice -n 19 "$OUT/test_flier" >"$OUT/test_flier.log" 2>&1 || fail=1
tail -n 1 "$OUT/test_flier.log"; grep FAIL "$OUT/test_flier.log" | head -n 10
$CC -o "$OUT/test_stage" "$HERE/test_stage.c" $SRC -lm >"$OUT/build.log" 2>&1 || { echo "[ERROR] stage build failed"; tail -n 20 "$OUT/build.log"; exit 1; }
nice -n 19 "$OUT/test_stage" >"$OUT/test_stage.log" 2>&1 || fail=1
tail -n 1 "$OUT/test_stage.log"; grep FAIL "$OUT/test_stage.log" | head -n 10
$CC -o "$OUT/test_ai" "$HERE/test_ai.c" $SRC -lm >"$OUT/build.log" 2>&1 || { echo "[ERROR] ai build failed"; tail -n 20 "$OUT/build.log"; exit 1; }
nice -n 19 "$OUT/test_ai" >"$OUT/test_ai.log" 2>&1 || fail=1
tail -n 1 "$OUT/test_ai.log"; grep FAIL "$OUT/test_ai.log" | head -n 10

$CC -o "$OUT/test_arena" "$HERE/test_arena.c" $SRC >"$OUT/build.log" 2>&1 || { echo "[ERROR] test_arena build failed"; tail -n 20 "$OUT/build.log"; exit 1; }
nice -n 19 "$OUT/test_arena" >"$OUT/test_arena.log" 2>&1 || fail=1
tail -n 1 "$OUT/test_arena.log"; grep FAIL "$OUT/test_arena.log" | head -n 10
$CC -o "$OUT/test_camera" "$HERE/test_camera.c" $SRC >"$OUT/build.log" 2>&1 || { echo "[ERROR] test_camera build failed"; tail -n 20 "$OUT/build.log"; exit 1; }
nice -n 19 "$OUT/test_camera" >"$OUT/test_camera.log" 2>&1 || fail=1
tail -n 1 "$OUT/test_camera.log"; grep FAIL "$OUT/test_camera.log" | head -n 10

# Island sprite set: importer + pipeline per look, tile/palette/alignment/overlap checks (needs build/gen/*_sprites.h from gmake)
PYTHON=${PYTHON:-/opt/homebrew/bin/python3.14}
(cd "$ROOT" && nice -n 19 "$PYTHON" -I tests/host/test_islands.py >"$OUT/test_islands.log" 2>&1) || fail=1
tail -n 1 "$OUT/test_islands.log"; grep -E 'FAIL|ERROR' "$OUT/test_islands.log" | head -n 10

# Knob completeness: every #define in tuning.h (except documented exemptions) has an override.
# Exemptions: STAGE_ / FLIER_START_ are layout and spawn constants (stage.c table, game_reset).
defs=$(grep '^#define [A-Z_]* ' "$ROOT/src/core/tuning.h" | awk '{print $2}' | grep -v -e '^SCREEN_W$' -e '^SCREEN_H$' -e '^STAGE_' -e '^FLIER_START_' | sort)
listed=$(awk '{print $1}' "$HERE/knobs.txt" | sort)
if [ "$defs" != "$listed" ]; then echo "[ERROR] knobs.txt does not match tuning.h"; fail=1; fi

$CC -o "$OUT/knob_base" "$HERE/knob_digest.c" $SRC >"$OUT/build.log" 2>&1 || { echo "[ERROR] knob build"; tail -n 20 "$OUT/build.log"; exit 1; }
base=$("$OUT/knob_base")
n=0; bad=0
while read -r name val; do
    n=$((n + 1))
    $CC -D"$name=$val" -o "$OUT/knob_var" "$HERE/knob_digest.c" $SRC >"$OUT/build.log" 2>&1 || { echo "[ERROR] knob $name build"; tail -n 5 "$OUT/build.log"; bad=$((bad + 1)); continue; }
    d=$("$OUT/knob_var")
    if [ "$d" = "$base" ]; then echo "[FAIL] knob $name=$val does not change output"; bad=$((bad + 1)); fi
done < "$HERE/knobs.txt"
echo "knobs: $n checked, $bad failed"
[ "$bad" -eq 0 ] || fail=1
rm -f "$OUT/knob_var" "$OUT/knob_base"
if [ "$fail" -eq 0 ]; then echo "[OK] all host tests passed"; else echo "[FAIL] host tests failed"; fi
exit $fail
