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
 * sweeps right and left, switching direction every DEMO_SWEEP_FRAMES frames. Chosen under the flap-impulse model (2026-11-11): the demo
 * flier cannot dodge, and 12 of 12 demos from different start frames end with it alive (the earlier 90 / 60 survived 4 of 12).
 * 2026-11-13: 50, above the rival ceiling (FLIER_RIVAL_CEILING_DROP below the hero ceiling): a rival never gets above the demo flier, and the higher
 * flier wins a bump. At 120 the flier hovered under the rivals and lost gum to them once they lifted off together. */
#ifndef DEMO_HOVER_Y
#define DEMO_HOVER_Y 50
#endif
#ifndef DEMO_SWEEP_FRAMES
#define DEMO_SWEEP_FRAMES 90
#endif

/* Attract overlay (how-to-play words and icons): least frames the action word, lever and A icon stay on one state before they may
 * change. First value 15 (a quarter second): the demo flaps about every 20 frames, so FLAP and STEER both show without flicker. */
#ifndef ATTRACT_HOLD_FRAMES
#define ATTRACT_HOLD_FRAMES 15
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

/* Flier flight model (src/core/flier.c), user decisions 2026-11-11. 16.16 fixed point, pixels per frame at 60 fps. */
#ifndef FLIER_FLAP_IMPULSE
#define FLIER_FLAP_IMPULSE 47104 /* upward speed added to vy by each air flap; 15% above the reference ratio (user 2026-11-12: flaps too weak) */
#endif
#ifndef FLIER_FLAP_COOLDOWN
#define FLIER_FLAP_COOLDOWN 9 /* frames between two flaps; a press inside it does nothing */
#endif
#ifndef FLIER_FLAP_THRUST_X
#define FLIER_FLAP_THRUST_X 38229 /* sideways speed added to vx by each air flap with a direction held */
#endif
#ifndef FLIER_FALL_MAX
#define FLIER_FALL_MAX 109227 /* downward speed cap */
#endif
#ifndef FLIER_FALL_MAX_NO_BALLOON
#define FLIER_FALL_MAX_NO_BALLOON 174763 /* downward speed cap without gum (2.6667 px/frame; also the dead fall) */
#endif
#ifndef FLIER_FLAP_IMPULSE_ONE_GUM
#define FLIER_FLAP_IMPULSE_ONE_GUM 39253 /* upward speed added by each air flap (and the ground jump) with exactly one gum */
#endif
#ifndef FLIER_PARACHUTE_FALL_MAX
#define FLIER_PARACHUTE_FALL_MAX 21845 /* downward speed cap under a parachute (0.3333 px/frame); a faster arrival is clamped */
#endif
#ifndef FLIER_GROUND_ACCEL
#define FLIER_GROUND_ACCEL 3793 /* walking speed change per frame on the ground (top walk speed in 24 frames) */
#endif
#ifndef FLIER_RISE_MAX
#define FLIER_RISE_MAX 109227 /* upward speed cap */
#endif

/* Flier contact boxes (src/core/flier.c flier_pair), whole pixels, measured on the Sootling art; see flier.h. A box is
 * centred on the flier x and measured upward from the feet bottom of the flier that owns it. */
#ifndef FLIER_BODY_HALF_W
#define FLIER_BODY_HALF_W 7 /* body half width */
#endif
#ifndef FLIER_BODY_TOP
#define FLIER_BODY_TOP 22 /* body height above the feet bottom; also where the gum starts */
#endif
#ifndef FLIER_GUM_HALF_W2
#define FLIER_GUM_HALF_W2 9 /* gum rim half width with two balloons */
#endif
#ifndef FLIER_GUM_HALF_W1
#define FLIER_GUM_HALF_W1 5 /* gum rim half width with one balloon */
#endif
#ifndef FLIER_GUM_BOTTOM
#define FLIER_GUM_BOTTOM 22 /* gum bottom edge above the feet bottom */
#endif
#ifndef FLIER_CEILING_FEET_Y
#define FLIER_CEILING_FEET_Y 31 /* lowest allowed feet bottom row at the top: the gum top (31 above the feet) sits on screen row 0, so the whole flier shows */
#endif
#ifndef FLIER_RIVAL_CEILING_DROP
#define FLIER_RIVAL_CEILING_DROP 32 /* computer fliers bounce off a line this many px below the hero ceiling, so the hero always fits above a rival at the top */
#endif
#ifndef FLIER_BOUNCE_RESTITUTION
#define FLIER_BOUNCE_RESTITUTION 205 /* every bounce (fliers, platform sides and underside, ceiling) keeps 205/256 of the approaching speed */
#endif
#ifndef FLIER_SPIKE_BOUNCE_MIN_VY
#define FLIER_SPIKE_BOUNCE_MIN_VY 65536 /* a dead body bouncing on spike tips leaves at least 1.0 px/frame upward (hop of about 9.6 px at FLIER_GRAVITY_NO_BALLOON 3413), so a slow arrival still shows a bounce */
#endif
#ifndef FLIER_PAIR_LEVEL_PX
#define FLIER_PAIR_LEVEL_PX 4 /* feet bottoms closer than this are level: gum meets gum and both bounce */
#endif

