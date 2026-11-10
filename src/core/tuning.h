/*
 * tuning.h - every gameplay constant for Bubblegum Brawl in one place.
 *
 * Units: positions and speeds are fixed point 8.8 (value / 256 = pixels) where the name says
 * "8.8"; everything else is whole pixels or whole frames. The game runs at 60 frames per second.
 * No floating point anywhere in the core.
 *
 * Every constant can be overridden on the compiler command line (-DNAME=value). The host test
 * suite does this to prove that each knob changes the output of a scripted run
 * (tests/host/knobs.txt lists the override value for each knob and run.sh checks the list is
 * complete).
 *
 * Exemptions (constants that are not knobs): SCREEN_W and SCREEN_H are hardware facts, not tuning. They are not
 * overridable in tests.
 */
#ifndef BRAWL_TUNING_H
#define BRAWL_TUNING_H

#define SCREEN_W 320
#define SCREEN_H 224

/* Distance the run counter (Game.distance) gains per frame while the player flier lives, 8.8 px (2.0). */
#ifndef SPEED_BASE
#define SPEED_BASE 512
#endif

/* ---- Screen flow (flow.c, nameentry.c) ---- */

/* Name entry: frames a direction must be held before it repeats, then frames between repeats. */
#ifndef NAME_REPEAT_DELAY
#define NAME_REPEAT_DELAY 20
#endif
#ifndef NAME_REPEAT_RATE
#define NAME_REPEAT_RATE 5
#endif

/* Name entry: frames without any input before the name typed so far is accepted
 * (60 s, user decision 2026-11-10; was 30 s). The screen shows the seconds left. */
#ifndef NAME_TIMEOUT_FRAMES
#define NAME_TIMEOUT_FRAMES 3600
#endif

/* Attract loop: how long each screen shows before the next one (title, table, demo). */
#ifndef ATTRACT_TITLE_FRAMES
#define ATTRACT_TITLE_FRAMES 420
#endif
#ifndef ATTRACT_TABLE_FRAMES
#define ATTRACT_TABLE_FRAMES 480
#endif
#ifndef ATTRACT_DEMO_FRAMES
#define ATTRACT_DEMO_FRAMES 900
#endif

/* Demo play input: the flier hovers. It flaps while below DEMO_HOVER_Y (pixels, y grows downwards) and steers
 * sweeps right and left, switching direction every DEMO_SWEEP_FRAMES frames. */
#ifndef DEMO_HOVER_Y
#define DEMO_HOVER_Y 90
#endif
#ifndef DEMO_SWEEP_FRAMES
#define DEMO_SWEEP_FRAMES 60
#endif

/* Game over screen length. */
#ifndef GAMEOVER_FRAMES
#define GAMEOVER_FRAMES 180
#endif

/* Save reminder screen ("open the MiSTer menu before power-off") length. */
#ifndef REMINDER_FRAMES
#define REMINDER_FRAMES 240
#endif

/* Operator reset: frames the A+B+C+D combo must be held on the title screen. */
#ifndef RESET_HOLD_FRAMES
#define RESET_HOLD_FRAMES 180
#endif

/* Arena slice (src/core/stage.c, game_step_arena). The stage is static: 8 platform rectangles in the 384x180 world
 * (world 384x180, ARENA_W in arena.h; world y = screen y; water at FLIER_WATER_Y kills). Platforms are solid from above only.
 * STAGE_* and FLIER_START_* are layout/spawn constants checked by tests/host/test_stage.c, not gameplay knobs. */
#ifndef STAGE_PLATFORM_COUNT
#define STAGE_PLATFORM_COUNT 8
#endif
#ifndef STAGE_PLATFORM_H
#define STAGE_PLATFORM_H 8
#endif
#ifndef STAGE_SPAWN_COUNT
#define STAGE_SPAWN_COUNT 6 /* computer flier spawn points in stage.c; also the computer flier array size */
#endif
#ifndef FLIER_START_X
#define FLIER_START_X 192
#endif
#ifndef FLIER_START_Y
#define FLIER_START_Y 120
#endif
#ifndef FLIER_START_BALLOONS
#define FLIER_START_BALLOONS 2
#endif

/* Computer fliers (src/core/ai.c, design doc 3.1 and 5.1). Distances are screen pixels: the reference values (50, 75,
 * 32) halved for the 0.5 reference scale. Angles are Q15 components of the unit direction to the target. */
#ifndef CPU_START_COUNT
#define CPU_START_COUNT 2 /* computer fliers in match 1; +1 per match won */
#endif
#ifndef CPU_MAX
#define CPU_MAX 6 /* cap (design doc 5.1); arrays are sized STAGE_SPAWN_COUNT, so never raise it above that */
#endif
#ifndef AI_THINK_FRAMES
#define AI_THINK_FRAMES 30 /* 500 ms */
#endif
#ifndef AI_THINK_JITTER
#define AI_THINK_JITTER 8 /* +- 125 ms */
#endif
#ifndef AI_FILL_DIST
#define AI_FILL_DIST 25 /* balloon-less and farther than this: refill state (idle) */
#endif
#ifndef AI_FLEE_DIST
#define AI_FLEE_DIST 37 /* closer than this and not clearly above: flee */
#endif
#ifndef AI_ABOVE_MARGIN
#define AI_ABOVE_MARGIN 16 /* "above the target by" this many pixels keeps the flier chasing */
#endif
#ifndef AI_STEER_MIN
#define AI_STEER_MIN 8192 /* |dir.x| above 0.25 steers */
#endif
#ifndef AI_FLAP_MAX
#define AI_FLAP_MAX 16384 /* dir.y below 0.5 flaps */
#endif

/* Follow camera over the 384 px arena (src/core/camera.c, design 2026-11-10-wide-arena-camera.md section 2). */
#ifndef CAM_DEAD_ZONE_PX
#define CAM_DEAD_ZONE_PX 4 /* a resting camera ignores a target closer than this */
#endif
#ifndef CAM_EASE_SHIFT
#define CAM_EASE_SHIFT 3 /* each frame covers 1 / 2^3 of the gap */
#endif
#ifndef CAM_MAX_STEP_PX
#define CAM_MAX_STEP_PX 2 /* at most this many pixels per frame (twice the human top speed) */
#endif

/* Arena scoring (design 3.3, NOT IN REFERENCE, placeholders for the user to tune). */
#ifndef SCORE_STOMP_POP
#define SCORE_STOMP_POP 500 /* player stomp pops a computer balloon */
#endif
#ifndef SCORE_CPU_DEFEAT
#define SCORE_CPU_DEFEAT 1000 /* player defeats a computer flier (last balloon popped or body kill) */
#endif
#ifndef SCORE_CPU_DROWN
#define SCORE_CPU_DROWN 250 /* a living computer flier falls into the water (not a defeated one) */
#endif
#ifndef SCORE_MATCH_WIN
#define SCORE_MATCH_WIN 1000 /* match won */
#endif
#ifndef SCORE_MATCH_CLEAN
#define SCORE_MATCH_CLEAN 2000 /* extra when no player balloon was lost in the match */
#endif

#endif /* BRAWL_TUNING_H */
