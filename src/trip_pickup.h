#ifndef TRIP_PICKUP_H
#define TRIP_PICKUP_H
/* Gum Trip pickups (plan step V3): one 2 x 2 tile sprite per held chunk that still has its pickup. */
#include <ngdevkit/types.h>
#include "core/trip_gen.h"

extern volatile u16 g_trip_pickup_draws; /* pickup sprites placed (one per pickup per frame): the test's proof the code ran */
extern volatile u16 g_trip_pickup_loads; /* tile loads queued (frame or chunk changed) */

void trip_pickup_load_palettes(void);
/* Per frame (also runs the collect effect state). g 0 (not in Gum Trip) or ready 0 (run-start hold) hides every pickup sprite. steps is the trip step count (animation). */
void trip_pickup_step(const TripGen *g, uint32_t scroll_px, uint32_t steps, int ready);
#endif
