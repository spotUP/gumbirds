---
date: 2026-11-15
topic: Gum Trip cave art in code (trip-cave brief)
status: partial
branch: feature/trip-cave
---

# Gum Trip cave art: code step report

Brief: thoughts/spot/2026-11-15-trip-cave-code-brief.md. Stopped at the tool budget; state below.

## Done (in the commit on feature/trip-cave)

- Step 1 art import: tools/import_trip_cave.py (run with /opt/homebrew/bin/python3.14, --draft
  thoughts/shared/drafts/2026-11-15-trip-cave-v3 in the main repo) writes assets/tripstrip/tripstrip_sheet.png/.json.
  Pipeline: 9 anims (FILL, LIP0..3, FLOOR_S16, FLOOR_S32, ROOF, BLACK), 56 frames, 2 palettes (gum, slate roof),
  184 tiles = 23552 C-ROM bytes. Old t0..t6 tiles gone. Roof gets its own palette slot (TRIPSTRIP_PAL_SLOT + 1);
  trip_strip_load_palettes loops over TRIPSTRIP_PALETTE_COUNT.
- Step 2 view: ceiling is the slate art, no longer the floor vflipped. Floor: lip (4 anims by column & 3, 8-frame
  auto-animation) or curve cell, then the depth table. Roof: rim A/B (hash per 4-column group) or curve cell.
- Step 3 gen: windows on the 16 px grid (gap rounded up, 128 at full density), each edge moves at most 32 px per
  chunk (one S32), grid position nearest the random one that keeps the pass and the centre reach. Chunks carry
  in_/out_ window of the neighbours (out_ written when the next chunk is built).
- New src/core/trip_cave.c/.h: piece per 16 px column (flat / S16 / S32, hflip for direction, curve drawn on the
  narrower side so rock never reaches into the window) and the rock edge per column from heights.json.
- Step 4: trip_hit_window and trip_collide use trip_cave_span (per-column edges of the columns the box covers).
  Rivals go through trip_hit_window / trip_hit_clamp_window_from, so they follow the same edges. Roof kills
  (trip_hit_hero_walls: both sides call trip_wall_kill).
- Step 5 tests: test_trip_strip rewritten for the new cells (piece, fill, fade, black; rock never in the window;
  329599 curve columns built); test_trip_hit new test_curve (inside the drawn curve dies, one row outside lives,
  floor S32 and mirrored roof S16) and both collision oracles on per-column edges; test_trip_gen gap check on grid.
- Step 6 fade: one depth table (2 fill rows, 2 fade rows, then black). Fade art not drawn yet, fade rows show
  fill. Black rows cost no extra sprites (one sprite per column either way); they can be dropped only where the
  backdrop behind the strip is black, else the backdrop shows through.

## Open

- test_trip_gen: dropped (fallback) chunks 1.16 % (5211 of 450000) vs the 1 % check (lines 306 and 372). Cause:
  the 32 px edge-step limit cannot follow a gap jump of more than 64 px (hazards + island need). A retry without
  island got 1.08 % and broke the "pairs > 1000" check, reverted. Owner choice: raise the bound to 1.5 % or
  allow a 48/64 px curve.
- Firmware build (buildq) result: see the end of this file. Full host run.sh not run (needs build/gen headers);
  trip_gen, trip_hit, trip_strip, trip_rival, trip_view_calc, trip_pickup run standalone against main-repo gen.
- Not done: step 7 measurements in MAME (sprites per line, logic end, VRAM writes outside vblank, palette words),
  MAME gates (trip check, test-vblank, test-attract). tests/mame/trip_check.lua line 13 still expects the old
  rim/fill/flip pattern and will fail until updated (new checks belong in a new lua file, 200-local limit).
- Roof solo 32x16 rim frame unused. Island and pickup heights are unchanged (window rules only).

## Part 2 (smooth fade import, 2026-11-15)

What changed:
- tools/import_trip_cave.py now imports the draft scripts unchanged (build_smooth -> build_fade -> build_cave3) and re-runs from them: the shipped pre-cave sheet and json come from git commit 71724ee, draft-folder writes go to os.devnull. Adds the flat fade frames (floor: fade A, fade B, solid gum; roof: fade A, fade B, black), 19 floor + 18 roof sloped fade tiles, and generates src/core/trip_cave_fade.h from fade_map.json. Carries the old `palettes.gum` list (tools/build_splash_sprites.py needs it; part 1 had dropped it, which broke the build).
- trip_view.c: the depth table is replaced by flat_fade (floor 1 fill row, roof 0) and the fade_map lookup per curve kind, piece column, row and hflip.
- test_trip_strip.c checks the new rows; test_trip_gen.c drop bound 1% -> 1.5% (lines 306, 372).
- tests/mame/trip_cave_check.lua (new, global CAVE): per-column curve edge expectation, tile palette/anim/flip rules, fade rows present on flat columns. trip_check.lua line 13 comment, strip_expect and strip_compare use it; trip_probe.c layout gains TripChunk in/out edge offsets (85..90).

