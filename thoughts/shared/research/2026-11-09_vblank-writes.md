---
date: 2026-11-09
topic: VRAM and palette writes outside vblank (ground and skyline pixel glitches)
tags: [neogeo, lspc, vblank, vram, mame, status-implemented]
status: implemented (test-vblank passes; test-laser and test-hit still fail, see Open)
---

# Vblank writes

## Problem
game_loop drew, showed sprites and scrolled the background before ng_wait_vblank, so 357-405 VRAM words per frame spilled into the visible display, and palette writes tore too.

## Baseline (current code before the change, make test-vblank)
280998 of 540645 VRAM register writes and 6231 of 6339 palette writes landed outside vblank.

## Change
- src/core/vram_queue.[ch]: pure queue (shadow of hardware state, dedup on enqueue, wanted-buffer diff for the fix layer, strip dedup by descriptor, FIFO, cost per op). Host test tests/host/test_vram_queue.c (415 checks).
- src/gfx.[ch]: single owner of VRAM and palette writes. main.c and bg.c enqueue only. SCB4, fix text, star tiles and lamp palettes go out on change only.
- Total VRAM register writes over the 1800-frame test run fell from 540645 to about 41000.
- Init (video_init) runs outside the per-frame budget by design: it enqueues everything and gfx_drain waits vblanks until the queue is empty, one budgeted flush per vblank.

## Measured MAME timing
- First pass: 3.66 us per register write in tight bursts, budget 380 register writes. Superseded: see Root cause (per-op overhead dominates; budget is now time, GFX_FLUSH_BUDGET_US).

## Root cause (measured 2026-11-09, second pass)
Hypotheses checked with a MAME Lua probe (screen line from time_until_pos, PC/SR at each register write):
- (a) window calibration: correct. IRQ ack (0x3C000C=4, PC 0x21A) at line 240 = first blank line, 39.8 lines before vblank end; 264 total lines, 224 visible, 40 blank.
- (b) double IRQ / other path: no. One ack per frame, no timer-IRQ ack (value 2) ever.
- (c) main-thread flush: no. Every late write has SR 0x21xx (inside the level-1 interrupt), PC in gfx_flush called from rom_callback_VBlank.
- (d) flush too long: yes. The flush starts on time (first write 0.4 lines after the ack) but each queued op cost about 2.3 lines (147 us). vq_pop wrapped the ring with `% VQ_CAP`: int-promoted, so a libgcc __modsi3 call (__divsi3 + __mulsi3, the 68000 has no 32-bit divide). The flush ran 100+ lines past vblank and the frame logic overran.
After removing `%` the per-op cost was still about 29 us for a single-word op (loop overhead, 5 us per extra address set) versus about 2.5 us per data write inside a strip, so a budget counted in register writes cannot bound the time.

## Fix
- vram_queue: ring wrap by compare (push, vq_pop); consumer side (vq_peek, vq_pop, vq_cost) static inline in the header.
- vq_cost is now flush time in microseconds: VQ_US_OP 34 per word/palette op, VQ_US_STRIP 50 + VQ_US_ROW 5 per row.
- gfx_flush: tight loop with locals, budget GFX_FLUSH_BUDGET_US 2000 (about 31 lines of the 40). Sentinel g_gfx_flush_max is now the longest estimated flush (us).
- Result: make test-vblank PASS, vram writes 49453 (outside vblank 0), palette 267 (0), latest write 28.7 lines into vblank. Same test on the code before this fix: 25340 of 40973 VRAM and 307 of 363 palette writes outside.

## Open
- make test-laser fails after the fix: no shot in the whole run (play from frame 362, game over before frame 2400, enemy_ahead never true with lockout 0). Before the fix it got a kill but all three pixel checks failed (beam, heat bar, hit flash: 0 pixels). The game logic now runs every frame instead of overrunning, so the spawn/death timeline the script relies on changed; not yet confirmed whether a drone/bot spawns before the idle hero dies.
- make test-hit fails before and after the fix with the same shape ("after invuln anim 65535", blink "other" frames > 0); hero_view area, not touched here.
- make test therefore stops at test-laser; its boot check and pixel checks were not reached. Host tests and test-unibios pass.