/* Sootling ground clips and flap clip (src/core/flier_view.c), user decisions 2026-11-11. Holds are 60 Hz ticks per art frame,
 * the same for every balloon count. */
#ifndef FLIER_WALK_HOLD
#define FLIER_WALK_HOLD 3 /* ticks per walk frame (8 frames, 24 ticks per cycle) */
#endif
#ifndef FLIER_LAND_HOLD_0
#define FLIER_LAND_HOLD_0 9 /* ticks on landing frame 0 (the squash) */
#endif
#ifndef FLIER_LAND_HOLD_1
#define FLIER_LAND_HOLD_1 12 /* ticks on landing frame 1 (the recovery) */
#endif
#ifndef FLIER_BREATHE_HOLD_0
#define FLIER_BREATHE_HOLD_0 36 /* ticks on breathing frame 0 (rest) */
#endif
#ifndef FLIER_BREATHE_HOLD_1
#define FLIER_BREATHE_HOLD_1 15 /* ticks on breathing frame 1 */
#endif
#ifndef FLIER_BREATHE_HOLD_2
#define FLIER_BREATHE_HOLD_2 21 /* ticks on breathing frame 2 */
#endif
#ifndef FLIER_BREATHE_HOLD_3
#define FLIER_BREATHE_HOLD_3 15 /* ticks on breathing frame 3 */
#endif
#ifndef FLIER_WALK_MIN_VX
#define FLIER_WALK_MIN_VX 8192 /* 16.16 px/frame: a grounded flier slower than this (0.125 px/frame, the first two frames of ground acceleration or the last two of braking) stands and breathes instead of walking */
#endif
#ifndef FLIER_FLAP_HOLD
#define FLIER_FLAP_HOLD 2 /* ticks per flap frame: 8 frames, 16 ticks per play; a press sooner than that cuts the wingbeat and restarts it */
#endif

/* Arena slice (src/core/stage.c, game_step_arena). The stage layout is picked per round: up to 8 platform rectangles in the 384x180 world
 * (world 384x180, ARENA_W in arena.h; world y = screen y; each flier's kill_y, set per hazard kind, kills; FLIER_WATER_Y is only the default). Platforms are solid on every side (flier_collide_solids), the box STAGE_PLATFORM_H deep.
 * STAGE_* and FLIER_START_* are layout/spawn constants checked by tests/host/test_stage.c, not gameplay knobs. */
