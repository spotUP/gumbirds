/*
 * tuning.h - every gameplay constant for Roofline in one place.
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
 * Exemptions (constants that are not knobs): MAX_OBSTACLES below is only the capacity of the
 * obstacle pool. SCREEN_W and SCREEN_H are hardware facts, not tuning. They are not overridable
 * in tests.
 *
 * Hit box note: the hero sprite is 34x40. The hit box is smaller (HERO_W x HERO_H) so that
 * near misses feel fair. See HERO_W and HERO_H.
 */
#ifndef ROOFLINE_TUNING_H
#define ROOFLINE_TUNING_H

#define SCREEN_W 320
#define SCREEN_H 224
#define MAX_OBSTACLES 8

/* Left edge of the hero hitbox in screen pixels. The hero never moves horizontally. */
#ifndef HERO_X
#define HERO_X 48
#endif

/* Hitbox width. The sprite is 34 wide; 4 px are shaved off each side so grazing a corner is forgiven. */
#ifndef HERO_W
#define HERO_W 26
#endif

/* Standing hitbox height. The sprite is 40 tall; 4 px are shaved off the top (hair and cap). */
#ifndef HERO_H
#define HERO_H 36
#endif

/* Ducking hitbox height. */
#ifndef HERO_DUCK_H
#define HERO_DUCK_H 18
#endif

/* Screen y of the floor line (hero feet). Screen is 320x224. */
#ifndef GROUND_Y
#define GROUND_Y 176
#endif

/* Initial upward jump speed, 8.8 px per frame (7.0). */
#ifndef JUMP_VEL
#define JUMP_VEL 1792
#endif

/* Downward acceleration, 8.8 px per frame squared (about 0.4). */
#ifndef GRAVITY
#define GRAVITY 102
#endif

/* Scroll speed at distance 0, 8.8 px per frame (2.0). */
#ifndef SPEED_BASE
#define SPEED_BASE 512
#endif

/* Scroll speed cap, 8.8 px per frame (5.0). */
#ifndef SPEED_MAX
#define SPEED_MAX 1280
#endif

/* Distance in pixels needed to add 1/256 px per frame of speed. Smaller is a faster ramp. */
#ifndef SPEED_RAMP_PX
#define SPEED_RAMP_PX 64
#endif

/* Spawn spacing in pixels at distance 0. */
#ifndef GAP_START
#define GAP_START 300
#endif

/* Smallest spawn spacing in pixels (hard floor of the ramp). */
#ifndef GAP_END
#define GAP_END 170
#endif

/* Distance in pixels needed to shrink the spacing by 1 px. */
#ifndef GAP_RAMP_PX
#define GAP_RAMP_PX 100
#endif

/* Random extra spacing in pixels, 0 to this minus 1. */
#ifndef GAP_JITTER
#define GAP_JITTER 80
#endif

/* Spawn weight of floor vents (jump only). */
#ifndef SPAWN_W_VENT
#define SPAWN_W_VENT 30
#endif

/* Spawn weight of high cables (duck only). */
#ifndef SPAWN_W_CABLE
#define SPAWN_W_CABLE 25
#endif

/* Spawn weight of drones (shootable, flying at head height). */
#ifndef SPAWN_W_DRONE
#define SPAWN_W_DRONE 20
#endif

/* Spawn weight of rooftop bots (shootable, on the ground). */
#ifndef SPAWN_W_BOT
#define SPAWN_W_BOT 25
#endif

/* Vent width in pixels. */
#ifndef VENT_W
#define VENT_W 32
#endif

/* Vent height in pixels. */
#ifndef VENT_H
#define VENT_H 24
#endif

/* Cable width in pixels. */
#ifndef CABLE_W
#define CABLE_W 48
#endif

/* Cable thickness in pixels. */
#ifndef CABLE_H
#define CABLE_H 16
#endif

/* Height of the cable underside above the floor in pixels. */
#ifndef CABLE_BOTTOM
#define CABLE_BOTTOM 28
#endif

/* Drone width in pixels. */
#ifndef DRONE_W
#define DRONE_W 28
#endif

/* Drone height in pixels. */
#ifndef DRONE_H
#define DRONE_H 20
#endif

/* Height of the drone underside above the floor in pixels. */
#ifndef DRONE_BOTTOM
#define DRONE_BOTTOM 26
#endif

/* Bot width in pixels. */
#ifndef BOT_W
#define BOT_W 28
#endif

/* Bot height in pixels. */
#ifndef BOT_H
#define BOT_H 28
#endif

