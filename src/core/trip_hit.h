/*
 * trip_hit.h - Gum Trip collision (plan T-B6): flier against the generated hazards, kill strips, pickups and islands.
 *
 * Pure logic, no hardware, no malloc, no division or modulo, no 64-bit arithmetic. The flier is in screen space (x 0..319);
 * the world is shifted by Trip.px whole pixels (the sub-pixel scroll Trip.frac is ignored: agent default). All tests are
 * done in integers relative to a chunk start, so the 32-bit world x never overflows.
 *
 * Box conventions (reused from the arena, source flier.c body_overlap, whole pixels, edges inclusive):
 *   - Flier body box: centre (x >> 16, y >> 16), half width FLIER_HALF_W, half height (flier_half_h >> 16) + 1.
 *   - Hazard and pickup: two boxes overlap when |centre distance| <= sum of half extents on both axes. Touching at the
 *     edge counts, one pixel further apart does not (same as body_overlap, where penetration 0 still overlaps).
 *   - Hazard half extents are TripGenHazard.hw/hh; the centre y sweeps (trip_hit_haz_y). Pickup half extent TRIP_PICKUP_HALF.
 *   - Kill strips are rows: the top strip is rows 0..win_top-1, the bottom strip rows win_bottom..179. The flier box is
 *     rows y-h..y+h; it hits the top strip when y - h <= win_top - 1 and the bottom strip when y + h >= win_bottom.
 *   - Islands only land the flier (top surface); sides and underside are passable, as the arena platforms.
 */
#ifndef BRAWL_TRIP_HIT_H
#define BRAWL_TRIP_HIT_H

#include <stdint.h>
#include "trip.h"
#include "trip_gen.h"

/* TRIP_SWEEP_STEP (sweep speed of the moving hazards) is a knob in tuning.h. */

/* trip_collide result bits */
#define TRIP_EV_PICKUP 1u   /* at least one pickup was collected (trip_pickup called for each) */
#define TRIP_EV_HIT    2u   /* a hit was applied (trip_hit returned 1) */

/* Centre y of a moving hazard at the given frame (Trip.steps): y + amp * sin(phase + frame * TRIP_SWEEP_STEP). The view
 * must use the same function. Pure; period 256 / gcd(256, TRIP_SWEEP_STEP) frames. */
int trip_hit_haz_y(const TripGenHazard *h, uint32_t frame);

/* 16.16 y of the highest island top that is at or below the flier's feet and under it (arena rule of stage_floor_y:
 * top >= feet, horizontal overlap strictly inside, box half width FLIER_HALF_W), else FLIER_NO_FLOOR. Pass it to
 * flier_step in the same frame, before the step. */
int32_t trip_hit_floor_y(const Trip *t, const TripGen *g, const Flier *f);

/* The solid boxes (flier_collide_solids) of the islands near the flier, in the same frame as trip_hit_floor_y (the
 * island placed by the chunk offset t->px - wx, so the box is in the flier's x). The box hangs TRIP_ISLAND_SOLID_H
 * below the island top. Writes at most max boxes, returns the count. */
/* Room for the islands of the chunks around the flier. */
#define TRIP_SOLIDS_MAX 8
int trip_hit_solids(const Trip *t, const TripGen *g, const Flier *f, FlierSolid *out, int max);

/* One frame after flier_step: walks only the held chunks whose x range the flier box reaches. Each pickup touched is
 * scored with trip_pickup and removed (TripGenPickup.present = 0) only when trip_pickup took it, so it scores once; a
 * hazard or strip overlap calls trip_hit once (it ignores the invincible window). Boxes use the flier size at call start.
 * Returns TRIP_EV_* bits. Chunks retired by tripgen_advance are never tested. */
unsigned trip_collide(Trip *t, TripGen *g, Flier *f);

/* The y interval (16.16) the flier centre may take so its box stays out of the tunnel rock of every chunk it overlaps
 * (rows y-h..y+h clear of rows 0..win_top-1 and win_bottom..179; with two chunks, the intersection). Returns 0 and leaves
 * lo/hi alone when no chunk overlaps or the interval is empty. */
int trip_hit_window(const Trip *t, const TripGen *g, const Flier *f, int32_t *lo, int32_t *hi);

/* Solid rock: an ALIVE or PARACHUTE flier whose box reaches a rock row is set to the window edge and its vy, when it
 * points into the rock, is reflected with flier_reflect (the restitution of the other bounces). FALLING and later states
 * pass through. Returns 1 if it pushed. Call after trip_collide (the hit tests overlap, the push removes it). */
int trip_hit_clamp_window(const Trip *t, const TripGen *g, Flier *f);
/* Same, with the flier's y at the start of the step: a computer flier that began above its lowered line keeps the hero line. */
int trip_hit_clamp_window_from(const Trip *t, const TripGen *g, Flier *f, int32_t y_before);

/* Hero against the tunnel walls (user decision 2026-11-11), for an ALIVE hero before and after the hazard push:
 * trip_hit_wall_touch: TRIP_WALL_TOP when the centre is above the window line (gum top 31 px under the rock row win_top),
 * TRIP_WALL_BOTTOM when it is below the lowest line (body box on the last clear row), else 0 (also 0 for FALLING and later).
 * trip_hit_hero_walls: bottom touch kills at once (trip_wall_kill, returns TRIP_EV_HIT, no clamp, no bounce); top touch
 * clamps to the line and reflects vy (flier_reflect), no gum loss. Rivals keep the bounce on both walls through
 * trip_hit_clamp_window_from. Call it before trip_collide, so the strip hit test never sees the hero inside the rock. */
#define TRIP_WALL_TOP    1
#define TRIP_WALL_BOTTOM 2
int trip_hit_wall_touch(const Trip *t, const TripGen *g, const Flier *f);
unsigned trip_hit_hero_walls(Trip *t, const TripGen *g, Flier *f);

/* Hero against the hazards, after trip_collide (which applied the gum loss and the cooldown): for every hazard box the hero
 * still overlaps, in invincible frames too, push the hero out along the axis that needs the shorter push (a tie goes
 * vertical, zero offset pushes up), in whole pixels, and bounce the velocity on that axis away from the hazard (flier_reflect
 * when it points into the hazard, at least TRIP_HAZ_KNOCK_MIN_SPEED). ALIVE and PARACHUTE only. The x push is clamped to
 * 0..319; a hero held at x 0 by the scroll can stay overlapped (the left edge pin, see the results note). */
void trip_hit_haz_bounce(const Trip *t, const TripGen *g, Flier *f);

/* Test sentinels: calls past the state guard, and pushes. */
extern volatile uint16_t g_trip_window_calls;
extern volatile uint16_t g_trip_window_clamps;

#endif
