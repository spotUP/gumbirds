/*
 * flier.h - balloon fighter physics (pure C, host tested in tests/host/test_flier.c, no hardware, no float,
 * no libm). Numbers come from thoughts/shared/research/2026-11-09_flier-reference-spec.md (the "spec");
 * section numbers below point into it.
 *
 * - Position and velocity are int32_t 16.16 fixed point, pixels per frame at 60 Hz, 320x224 screen (arena 384 wide, wrapping: arena.h), reference
 *   scale 0.5 (spec 2.1, 2.2). (x, y) is the centre of the body box.
 * - Every lerp weight is shift-add; no `/` or `%` and no 32x32 multiply on any path (68000: no hardware
 *   divide, no 32-bit multiply). Multiplies are int16 x int16.
 * - Physics only: the caller supplies the floor under the fighter each frame (level data, spec NIR-15) and
 *   routes input and fighter pairs here.
 */
#ifndef BRAWL_FLIER_H
#define BRAWL_FLIER_H

#include <stdint.h>

#define FL_PX(n) ((int32_t)(n) * 65536) /* whole pixels to 16.16 */

/* ---- Constants. Each line: name, reference value, spec section. Raw = 16.16. ---- */
#define FLIER_GRAVITY_NO_BALLOON   1820     /* 200 px/s^2 -> 0.027778 px/frame^2 (3.1) */
#define FLIER_GRAVITY_BALLOON      728      /* 80 px/s^2 (200 x 0.4) -> 0.011111 (3.1) */
#define FLIER_TOP_AIR_SPEED        65536    /* 120 px/s red preset -> 1.0 px/frame (3.1) */
#define FLIER_TOP_LAND_SPEED       54613    /* 100 px/s -> 0.83333 (3.1) */
#define FLIER_GROUND_JUMP_VY       (-27307) /* 50 px/s up with balloons (3.1, 3.2) */
#define FLIER_GROUND_JUMP_VY_NOBAL (-54613) /* 100 px/s up, 2 x jump height, no balloon (3.2) */
#define FLIER_MIN_BOUNCE_SPEED     27307    /* 50 px/s wall/ceiling bounce minimum, ceiling too (3.6) */
#define FLIER_FALL_START_VY        (-27307) /* 50 px/s up when a fall starts (3.5) */
#define FLIER_PARACHUTE_GRAVITY    182      /* 20 px/s^2 (3.5) */
#define FLIER_PARACHUTE_SWAY       17476    /* 32 px/s sway amplitude (3.5) */
#define FLIER_KNOCKBACK_VICTIM     21845    /* 40 px/s (4.3 item 2) */
#define FLIER_KNOCKBACK_ATTACKER   40960    /* 75 px/s (4.3 item 2) */
/* Lerp weights (flap strength, land friction, air blend all 0.2; parachute sway 0.1) are the shift-add
 * functions in flier.c, taken to 8 terms so the spec's raw numbers (-13107 first flap) come out exact. */
#define FLIER_INVINCIBLE_POP       60       /* 1000 ms after losing a balloon (4.2) */
#define FLIER_INVINCIBLE_PARACHUTE 30       /* 500 ms when the last balloon goes and a parachute opens (4.2) */
#define FLIER_SWAY_PERIOD          30       /* sway target changes every 500 ms = 30 frames (3.5) */
#define FLIER_SWAY_PHASE_STEP      10430    /* one radian in 8.8 table indices: 256 / 2pi x 256 (3.5, sin(n)) */
#define FLIER_MAX_BALLOONS         2        /* art has two pods (user decision 2026-11-10); NIR-5 default was 3 */

#define FLIER_WORLD_H              180      /* 360 ref px x 0.5 (3.6) */
#define FLIER_WATER_Y              180      /* water line, kills on contact (3.6, 4.3 item 6) */
#define FLIER_REMOVE_Y             200      /* a falling fighter is gone below this (400 ref px, 3.5) */
#define FLIER_NO_FLOOR             0x7FFFFFFF /* floor_y value meaning "no floor under the fighter" */

