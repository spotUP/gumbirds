---
date: 2026-11-09
topic: Engine object pool (src/core/obj_pool) and its frame cost at the maximum object count
tags: [engine, sprites, vram-queue, performance, neo-geo]
status: open
---

# Object pool

## What exists

- `src/core/obj_pool.[ch]`: pure C pool of `POOL_MAX` (32) objects. Each object has a 16.16 position and velocity, a
  type, flags, and an animation frame and tick. The free list is an O(1) LIFO with no malloc. A spawn into a full pool
  returns `POOL_NONE`. Object i owns hardware sprites `base + i * POOL_COLS` (3 columns), so runs never fragment.
  `obj_pool_free` sets a hide bit, and the view hides that run once (`obj_pool_take_hidden`). No `/` or `%` anywhere.
- `src/sprite_slots.h`: `POOL_SPRITE_BASE 96`, `POOL_SPRITE_COUNT 96` (sprites 96..191) replace the old obstacle
  range. `src/main.c` asserts the range against the background, the hero and `POOL_SPRITES`.
- Host test `tests/host/test_obj_pool.c` (in `tests/host/run.sh`): 217 checks covering alloc/free, sprite runs, the
  hide-once mask, motion with gravity, and animation wrapping.

## Wiring (route: clean swap)

The obstacle sprite slot management in `src/main.c` now goes through the pool. Game logic is unchanged (`game.c` keeps
obstacles in 8.8). `pool_sync_obstacles` allocates a pool object when an obstacle turns active and frees it when the
obstacle goes inactive or off screen. Each frame it copies the position (x = hit box left, y = hit box bottom).
`pool_show` draws every live object. It requeues the SCB1 tile strips only when the animation frame changes
(`g_pool_drawn` cache). Otherwise it calls the new `gfx_sprite_place`, which writes only SCB2..4.

`obj_pool.c` is `#include`d at the end of `main.c` because the Makefile `CORE_SRCS` list could not be edited in this
task. Move it to `CORE_SRCS` and add `src/core/obj_pool.h` to the main.o dependency line.

## Reachability check (tests/mame/vblank_check.lua)

Sentinels are read from `build/rom.elf` through nm, using the path from config.mk: `g_pool_frames`, `g_pool_live`,
`g_pool_stress`, `g_gfx_backlog_max` and `g_gfx_flush_max`. `POOL_MAX` comes from the 9th `hit_probe` value.

1. The first PLAYING frame with `g_pool_frames > 0` proves the obstacles draw through the pool.
2. Thirty frames later the script sets `g_pool_stress`, which fills the pool with 32 drifting drones and bots.
3. The script requires at least 100 PLAYING frames at 32 live objects with 0 missed frame steps.
4. It reports the latest frame logic end (the `g_frame_counter` write, as lines after vblank end; 999 means the write
   landed inside vblank, which is an overrun) and the maximum queue backlog after a flush.

## Result: 32 moving objects do NOT hold 60 Hz (test-vblank FAILS)

Last run (with the strip cache):
- The pool ran in normal play. The obstacles drew for 31 frames before stress started.
- 1138 frames ran at 32 objects. 690 of them had no game step, so the game runs at about 30 Hz.
- The frame logic overran into vblank (999).
- The queue backlog after a flush peaked at 339 of 384 ops. Every flush used the full 2000 us budget.
- 0 VRAM writes landed outside vblank.

The run before the strip cache was about the same: 840 of 1379 frames missed, backlog 336.

Root cause: vblank flush throughput, not pool logic. The disassembly shows no div or mod calls in the pool path.
`vq_cost` budgets about 34 us per single word op and about 50 us + 5 us per row for a strip. That is roughly 58 word
ops per 2000 us flush. Each moving object costs at least one SCB4 word per frame, plus an SCB3 word when y changes.
Each animation frame change costs 3 strips. With 32 objects this exceeds the budget before the background and hero
add their own ops. The queue then fills, and `RETRY` in gfx.c blocks the main loop in `gfx_drain`, so frames are
missed.

