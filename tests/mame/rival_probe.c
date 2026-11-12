/* Compiled with the 68000 compiler (-S) by the test-trip rule once the rival block is merged into trip_check.lua
 * (rival block of tests/mame/trip_check.lua). Compile like trip_probe.c: $(M68KGCC) $(NGCFLAGS) -Ibuild -S.
 * Order is fixed (1-based in Lua), offsets from the start of Flow:
 *  1 Game.mode  2 Game.trip.bonus  3 Game.flier.x  4 Game.flier.y  5 Game.flier.state  6 Game.flier.balloons
 *  7 trip_rivals.next_px  8 trip_rivals.spawned  9 trip_rivals.popped  10 trip_rivals.retired
 *  11 trip_rivals.r[0] base (TripRival)  12 sizeof(TripRival)  then inside TripRival:
 *  13 active  14 variant  15 f.x  16 f.y  17 f.balloons  18 f.state
 *  then constants: 19 TRIP_RIVAL_MAX  20 TRIP_RIVAL_POP_POINTS  21 TRIP_RIVAL_BAND_BONE  22 TRIP_RIVAL_BAND_BRUISER
 *  23 TRIP_RIVAL_OBJ_BASE (first pool object of the rivals)  24 POOL_SPRITE_BASE  25 POOL_COLS  26 SB_LIMIT
 *  27 Game.flier.vy (offset, last on purpose: the stomp assist writes a downward vy) */
#include <stddef.h>
#include "../../src/core/flow.h"
#include "../../src/sprite_slots.h"
#include "../../src/core/sprite_budget.h"
#include "../../src/core/obj_pool.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
#define R(m) (G(trip_rivals) + offsetof(TripRivals, m))
unsigned int probe[] = {
    G(mode), G(trip) + offsetof(Trip, bonus),
    G(flier) + offsetof(Flier, x), G(flier) + offsetof(Flier, y), G(flier) + offsetof(Flier, state), G(flier) + offsetof(Flier, balloons),
    R(next_px), R(spawned), R(popped), R(retired),
    R(r), sizeof(TripRival),
    offsetof(TripRival, active), offsetof(TripRival, variant),
    offsetof(TripRival, f) + offsetof(Flier, x), offsetof(TripRival, f) + offsetof(Flier, y),
    offsetof(TripRival, f) + offsetof(Flier, balloons), offsetof(TripRival, f) + offsetof(Flier, state),
    TRIP_RIVAL_MAX, TRIP_RIVAL_POP_POINTS, TRIP_RIVAL_BAND_BONE_PX, TRIP_RIVAL_BAND_BRUISER_PX,
    TRIP_RIVAL_OBJ_BASE, POOL_SPRITE_BASE, POOL_COLS, SB_LIMIT,
    G(flier) + offsetof(Flier, vy),
};
