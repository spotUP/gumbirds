/* Gum Trip pickup bob and collect effect (core state, src/core/trip_pickup_fx.c; bob table src/core/trip_view.c). */
#include <stdio.h>
#include <stdint.h>
#include "../../src/core/trip_pickup_fx.h"
#include "../../src/core/trip_view.h"
#include "../../src/core/camera.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; if (failures <= 20) printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

int main(void) {
    /* bob: draft table, one entry per idle frame, inside BOB_MIN..BOB_MAX, wraps with the frame number */
    static const int want[16] = { -2, -1, 0, 1, 3, 3, 3, 2, 1, 0, -1, -1, -2, -2, -2, -2 };
    int f, r, seeds = 0, effects = 0, shown = 0, cancelled = 0, pending = 0;
    uint32_t seed;
    for (f = 0; f < 16; f++) {
        CHECK(trip_view_pickup_bob(f) == want[f]);
        CHECK(trip_view_pickup_bob(f) >= TRIP_VIEW_PICKUP_BOB_MIN && trip_view_pickup_bob(f) <= TRIP_VIEW_PICKUP_BOB_MAX);
        CHECK(trip_view_pickup_bob(f + 16) == want[f]);
    }
    /* the bob follows the idle frame: steps 16 and 17 are idle frame 4 and bob 3 */
    CHECK(trip_view_pickup_bob(trip_view_pickup_frame(16)) == 3 && trip_view_pickup_bob(trip_view_pickup_frame(0)) == -2);

    /* one scripted collect */
    {
        TripGen g; TripPickupFx fx; const TripChunk *c = 0; uint32_t steps = 1000;
        tripgen_init(&g, 7);
        tripgen_advance(&g, 0);
        trip_pickup_fx_init(&fx);
        for (r = 0; r < TRIP_GEN_RING; r++) { c = trip_view_ring_chunk(&g, r, 1); if (c && c->pickup.present) break; }
        if (r == TRIP_GEN_RING) { tripgen_advance(&g, 700); for (r = 0; r < TRIP_GEN_RING; r++) { c = trip_view_ring_chunk(&g, r, 1); if (c && c->pickup.present) break; } }
        if (r == TRIP_GEN_RING) c = 0;
        CHECK(c && c->pickup.present);
        if (c && c->pickup.present) {
            TripChunk *m = &g.ring[r];
            uint32_t sc = c->wx + (uint32_t)c->pickup.x - 100;
            trip_pickup_fx_update(&fx, &g, steps, 1);
            CHECK(trip_pickup_fx_frame(&fx, r, steps) == -1);          /* nothing before a collect */
            m->pickup.present = 0;                                        /* trip_hit collects it */
            trip_pickup_fx_update(&fx, &g, steps + 1, 1);
            CHECK(trip_pickup_fx_frame(&fx, r, steps + 1) == 0);
            CHECK(trip_pickup_fx_frame(&fx, r, steps + 4) == 0);
            CHECK(trip_pickup_fx_frame(&fx, r, steps + 5) == 1);
            CHECK(trip_pickup_fx_frame(&fx, r, steps + 1 + 31) == 7);
            CHECK(trip_pickup_fx_frame(&fx, r, steps + 1 + 32) == -1);
            CHECK(trip_pickup_fx_left(&fx, r, sc) == 100 - TRIP_VIEW_PICKUP_LEFT_OFF);
            CHECK(trip_pickup_fx_top(&fx, r) == m->pickup.y - 16);
            /* update keeps it alive until the end, then drops it */
            trip_pickup_fx_update(&fx, &g, steps + 1 + 31, 1);
            CHECK(trip_pickup_fx_frame(&fx, r, steps + 1 + 31) == 7);
            trip_pickup_fx_update(&fx, &g, steps + 1 + 32, 1);
            CHECK(fx.active[r] == 0);
            /* the hold drops a running effect */
            m->pickup.present = 1; trip_pickup_fx_update(&fx, &g, steps + 100, 1);
            m->pickup.present = 0; trip_pickup_fx_update(&fx, &g, steps + 101, 1);
            CHECK(trip_pickup_fx_frame(&fx, r, steps + 101) == 0);
            trip_pickup_fx_update(&fx, &g, steps + 102, 0);
            CHECK(trip_pickup_fx_frame(&fx, r, steps + 102) == -1);
        }
    }

    /* sweep: collect every pickup the moment its centre is at screen x 160 (1 px per step, the top speed); an effect
     * must play all 8 frames on the screen, and be cancelled only when the chunk is gone (the sprite is off screen then) */
    for (seed = 1; seed <= 100; seed++) {
        TripGen g; TripPickupFx fx; uint32_t px, steps = 0;
        tripgen_init(&g, seed);
        trip_pickup_fx_init(&fx);
        seeds++;
        for (px = 0; px < 20000; px++) {
            int s, seen_mask[TRIP_GEN_RING];
            steps++;
            tripgen_advance(&g, px);
            for (s = 0; s < TRIP_GEN_RING; s++) {
                TripChunk *c = (TripChunk *)trip_view_ring_chunk(&g, s, 1);
                if (c && c->pickup.present && (int)(c->wx + (uint32_t)c->pickup.x) - (int)px <= 160) c->pickup.present = 0;
            }
            for (s = 0; s < TRIP_GEN_RING; s++) seen_mask[s] = fx.active[s];
            trip_pickup_fx_update(&fx, &g, steps, 1);
            for (s = 0; s < TRIP_GEN_RING; s++) {
                int fr = trip_pickup_fx_frame(&fx, s, steps);
                if (!seen_mask[s] && fr == 0) effects++;
                if (fr >= 0) {
                    shown++;
                    CHECK(fr <= TRIP_VIEW_COLLECT_FRAMES - 1);
                    CHECK(trip_pickup_fx_left(&fx, s, px) != CAMERA_COL_HIDDEN);   /* still on screen for all 32 frames */
                    CHECK(trip_pickup_fx_top(&fx, s) >= 0 && trip_pickup_fx_top(&fx, s) + 32 <= 180);
                } else if (seen_mask[s] && !fx.active[s]) {
                    /* ended: either all 8 frames ran, or the chunk went; count a cut-short effect only when the sprite was still on screen */
                    cancelled += trip_pickup_fx_left(&fx, s, px) != CAMERA_COL_HIDDEN && fx.start[s] + 32 > steps ? 1 : 0;
                }
            }
        }
        for (r = 0; r < TRIP_GEN_RING; r++) if (fx.active[r]) pending += (int)((TRIP_VIEW_COLLECT_FRAMES << TRIP_PICKUP_FX_SHIFT) - (steps - fx.start[r]) - 1); /* steps still to show at the end of the sweep */
    }
    CHECK(effects > 100);
    CHECK(shown + pending == effects * (TRIP_VIEW_COLLECT_FRAMES << TRIP_PICKUP_FX_SHIFT));
    CHECK(cancelled == 0);
    printf("seeds %d effects %d frames shown %d cut short on screen %d\n%s: %d checks, %d failed\n", seeds, effects, shown, cancelled, failures ? "FAIL" : "PASS", checks, failures);
    return failures != 0;
}