#ifndef STAGE_PLATFORM_COUNT
#define STAGE_PLATFORM_COUNT 8 /* platform slots of the largest layout (user decision: 8); a layout with fewer islands leaves the rest zero (w 0 = unused, no columns drawn) */
#endif
#ifndef STAGE_PLATFORM_H
#define STAGE_PLATFORM_H 12 /* solid depth below the standing line: the drawn island art (assets/islands, 16 px piece, line row 4) ends 12 px below it */
#endif
#ifndef STAGE_SPAWN_COUNT
#define STAGE_SPAWN_COUNT 6 /* computer flier spawn points per layout in stage.c; also the computer flier array size (arcade layouts hold 3 to 6 rivals, stage_rival_count) */
#endif
#ifndef FLIER_START_X
#define FLIER_START_X 40
#endif
#ifndef FLIER_START_Y
#define FLIER_START_Y 158
#endif
#ifndef FLIER_HIT_COOLDOWN
#define FLIER_HIT_COOLDOWN 20 /* frames of immunity after a balloon pops (BR-D4); was 60. The parachute window stays FLIER_INVINCIBLE_PARACHUTE */
#endif
#ifndef FLIER_SPAWN_INVINCIBLE
#define FLIER_SPAWN_INVINCIBLE 600 /* frames the player is immune after a spawn; any left/right/flap input ends it early (BR-D5) */
#endif
#ifndef FLIER_BLINK_HALF_PERIOD
#define FLIER_BLINK_HALF_PERIOD 4 /* frames shown, then the same number hidden, while a flier is protected (invincible or spawn_inv) */
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
#define CPU_MAX 3 /* arena cap (design doc 5.1); arcade stages use stage_rival_count instead; arrays are sized STAGE_SPAWN_COUNT */
#endif
#ifndef AI_THINK_FRAMES
#define AI_THINK_FRAMES 30 /* 500 ms */
#endif
#ifndef AI_THINK_JITTER
#define AI_THINK_JITTER 8 /* +- 125 ms */
#endif
#ifndef AI_RANK_THINK_STEP
#define AI_RANK_THINK_STEP 6 /* arcade: each rival rank above 1 thinks this many frames sooner (rank 1 is the arena value) */
#endif
#ifndef ARC_LIVES_START
#define ARC_LIVES_START 3 /* lives in an arcade run (own first value) */
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
#ifndef AI_OVERHEAD_PX
#define AI_OVERHEAD_PX 24 /* a platform whose underside is this close above a flier that wants to climb makes it steer to the nearer edge */
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
#ifndef MATCH_END_FRAMES
#define MATCH_END_FRAMES 120 /* round end banner hold (RE_HOLD) before the camera slide back to the spawn (user 2026-11-11) */
#endif
#ifndef ROUND_START_TEXT_FRAMES
#define ROUND_START_TEXT_FRAMES 60 /* "ROUND nn" shown with everything frozen (user decision 2026-11-11) */
#endif
#ifndef ROUND_GO_TEXT_FRAMES
#define ROUND_GO_TEXT_FRAMES 30 /* "GO!" shown with everything frozen */
#endif
#ifndef SCORE_MATCH_CLEAN
#define SCORE_MATCH_CLEAN 2000 /* extra when no player balloon was lost in the match */
#endif

/* Gum Trip (src/core/trip.c, plan 2026-11-10-gum-trip-build-plan.md section 5). */
/* Scroll speed, 16.16 px per frame. Start 0.75 and cap 1.0 (= FLIER_TOP_AIR_SPEED): user decisions 2026-11-10/11. */
#ifndef TRIP_SCROLL_START
#define TRIP_SCROLL_START 49152
#endif
#ifndef TRIP_SCROLL_MAX
#define TRIP_SCROLL_MAX 65536
#endif
/* Whole pixels scrolled until the speed reaches TRIP_SCROLL_MAX (plan section 5 proposal; ramp is continuous, user 2026-11-11). */
#ifndef TRIP_RAMP_PX
#define TRIP_RAMP_PX 20000
#endif
/* Gum meter (plan section 5 proposals, tuned in play). Units of gum; the meter has a half mark at GUM_MAX / 2. */
#ifndef GUM_MAX
#define GUM_MAX 1024
#endif
#ifndef GUM_START
#define GUM_START 768
#endif
/* Frames per unit of gum lost: 2 gives 0.5 gum per frame (plan section 5). */
#ifndef GUM_DECAY_FRAMES
#define GUM_DECAY_FRAMES 2
#endif
/* Game frames per sheet frame of the player's gum bubble (src/core/gum_view.c): wobble loop, then pop one shot. */
#ifndef GUM_WOBBLE_FRAMES
#define GUM_WOBBLE_FRAMES 6
#endif
#ifndef GUM_POP_FRAMES
#define GUM_POP_FRAMES 3
#endif
/* Where the bubble hangs on the player (src/core/gum_view.c, Sootling E art): its bottom edge sits GUM_BIRD_ROW pixels below the
 * bird sprite top plus the per frame dy; its string column is the bird's string column, GUM_BIRD_DX / GUM_BIRD_DX_FLIP pixels
 * from the bird centre (the mirrored bird's string is one pixel further left). */
#ifndef GUM_BIRD_ROW
#define GUM_BIRD_ROW 8
#endif
#ifndef GUM_BIRD_DX
#define GUM_BIRD_DX 1
#endif
#ifndef GUM_BIRD_DX_FLIP
#define GUM_BIRD_DX_FLIP 0
#endif
/* Game frames per sheet frame of the splash a flier makes in water and in lava (src/core/splash_view.c; assets/splash/splash.json). */
#ifndef SPLASH_TICKS
#define SPLASH_TICKS 3
#endif
#ifndef SPLASH_LAVA_TICKS
#define SPLASH_LAVA_TICKS 4
#endif
#ifndef GUM_PICKUP
#define GUM_PICKUP 256
#endif
#ifndef GUM_HIT_CHUNK
#define GUM_HIT_CHUNK 256
#endif
/* Score (plan section 5, user 2026-11-10/11): distance points = scrolled px >> TRIP_SCORE_PX_SHIFT (1 per 8 px);
 * a pickup adds TRIP_PICKUP_POINTS x streak (uncapped streak, breaks only on a hit). */
