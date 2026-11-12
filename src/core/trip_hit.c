/* trip_hit.c - Gum Trip collision, see trip_hit.h. */
#include "trip_hit.h"

int trip_hit_haz_y(const TripGenHazard *h, uint32_t frame) {
    uint8_t a = (uint8_t)(h->phase + (uint8_t)(frame * TRIP_SWEEP_STEP));
    /* int16 x uint8 fits int32; arithmetic shift rounds toward minus, same on every host */
    return h->y + (int)(((int32_t)flier_sin(a) * (int32_t)h->amp) >> 15);
}

static int iabs(int v) { return v < 0 ? -v : v; }

/* Next ring slot without modulo */
static int next_slot(int s) { return s + 1 == TRIP_GEN_RING ? 0 : s + 1; }

int32_t trip_hit_floor_y(const Trip *t, const TripGen *g, const Flier *f) {
    int32_t best = FLIER_NO_FLOOR;
    int32_t feet = f->y + flier_half_h(f), hw = FL_PX(FLIER_HALF_W);
    int fx = (int)(f->x >> 16);
    int s = g->head, i;
    for (i = 0; i < g->count; i++, s = next_slot(s)) {
        const TripChunk *c = &g->ring[s];
        int rel = (int)(int32_t)(t->px - c->wx) + fx;   /* flier whole x relative to the chunk start */
        int32_t x16, top;
        if (!c->island.present) continue;
        if (rel + FLIER_HALF_W < c->island.x || rel - FLIER_HALF_W > c->island.x + c->island.w) continue;  /* broad phase */
        top = FL_PX(c->island.y);
        if (top < feet) continue;
        x16 = f->x + FL_PX((int32_t)(t->px - c->wx));
        if (x16 + hw <= FL_PX(c->island.x) || x16 - hw >= FL_PX(c->island.x + c->island.w)) continue;
        if (top < best) best = top;
    }
    return best;
}

int trip_hit_solids(const Trip *t, const TripGen *g, const Flier *f, FlierSolid *out, int max) {
    int n = 0;
    int fx = (int)(f->x >> 16);
    int s = g->head, i;
    for (i = 0; i < g->count && n < max; i++, s = next_slot(s)) {
        const TripChunk *c = &g->ring[s];
        int rel = (int)(int32_t)(t->px - c->wx) + fx;
        if (!c->island.present) continue;
        if (rel + FLIER_SOLID_MAX_HALF_W + 8 < c->island.x || rel - FLIER_SOLID_MAX_HALF_W - 8 > c->island.x + c->island.w) continue;  /* broad phase, 8 px of reach */
        out[n].x16 = FL_PX(c->island.x) - FL_PX((int32_t)(t->px - c->wx));
        out[n].y16 = FL_PX(c->island.y);
        out[n].w16 = FL_PX(c->island.w);
        out[n].h16 = FL_PX(TRIP_ISLAND_SOLID_H);
        n++;
    }
    return n;
}

volatile uint16_t g_trip_window_calls;
volatile uint16_t g_trip_window_clamps;

/* Half height in whole rows of the body box, the one rule trip_collide and the window clamp share. */
static int body_half_h(const Flier *f) { return (int)(flier_half_h(f) >> 16) + 1; }

int trip_hit_window(const Trip *t, const TripGen *g, const Flier *f, int32_t *lo, int32_t *hi) {
    int fx = (int)(f->x >> 16), fh = body_half_h(f);
    int s = g->head, i, top = -32768, bot = 32767, any = 0;
    for (i = 0; i < g->count; i++, s = next_slot(s)) {
        const TripChunk *c = &g->ring[s];
        int rel = (int)(int32_t)(t->px - c->wx) + fx;
        if (rel + FLIER_HALF_W < 0 || rel - FLIER_HALF_W > TRIP_CHUNK_PX - 1) continue;
        if (c->win_top > top) top = c->win_top;
        if (c->win_bottom < bot) bot = c->win_bottom;
        any = 1;
    }
    /* the box rows y-fh..y+fh must avoid rows 0..top-1 and bot..179 (the trip_collide rule) */
    if (!any || top + fh > bot - 1 - fh) return 0;
    *lo = (int32_t)(top + fh) << 16;
    *hi = (int32_t)(bot - 1 - fh) << 16;
    /* The whole flier, gum included, stays below the rock above win_top (flier_ceiling_y, the arena ceiling rule), and a computer
     * flier keeps its lowered line; each applies only where the window still holds it (a window of about 65 rows holds the lowered
     * line; with TRIP_GAP_MIN 120 the rival fallback below is unreachable in play, it stays as a guard). */
    {
        int32_t c = flier_ceiling_y(f, top, f->rival);
        if (c > *hi) c = flier_ceiling_y(f, top, 0);
        if (c <= *hi && c > *lo) *lo = c;
    }
    return 1;
}

int trip_hit_clamp_window_from(const Trip *t, const TripGen *g, Flier *f, int32_t y_before) {
    int32_t lo, hi;
    int pushed = 0;
    if (f->state >= FLIER_FALLING) return 0;
    g_trip_window_calls++;
    if (!trip_hit_window(t, g, f, &lo, &hi)) return 0;
    if (f->rival && y_before < lo) {
        /* A computer flier that began the step above its lowered line (spawned there, or standing on an island under the rock)
         * keeps the hero line: the lowered line would push it down into the island. It bounces off the lowered line only when
         * it rises from below it (same rule as flier_step in the arena). */
        Flier h = *f;
        h.rival = 0;
        trip_hit_window(t, g, &h, &lo, &hi);
    }
    if (f->y < lo) {
        f->y = lo;
        if (f->vy < 0) f->vy = flier_reflect(f->vy);
        pushed = 1;
    } else if (f->y > hi) {
        f->y = hi;
        if (f->vy > 0) f->vy = flier_reflect(f->vy);
        pushed = 1;
    }
    if (pushed) g_trip_window_clamps++;
    return pushed;
}