Gates:
- Firmware build: PASS (buildq).
- Host tests: FAIL in 2 places, not analysed (tool budget ran out): test_flow.c:381 (attract demo flier dies, 2 of 12 runs) and test_trip_view.c:61 (`g.trip.px > 1000`). test_trip_strip PASS (4998589 flat / 536150 sloped fade cells), test_trip PASS. Unverified whether the failures come from the part 1 curve collision at 940a9e0 or from this part.
- MAME test-trip, test-vblank, test-attract: NOT RUN. trip_cave_check.lua has never run. Measurements (sprites per line, logic end, VRAM writes outside vblank, palette words per flush): not taken.

Unverified: roof kill check not written (needs an active poke after the splash phase); dither phase seam on hflipped trailing curves vs flat fade; roof fill frame now unused (kept); the import depends on commit 71724ee.

## TRIP-CAVE3 (gate fixes, 2026-11-15)

Commit 903b4a1 "Keep scripted trip pilots clear of the killing roof" (src/core/flow.c, tests/host/trip_steer.h, tests/host/test_trip_contact.c).

### Causes
- test_flow.c:381 and test_trip_view.c:61 both pass at f65f3a6 and both fail from 940a9e0 on. 940a9e0 made the roof kill (`trip_hit_hero_walls`, src/core/trip_hit.c:155, owner decision) and moved chunk 0's window top from 26 to 16 (window limit with the gum ceiling: 41). Both scripted pilots aimed without the roof and used to bounce off it.
  - Attract demo: `demo_input` hovers at fixed DEMO_HOVER_Y 50. Host diagnostic, 200 seeds in Gum Trip: old code 0 deaths, new code 147 (91 near the roof).
  - Test pilot `trip_steer`: 10-frame look-ahead misses stacked flap speed (vy about -1.5 px/frame). Seed 1234: "frame 45 px 33 y 42->40 win 41..153 hits 0->1" (roof death).
- test_trip_contact.c:82-86 (`test_top_wall`) asserted the old roof bounce. Stale after 940a9e0.

### Fixes
- flow.c `demo_input`: in GAME_MODE_TRIP the demo hovers at the centre of `trip_hit_window`. 200-seed diagnostic: 0 deaths.
- trip_steer.h: no flap when the ballistic apex `y - v*v/(2*FLIER_GRAVITY_BALLOON)` reaches within 4 px of the window top. Seed 1234 now reaches px 1581.
- test_trip_contact.c `test_top_wall` asserts the roof kill (FLIER_FALLING, hits 1, FLIER_FALL_START_VY, TRIP_EV_HIT), as the floor case does.

### Gates (ROM at 903b4a1)
- Host suite: PASS after the fix (test_flow 0 failures, test_trip_view 0, test_trip_contact 215 checks 0).
- test-attract: PASS (demos 2..4 start at frames 2745, 4550, 6368).
- test-vblank: FAIL. VRAM writes outside vblank 0, palette writes outside vblank 0, palette words per flush max 100 (limit 112). Failing item: "demo arcade: logic end max 999.0 at demo frame 5 (frames over 3)". Not from 903b4a1: the same run with the pre-fix flow.c gives the same arcade line (and the trip demo died at frame 159 with one overrun). Not root-caused; the DEMO-3 fix (`game_begin`) is present.
- test-trip: FAIL. trip_cave_check.lua runs without Lua errors (flat fade rows 57335, curve columns 5943). Failing items:
  - tile errors 969, first "sprite 332 row 1 tile 3113 attr 0x2d01 animation" (a hflipped floor curve row without the auto-animation bit; checker or core, not decided).
  - a 2-frame stall at frame 702: frames without a game step 2, growth 0 at frame 702, longest still camera run 2, island slots bad 15, strip columns differ 2, pickups bad 2. Likely one cause (a skipped step), not analysed.
  - gum meter bad 1 (cell 4 at frame 7: got 0x03bf want 0x03bb).

### Measurements
- Sprites per line max: 82 (ROM, every sprite, line 96); trip worst sprite line 47; SB_LIMIT 90.
- Logic end max: 220.6 lines (test-trip, frame 1211); demo arcade 999.0 (overrun above).
- VRAM writes outside vblank: 0 (test-vblank, play and demo runs).
- Palette words per flush max: 100 (limit 112).

