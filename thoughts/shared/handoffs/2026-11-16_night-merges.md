---
date: 2026-11-16
session: arcadegame-6
status: night work done, waiting on owner
---

# Handoff: 2026-11-16 night merges (session arcadegame-6)

Ledger: thoughts/spot/todos.md, section "## 2026-11-16 night (session arcadegame-6)". Trust it over this file.

## Merged into integ/beta1 overnight (all merge gates PASS)
- 4746570 stage HUD, game over text, continue skip.
- a23a822 re-pump gum step (balloon count; lever ARC_REPUMP_STAND_FRAMES if still fast).
- 37b5b85 attract overlay palette slot (ATTRACT_PAL_SLOT = FIX_PAL_COUNT, assert < 16).
- 98f7fdd demo frame cost cut (vq_scb_run skip-unchanged, island place written-only, trip_pickup early return).
- R10 spark column host check (test_sprite_budget). Bug not reproduced; column fits since 6afe456.
- ad40cab vent spark loops every 16 ticks inside the plume kill box (test_vent_kill_visible). Report thoughts/spot/reports/spark-hold.md.
- 1b8979d demo flier driven by rival AI; Gum Trip seeks gum and looks 72 px ahead for hazards. 300 seeded demos, 0 deaths. Demo arena logic end 219.6 (limit 224). No deliberate attack. Report thoughts/spot/reports/demo-ai.md.

integ/beta1 head 1b8979d. Not merged into main, not pushed.

## Owner checks (LOCAL MAME, `nice -n 19 gmake run` in .claude/worktrees/beta1)
- Attract demo: bird collects gum, does not hit roof, icons constant colour across moods.
- R10 x=320 vent: spark visible over the whole plume kill time; judge whether the 16-tick loop pop looks odd (option: fable agent draws a taller plume).
- Re-pump growth / lift-off speed; HUD STAGE/BONUS, GAME OVER, continue plate.
- Logo, roof boulders, BONUS STAGE text, continue after credits, high score after restart, MiSTer load.

## Owner decisions open
- Parachute variant: gallery thoughts/shared/drafts/2026-11-16-gum-parachute/index.html (A/B/C). Then wire FLIER_PARACHUTE in main.c.
- 2P co-op planning round.
- Remove worktrees whose only change is cfg/neogeo.cfg (needs --force): cont-restart walk-cost3 black-screen rival-sound unibios-coin vent-warn vblank-demo. Branch fix/vblank-demo merged, delete with it.
- Merge integ/beta1 into main and push.
