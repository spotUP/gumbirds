#include "trip_pickup_fx.h"
#include "trip_view.h"
#include "camera.h"

void trip_pickup_fx_init(TripPickupFx *fx) {
    for (int r = 0; r < TRIP_GEN_RING; r++) { fx->key[r] = 0; fx->seen[r] = 0; fx->active[r] = 0; fx->start[r] = 0; fx->wx[r] = 0; fx->cy[r] = 0; }
}

void trip_pickup_fx_update(TripPickupFx *fx, const TripGen *g, uint32_t steps, int ready) {
    for (int r = 0; r < TRIP_GEN_RING; r++) {
        const TripChunk *c = (g && ready) ? trip_view_ring_chunk(g, r, 1) : 0;
        if (!c) { fx->key[r] = 0; fx->seen[r] = 0; fx->active[r] = 0; continue; }
        if (fx->key[r] != c->wx + 1) {          /* a new chunk in the slot: the old effect is gone */
            fx->key[r] = c->wx + 1; fx->active[r] = 0;
        } else if (fx->seen[r] && !c->pickup.present) {
            fx->active[r] = 1; fx->start[r] = steps;
            fx->wx[r] = c->wx + (uint32_t)(int32_t)c->pickup.x; fx->cy[r] = (int16_t)c->pickup.y;
        }
        fx->seen[r] = c->pickup.present ? 1 : 0;
        if (fx->active[r] && ((steps - fx->start[r]) >> TRIP_PICKUP_FX_SHIFT) >= TRIP_VIEW_COLLECT_FRAMES) fx->active[r] = 0;
    }
}

int trip_pickup_fx_frame(const TripPickupFx *fx, int r, uint32_t steps) {
    uint32_t f;
    if (!fx->active[r]) return -1;
    f = (steps - fx->start[r]) >> TRIP_PICKUP_FX_SHIFT;
    return f < TRIP_VIEW_COLLECT_FRAMES ? (int)f : -1;
}

int trip_pickup_fx_left(const TripPickupFx *fx, int r, uint32_t scroll_px) {
    int sx = trip_view_screen_x(fx->wx[r], scroll_px) - TRIP_VIEW_PICKUP_LEFT_OFF;
    return (sx > -(TRIP_VIEW_PICKUP_COLS << 4) && sx < TRIP_VIEW_SCREEN_W) ? sx : CAMERA_COL_HIDDEN;
}

int trip_pickup_fx_top(const TripPickupFx *fx, int r) { return fx->cy[r] - TRIP_VIEW_COLLECT_TOP_OFF; }