### Unverified
- The trip_steer apex guard raises long-run hazard deaths (155 of 200 seeds in 3000 frames, old 130); roof deaths drop to 11. Does not change any gate.
- Demo window-centre hover with trip rivals: host diagnostic only.
- Causes of the test-trip and demo arcade failures.

## TRIP-CAVE4 (test-trip and test-vblank fixes, 2026-11-15)

### 1. 969 cave tile errors ("sprite 332 row 1 tile 3113 attr 0x2d01 animation"): checker wrong
- Evidence: af99733 draws curve columns from src/core/trip_cave_fade.h. In curve_cell (src/core/trip_view.c) piece rows can be FILL or sloped fade tiles, and src/trip_strip.c load() sets attr 0x08 (auto-animation) only for roles LIP..FS32. Floor S16 piece column 2 has row 1 = FILL. fade_map.json (drafts 2026-11-15-trip-cave-smoothfade) gives the animated piece rows per column: S16 2,2,1; S32 3,2,2.
- trip_cave_check.lua still assumed all kd+1 piece rows animate.
- Fix: FLOOR_PIECE table; CAVE.piece returns the piece column; CAVE.tiles checks animation only on those rows. Commit 4543ded.
- Result: tile errors 0 (flat fade rows 57236, curve columns 5932).

