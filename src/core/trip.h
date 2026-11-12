/*
 * trip.h - Gum Trip core: forced scroll, gum meter, streak score, run end (plan T-B2, T-B3).
 *
 * Pure logic, no hardware. Fixed point as the core: scroll speed is 16.16 px per frame, positions of the flier are
 * Flier 16.16. No division or modulo in trip_step (the speed ramp uses an error accumulator, gum decay a tick counter).
 * The flier stays in screen space (x 0..319); the world moves under it (plan spine 2, 3).
 */
#ifndef BRAWL_TRIP_H
#define BRAWL_TRIP_H

#include <stdint.h>
#include "flier.h"
#include "tuning.h"

/* Not a knob (display fact, 6 digits): the score clamps here and never wraps. */
#define TRIP_SCORE_CAP 999999u
/* Spawn point of the trip flier (screen pixels, layout constants like FLIER_START_*: not knobs). */
#define TRIP_START_X 160
#define TRIP_START_Y 90

typedef struct {
    uint32_t px;          /* whole pixels scrolled (distance); u32 holds 4e9 px */
    uint32_t frac;        /* sub-pixel part of the scroll, 0..65535 */
    uint32_t speed;       /* current scroll speed, 16.16 px per frame */
    uint32_t ramp_acc;    /* error accumulator of the speed ramp */
    uint16_t gum;         /* 0..GUM_MAX */
    uint16_t decay_tick;  /* frames since the last unit of gum was lost */
    uint32_t streak;      /* pickups since the last hit; the multiplier. Uncapped. */
    uint32_t bonus;       /* accumulated pickup points, saturates at TRIP_SCORE_CAP */
    uint32_t pickups, hits;
    uint32_t steps;       /* sentinel: calls of trip_step */
} Trip;

void trip_init(Trip *t);
/* One frame: scroll, carry the flier left and clamp it to the screen, decay gum, derive balloons, start the fall at 0. */
void trip_step(Trip *t, Flier *f);
/* Gum pickup: +GUM_PICKUP clamped to GUM_MAX, streak +1, bonus +TRIP_PICKUP_POINTS x streak. Ignored once the flier is not ALIVE. */
int trip_pickup(Trip *t, Flier *f);
/* Hazard hit: -GUM_HIT_CHUNK (floor 0), streak to 0, invincible for FLIER_INVINCIBLE_POP. Returns 0 (nothing) while invincible or not ALIVE. */
int trip_hit(Trip *t, Flier *f);
/* The hero touched the bottom wall (tunnel rock): gum goes to 0 at once and the fall starts on this frame, whatever the
 * protection (invincible, spawn_inv). Returns 1 if it killed, 0 when the flier is not ALIVE (a second call changes nothing). */
int trip_wall_kill(Trip *t, Flier *f);
/* Run end: the flier is DROWNED or GONE (the same condition the arena uses). */
int trip_over(const Flier *f);
/* Score shown to the player: distance points plus bonus, clamped to 999999. */
uint32_t trip_score(const Trip *t);
/* Balloons (0..2) derived from gum: 2 at or above the half mark, 1 above 0, else 0. */
uint8_t trip_gum_balloons(uint16_t gum);
/* Scroll speed (16.16) that applies after px whole pixels, for tests and the view: pure function of distance. */
uint32_t trip_speed_at(uint32_t px);
/* Hazards per chunk at distance px, 8.8. Uses a division: call per chunk, never per frame. */
uint32_t trip_density_at(uint32_t px);

#endif
