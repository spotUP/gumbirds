#ifndef TRIP_STRIP_H
#define TRIP_STRIP_H
/* Gum Trip floor and ceiling kill strips (plan step V2): 22 sprite columns each, drawn from the generated chunks' safe windows. */
#include <ngdevkit/types.h>
#include "core/trip_gen.h"

extern volatile u16 g_trip_strip_draws; /* frames the strip code ran with a ready course: the test's proof the code was reached */

void trip_strip_load_palettes(void);
void trip_strip_init(void); /* boot: sprite size words and hidden SCB3, outside the per-frame flush budget */
/* Per frame. g 0 (not in Gum Trip) hides every strip column. ready 0 (run-start hold) keeps them hidden but queues the tiles of the
 * columns whose chunk exists, so the first ready frame only shows them. */
void trip_strip_step(const TripGen *g, uint32_t scroll_px, int ready);
#endif