/* Body box (4.4, ours = ref x 0.5; NIR-12: AABB of the capsule's bounding size), half extents in pixels. */
#define FLIER_HALF_W               2        /* 4 px wide */
#define FLIER_HALF_H16_BALLOON     360448   /* 11 px tall / 2, with balloons, 16.16 */
#define FLIER_HALF_H16_NOBAL       229376   /* 7 px tall / 2, without balloons, 16.16 */

typedef enum {
    FLIER_ALIVE = 0,    /* flying or standing (see on_ground) */
    FLIER_PARACHUTE,    /* last balloon lost in the air with a parachute (3.5) */
    FLIER_FALLING,      /* dead, falling, input ignored, collisions off (3.5) */
    FLIER_DROWNED,      /* touched the water; frozen, the caller plays the splash (4.3 item 6) */
    FLIER_GONE          /* fell below FLIER_REMOVE_Y, remove it */
} FlierState;

typedef struct {
    int32_t x, y;        /* body centre, 16.16 pixels */
    int32_t vx, vy;      /* pixels per frame, 16.16 */
    int32_t sway_target; /* parachute horizontal target, 16.16 */
    uint16_t sway_phase; /* 8.8 sine table index, advances once per FLIER_SWAY_PERIOD */
    uint8_t state;       /* FlierState */
    uint8_t balloons;    /* 0..FLIER_MAX_BALLOONS: the life count (4.1) */
    uint8_t invincible;  /* frames left */
    uint8_t on_ground;
    uint8_t flap_prev;   /* button level last frame, for the press edge */
    uint8_t has_parachute;
    uint8_t sway_tick;
    uint8_t facing;      /* 1 = right, 0 = left: the last non-zero input dir (view only, never read by the physics) */
} Flier;

typedef struct {
    int8_t dir;          /* -1, 0, +1 */
    uint8_t flap;        /* button level this frame (the module finds the press edge) */
} FlierInput;

void flier_init(Flier *f, int32_t x, int32_t y, uint8_t balloons, uint8_t has_parachute);
/* One frame. floor_y is the 16.16 y of the surface under the fighter (feet land on it), or FLIER_NO_FLOOR. */
void flier_step(Flier *f, const FlierInput *in, int32_t floor_y);
/* Loses one balloon unless invincible (spec 4.2). Returns 1 if a balloon popped. */
int flier_lose_balloon(Flier *f);
/* Body contact (spec 4.3 item 3, design 1.6 rules 2-3): a standing or flying flier with no balloons that another live
 * body touches starts falling. Returns 1 if it did. */
int flier_body_kill(Flier *victim, const Flier *other);
/* Body-contact reflect (spec 4.3 item 3 bounce, spec 3.6, design 1.6 rules 3-4): a (alive, with balloons) touching a live
 * body b reflects about the contact normal (axis of least penetration, from b to a) with the 50 px/s minimum. A
 * balloon-less a gets no bounce (it dies by flier_body_kill); b having no balloons does not stop a bouncing. Evaluate
 * both orders per pair, before flier_body_kill. Returns 1 if a bounced. */
int flier_body_bounce(Flier *a, const Flier *b);
/* Adds a balloon up to FLIER_MAX_BALLOONS (NIR-8 pickup). Returns 1 if added. */
int flier_add_balloon(Flier *f);
/* Half height of the body box, 16.16. */
int32_t flier_half_h(const Flier *f);
/* Attacker's feet box overlaps victim's balloon box (4.4, whole pixels). */
int flier_feet_hit(const Flier *attacker, const Flier *victim);
/* Stomp (4.3 item 1-2): if the boxes overlap and the rules allow, pops one victim balloon and applies the
 * knockback along the line between the fighters (NIR-12 default). Returns 1 if a balloon popped. */
int flier_stomp(Flier *attacker, Flier *victim);
/* Unit vector from (dx, dy) as a 256-step angle (0 = +x, 64 = +y down); (0,0) gives 0. Binary search with
 * cross products, no divide. Exposed for tests. */
uint8_t flier_angle(int32_t dx, int32_t dy);
/* Q15 sine and cosine of a 256-step angle. */
int16_t flier_sin(uint8_t a);
int16_t flier_cos(uint8_t a);

#endif
