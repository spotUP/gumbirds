# CPU opponent framework (branch feat/cpu-opponent)

Minigames: 7, counted from gg_order[GG_PICK_COUNT] in src/core/flow.c and the GG_* enum in gumgames.h (Big Blow, Burst Race, Bubble Gather, Pop Drop, Flap Dash, Gum Fling, Poop the Man). Party Toss/Tug are separate party rules.

## Done
- src/core/cpu_opponent.{h,c}: CpuLevel table (delay, miss_pct, period) for Easy/Normal/Hard, Cpu state (seeded Rng), cpu_act(), cpu_flapdash(), cpu_input(Game*).
- Game.cpu_level / Game.opp; game_step sets input2 = cpu_input(g) when cpu_level != 0, players == 1 and the countdown is over.
- tests/host/test_cpu_opponent.c (in run.sh). Makefile CORE_SRCS has cpu_opponent.

## Where the next game goes
Add `uint8_t cpu_<game>(Cpu *c, ...)` in cpu_opponent.c and one `if (g->gg_<x>) return ...` line in cpu_input. Tune rows in cpu_levels.

## NOT done, needs owner decision
1. Flap Dash has no P2 and no gaps: it is a solo 3-lap time trial (hero[0] only, always players = 1, camera follows one bird, record = hero[0] time). So "same rules as 2-player" does not exist for it. The CPU behaviour is an altitude controller (flap when below CPU_DASH_TARGET_Y, reaction delay, miss rolls; a fumbled flap usually drowns the bird, there is no recovery) driving a second GgDash/Flier. That second bird is not in Game yet (cpu_input reads hero[1], which stays GONE): needs a rival GgDash, its draw (sprites/palette p2 or cpu), camera handling and a result rule (who finished first). Records: flow.c writes the dash record from game.dash (P1) only, so a CPU bird cannot write a human record as long as that stays.
2. Level choice screen: there is no 1P/2P start screen. P2 joins by pressing start in play (players = 2). Needs a decision where the pick goes (title row? after mode pick?) before flow sets Game.cpu_level and calls cpu_init(&g->opp, level, seed) after game_reset.
3. Real ROM build and MAME not run (host tests only).

## Findings
Flap Dash physics: the bird drowns if the first flap comes later than about frame 4 and any gap over about 8 frames is fatal; presses faster than every 6 frames all finish in about 705 frames (speed cap). So delay is 1..3 frames and difficulty is the miss rate (Easy 25, Normal 12, Hard 3 percent): over 40 seeds Easy finishes 26, Normal 33, Hard 40.
