/*
 * trip_rival.h - Gum Trip rivals (plan T-B7): computer Sootlings that enter from the right edge, chase (or patrol),
 * can be stomped and take a gum chunk from the hero on contact.
 *
 * Pure logic, no hardware, no malloc, no division or modulo and no 64-bit arithmetic in any per-frame path (spawn
 * decisions call trip_density_at, which divides, once per spawn only). A rival is a plain Flier (flier_step, flier_pair,
 * flier_pair_apply are called as they are); the hero stays in screen space (Trip carries it), a rival is carried left by
 * exactly the world scroll of the frame (Trip.px/frac delta), so it needs no x wrap (Flier.no_wrap = 1).
 *
 * Wrap note: flier_pair folds x across the 384 arena seam. Rivals live at x -16..~340 and hero at 0..319; every pair tested
 * is closer than 40 px, and a pair 340 apart folds to 44 (outside the 18 px widest pair reach), so the fold never
 * creates a false contact (tested at spawn x vs hero x 0).
 *
 * Contact: the hero and a rival use the arena pair rule (flier_pair, boxes in flier.h): the higher flier pops the lower
 * flier's gum, at the same height (feet bottoms less than FLIER_PAIR_LEVEL_PX apart) both bounce and nobody pops, a pop on
 * an invincible flier is a bounce. A hero pop costs the rival a balloon (+TRIP_RIVAL_POP_POINTS); a rival pop costs the hero
 * one gum chunk through trip_hit (streak reset, hits count, invincible window). Both fliers bounce in every contact.
 */
#ifndef BRAWL_TRIP_RIVAL_H
#define BRAWL_TRIP_RIVAL_H

#include <stdint.h>
#include "tuning.h"
#include "rng.h"
#include "flier.h"
#include "trip.h"
#include "trip_gen.h"

/* Variants (user 2026-11-10: all three; look = palette swap, behaviour = agent default):
 *   HORNET  A  agile chaser: thinks fast, steers and flaps at the hero, one balloon.
 *   BONE    B  patrol: ignores the hero, holds the altitude it spawned at, drifts with the scroll, one balloon.
 *   BRUISER C  heavy chaser: thinks slowly, chases, two balloons (two stomps). */
typedef enum { TRIP_RIVAL_HORNET = 0, TRIP_RIVAL_BONE = 1, TRIP_RIVAL_BRUISER = 2, TRIP_RIVAL_VARIANTS = 3 } TripRivalVariant;

/* trip_rivals_step / _resolve result bits */
#define TRIP_RIV_EV_SPAWN  1u   /* a rival entered */
#define TRIP_RIV_EV_POP    2u   /* the hero popped a rival balloon (stomp) */
#define TRIP_RIV_EV_HIT    4u   /* a rival touched the hero and trip_hit took gum */
#define TRIP_RIV_EV_RETIRE 8u   /* a rival left the pool (scrolled off left, fell out, drowned) */

typedef struct {
    Flier f;
    uint8_t active;
    uint8_t variant;     /* TripRivalVariant */
    uint8_t timer;       /* frames to the next think */
    int8_t dir;          /* held between thinks */
    int16_t hold_y;      /* BONE: altitude to hold, whole pixels */
    uint32_t thinks;
} TripRival;

typedef struct {
    TripRival r[TRIP_RIVAL_MAX];
    Rng rng;
    uint32_t next_px;            /* distance of the next spawn */
    uint32_t last_px, last_frac; /* Trip scroll seen last frame, to carry rivals by the exact world step */
    uint32_t spawned, popped, hits, retired;   /* sentinels */
    uint32_t blocked;            /* frames a spawn was due but the pool was full or no chunk was held */
    uint32_t steps;
} TripRivals;

void trip_rivals_init(TripRivals *R, const Trip *t, uint32_t seed);
/* Rivals alive (active), 0..TRIP_RIVAL_MAX. */
int trip_rivals_alive(const TripRivals *R);
/* Spawn due rivals, think, flier_step each (islands from trip_hit_floor_y), carry left by the frame's scroll, retire.
 * Returns SPAWN/RETIRE bits. Call after trip_step of the same frame. */
unsigned trip_rivals_advance(TripRivals *R, const Trip *t, const TripGen *g, const Flier *hero);
/* Hero against every ALIVE rival by flier_pair: hero higher pops the rival (a last balloon makes it fall; +TRIP_RIVAL_POP_POINTS),
 * rival higher pops the hero's gum (trip_hit; nothing inside the invincible window), level contact bounces. Both bounce. A solid island between the hero and the rival blocks the contact (flier_pair_blocked; g supplies the islands). Needs hero ALIVE. */
unsigned trip_rivals_resolve(TripRivals *R, Trip *t, const TripGen *g, Flier *hero);
/* advance then resolve. */
unsigned trip_rivals_step(TripRivals *R, Trip *t, const TripGen *g, Flier *hero);

#endif