Fix options (root-cause layer: `src/core/vram_queue` + `gfx_flush`):
- A strided run op. Set `REG_VRAMMOD` to the stride and write the SCB4 (or SCB3) words of many sprites in one op,
  paying the per-op overhead once. Pool runs sit at a stride of 3. A per-frame "all pool x" op is one address set plus
  32 data writes.
- Cut the per-op overhead (about 29 us, roughly 350 cycles) in the flush loop, for example with a hand-written
  68000 loop.
- Fall back on budget: lower `POOL_MAX` for things that move every frame, or animate fewer objects per frame.

## Open

- test-vblank is red until the flush fix lands. The check is correct and stays strict.
- `obj_pool.c` is built through `#include` in main.c (the Makefile was not edited).
- Existing per-frame u32 divisions outside this change: main.c hero frame `(g->frame / HERO_RUN_TICKS) % ...`,
  bg_update, flow_view, laser_view_flash and rng_range.

## Flush speed fix

Measured before the change (make test-vblank, 32 pool objects): 697 of 1145 frames at 32 objects had no game step,
the queue backlog after a flush peaked at 339 of 384 ops, every flush used the full 2000 us budget, and the latest
write landed 30.1 lines into vblank. 0 writes landed outside vblank. A static cycle count of the old `gfx_flush` loop
gives about 370 cycles (31 us) per single word op. That matches the measured 58 data words in about 28 lines.

Violated invariant: the flush time of an op must be dominated by its register writes. Instead, about 90% of each word
op went to bookkeeping: 12-byte op indexing done with adds, a 32-bit budget compare, `vq_cost` recomputed per op, and
the ring head and count reloaded and stored on every op (the u16 hardware writes may alias the u16 queue fields).
On top of that, `pool_show` queued one op per SCB3 and SCB4 word, so 32 moving objects cost at least 64 ops per frame.
Root-cause layer: `gfx_flush` (src/gfx.c) and `src/core/vram_queue.[ch]`.

Changes:
- `VqOp.cost` is set on enqueue. `vq_cost` returns it.
- `gfx_flush` keeps head, count and the u16 budget in locals, walks ops by pointer, and stores the ring state once.
  From the disassembly: a word op is about 158 cycles (13 us), down from about 370 (31 us).
- New op `VQ_RUN` (`vq_scb_run`, `gfx_scb_run`): one address set, `REG_VRAMMOD` = stride, then n data words read
  from the SCB shadow. It dedupes per word against the same shadow as `vq_scb_word`, and queues only the span from the
  first to the last changed word. A full queue rejects the run without touching the shadow. A word inside a run costs
  about 42 cycles (3.5 us) plus about 230 cycles of op overhead.
- `pool_show` (src/main.c) writes all pool SCB3 and SCB4 words as two runs at stride `POOL_COLS`. The followers stay
  sticky through `gfx_sprite_chain`, which dedupes to zero ops after the first frame.
- Host test `tests/host/test_vram_queue.c` covers the run op: queueing, dedupe, the shared shadow, the partial span,
  the range check and the full-queue case. tests/host/run.sh passes.

Status: NOT verified in MAME. The run after the change could not measure anything: the game never booted (0 game RAM
writes, BIOS reset loop, PC in BIOS or garbage). The other agent's own run at the same time failed with "game not
running before coin". At the same time, `build/rom.elf` was being relinked by a concurrent build (the boot-section
`jsr <main>` address changed between two reads of the same file), and src/main.c has new rom_game / rom_title /
g_boot_magic boot hooks (around lines 424-503) that are not part of this change. Re-run `make test-vblank` once the
tree builds and boots, and record the backlog max, flush max and missed steps here.

## 32-object vblank fix

Date: 2026-11-09. `make test-vblank` failed the pool stress (POOL_MAX 32): 323 of 727 PLAYING frames without a
game step, backlog max 80, flush max 1999 of 2000 us, yet about 54 % idle.