/* Extra leftward speed of enemies on top of the scroll, 8.8 px per frame (0.5). */
#ifndef ENEMY_EXTRA_SPEED
#define ENEMY_EXTRA_SPEED 128
#endif

/* Laser bolt length in pixels. */
#ifndef LASER_W
#define LASER_W 16
#endif

/* Laser bolt thickness in pixels. */
#ifndef LASER_H
#define LASER_H 6
#endif

/* Laser bolt speed, 8.8 px per frame (8.0). */
#ifndef LASER_SPEED
#define LASER_SPEED 2048
#endif

/* Frames between shots while A is held. */
#ifndef LASER_FIRE_INTERVAL
#define LASER_FIRE_INTERVAL 8
#endif

/* Bolt top edge, pixels below the top of the hero hitbox. */
#ifndef LASER_Y_OFFSET
#define LASER_Y_OFFSET 8
#endif

/* Bolts alive at once (capacity of the bolt pool). */
#ifndef MAX_BOLTS
#define MAX_BOLTS 4
#endif

/* Heat that triggers the overheat lockout. */
#ifndef HEAT_MAX
#define HEAT_MAX 256
#endif

/* Heat added per shot. */
#ifndef HEAT_PER_SHOT
#define HEAT_PER_SHOT 48
#endif

/* Heat removed per frame. */
#ifndef HEAT_COOL
#define HEAT_COOL 3
#endif

/* Frames the light stays dark after an overheat (1.5 s at 60 fps). */
#ifndef LOCKOUT_FRAMES
#define LOCKOUT_FRAMES 90
#endif

/* Base score per kill. */
#ifndef KILL_SCORE
#define KILL_SCORE 200
#endif

/* Frames after a kill in which the next kill extends the chain. */
#ifndef CHAIN_WINDOW
#define CHAIN_WINDOW 120
#endif

/* Highest score multiplier. Multiplier is 1 plus the chain length, capped here. */
#ifndef CHAIN_MAX
#define CHAIN_MAX 5
#endif

/* Distance score: one point per 2^DIST_SHIFT pixels travelled. */
#ifndef DIST_SHIFT
#define DIST_SHIFT 3
#endif

/* A dodged hazard passing closer than this many pixels counts as a near miss. */
#ifndef NEAR_MISS_PX
#define NEAR_MISS_PX 8
#endif

/* Score for each near miss. */
#ifndef NEAR_MISS_BONUS
#define NEAR_MISS_BONUS 50
#endif

/* Lives at the start of a run. */
#ifndef LIVES_START
#define LIVES_START 3
#endif

/* Frames of invulnerability after a hit. */
#ifndef INVULN_FRAMES
#define INVULN_FRAMES 120
#endif

/* Hero look after a hit (hero_view.c): frames the knocked-back HIT pose shows right after the hit. */
#ifndef HIT_POSE_FRAMES
#define HIT_POSE_FRAMES 10
#endif

/* Hero look after a hit: after the HIT pose the hero runs on and blinks; frames per visible or hidden phase. */
#ifndef HIT_BLINK_FRAMES
#define HIT_BLINK_FRAMES 4
#endif

/* ---- Screen flow (flow.c, nameentry.c) ---- */

/* Name entry: frames a direction must be held before it repeats, then frames between repeats. */
#ifndef NAME_REPEAT_DELAY
#define NAME_REPEAT_DELAY 20
#endif
#ifndef NAME_REPEAT_RATE
#define NAME_REPEAT_RATE 5
#endif

/* Name entry: frames without any input before the name typed so far is accepted (30 s). */
#ifndef NAME_TIMEOUT_FRAMES
#define NAME_TIMEOUT_FRAMES 1800
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

/* Arena slice (src/core/stage.c, game_step_arena). The stage is static: 8 platform rectangles in the 320x180 world
 * (world x = screen x, world y = screen y; water at FLIER_WATER_Y kills). Platforms are solid from above only.
 * STAGE_* and FLIER_START_* are layout/spawn constants checked by tests/host/test_stage.c, not gameplay knobs. */
#ifndef STAGE_PLATFORM_COUNT
#define STAGE_PLATFORM_COUNT 8
#endif
#ifndef STAGE_PLATFORM_H
#define STAGE_PLATFORM_H 8
#endif
#ifndef FLIER_START_X
#define FLIER_START_X 160
#endif
#ifndef FLIER_START_Y
#define FLIER_START_Y 120
#endif
#ifndef FLIER_START_BALLOONS
#define FLIER_START_BALLOONS 2
#endif

#endif /* ROOFLINE_TUNING_H */
