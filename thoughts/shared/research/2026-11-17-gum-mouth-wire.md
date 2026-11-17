---
date: 2026-11-17
topic: Wire gum-mouth v4 bird art into the game
branch: feature/gum-mouth-wire (from integ/beta1 0b02be0)
status: wired, gates in the final report
---

# Gum-mouth v4 wiring

## What changed
- Importer: `tools/import_gum_mouth_sheet.py` assembles `assets/flier/gum_mouth/frames_B.txt` (hand-typed grids, never redrawn) into `assets/flier/gum_mouth/sheet/{sheet.png,frames.json}`. It only shifts rows so the last art row lands on row 31, lays out the 12 clips and writes per-frame gum offsets. `tools/import_flier_sheet.py` (extended: extra palettes, extra tables) turns that into `assets/flier/sootling_sheet.{png,json}`, the same grid twice (player palette rows, cpu palette rows).
- Tiles: 304 -> 72 (`SOOTLING_TILE_COUNT 72`). Frames: 105 -> 69. Clips: 15 -> 12.
- Clips (first, count): flap 0/13, fly 13/12 loop, settle 25/15, idle 40/6 loop, pump 46/4, inflate 50/4, fall 54/2 loop, pop2 56/2, pop1 58/3, walk 61/2 loop, land 63/2, breathe 65/4 loop.
- `src/core/flier_view.[ch]`: new clip model. Constant blow loop is `fly`. A flap press plays `flap` (sheet ticks, restart on a press). A facing change in the air plays `settle` (rest_fl/rest_fr foot-lag frames); a press cuts it to `flap`. No balloons in the air uses `idle`. Ground, landing and breathing timing unchanged (walk/land/breathe hold knobs). `FLIER_FLAP_HOLD` removed (flap now uses sheet ticks).
- Landing blow-up: the `pump` clip replaces the old pump frames; `flier_pump_frame` spreads ARC_PUMP_STAGES over its 4 frames. Game logic unchanged.
- Gum placement: per-frame tables `SOOTLING_TABLE_GUM_DX/DY/SHOW` (src/core/gum_view.c). Bubble hidden in strain and burst frames. `GUM_BIRD_ROW 14`, `GUM_BIRD_DX 0`, `GUM_BIRD_DX_FLIP -1`.
- Gum Trip distress: `trip_view_distress(step)` (src/core/trip_view.c) maps the meter step to stage 0..3: step >= 5 healthy, 4 -> 1, 3 -> 2, <= 2 -> 3 (same steps as the warning blink). `set_distress` in src/main.c swaps the player palette slot for `sootling_extra_palettes[stage]`; reset to stage 0 on leaving Trip or a state change. Extra palettes: 0 = p2, 1..3 = distress1..3.
- Pupils look up at the gum; rest_fwd dropped (owner choice).
- Tests: test_flier_view.c rewritten for the new clips; test_gum_view.c reads the generated tables; test_trip_view_calc.c covers distress; knob_digest.c and knobs.txt follow the removed knob.

## Invented mappings (art has no frame for these)
- pop2, pop1, fall use strain/burst; inflate uses in/puff/blast/puff; pump and land use the stand poses; walk reuses stand_in/stand_puff (no walk art).
- Balloon-count variants collapsed: flap1/flap2 and fly variants are one clip each.
- Distress thresholds (steps 4, 3, <=2) are my choice.
- `GUM_BIRD_ROW 14` is a computed guess, not verified by eye.

## Not wired / not updated
- `tests/mame/flier_check.lua` (make target at Makefile:402) still checks the old 8-frame flap with FLIER_FLAP_HOLD. Not one of the three gates; will fail until rewritten for the 13-frame flap clip.
- `FlierAnim`/flier_view.h header comment and RULES.md "Flier art" line: see commits.
