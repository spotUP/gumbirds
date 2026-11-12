/*
 * trip_pickup_fx.h - Gum Trip pickup collect effect state (plan Q8 default (a): the effect plays fully).
 *
 * Pure, no hardware. One effect per ring slot. update() is called once per frame after the game step: it sees a held chunk's pickup
 * go from present to collected (trip_hit clears TripGenPickup.present) and starts the effect at the pickup centre; the effect runs
 * TRIP_VIEW_COLLECT_FRAMES frames of 4 steps each, counted in trip steps. It is cancelled when the slot's chunk
 * is replaced or not held (the pickup is then far off the left edge of the screen).
 */
#ifndef BRAWL_TRIP_PICKUP_FX_H
#define BRAWL_TRIP_PICKUP_FX_H

#include <stdint.h>
#include "trip_gen.h"

#define TRIP_PICKUP_FX_SHIFT 2   /* 4 steps per effect frame */

typedef struct {
    uint32_t key[TRIP_GEN_RING];     /* chunk wx + 1 last seen in the slot, 0 = none */
    uint8_t seen[TRIP_GEN_RING];     /* that chunk's pickup was present at the last update */
    uint8_t active[TRIP_GEN_RING];
    uint32_t start[TRIP_GEN_RING];   /* trip steps when the effect began */
    uint32_t wx[TRIP_GEN_RING];      /* world x of the pickup centre */
    int16_t cy[TRIP_GEN_RING];       /* y of the pickup centre */
} TripPickupFx;

void trip_pickup_fx_init(TripPickupFx *fx);
/* ready 0 (run-start hold, not in Gum Trip) drops every effect. */
void trip_pickup_fx_update(TripPickupFx *fx, const TripGen *g, uint32_t steps, int ready);
/* Collect frame 0..TRIP_VIEW_COLLECT_FRAMES-1 of ring slot r, or -1 when none plays. */
int trip_pickup_fx_frame(const TripPickupFx *fx, int r, uint32_t steps);
/* Sprite left (16 px columns start there) or CAMERA_COL_HIDDEN when off screen; top line of the sprite. */
int trip_pickup_fx_left(const TripPickupFx *fx, int r, uint32_t scroll_px);
int trip_pickup_fx_top(const TripPickupFx *fx, int r);
#endif