#ifndef TRIP_SCORE_PX_SHIFT
#define TRIP_SCORE_PX_SHIFT 3
#endif
#ifndef TRIP_PICKUP_POINTS
#define TRIP_PICKUP_POINTS 50
#endif
/* Hazard density per chunk (plan section 5): 0 until TRIP_DENSITY_START_PX, rising linearly to TRIP_DENSITY_MAX
 * hazards per chunk at TRIP_DENSITY_FULL_PX. Returned in 8.8 (256 = one hazard per chunk). */
#ifndef TRIP_DENSITY_START_PX
#define TRIP_DENSITY_START_PX 600
#endif
#ifndef TRIP_DENSITY_FULL_PX
#define TRIP_DENSITY_FULL_PX 8000
#endif
#ifndef TRIP_DENSITY_MAX
#define TRIP_DENSITY_MAX 3
#endif

/* Gum Trip layout generator (src/core/trip_gen.c, plan T-B5) and collision (src/core/trip_hit.c, T-B6). Sources of the
 * numbers are named per knob; "agent default" values are tuned in play. */
/* Chunk width in world px (plan T-B5 proposal 192). Must be a multiple of TRIP_SLOT_PX (trip_gen.h), 4 to 8 slots. */
#ifndef TRIP_CHUNK_PX
#define TRIP_CHUNK_PX 192
#endif
/* Window height in rows (user decision 2026-11-11): about 144 at distance 0, shrinking to about 120 as trip_density_at
 * reaches its maximum; difficulty comes from hazard density, not from narrow walls. With the gap at or above 120 the
 * hazard need (trip_gen.c try_layout) never exceeds it, so hazards never widen a window. */
#ifndef TRIP_GAP_MIN
#define TRIP_GAP_MIN 120
#endif
#ifndef TRIP_GAP_START
#define TRIP_GAP_START 144
#endif
/* Free corridor height that must remain beside every hazard and between chunks: flier box (11 px with balloons) plus
 * 6 px each side (agent default). */
#ifndef TRIP_PASS_MIN
#define TRIP_PASS_MIN 24
#endif
/* Pickup spacing in world px between consecutive pickups (plan section 5: 256..448, mean about 352). Pickups sit on
 * the slot grid, so the spacing is a whole number of slots inside this band (6..9 slots = 288..432, mean 360). */
#ifndef TRIP_PICKUP_SPACING_MIN
#define TRIP_PICKUP_SPACING_MIN 256
#endif
#ifndef TRIP_PICKUP_SPACING_MAX
#define TRIP_PICKUP_SPACING_MAX 448
#endif
/* Slot (0..slots-1) of the single pickup in chunk 0 (plan F5; agent default 3, x 168 px, right of the start). */
#ifndef TRIP_FIRST_PICKUP_SLOT
#define TRIP_FIRST_PICKUP_SLOT 3
#endif
/* Hazard kind by distance band (main-session proposal, plan decisions 2026-11-10): coal C below TRIP_BAND_VENT_PX,
 * vent B below TRIP_BAND_CLOUD_PX, cloud A beyond. One kind per chunk keeps the worst scanline at one instance. */
#ifndef TRIP_BAND_VENT_PX
#define TRIP_BAND_VENT_PX 2700
#endif
#ifndef TRIP_BAND_CLOUD_PX
#define TRIP_BAND_CLOUD_PX 5400
#endif
/* ---- Gum Trip rivals (trip_rival.h; user decisions 2026-11-11: variant by distance band, pop worth 100 flat) ---- */
/* Rivals alive at once (plan section 5: max 2). */
#ifndef TRIP_RIVAL_MAX
#define TRIP_RIVAL_MAX 2
#endif
/* First rival at this scrolled distance and the base spacing to the next (plan section 5: 1200, then 1500). */
#ifndef TRIP_RIVAL_FIRST_PX
#define TRIP_RIVAL_FIRST_PX 1200
#endif
#ifndef TRIP_RIVAL_EVERY_PX
#define TRIP_RIVAL_EVERY_PX 1500
#endif
/* Density ramp (agent default): the spacing shrinks by ((density 8.8 >> 2) * K) >> 6 px, i.e. K * density per chunk at
 * 256 = one hazard per chunk (K 250: 750 px less at the 3-per-chunk maximum), never below TRIP_RIVAL_EVERY_MIN_PX. */
