---
date: 2026-11-09
topic: P5.1 high score reachability test
tags: [test, hiscore, backup-ram, mame, p5.1]
status: test written; boot 2 FAILS on a real persistence bug (open)
---
# P5.1 result

Files: tests/mame/hiscore_reach.lua, tests/mame/reach_probe.c, Makefile target test-reach (called from test).
Src change: `volatile u32 g_hiscore_saves` in src/main.c, incremented next to hiscore_serialise.

Boot 1 PASSES: autoplay to score 1356, game over, name REACHTST typed through the real name entry screen,
save sentinel 0 -> 1, g_hiscore_image holds the entry at row 9.
Boot 2 FAILS (correctly): same nvram dir, backup RAM image row 9 is empty.

## Cause of the boot 2 failure (unverified fix)
ngdevkit backup-ram.h: data in .bss.bram (0x100000) "is automatically saved each time the attract mode is run"
(BIOS USER command 3) and restored at start. The game's flow runs attract itself and never returns to the BIOS,
so MAME's saveram (nvram/neogeo/saveram) never receives the table: it holds only BIOS data. Same risk on the
cabinet (P5.2). Needs a decision: trigger a BIOS attract/return after a save, or write backup RAM directly.

## Other finding
Makefile has no header dependencies: build/src/core/flow.o was stale (17:15) against game.h (19:59), so Flow
layout in flow.o differed from main.o by 8 bytes. I touched flow.c, nameentry.c, hiscore.c, rng.c to rebuild.
Add -MMD deps or `make clean`.

## Test notes
Autoplay jump lead is 4 frames of travel (ROOFLINE_JL overrides); vent window is tight at start speed.
Threshold for idle-until-death: score above 1200 (table minimum 1000, ties rank below).

## Persistence fix

### Root cause (two layers)

1. Game layer (fixed). `rom_game` never returned to the BIOS. `game_loop` was `noreturn`, so the
   BIOS never got a SYSTEM_RETURN. Both nullbios and the real MVS BIOS copy the block named by
   header 0x10E/0x112 (here 0x100000, 0x84 bytes) to slot backup RAM only after USER returns
   through SYSTEM_RETURN. The cart header was already correct.
   Fix in `src/main.c`: when `g_flow.dirty` is consumed, set `g_bram_unsaved`. At the end of that
   frame, if `bios_user_mode == 1` (game mode), return from `rom_game`. The BIOS saves and calls
   USER again. `g_boot_magic` makes the re-entry take `resume_game_loop()`, so the screen
   continues without a visible change. Attract, title and name entry behave the same.
2. BIOS layer (not fixed, outside the repo). The ngdevkit nullbios `save_game_data_to_bram`
   (biosstart.S, upstream master 8756cbd, which matches the installed sp-s2.sp1 byte for byte)
   writes 0xD00320+ without first writing REG_SRAMUNLOCK (0x3A001D). MAME drops locked saveram
   writes. Only the credits code (`WITH_BACKUP_RAM_RW` in utils.h) unlocks. `load_soft_dip`
   has the same omission. So no game can persist under stock nullbios in MAME.

### Verification

- UniBIOS 4.0: `make test-reach-unibios` (new target) passes boot 1 and boot 2, REACHTST 1290 row 9.
  With the return disabled (`if (0 && ...)`), boot 2 fails. Revert-fail is proven.
- Stock nullbios: boot 2 still fails because of layer 2.
- nullbios patched with an unlock/lock pair around `save_game_data_to_bram`: inconclusive. The
  run timed out in boot 1 ("no result from Lua script", 299 s) while another MAME was running.
- Real SNK MVS BIOS: not run. This is the documented protocol only.

### Options for nullbios (decision open)

- A (root cause): vendor a pinned, patched nullbios with unlock/lock in `save_game_data_to_bram` and
  `load_soft_dip`, use it for `make test`, and send the patch upstream.
