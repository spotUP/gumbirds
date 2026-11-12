/* Scripted Gum Trip pilot for host tests (test_trip.c, knob_digest.c): reads the course from the generator's own chunks
 * and returns the button byte for game_step. Not game code. Flies the flier along the clear band of the chunk it is in,
 * dips for the pickup in its own slot, can land on the next island, or can fly into the next hazard on purpose.
 * Needs game.h and trip_hit.h (trip_hit_haz_y). */
#ifndef BRAWL_TRIP_STEER_H
#define BRAWL_TRIP_STEER_H

#include "../../src/core/game.h"
#include "../../src/core/nameentry.h"

typedef enum { STEER_AVOID = 0, STEER_LAND, STEER_HIT } SteerMode;


/* Target y (whole px) and landing flag for this frame; x wishes are returned through *dir. */
static uint8_t trip_steer(const Game *g, SteerMode mode)
{
    const Flier *f = &g->flier;
    uint32_t px = g->trip.px;
    int fx = (int)(f->x >> 16), fy = (int)(f->y >> 16);
    uint32_t wxf = px + (uint32_t)fx;
    uint32_t ci = wxf / TRIP_CHUNK_PX, k;
    const TripChunk *c = tripgen_get(&g->trip_gen, ci);
    int target = 90, dir = 0, no_flap = 0, want_x = 160;
    uint8_t in = 0;
    if (c) {
        int lo = c->band_top, hi = c->band_bottom;
        const TripChunk *n = tripgen_get(&g->trip_gen, ci + 1);
        if (n && (int)(wxf - c->wx) > TRIP_CHUNK_PX - 24) { /* bands of neighbours overlap by TRIP_PASS_MIN: use the overlap */
            if (n->band_top > lo) lo = n->band_top;
            if (n->band_bottom < hi) hi = n->band_bottom;
        }
        target = (lo + hi) / 2;
        for (k = ci; k < ci + 3; k++) {
            const TripChunk *q = tripgen_get(&g->trip_gen, k);
            int i;
            if (!q) continue;
            if (q->pickup.present && mode == STEER_AVOID) {
                int dx = (int)(q->wx + (uint32_t)q->pickup.x) - (int)wxf;
                if (dx >= -22 && dx <= 22) { target = q->pickup.y; break; }
            }
            if (mode == STEER_LAND && q->island.present) {
                int l = (int)q->wx + q->island.x, r = l + q->island.w;
                if ((int)wxf + 4 < r - 2) {
                    int mid = (l + r) / 2;
                    want_x = fx + (mid - (int)wxf);
                    if ((int)wxf >= l + 2 && (int)wxf <= r - 2) no_flap = 1; /* above it: sink onto it */
                    else target = q->island.y - 22;
                    break;
                }
            }
            if (mode == STEER_HIT) {
                for (i = 0; i < q->n_haz; i++) {
                    int hx = (int)q->wx + q->haz[i].x;
                    if (hx > (int)wxf + 2) {
                        target = trip_hit_haz_y(&q->haz[i], g->trip.steps);
                        k = ci + 3;
                        break;
                    }
                }
                if (k >= ci + 3) break;
            }
        }
    }
    if (want_x > fx + 3) dir = 1; else if (want_x < fx - 3) dir = -1;
    if (!no_flap && (f->y + 10 * f->vy) > FL_PX(target) && f->flap_cd == 0 && !f->flap_prev) in |= IN_A;
    if (dir > 0) in |= IN_RIGHT; else if (dir < 0) in |= IN_LEFT;
    (void)fy;
    return in;
}

#endif