#ifndef TRIP_RIVAL_DENSITY_K
#define TRIP_RIVAL_DENSITY_K 250
#endif
#ifndef TRIP_RIVAL_EVERY_MIN_PX
#define TRIP_RIVAL_EVERY_MIN_PX 600
#endif
/* Spawn centre x (agent default 336: the 24 px wide art then starts at 324, right of the 320 px screen) and the left
 * retire x (agent default -16: the art right edge, centre + 12, is left of the screen). */
#ifndef TRIP_RIVAL_SPAWN_X
#define TRIP_RIVAL_SPAWN_X 336
#endif
#ifndef TRIP_RIVAL_RETIRE_X
#define TRIP_RIVAL_RETIRE_X (-16)
#endif
/* Bonus points for popping a rival (plan T-B8 gives none: agent default 100). Added to Trip.bonus, no streak change. */
#ifndef TRIP_RIVAL_POP_POINTS
#define TRIP_RIVAL_POP_POINTS 100
#endif
/* Think interval per variant in frames, plus 0..7 random (agent defaults). */
#ifndef TRIP_RIVAL_THINK_HORNET
#define TRIP_RIVAL_THINK_HORNET 14
#endif
#ifndef TRIP_RIVAL_THINK_BONE
#define TRIP_RIVAL_THINK_BONE 20
#endif
#ifndef TRIP_RIVAL_THINK_BRUISER
#define TRIP_RIVAL_THINK_BRUISER 22
#endif
/* Rival variant by the trip distance at spawn: Hornet below TRIP_RIVAL_BAND_BONE_PX, Bone from it, Bruiser from
 * TRIP_RIVAL_BAND_BRUISER_PX (user 2026-11-11: 2700 and 5400, the hazard kind bands). */
#ifndef TRIP_RIVAL_BAND_BONE_PX
#define TRIP_RIVAL_BAND_BONE_PX 2700
#endif
#ifndef TRIP_RIVAL_BAND_BRUISER_PX
#define TRIP_RIVAL_BAND_BRUISER_PX 5400
#endif
/* Frames each mode's table shows on the attract table screen before the other mode's takes over (user 2026-11-11:
 * 240 Arena then 240 Gum Trip inside the 480 frame table screen). Must be > 0. */
#ifndef SCORE_TABLE_SWAP_FRAMES
#define SCORE_TABLE_SWAP_FRAMES 240
#endif
#if SCORE_TABLE_SWAP_FRAMES <= 0
#error "SCORE_TABLE_SWAP_FRAMES must be positive"
#endif
/* Hit box half extents (plan: A 36x26, B 20x20, C 16x14) and vertical sweep amplitude (agent default; the art drafts
 * give no sweep). The generator reserves the swept box. */
#ifndef TRIP_COAL_AMP
#define TRIP_COAL_AMP 6
#endif
#ifndef TRIP_VENT_AMP
#define TRIP_VENT_AMP 4
#endif
#ifndef TRIP_CLOUD_AMP
#define TRIP_CLOUD_AMP 4
#endif
/* Largest random move of the window top between chunks (agent default) and largest allowed window centre move
 * (plan F2: must be climbable within one chunk at max scroll; the test measures the flier against it). */
#ifndef TRIP_WIN_STEP_MAX
#define TRIP_WIN_STEP_MAX 24
#endif
#ifndef TRIP_CENTRE_REACH
#define TRIP_CENTRE_REACH 96
#endif
/* Chance in percent of an island in a chunk (agent default) and its thickness; islands sit on the window floor. */
#ifndef TRIP_ISLAND_PCT
#define TRIP_ISLAND_PCT 50
#endif
#ifndef TRIP_ISLAND_H
#define TRIP_ISLAND_H 8
#endif
#ifndef TRIP_HAZ_KNOCK_MIN_SPEED
#define TRIP_HAZ_KNOCK_MIN_SPEED 65536 /* 16.16: least speed away from a hazard after a touch (1.0 px/frame, same value as FLIER_SPIKE_BOUNCE_MIN_VY); a slow or still hero is knocked back at least this fast */
#endif
#ifndef TRIP_ISLAND_SOLID_H
#define TRIP_ISLAND_SOLID_H 12 /* solid depth below an island's standing line: the drawn art (16 px piece, line row 4) ends 12 px below it */
#endif
/* Generate this many px beyond the right screen edge (agent default). */
#ifndef TRIP_GEN_AHEAD_PX
#define TRIP_GEN_AHEAD_PX 96
#endif
/* Sweep speed of the moving hazards in 256-step phase units per frame (agent default 3: period about 85 frames). */
#ifndef TRIP_SWEEP_STEP
#define TRIP_SWEEP_STEP 3
#endif

#endif /* BRAWL_TUNING_H */