- B (shim, not recommended): the game writes REG_SRAMUNLOCK before SYSTEM_RETURN. A real BIOS
  does not need this.
- C: report upstream only. `make test-reach` on stock nullbios stays red until upstream fixes it.

### test-reach "tail: ... mame1.log: No such file"

The Makefile never deletes `build/test-run.*` during a run. The dir was deleted from outside,
most likely by another session's scratch cleanup. The `tail` now falls back to an `[ERROR]`
line that names this cause, so it no longer aborts under `set -e` with a bare message.
`REACH_BIOS_FLAGS` (default `-rp $(ROM)`) selects the BIOS.

### Regression found after the first write-up (return now disabled)

- With the return-to-BIOS enabled, `make test` fails in test-laser ("no result from laser Lua script")
  and `make test-unibios` fails ("game not running before coin (text 0eee hero 0000 counter 0)").
  With only that `if` disabled, test-laser passes (shots 3 kills 1). The return path is the cause.
- `g_flow.dirty` is set only by name entry and the title reset combo, so the cause is in the
  re-entry, not an early save. Unverified suspects: `game_loop` locals (game state, scene) start
  fresh on re-entry, and UniBIOS may re-enter through a different USER command or mode.
- The patched-nullbios test-reach also stops in boot 1 when the machine is idle (108% speed), so the
  same re-entry bug is a likely cause there too, not machine load.
- The tree now keeps the code behind `if (0 && ...)`, so `make test` stays green. Next step:
  move the game_loop state into statics (or g_flow) so re-entry continues the same frame, then
  enable it again and run test-laser, test-unibios and test-reach-unibios.

## Re-entry fix

- Real cause of the earlier "return breaks test-laser / test-unibios": not reproducible. With the SYSTEM_RETURN enabled both pass. No state is lost on re-entry: g_flow, g_frame_counter, g_bram_unsaved, g_draw_state and the pool are statics; the only game_loop local (FlowView view) is recomputed each frame. rom_game / rom_title resume through g_boot_magic into resume_game_loop. The earlier failures came from a concurrent relink on a mid-edit tree.
- Codegen note: with the return disabled, gcc infers game_loop noreturn, and rom_game / rom_title end in `jsr resume_game_loop` with no rts. Harmless while disabled; the enabled build tail-calls correctly.
- Return enabled in src/main.c (end of game_loop, `g_bram_unsaved && bios_user_mode == 1`).
- Makefile: test-reach now runs on UniBIOS 4.0 (REACH_BIOS_FLAGS); test-reach-unibios removed. nullbios still writes backup RAM without REG_SRAMUNLOCK, so it cannot run this test. nullbios is not patched or shimmed.
- Results: test-reach passes both boots on UniBIOS. Revert check: with `if (0 && ...)` boot 1 passes and boot 2 fails ("backup RAM row 9 is '        ' 0"); re-enabled, it passes again. test-laser and test-unibios pass with the return enabled.

### test-vblank still red (open)

- Boot is fine. 0 VRAM and palette writes outside vblank. Missed game steps at 32 objects: about 1 in 3 frames (323 of 727). Logic end max 999 (frame counter written inside vblank = overrun). Queue backlog after flush max 80 ops, flush max 1999 us (budget 2000 us always hit), max data words per frame 408.
- Debugger trace of 3 stress frames: 54% of instructions in gfx_wait_vblank, so the CPU is not saturated in those frames; no gfx_drain (RETRY) call in them.
- Tried and reverted (no effect on the numbers): (1) send pool chain words and hidden spare columns only on a frame change, (2) stagger anim_tick by slot parity at alloc. Hypotheses "per-frame redundant words" and "in-phase strip bursts" are not the cause.
- Next: measure per-op flush cost against vq_cost (the 2000 us cut with an 80-op backlog every frame suggests the cost model or per-op flush overhead is the limit), and count where the frame-counter write lands relative to vblank per frame, not only the max.
