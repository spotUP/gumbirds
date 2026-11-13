#ifndef ISLAND_H
#define ISLAND_H
/*
 * Floating islands (plan thoughts/spot/2026-11-10-islands-build-plan.md, I7). One sprite per 16 px column from ISLAND_SPRITE
 * (sprite_slots.h), one sticky chain per stage platform, drawn from the stage table (src/core/stage.c, the same table the
 * collision reads) and the generated piece tables (src/core/island_layout.c). The two cap pieces carry attribute bit 3, so the
 * LSPC auto-animation steps their 8 tiles by itself: the CPU writes tiles once when a match starts and then only head x
 * (the camera), which gfx_word drops while the camera stands still.
 */
#include <ngdevkit/types.h>
#include "core/trip_gen.h"

void island_step(u8 playing, int cam_px); /* per frame: shows the islands on the rise of playing, hides them on the fall, follows the camera */
void island_relayout(void); /* the stage layout changed: reload the columns on the next island_step */

void island_autoanim_baseline(void); /* LSPC auto-animation counter to ISLAND_STEP_FRAMES: at boot, and where a hazard hands the counter back */

/* Gum Trip (plan step V1): the arena islands stay hidden (island_step is called with playing 0) and the islands of the generated
 * course chunks take the island sprites, TRIP_VIEW_ISLAND_BLOCK columns per ring slot. g is the course while a trip runs, 0
 * otherwise (the arena islands are loaded again on the way out). ready is game_trip_ready: no chunk is read while it is 0. */
void island_trip_step(const TripGen *g, uint32_t scroll_px, int ready);

extern volatile u16 g_island_trip_draws; /* frames the generated islands were placed (test sentinel) */
extern volatile u16 g_island_draws; /* frames the islands were placed (test sentinel) */
#endif
