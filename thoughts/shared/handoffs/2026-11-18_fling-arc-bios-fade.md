---
date: 2026-11-18
topic: Gum Fling aim arc merged, BIOS-return screen fade nearly done, music fade deferred
tags: [handoff, gum-games, gum-fling, bios-return, fade, popdrop]
status: draft
---

# Handoff 2026-11-18: fling aim arc, BIOS-return fade

## Tasks
1. BIOS-RETURN-FADE: fade the screen down before SYSTEM_RETURN at game end and up after video_init, every mode. Owner: "why do we need a black cut at all? if it must be there fade down and up not a hard cut". NOT merged: test-trip fails.
2. FLING-AIM-ARC: in-air aim pointer and dotted throw path in Gum Fling. Merged into feature/gum-games (07ddb0b), builds. Owner play-test pending.
3. MUSIC-FADE-DRIVER: owner picked "Driver fade later". The nullsound Z80 driver has no volume or fade command (only play ids, stop_music 2, reset_driver 3). Do it after Gum Fling PASS and the Pop Drop merge.
4. Pop Drop merge: waits for Gum Fling PASS. Plan: thoughts/shared/plans/2026-11-18-popdrop-freefall-progress.md.

## Critical references
- Ledger: thoughts/spot/todos.md, rows BIOS-RETURN-FADE (~5191), MUSIC-FADE-DRIVER, SESSION-HANDOFF, knob baseline (~5190).
- Fade report (git-ignored, only copy is in the worktree): .claude/worktrees/bios-fade/thoughts/spot/reports/bios-return-fade.md
- Fade branch fix/bios-return-fade, worktree .claude/worktrees/bios-fade, commits f946a5e (WIP) + 32d08a7 (fix).
- Fling arc code: fling_arc_step in src/main.c, gumfling_path in src/core/gg_fling.c, FLING_ARC_SPRITE in src/sprite_slots.h (shares TRIP_STRIP_SPRITE range, 10 slots).
- Fling snapshot: thoughts/shared/drafts/2026-11-18-fling-arc/index.html
- Black gap report: thoughts/spot/reports/gameover-black-gap.md

## Recent changes
- gum-games: black gap cut 45 to ~12 frames (5e7e2bb, bg_set_mood(mood, 1) in video_init). Arcade and trip gates for that change were never run.
- gum-games: fling aim arc merged (feature/fling-aim-arc merged then deleted; worktree removed).
- fix/bios-return-fade 32d08a7: screen_fade steps two levels per pass with cheap 4-bit scaling (fade-up ~23 frames); tests/mame/black_screen_check.lua now pokes Flow.last_score at the real offsets 38 and 42 (was 22, so the old "no run ranks" check passed only by timing).

## Learnings
- UniBIOS clears the palette for 47-59 frames on SYSTEM_RETURN. That black cannot be removed, only softened.
- bg_fade_color is too slow for a full 4096-word palette pass on the 68000 (three software 32-bit multiplies per word, ~5 frames a pass).
- bss ends at 0x10B600, ~15 KB below the BIOS area at 0x10F300. The 8 KB fade buffer is safe.
- Knob baseline on gum-games: "knobs: 141 checked, 0 failed". A knob failure on the popdrop branch is Pop Drop's own.
- `git branch -d` refuses branches merged into gum-games but not into the main checkout's HEAD. Check with `git merge-base --is-ancestor <branch> feature/gum-games`, then -D.

## Gate state on fix/bios-return-fade (32d08a7)
- test-black-screen PASS, test-arcade PASS.
- test-trip FAIL: "trip splat check: not PLAYING when the death was due". It passes with screen_fade stubbed out. Agent's unverified guess: the longer boot shifts the flap rhythm in tests/mame/trip_check.lua against the MAME frame count. Start is pinned to g_frame_counter, so check whether the test (not the game) is timing-bound before touching game code.

## Next steps (ordered)
1. Owner play-tests the Gum Fling aim arc LOCAL: `cd .claude/worktrees/gum-games && gmake run`. Watch for off-screen dots on high-power throws and 16x16 dot readability. 2P turns never run.
2. One sonnet agent: find the test-trip cause on fix/bios-return-fade (test or game), fix at the root, all three gates green. Then merge into gum-games, build, owner play-test of the fade (game over in every mode).
3. On Gum Fling PASS: Pop Drop merge per its progress plan (fix its knob failure first).
4. MUSIC-FADE-DRIVER.
5. Later: refresh ingame_card.png; delete stray src/core/vram_queue.c-E and tests/host/test_ai.c-E in the main checkout.

## Other notes
- Old locked agent-* worktrees (countdown, fling-check, menu-drill, gg-countdown, countdown-art) are not from this session's agents; ownership not checked, left alone.
- Builds: nice -n 19 gmake, no buildq. Headless MAME: SDL_VIDEODRIVER=dummy, -video none; `git checkout -- cfg/neogeo.cfg` after every run.
