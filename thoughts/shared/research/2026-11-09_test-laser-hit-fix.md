---
date: 2026-11-09
topic: make test-hit / test-laser failures - root cause is a 30 Hz main loop
tags: [test, mame, performance, vblank, hit, laser]
status: resolved
---

# test-hit / test-laser fix attempt

## Result

- make test-hit: FAIL (not re-run after the perf changes; root cause below is not fixed yet).
- make test-laser: not run (same root cause expected to shift its timeline; fix this first).
- make test-vblank: FAIL now, by the new frame-step assertion (intended regression check).
  Before any change: 627 of 1245 PLAYING frames without a game step. After the two fixes below: 391 of 1009.
- Host tests (tests/host/run.sh): PASS.
- Rest of make test: not run.

## Root cause

Violated invariant: the game loop must do exactly one game step per video frame (60 Hz). It does one step
every two frames: measured g_frame_counter advances 30 per 60 MAME frames, in TITLE and in PLAYING alike
(Lua probe reading g_frame_counter every frame end). The frame logic (plus the vblank IRQ: BIOS + flush,
flush budget 2000 us is always used up) takes longer than one frame, so the main loop misses every second
vblank. The vblank agent's "no longer overruns" was about VRAM writes landing in vblank, not about frame rate.

test-hit failure follows directly: INVULN_FRAMES (120) and HIT_POSE_FRAMES (10) are game steps, the Lua
check counts MAME frames. At MAME frame INVULN+6 after the hit invuln is still 58 and the hero is in a
hidden blink phase (anim 0xFFFF); "other 8" is the HIT pose lasting 20 MAME frames instead of 10. The
sentinels are written correctly (src/main.c hero_hide / hero_pick_frame); the test's 60 Hz assumption is the
game's design, so the fix belongs in the game (frame cost), not in hit_check.lua.

test-laser: its fixed frame counts also assume 60 Hz; re-check after the loop runs at 60 Hz before rewriting
it to the sentinel-driven timeline the brief asked for.

## PC profile (68000 PC sampled every 37 us in MAME, frames 600-900, PLAYING)

Before: bg_slot_world_col 29.5 percent of all time (two 32-bit `%` = libgcc __umodsi3 per call, 63 calls per
frame), gfx_wait_vblank (idle) 17.6, vq_scb_word 13.5, gfx_word 5.6, push 4.0, update_ring 3.8,
vq_fix_put 2.7, gfx_text 2.4, gfx_flush 2.3.
After the bg fix: idle 45.3, vq_scb_word 13.5, gfx_word 5.5, push 3.9, update_ring 3.9, vq_fix_put 2.7,
gfx_text 2.4. Still about 1.1 frames of busy time per game step.

## Changes made

- src/core/bg_scroll.c/.h: new bg_ring_slot(w) and bg_slot_world_col_at(first, first_slot, slot) (wrap by
  compare); bg_slot_world_col now calls them (host test test_bg.c still covers it).
- src/bg.c: update_ring computes first_slot once per layer; write_column uses bg_ring_slot.
- src/core/vram_queue.c/.h: vq_scb_word is an inline dedupe test in the header; the push part is
  vq_scb_word_push.
- tests/mame/vblank_check.lua + Makefile test-vblank: ROOFLINE_FRAME_ADDR; asserts at most 2 PLAYING frames
  without a g_frame_counter step (regression check for the 30 Hz loop; fails before, still fails now).

## Next steps (in order)

1. Cut per-frame main-loop cost further until test-vblank's frame-step check passes. Candidates from the
   profile: gfx_word wrapper (RETRY loop + call per word; make the dedupe path inline in gfx.h too),
   count gfx_word calls per frame and stop re-sending hide words for inactive obstacle/laser slots every frame,
   draw() re-sending all fix text each frame (gfx_text / vq_fix_put; skip when the string is unchanged),
   put_number using 32-bit `/ 10` and `% 10` (libgcc). Re-profile after each step (Lua PC sampler:
   coroutine with emu.wait(0.000037), cpu.state["PC"], attribute libgcc PCs to the return address on SP).
2. Then re-run test-hit; expected to pass unchanged once the loop is at 60 Hz.
3. Then rework laser_check.lua to a sentinel-driven timeline (wait until a drone/bot is ahead in range,
   then hold A; avoid death by jump), and run the rest of make test.

## Loop 60 Hz fix

Result (2026-11-09): make test PASS (host, test-laser, test-hit, test-vblank, boot/pixel checks).
test-vblank: 0 of 600 PLAYING frames without a game step (was 391 of 1009). test-unibios not re-run.

Measured first (Lua timeline probe, lines after vblank start, 264 lines per frame): the vblank flush wrote
exactly the 58-word budget in lines 1-28 and the wait exited at about line 30, so BIOS + flush were short
and gfx_wait_vblank had no logic bug. The cost was the main loop itself: PLAYING frame logic ran from line
30 to 250-270 (2 steps per 3 frames), with a 60-80 op queue backlog every frame (more ops queued than the
flush budget) and RETRY drain stalls at coin/start when the queue hit VQ_CAP. Biggest producer: 63 ring
SCB4 words per frame (3 rings x 21 sprites) in bg.c update_ring. Profile: gfx_word 13.6 %, vq_scb_word_push
10.1 %, gfx_flush 6.7 %, bg_update 5.2 %, __udivsi3 1.2 %.

Root cause: per-frame main-loop cost (about 14-15 ms) plus the send-everything ring update that kept the
VRAM queue over budget. Fixes:
- src/core/vram_queue.h: vq_scb_same() / vq_scb_word() inline dedupe; src/gfx.h: gfx_word() is now an
  inline dedupe check that only calls gfx_word_push() (src/gfx.c, RETRY + push) on a changed word. The
  queue is exported as g_gfx_q for that.
- src/bg.c: each ring is two sticky SCB3 chains. Per frame only the head SCB3 (when the first slot moves:
  old head made sticky, new head gets y/size), the head SCB4 and slot 0's SCB4 are sent: 2-4 words per ring
  instead of 21. bg_init writes only SCB2; update_ring writes the full SCB3 chain once on !g_valid.
- src/bg.c bg_update: lamp/star phases advance with u8 counters while frame steps by one; the 32-bit `%`
  and `/` run only on a jump (reset, first call).
After: PLAYING frame logic ends at line 115-135, queue backlog 6-26 ops, all words flushed per vblank.

Tests:
- tests/mame/laser_check.lua rewritten to a sentinel-driven timeline: coin once g_frame_counter has moved
  30 steps, hold start until the flow state is PLAYING, hold A only while a drone/bot is ahead and in range
  and the laser is not locked out, jump vents and close bots (B edge), duck cables (C). The beam snapshot is
  taken one frame after the bolt is seen in RAM (VRAM is written in the next vblank, so the screen shows the
  previous step); at 30 Hz this lag was hidden. Fails if PLAYING is left before a kill; reports hits/lives
  (last run: hits 0, lives 3 -> 3). Only a 6000-frame watchdog remains. Makefile passes ROOFLINE_FRAME_ADDR;
  tests/mame/laser_probe.c appends lives, hero_h, hero_vy, invuln.
- tests/mame/check_bg_pixels.py: BG_LAMP_OFF (written at run time by lamp_set into both far and mid
  palettes) is excluded from layer-unique colours. At 60 Hz the playing snapshot lands in the lamp-off phase
  and the far lamps (y 76-81) counted as 12 "mid above band" pixels. The check's colour model missed the
  runtime palette swap; the game is correct.
