---
date: 2026-11-10
topic: flier arena slice wiring
status: implemented, uncommitted
---

# Flier arena slice: wiring

Runner hero replaced by the flier core (src/core/flier.[ch]) in PLAYING. Spec: 2026-11-09_flier-reference-spec.md.

## Changed per file
- src/core/tuning.h: STAGE_PLATFORM_COUNT 8, STAGE_PLATFORM_H 8, FLIER_START_X 160, FLIER_START_Y 120, FLIER_START_BALLOONS 2.
- src/core/stage.[ch] (new): const table `stage_platforms[8]`, `stage_floor_y(x16, feet16)` (highest platform top at or below the feet overlapping x +- FLIER_HALF_W, else FLIER_NO_FLOOR; solid from above only). Update 2026-11-11: the platform body is also solid; stage_solids_near + flier_collide_solids bounce a flier off undersides and sides, stage_floor_y stays the floor line only.
- src/core/game.[ch]: Game gains `Flier flier; uint32_t flier_steps` (the sentinel). game_reset inits the flier (no parachute). New `game_step_arena`: A = flap, left/right = dir, `flier_step` with the stage floor, `flier_steps++`; over when state >= DROWNED (DROWNED or GONE); score = survival distance + bonus. Old runner `game_step` kept for legacy host tests.
- src/core/flow.c: demo and PLAYING call game_step_arena.
- src/main.c: hero sprite follows the flier (runner frames as placeholder; hidden when GONE or below screen); one OB_VENT pool object per platform (`pool_sync_stage`); lasers hidden in play; HUD "Balloons N" (fix layer); city stays still (bg_update(0, ...)).
- Makefile: CORE_SRCS + flier stage; `test-flier` target, added to `test`.
- tests/host: run.sh (stage.c in SRC, test_stage run, exemptions), test_stage.c (new), test_flow.c, knob_digest.c, knobs.txt.
- tests/mame: flier_probe.c, flier_check.lua (new); reach_probe.c, hiscore_reach.lua, unibios_check.lua (autoplay rewritten for the flier).

## Stage layout (x, y top, width; height 8; water y=180 kills)
(0,164,64) (256,164,64) (112,140,96) (24,104,64) (232,104,64) (120,72,80) (0,40,48) (272,40,48).
Start (160,120) falls onto the middle island (112..208, top 140). Gaps between islands are over water.

## Sentinel and test
`Game.flier_steps` counts flier_step calls. flier_check.lua: coin, start, settle on island, 8 A edges (y must rise > 4 px), walk off right edge, steer back over the gap with left+flap until vx<=0, drop. Asserts flow GAME_OVER, flier state DROWNED, y near 180, over==1, flier_steps >= 100 and within 3 of game-loop frames in PLAYING.

## Results (each run individually)
- tests/host/run.sh: [OK] all host tests passed (test_flow 36172 checks, stage 30, flier 2107, knobs 58 checked, 0 failed).
- gmake test-flier: PASS flier rose 29.2 px after 8 flaps, drowned at y 174.6, flow GAME_OVER, flier_steps 458 of 460 frames, score 114.
- gmake test-unibios: PASS (second phase now steers the flier into the water).
- gmake test-reach: PASS boot 1 saved 'REACHTST' 1251 at row 9; boot 2 table row 9 matches.
- Fail-when-bypassed: with the flier_step call in game_step_arena commented out, test-flier gave `FAIL flier never landed on the island`, rc=2. Restored; test-flier passes again.

## Old tests that now fail (not fixed, per brief)
- test-laser: no result from Lua script; needs runner obstacles and laser, absent in play.
- test-hit: no result; same runner autoplay and hit assumptions.
- test-scroll: FAIL PLAYING frames 3259, checked 3257, late scroll frames 0 ...; city is still in play so the scroll chain assertion no longer holds.
- test-sound: no result; script drives jump (B) and fire, not present in the arena.
- test-vblank: PASS.

## Host-test notes
- test_flow and knob_digest teleport the flier over the gap (x 100) and set `game.bonus` so a run ends in game over and ranks for name entry (survival score alone stays under the table minimum 1000).
- Knob exemptions (written in run.sh): STAGE_*, FLIER_START_* (layout/spawn constants); DEMO_JUMP_ODDS, DEMO_DUCK_ODDS, DEMO_DUCK_FRAMES (removed from knobs.txt; they drive runner-only IN_B/IN_C demo inputs the arena ignores).
- knob_digest.c gained a KNOB_DEBUG stderr print (off by default).

## Open issues
- Platform art is one OB_VENT object per platform (placeholder).
- Attract demo holds A only, so the flier sits on the island until the demo timeout; demo does not exercise the flier.
- Score is survival time while the city is still; legacy runner game_step stays only for host tests.
- Runner-only demo knobs are dead (exempted above); lives unused in the HUD.
- Flier x is not clamped to platform edge art.
- cfg/neogeo.cfg shows modified in git status; written by MAME runs, not edited by hand.
- old laser/hit/scroll/sound tests need retiring or rewriting (second agent).

## Runner test retirement

Done 2026-11-10 (uncommitted). The runner tests are retired or re-pointed at the flier.

Deleted: tests/mame/laser_check.lua, check_laser_pixels.py, laser_probe.c, hit_check.lua, check_obstacle_pixels.py, layout_probe.c. Makefile targets test-laser and test-hit removed (also from `test` and .PHONY, plus the obstacle pixel call and BRAWL_OBS_LAYOUT).

Changed:
- src/core/game.[ch]: new `Game.flaps` counter, bumped on a flap press edge while the flier lives.
- src/core/sound_events.[ch], src/sound.c: SE_JUMP, SE_HIT, SE_LASER removed. New SE_FLAP (0x01) fires when `flaps` grows and plays the old jump sample. SFX files and the ids hit/laser stay in SFX_NAMES in the Makefile.
- src/core/flow.[ch], tuning.h: demo input flaps to hold DEMO_HOVER_Y and sweeps left/right every DEMO_SWEEP_FRAMES. Old DEMO_JUMP_ODDS, DEMO_DUCK_ODDS, DEMO_DUCK_FRAMES and `duck_left` removed.
- tests/host: knobs.txt (DEMO_HOVER_Y, DEMO_SWEEP_FRAMES; both move the digest), run.sh (old exemption removed), knob_digest.c (mixes flaps and flier x/y), test_sound_queue.c.
- tests/mame: scroll_check.lua asserts a still city (scroll triple constant on every PLAYING frame); the g_bg_rebases sentinel is dropped because bg_update gets distance 0 forever. sound_check.lua expects coin, music, flap, stop, game over. New flier_drive.lua (shared walk-off-and-drown input, used by scroll and sound checks, layout via BRAWL_FLIER_LAYOUT in the Makefile). boot_check.lua lost the obstacle snapshot. check_hero_pixels.py now boxes the flier spawn; the pre-start bound is dropped because the attract demo flies the flier (pre-start count is reported only).
- RULES.md: Test, Flier, Scroll, Sound lines updated.

Results: see the final test run in the session report (host, flier, reach, vblank, scroll, sound, boot/pixels).

Dead runner code left: legacy game_step with obstacle, laser and duck logic; CORE_SRCS obstacle_view and laser_view; obstacle and heat sprite pipelines and assets; hit_probe.c (now only a flow-offset probe); unused Flow.demo_rng; Game.shots, Game.hits; HUD lives; Makefile comments and RULES.md Sprites line that still mention obstacles. The earlier open issues about broken old tests and the demo holding A only are resolved.