int trip_hit_clamp_window(const Trip *t, const TripGen *g, Flier *f) {
    return trip_hit_clamp_window_from(t, g, f, f->y);
}

unsigned trip_collide(Trip *t, TripGen *g, Flier *f) {
    unsigned ev = 0;
    int fx = (int)(f->x >> 16), fy = (int)(f->y >> 16);
    int fh = body_half_h(f);
    int s = g->head, i, k, hit = 0;
    for (i = 0; i < g->count; i++, s = next_slot(s)) {
        TripChunk *c = &g->ring[s];
        int rel = (int)(int32_t)(t->px - c->wx) + fx;   /* flier whole x relative to the chunk start */
        if (rel + FLIER_HALF_W < 0 || rel - FLIER_HALF_W > TRIP_CHUNK_PX - 1) continue;   /* flier box misses the chunk */
        if (fy - fh <= c->win_top - 1 || fy + fh >= c->win_bottom) hit = 1;
        for (k = 0; k < c->n_haz; k++) {
            const TripGenHazard *h = &c->haz[k];
            if (iabs(rel - h->x) <= h->hw + FLIER_HALF_W && iabs(fy - trip_hit_haz_y(h, t->steps)) <= h->hh + fh) hit = 1;   /* trip_hit_haz_bounce repeats this test */
        }
        if (c->pickup.present && iabs(rel - c->pickup.x) <= TRIP_PICKUP_HALF + FLIER_HALF_W &&
            iabs(fy - c->pickup.y) <= TRIP_PICKUP_HALF + fh) {
            if (trip_pickup(t, f)) { c->pickup.present = 0; ev |= TRIP_EV_PICKUP; }
        }
    }
    if (hit && trip_hit(t, f)) ev |= TRIP_EV_HIT;
    return ev;
}

int trip_hit_wall_touch(const Trip *t, const TripGen *g, const Flier *f) {
    int32_t lo, hi;
    if (f->state >= FLIER_FALLING) return 0;
    g_trip_window_calls++;   /* the hero's per-frame window check (the T8 sentinel counts it) */
    if (!trip_hit_window(t, g, f, &lo, &hi)) return 0;
    if (f->y < lo) return TRIP_WALL_TOP;
    if (f->y > hi) return TRIP_WALL_BOTTOM;
    return 0;
}

unsigned trip_hit_hero_walls(Trip *t, const TripGen *g, Flier *f) {
    int side = trip_hit_wall_touch(t, g, f);
    if (side == TRIP_WALL_BOTTOM) return trip_wall_kill(t, f) ? TRIP_EV_HIT : 0u;
    if (side == TRIP_WALL_TOP) trip_hit_clamp_window(t, g, f);   /* bounce down: vy reflected, no gum loss */
    return 0;
}

/* Away speed: reflect an approaching velocity, then guarantee TRIP_HAZ_KNOCK_MIN_SPEED away from the hazard. dir is +1 when
 * the hero lies on the positive side of the hazard centre on this axis, -1 on the negative side. */
static int32_t knock(int32_t v, int dir) {
    if ((dir > 0 && v < 0) || (dir < 0 && v > 0)) v = flier_reflect(v);
    if (dir > 0 && v < TRIP_HAZ_KNOCK_MIN_SPEED) v = TRIP_HAZ_KNOCK_MIN_SPEED;
    if (dir < 0 && v > -TRIP_HAZ_KNOCK_MIN_SPEED) v = -TRIP_HAZ_KNOCK_MIN_SPEED;
    return v;
}

void trip_hit_haz_bounce(const Trip *t, const TripGen *g, Flier *f) {
    int s, i, k;
    if (f->state >= FLIER_FALLING) return;
    s = g->head;
    for (i = 0; i < g->count; i++, s = next_slot(s)) {
        const TripChunk *c = &g->ring[s];
        for (k = 0; k < c->n_haz; k++) {
            const TripGenHazard *h = &c->haz[k];
            int fx = (int)(f->x >> 16), fy = (int)(f->y >> 16), fh = body_half_h(f);
            int rel = (int)(int32_t)(t->px - c->wx) + fx;
            int hy = trip_hit_haz_y(h, t->steps);
            int dx = rel - h->x, dy = fy - hy;
            int sx = h->hw + FLIER_HALF_W + 1, sy = h->hh + fh + 1;   /* centre distance that clears the inflated box */
            int need_x, need_y;
            if (iabs(dx) >= sx || iabs(dy) >= sy) continue;   /* the trip_collide overlap test, negated */
            need_x = sx - iabs(dx);
            need_y = sy - iabs(dy);
            if (need_x < need_y) {
                int dir = dx < 0 ? -1 : 1;   /* dx == 0 pushes right: only when the sideways clearance is shorter than the vertical one */
                f->x += (int32_t)dir * (int32_t)need_x * 65536;
                if (f->x < 0) f->x = 0;
                if (f->x > FL_PX(319)) f->x = FL_PX(319);
                f->vx = knock(f->vx, dir);
            } else {
                int dir = dy > 0 ? 1 : -1;   /* zero offset: push up */
                f->y += (int32_t)dir * (int32_t)need_y * 65536;
                f->vy = knock(f->vy, dir);
            }
        }
    }
}
