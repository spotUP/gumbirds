---
date: 2026-11-14
topic: attract demo world and bonus result screen
status: blocked - test-vblank fails on the demo fix
---

# Attract demo world + bonus result screen

## Bug 1: attract demo shows only the overlay

- Violated invariant: the attract demo shows the game it steps (hero, camera, islands, hazards, gum, arcade elements) under the overlay.
- Root cause: src/main.c gated all world drawing and stepping on `view.state == FLOW_PLAYING`. The demo runs in FLOW_ATTRACT_DEMO (src/core/flow.c:154-170 steps the game), so the logic ran but hero_and_mode hid the hero, the camera stayed 0, and the world step functions got 0.
- Fix: `world_shown()` in src/main.c (PLAYING or ATTRACT_DEMO, with a game). hero_and_mode and the world steps (hazard_step, arcade_elems_step, arcade_bonus_step, island_step, trip steps, gum_step, splash_update) use it; hazard restart counts the demo as playing. bios_user_mode stays 1 in the demo (attract). Round banner, continue and sound stay PLAYING-only.
- Guard: tests/mame/attract_check.lua T4 reads the hero sprite (SCB3/SCB4 of slot 257) every demo frame; fails when the hero is shown on fewer than half the demo frames or moves fewer than 20 times.
- Revert proof (old src, new test): `FAIL T4 demo 1: no world under the overlay (hero shown 0 of 900 frames, moved 0 times)`.

## Bug 2: bonus result screen exits without a press

- Violated invariant: after the tally the result screen holds until A or Start.
- Root cause: src/core/result.c phase P_END ended the sequence on a timer; res_step had no input.
- Fix: `res_step(Result *, uint32_t *add, uint8_t press)`; P_END renamed P_WAIT and holds until press. src/core/game.c arc_interlude passes the A edge. src/main.c folds a Start edge (bios_statchange bit 0) into IN_A only while the result screen is up. No timeout: the attract demo never reaches a bonus stage.
- Guards: tests/host/test_result.c "the result screen waits for a press after the tally" (5000 frames without a press stays up, a press ends it, nothing more added); tests/mame/arcade_check.lua releases input to result frame 700, then presses A; fails "result screen exited without a press" or "ignored the A press".
- Revert proof (old src, new test): `FAIL result screen exited without a press after 217 frames (it must wait for A or Start)`.

## Counter digits

- Headless trace (RES_TRACE env in arcade_check.lua) of fix rows 4, 13, 19, 23 and the five wheel sprites over 701 result frames: every row decodes correctly. The SCORE row lags the score by exactly one frame (one dirty region per frame). The wheels roll the short way at 8 px/frame and the art frame tile matches the digit. No digit bug found in a non-perfect run (4 caught x 300).
- Likely the reported "buggy counter" was the screen leaving before the tally could be read. Not verified: a perfect run (ticket, 5-digit BONUS on row 23).
- Guard added: arcade_check.lua decodes row 19 on every result frame from frame 30 against col 19 (always '0') and fails "result SCORE row wrong" when it shows neither this frame's nor the previous frame's score.

## Gates (fixed code)

- build OK, host tests OK, test-attract PASS, test-arcade-bonus PASS (result 701 frames, +1200, logic end 211.6, 80 sprites per line), test-arcade PASS, test-trip PASS.
- **test-vblank FAIL** (log: thoughts/spot/2026-11-14-vblank-demo-fail.log). VRAM and palette writes outside vblank are 0, but the demo now overruns the frame: logic end 999 (commit inside the next vblank) on arena 420 of 900, arcade 66 of 150, trip 17 of 900 demo frames; flush max 2000 us. Overrun buckets: bg_near/mida/midb/far scb, island scb. Old code passed because the demo drew nothing.

## Open: demo frame overrun (not root-caused)

- The same world drawing fits in PLAYING (test-arcade 216.3, test-trip 209.0, vblank play classes pass), so something demo-only costs about a frame. Not measured yet. Candidates: the draw() path in FLOW_ATTRACT_DEMO (HUD, overlay), the hero_and_mode demo branch, and the demo camera (constant left/right sweep) making bg_update and island_step heavier than in the play runs.
- Next step: per-function line markers in the arena demo (vblank_check queue-side bucket lines for class demo) to find the frame-long item. Do not merge before this is fixed.

## Risks

- Start folds into IN_A only on the result screen; player_start refuses Start during play, so no credit is taken.
- Demo bios_user_mode stays 1.