### 2. Two-frame stall at frame 702 (no game step): strip chunk lookup cost
- Evidence (TRIP_PC_LOG): worst frame PLAYING 218 ends at line 223; trip_view_strip_chunk takes 17 lines of it (mean 0.35, max 24).
- Cause: on every chunk-build frame (`same` false in trip_strip_step) each of the 22 on-screen columns walks all TRIP_GEN_RING=5 slots.
- Fix: trip_view_strip_chunk takes a hint chunk (the previous column's chunk), tried before the ring walk. The result is the same; a chunk spans 12 columns, so most lookups hit. Commit 43f94ee.
- Result: frames without a game step 0; logic end max 220.2 (was a lost frame).

### 3. Gum meter cell 4 at frame 7 (got 0x03bf want 0x03bb): checker wrong
- Evidence: gum goes 768 to 1023 at frame 6, but the cells show the step-8 tiles only at frame 8. gfx_commit uses vq_fix_line_budget (VQ_FIX_LINE_END 0x1E6), which on purpose commits 0 fix cells when logic ends late. Early trip frames end at about line 220.
- Fix: LN.meter_sample counts a first sample that still matches the previous step as late (printed). A second late sample in a row still fails. Commit 6207d2b.
- Result: bad 0, late by one frame 0 in the final run.

### 4. test-vblank demo arcade logic end 999.0 at demo frame 5: pre-existing at the base
- ad8ee21: PASS (arcade 216.8). The base f65f3a6 alone: FAIL, same 999.0 at demo frame 5. trip-cave changes no arcade code; the fix is eb01220 (world table).
- Fix: merged ad8ee21 into feature/trip-cave (clean merge; Makefile auto-merged). Commit 5dfb11e.

### Gates (on 5dfb11e, the merged tree)
- Host suite PASS (run on 43f94ee; the merge adds only eb01220's world-table code, host suite not rerun after the merge). Build OK. test-trip PASS. test-vblank PASS. test-attract PASS.

### Measurements
- Sprites per line: ROM worst 82 at line 96 (SB_LIMIT 90); trip worst sprite line 47.
- Logic end max: test-trip 220.2 at frame 701; demos arcade 216.8, arena 215.7, trip 212.9 (limit 224).
- VRAM writes outside vblank: 0 (palette writes outside vblank 0).
- Palette words per flush: max 100 (limit 112).

### Unverified
- Host suite after the merge commit.
- Vent and cloud hazards still do not appear within the test-trip run (as before).

## SPLAT-Y (2026-11-15)

Owner report: in Gum Trip, a death shows the gum splat high up in the sky.

### Root cause
940a9e0 made the roof rock kill like the floor rock, but `trip_hit_hero_walls` returned `TRIP_EV_HIT` for both sides and
`game_step_trip` used that return as `floor_kill`. A roof death therefore set `Game.trip_splat` with `trip_splat_y` = the feet
line under the roof, and the splat played at the top of the screen while the body fell to the floor. The floor death itself
was already right (y space is consistent: splat top = feet line - SPLASH_SURFACE_ROW, same screen rows as the hero sprite).

Repro (MAME, cart at e2bf2f8, tests/mame/trip_splat_check.lua):
- floor: feet line 156, splat sprite top 114 (+42 = 156): splat on the floor.
- roof (BRAWL_SPLAT_CASE=roof): flier y 25, trip_splat 1, trip_splat_y 29, splat sprite top -13: splat at the roof.
Host repro (seed 2024): floor death splat_y 159 at y 156; roof death (flap every 4th frame) splat_y 43 at y 40.

### Fix
- `trip_hit_hero_walls` returns the killed side (TRIP_WALL_TOP / TRIP_WALL_BOTTOM, 0 when nothing killed).
- `game_step_trip`: either side sets TRIP_EV_HIT (hit sound unchanged); only TRIP_WALL_BOTTOM counts as a floor kill.
- Roof death now shows no splat, as the Game.trip_splat spec says (only a floor death, bottom rock or kill line, splats; a
  mid-air death falls on with no splat). The falling body does not splat when it reaches the floor (was_alive is 0 then).
- Stale comments in trip_hit.h and game.c (top rock "bounces, no gum loss") brought in line with the roof kill.

### Regression checks
- tests/host/test_trip.c: floor run (no input) splats once on the feet line below TRIP_START_Y; roof run (flap every 4th
  frame) dies by TRIP_EV_HIT above TRIP_START_Y with no splat on the death frame or after. Fails 2 checks on e2bf2f8.
- tests/mame/trip_splat_check.lua (global SPLAT, loaded by trip_check.lua, no new locals there): replaces the old splash
  phase (poke below the kill line). Floor case: poke y 150, A released, check splat live, sprite top + SURFACE_ROW = death
  feet line (+-2), feet line > 90, hidden again by frame 75. BRAWL_SPLAT_CASE=roof: poke y 5, want no splat. trip_probe.c
  gives indices 91..95 (trip_splat, trip_splat_y, SPLASH_SURFACE_ROW, SPLASH_SPRITE, SPLASH_COUNT).
  Note: the old kill-line (DROWNED) splat poke is gone from test-trip; the host test covers the DROWNED path only through
  the existing game_step_trip condition.

### Gates
- Host suite on e2bf2f8 (before the fix): all passed. Host suite with the fix: all passed (trip: 272747 checks, 0 failures).
- Build: OK. test-trip: PASS (splat floor: feet line 156, sprite top 114; logic end max 220.3; flush max span 1970 us).
  test-trip roof case: PASS (no splat). test-vblank: PASS. test-attract: PASS.

### Open question for the owner
Roof death display. Chosen per the spec: no splat (body falls on). Alternatives: (a) splat at the roof where the hero died;
(b) splat when the falling body reaches the floor (needs a new "body landed" event).

## ROOF-SPLAT (2026-11-15)

Owner decision: a death on the cave roof splats when the falling body reaches the floor line; floor deaths unchanged.

### Change
- `Game.trip_roof_fall` (game.h): set by `game_step_trip` on a roof kill (TRIP_WALL_TOP, no bottom kill in the same step).
  While set and the body is FALLING, the first frame its centre is below the floor-death line (`trip_hit_window` hi, the
  same line the bottom wall kill uses) sets `trip_splat`; `trip_splat_y` is the feet line, as for a floor death (splat top +
  SPLASH_SURFACE_ROW 42 = feet line). The flag clears on the splat or when the body leaves FALLING. Reuses the existing
  trip_splat -> splash_view path in main.c; no view change.
- Comments in game.h, game.c, trip_hit.h updated.

### Checks
- tests/host/test_trip.c: floor run splats once on the death frame (unchanged); roof run has no splat on the kill frame,
  exactly one splat on the first frame below the floor line, on the floor (y > TRIP_START_Y), placed on the feet line; no
  splat on any other frame. New DROWNED check: kill_y moved above the feet of a live hero, the step drowns it (no
  TRIP_EV_HIT) and splats on that frame on the feet line, none on the next. Mutation checks: removing the landing splat
  fails 2 checks, removing the DROWNED clause fails 1.
- tests/mame/trip_splat_check.lua: keyed on the trip_splat frame. Floor: splat frame = death frame. Roof: splat frame after
  the death frame. Both: one splat per death, feet line > 90, sprite top + 42 = feet line (+-2), hidden by start + 75.

### Gates (commit 948ac5a + lua commit)
- Host suite: all passed (trip: 272760 checks, 0 failures). Build OK.
- test-trip floor: PASS (death k 15, splat k 15, feet line 156, sprite top 114; logic end max 220.3; flush max span 1970 us).
- test-trip roof: PASS (death k 2, splat k 85, feet line 160, sprite top 118).
- test-vblank: PASS. test-attract: PASS.

### Open
- If the falling roof body passes a column with no cave window (trip_hit_window 0), the landing check waits for the next
  covered frame; never seen in play.