### Measurements (MAME Lua probes, lines of 64 us, 264 lines per frame)

- Timeline probe: one game step took 234-352 lines of main-loop logic, more than one frame. When the step ends
  inside vblank the flush is skipped (main loop not parked), gfx_wait_vblank then waits a whole extra frame: the
  game runs in a 30 Hz lockstep. That forced wait is the "54 % idle". It is a symptom, not spare time.
- Cost model vs real flush (first to last VRAM write per vblank, 403 flushes): model 1093 us average, real 1124 us.
  The vq cost model is about 3 % low; the flush and its budget are not the problem.
- "logic end max 999" in vblank_check.lua: any g_frame_counter write inside vblank is clamped to 999, so an overrun
  longer than one frame reads as a small number. Real overrun evidence, but the number under-reports.
- Main-loop segments at 32 objects before the fix (average / max lines): pool_show 148.6 / 219.8, draw 38.1 / 85.6,
  laser_show 36.3 / 37.6, bg_update 21.9 / 57.6, pool_stress 12.6, flow_step 4.0, gfx_commit 4.4 (107.9 on a drain).
  Total about 270 lines average.
- PC profile: pool_show 11.4 %, gfx_sprite_chain 8.1, vq_strip 5.8, vq_scb_run 4.9, gfx_sprite_block 4.2 (heat
  bar every frame), vq_fix_put + gfx_text 6.0, __udivsi3 1.1 (put_number u32 `/ 10`, `% 10`).

### Root cause

Violated invariant: frame logic plus the vblank flush must fit in one frame (the logic must end before the next
vblank start, about 220 lines after the flush). Root-cause level: the main-loop view code re-sends unchanged state
every frame. pool_show ran the sticky chain (5 dedupe checks) and the spare-column hides for every object every
frame and built strips one out-of-line call per column; laser_show redrew all heat bar sprites every frame;
draw() re-sent all fix text and divided the score with libgcc every frame. Not the cost model, not the flush,
not a missed queue dedupe.

### Change

- src/main.c pool_show: chain and spare-column hides only when the object's width changes (new g_pool_cols[],
  cleared by pool_hide_run / pool_hide_all with g_pool_drawn); strips only on a frame change.
- src/main.c laser_show: heat bar sprites redrawn only when (cells, visible) changes (g_bar_drawn, reset by
  laser_hide_all).
- src/main.c draw: header text once per state (after gfx_cls); score/lives HUD only when they change;
  put_number by power-of-ten subtraction (no 32-bit divide).
- src/core/obj_pool.h: obj_pool_anim static inline (was out of line per object per frame).
- src/core/vram_queue.c/.h: vq_strips (one call per sprite block, ops filled in place via tail_op, vq_strip is
  a wrapper); vq_fix_text (one call per string, incremental cell index; gfx_text uses it); vq_scb_run walks the
  shadow by pointer. src/gfx.c gfx_sprite_strips uses vq_strips with a drain-and-continue on a full queue.
- tests/host/test_vram_queue.c: vq_strips case (column sprites/tiles, dedupe, wrapper agreement).

After (same probe): pool_show 85.8 / 142.0 lines, laser_show 4.1, draw 5.2 average; logic end at 32 objects
207.6 lines after vblank end (limit 224); 0 missed steps at 32 objects; backlog max 73, flush max 1999 us
(strip bursts when all drones flip together still use the full flush budget; the backlog drains next frames).

### Tests

- Regression: with only src/main.c reverted to the pre-fix copy, test-vblank FAILS (211 missed steps at 32
  objects).
- Host tests PASS. make test PASS in full (host, laser, reach, hit, vblank, boot/pixel checks). make test-unibios PASS.
- Open: overall "logic end max 999" (outside the 32-object phase) is still reported; likely the coin/start
  video_init drain, which blocks by design. Unverified: not probed.
