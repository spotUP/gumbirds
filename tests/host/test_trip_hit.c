/* Gum Trip collision (plan T-B6): box edges, scoring once, invincible window, landing, retired chunks, and a long
 * seeded run with the real generator cross-checked by a brute-force overlap over every held chunk.
 * Prints "DIGEST <n>" so a knob override (-DTRIP_SWEEP_STEP=5) shows it moves the output. */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "../../src/core/trip_hit.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; if (failures <= 400) printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)
static uint32_t digest;
static void mix(uint32_t v) { digest = (digest ^ v) * 16777619u; }

/* one hand-made chunk 0, wide open window, no strips */
static void one_chunk(TripGen *g) {
    memset(g, 0, sizeof *g);
    g->count = 1;
    g->ring[0].win_top = 0; g->ring[0].win_bottom = TRIP_GEN_WORLD_H;
}
static void fresh(Trip *t, Flier *f, int x, int y) {
    trip_init(t);
    flier_init(f, FL_PX(x), FL_PX(y), 2, 0);   /* 2 balloons: half height 5.5 -> box half 6 */
}
static void put_haz(TripGen *g, int x, int y, int hw, int hh, int amp, int phase) {
    TripGenHazard *h = &g->ring[0].haz[0];
    h->kind = 0; h->hw = (uint8_t)hw; h->hh = (uint8_t)hh; h->amp = (uint8_t)amp; h->phase = (uint8_t)phase;
    h->x = (int16_t)x; h->y = (int16_t)y;
    g->ring[0].n_haz = 1;
}

static void test_haz_edges(void) {
    TripGen g; Trip t; Flier f; int d;
    /* horizontal: hazard x 100, hw 16, flier half width 2: touching at 18, apart at 19 */
    for (d = 17; d <= 19; d++) {
        one_chunk(&g); put_haz(&g, 100, 90, 16, 14, 0, 0); fresh(&t, &f, 100 + d, 90);
        unsigned ev = trip_collide(&t, &g, &f);
        CHECK(((ev & TRIP_EV_HIT) != 0) == (d <= 18));
        CHECK(t.hits == (d <= 18 ? 1u : 0u));
        CHECK(t.gum == (d <= 18 ? GUM_START - GUM_HIT_CHUNK : GUM_START));
        one_chunk(&g); put_haz(&g, 100, 90, 16, 14, 0, 0); fresh(&t, &f, 100 - d, 90);
        CHECK(((trip_collide(&t, &g, &f) & TRIP_EV_HIT) != 0) == (d <= 18));
    }
    /* vertical: hh 14 + flier box half 6 = 20 touching, 21 apart (two balloons) */
    for (d = 19; d <= 21; d++) {
        one_chunk(&g); put_haz(&g, 100, 90, 16, 14, 0, 0); fresh(&t, &f, 100, 90 + d);
        CHECK(((trip_collide(&t, &g, &f) & TRIP_EV_HIT) != 0) == (d <= 20));
        one_chunk(&g); put_haz(&g, 100, 90, 16, 14, 0, 0); fresh(&t, &f, 100, 90 - d);
        CHECK(((trip_collide(&t, &g, &f) & TRIP_EV_HIT) != 0) == (d <= 20));
    }
    /* no balloons (state alive, box half 4): 18 touching, 19 apart */
    for (d = 17; d <= 19; d++) {
        one_chunk(&g); put_haz(&g, 100, 90, 16, 14, 0, 0); fresh(&t, &f, 100, 90 + d);
        f.balloons = 0; t.gum = 0;
        CHECK(((trip_collide(&t, &g, &f) & TRIP_EV_HIT) != 0) == (d <= 18));
    }
    /* the scroll shifts the world: same hazard seen at px 40 needs the flier 40 px further left on screen */
    one_chunk(&g); put_haz(&g, 100, 90, 16, 14, 0, 0); fresh(&t, &f, 60 + 18, 90); t.px = 40;
    CHECK(trip_collide(&t, &g, &f) & TRIP_EV_HIT);
    one_chunk(&g); put_haz(&g, 100, 90, 16, 14, 0, 0); fresh(&t, &f, 60 + 19, 90); t.px = 40;
    CHECK(!(trip_collide(&t, &g, &f) & TRIP_EV_HIT));
}

static void test_sweep(void) {
    TripGenHazard h; uint32_t fr; int lo = 1000, hi = -1000;
    memset(&h, 0, sizeof h); h.y = 90; h.amp = 6; h.phase = 17;
    for (fr = 0; fr < 256; fr++) {
        int y = trip_hit_haz_y(&h, fr);
        if (y < lo) lo = y;
        if (y > hi) hi = y;
        CHECK(y >= 90 - 6 && y <= 90 + 6);
        CHECK(y == trip_hit_haz_y(&h, fr + 256));   /* period divides 256 */
    }
    CHECK(lo >= 84 && lo <= 85 && hi >= 95 && hi <= 96);   /* nearly the full swept box is reached (Q15 sine floors 5.99 to 5) */
    CHECK(trip_hit_haz_y(&h, 0) == 90 + (int)(((int32_t)flier_sin(17) * 6) >> 15));
    mix((uint32_t)trip_hit_haz_y(&h, 5)); mix((uint32_t)trip_hit_haz_y(&h, 31));
    /* the box moves with the frame: a flier parked at the top of the sweep is hit only near that frame */
    {
        TripGen g; Trip t; Flier f; int hits = 0;
        one_chunk(&g); put_haz(&g, 100, 90, 16, 14, 6, 0);
        for (fr = 0; fr < 256; fr++) {
            fresh(&t, &f, 100, 90 - 26);     /* 26 above: touches only when the hazard centre is within 6 of the top */
            t.steps = fr;
            if (trip_collide(&t, &g, &f) & TRIP_EV_HIT) { hits++; CHECK(trip_hit_haz_y(&g.ring[0].haz[0], fr) <= 90 - 6); }
        }
        CHECK(hits > 0 && hits < 256);
        mix((uint32_t)hits);
    }
}

static void test_strips(void) {
    TripGen g; Trip t; Flier f; int y;
    one_chunk(&g); g.ring[0].win_top = 40; g.ring[0].win_bottom = 140;
    /* top strip rows 0..39: box rows y-6..y+6 touches when y - 6 <= 39, i.e. y <= 45 */
    for (y = 44; y <= 47; y++) { fresh(&t, &f, 100, y); CHECK(((trip_collide(&t, &g, &f) & TRIP_EV_HIT) != 0) == (y <= 45)); }
    /* bottom strip rows 140..179: touches when y + 6 >= 140, i.e. y >= 134 */
    for (y = 132; y <= 135; y++) { fresh(&t, &f, 100, y); CHECK(((trip_collide(&t, &g, &f) & TRIP_EV_HIT) != 0) == (y >= 134)); }
    /* the strip covers the chunk's x range only: flier box 2 px left of chunk start touches, 3 px does not */
    fresh(&t, &f, 0, 20); t.px = 0;
    CHECK(trip_collide(&t, &g, &f) & TRIP_EV_HIT);
    fresh(&t, &f, 0, 20); t.px = TRIP_CHUNK_PX + 2;              /* flier world x 194, box 192..196: right of the chunk */
    CHECK(!(trip_collide(&t, &g, &f) & TRIP_EV_HIT));
    fresh(&t, &f, 0, 20); t.px = TRIP_CHUNK_PX + 1;              /* box 191..195 touches the last column 191 */
    CHECK(trip_collide(&t, &g, &f) & TRIP_EV_HIT);
}

static void test_pickup_once(void) {
    TripGen g; Trip t; Flier f; unsigned ev; uint32_t bonus1;
    one_chunk(&g);
    g.ring[0].pickup.present = 1; g.ring[0].pickup.x = 100; g.ring[0].pickup.y = 90;
    fresh(&t, &f, 100 + 14, 90 + 18);       /* touching: 12 + 2 = 14 across, 12 + 6 = 18 down */
    t.gum = 100;
    ev = trip_collide(&t, &g, &f);
    CHECK(ev == TRIP_EV_PICKUP);
    CHECK(t.pickups == 1 && t.streak == 1 && t.gum == 100 + GUM_PICKUP && t.bonus == TRIP_PICKUP_POINTS);
    CHECK(g.ring[0].pickup.present == 0);
    bonus1 = t.bonus;
    ev = trip_collide(&t, &g, &f);          /* still inside it: scores nothing more */
    CHECK(ev == 0 && t.pickups == 1 && t.bonus == bonus1);
    /* one pixel apart: no pickup, and it stays */
    one_chunk(&g);
    g.ring[0].pickup.present = 1; g.ring[0].pickup.x = 100; g.ring[0].pickup.y = 90;
    fresh(&t, &f, 100 + 15, 90);
    CHECK(trip_collide(&t, &g, &f) == 0 && g.ring[0].pickup.present == 1);
    fresh(&t, &f, 100, 90 + 19);
    CHECK(trip_collide(&t, &g, &f) == 0 && g.ring[0].pickup.present == 1);
    /* a falling flier does not take it, and it stays for nobody else to lose */
    fresh(&t, &f, 100, 90); f.state = FLIER_FALLING;
    CHECK(trip_collide(&t, &g, &f) == 0 && g.ring[0].pickup.present == 1 && t.pickups == 0);
    /* a pickup scores even inside the invincible window (only hits are ignored) */
    fresh(&t, &f, 100, 90); f.invincible = 30;
    CHECK(trip_collide(&t, &g, &f) == TRIP_EV_PICKUP && f.invincible == 30);
    mix(t.bonus);
}

static void test_invincible(void) {
    TripGen g; Trip t; Flier f; unsigned ev; int i;
    one_chunk(&g); put_haz(&g, 100, 90, 16, 14, 0, 0);
    fresh(&t, &f, 100, 90); t.streak = 3;
    ev = trip_collide(&t, &g, &f);
    CHECK(ev == TRIP_EV_HIT && t.hits == 1 && t.streak == 0 && t.gum == GUM_START - GUM_HIT_CHUNK && f.invincible == FLIER_INVINCIBLE_POP);
    /* standing in the hazard for the whole window costs nothing more */
    for (i = 0; i < FLIER_INVINCIBLE_POP; i++) {
        uint16_t gum = t.gum;
        CHECK(trip_collide(&t, &g, &f) == 0 && t.hits == 1 && t.gum == gum);
        f.invincible--;
    }
    CHECK(f.invincible == 0);
    CHECK(trip_collide(&t, &g, &f) == TRIP_EV_HIT && t.hits == 2);   /* window over: hit again */
    /* spawn protection also refuses a hazard hit (SI), and the window ends on its own */
    fresh(&t, &f, 100, 90); f.spawn_inv = 5;
    CHECK(trip_collide(&t, &g, &f) == 0 && t.hits == 0 && f.invincible == 0);
    f.spawn_inv = 0;
    CHECK(trip_collide(&t, &g, &f) == TRIP_EV_HIT && t.hits == 1);
    /* an unrelated pickup keeps the streak (the streak breaks only on a hit): after a pickup, no hit, streak stays */
    {
        TripGen g2; Trip t2; Flier f2;
        one_chunk(&g2); g2.ring[0].pickup.present = 1; g2.ring[0].pickup.x = 100; g2.ring[0].pickup.y = 90;
        fresh(&t2, &f2, 100, 90); trip_collide(&t2, &g2, &f2);
        CHECK(t2.streak == 1);
        f2.x = FL_PX(300);
        trip_collide(&t2, &g2, &f2);
        CHECK(t2.streak == 1);
    }
}

static void test_landing(void) {
    TripGen g; Trip t; Flier f; FlierInput in = {0, 0}; int i;
    one_chunk(&g);
    g.ring[0].island.present = 1; g.ring[0].island.x = 40; g.ring[0].island.y = 100; g.ring[0].island.w = 64; g.ring[0].island.h = TRIP_ISLAND_H;
    fresh(&t, &f, 70, 60);
    CHECK(trip_hit_floor_y(&t, &g, &f) == FL_PX(100));
    for (i = 0; i < 200 && !f.on_ground; i++) {
        flier_step(&f, &in, trip_hit_floor_y(&t, &g, &f));
        trip_collide(&t, &g, &f);
    }
    CHECK(f.on_ground == 1 && f.vy == 0);
    CHECK(f.y + flier_half_h(&f) == FL_PX(100));        /* feet exactly on the island top */
    /* horizontal edges: strictly inside by the arena rule, flier half width 2 */
    fresh(&t, &f, 40 - 2, 60); CHECK(trip_hit_floor_y(&t, &g, &f) == FLIER_NO_FLOOR);   /* box ends at the left edge */
    fresh(&t, &f, 40 - 1, 60); CHECK(trip_hit_floor_y(&t, &g, &f) == FL_PX(100));
    fresh(&t, &f, 104 + 2, 60); CHECK(trip_hit_floor_y(&t, &g, &f) == FLIER_NO_FLOOR);
    fresh(&t, &f, 104 + 1, 60); CHECK(trip_hit_floor_y(&t, &g, &f) == FL_PX(100));
    /* feet below the top: passes through (no floor) */
    fresh(&t, &f, 70, 100); CHECK(trip_hit_floor_y(&t, &g, &f) == FLIER_NO_FLOOR);
    /* the scroll moves the island under the flier */
    fresh(&t, &f, 70 - 50, 60); t.px = 50; CHECK(trip_hit_floor_y(&t, &g, &f) == FL_PX(100));
    fresh(&t, &f, 70 - 50, 60); t.px = 0;  CHECK(trip_hit_floor_y(&t, &g, &f) == FLIER_NO_FLOOR);
    /* an island is not a hazard */
    fresh(&t, &f, 70, 100 + 3); CHECK(trip_collide(&t, &g, &f) == 0);
}

/* Islands are solid on every side in Gum Trip too: the body is TRIP_ISLAND_SOLID_H deep under the standing line. */
static int tstep(Trip *t, TripGen *g, Flier *f) {
    int32_t px = f->x, py = f->y;
    FlierInput in = {0, 0};
    FlierSolid so[TRIP_SOLIDS_MAX];
    flier_step(f, &in, trip_hit_floor_y(t, g, f));
    return flier_collide_solids(f, px, py, so, trip_hit_solids(t, g, f, so, TRIP_SOLIDS_MAX));
}
static void test_island_solid(void) {
    TripGen g; Trip t; Flier f; FlierSolid so[TRIP_SOLIDS_MAX]; int i;
    one_chunk(&g);
    g.ring[0].island.present = 1; g.ring[0].island.x = 40; g.ring[0].island.y = 100; g.ring[0].island.w = 64; g.ring[0].island.h = TRIP_ISLAND_H;
    fresh(&t, &f, 70, 60);
    CHECK(trip_hit_solids(&t, &g, &f, so, TRIP_SOLIDS_MAX) == 1);
    CHECK(so[0].x16 == FL_PX(40) && so[0].y16 == FL_PX(100) && so[0].w16 == FL_PX(64) && so[0].h16 == FL_PX(TRIP_ISLAND_SOLID_H));
    fresh(&t, &f, 300, 60);
    CHECK(trip_hit_solids(&t, &g, &f, so, TRIP_SOLIDS_MAX) == 0);   /* far away */
    t.px = 0;
    /* underside: rising from below turns back, box stays under the body */
    fresh(&t, &f, 70, 100 + TRIP_ISLAND_SOLID_H + FLIER_GUM_TOP - 5);
    f.no_wrap = 1; f.vy = -FL_PX(3);
    CHECK(tstep(&t, &g, &f) == 1 && f.vy > 0 && f.y + flier_half_h(&f) - FL_PX(FLIER_GUM_TOP) == FL_PX(100 + TRIP_ISLAND_SOLID_H));   /* gum top on the island bottom */
    /* side: flying into the left edge bounces back */
    fresh(&t, &f, 30, 106);
    f.no_wrap = 1; f.vx = FL_PX(3);
    CHECK(tstep(&t, &g, &f) == 1 && f.vx < 0 && f.x + FL_PX(FLIER_SOLID_MAX_HALF_W) == FL_PX(40));
    /* landing from above still lands, no solid hit */
    fresh(&t, &f, 70, 60);
    f.no_wrap = 1;
    for (i = 0; i < 200 && !f.on_ground; i++) CHECK(tstep(&t, &g, &f) == 0);
    CHECK(f.on_ground && f.y + flier_half_h(&f) == FL_PX(100));
}

/* ---- long seeded run with the real generator and a brute-force overlap over every held chunk ---- */
typedef struct { uint32_t index; TripChunk c; } Hist;
#define HIST_N 400
static Hist hist[HIST_N];
static uint32_t hist_n;
static uint8_t taken[HIST_N];

static void record(const TripGen *g) {
    int i, s = g->head;
    for (i = 0; i < g->count; i++, s = (s + 1) % TRIP_GEN_RING) {
        uint32_t idx = g->ring[s].index;
        if (idx >= hist_n && idx < HIST_N) { hist[idx].index = idx; hist[idx].c = g->ring[s]; hist_n = idx + 1; }
    }
}

typedef long long ll;
static ll lab(ll v) { return v < 0 ? -v : v; }

static void test_long_run(uint32_t seed, uint32_t *tot_pick, uint32_t *tot_hit, uint32_t *tot_haz, uint32_t *tot_strip) {
    TripGen g; Trip t; Flier f; Rng r; uint32_t fr, bpick_total = 0;
    int j;
    memset(taken, 0, sizeof taken); memset(hist, 0, sizeof hist); hist_n = 0;
    tripgen_init(&g, seed);
    trip_init(&t);
    flier_init(&f, FL_PX(160), FL_PX(90), 2, 0);
    rng_seed(&r, seed ^ 0x5eed);
    for (fr = 0; fr < 11000; fr++) {
        int fx, fy, fh, s, i, k;
        unsigned ev; int exp_pick = 0, exp_haz = 0, exp_strip = 0, exp_hit;
        uint32_t pk0 = t.pickups, ht0 = t.hits, gum0 = t.gum;
        t.px += 3; t.steps++;
        tripgen_advance(&g, t.px);
        record(&g);
        f.x = (int32_t)((rng_next(&r) % 320u) << 16) | (int32_t)(rng_next(&r) & 0xFFFF);
        f.y = (int32_t)((rng_next(&r) % 180u) << 16) | (int32_t)(rng_next(&r) & 0xFFFF);
        f.state = FLIER_ALIVE; f.balloons = (rng_next(&r) & 3) ? 2 : (rng_next(&r) & 1);
        if (rng_next(&r) & 1) f.invincible = 0;
        t.gum = GUM_START;
        gum0 = t.gum;
        fx = (int)(f.x >> 16); fy = (int)(f.y >> 16); fh = (int)(flier_half_h(&f) >> 16) + 1;
        /* brute force in world coordinates over every held chunk, no near filter */
        s = g.head;
        for (i = 0; i < g.count; i++, s = (s + 1) % TRIP_GEN_RING) {
            const TripChunk *c = &g.ring[s];
            ll wx0 = (ll)t.px + fx - FLIER_HALF_W, wx1 = (ll)t.px + fx + FLIER_HALF_W;
            ll cx0 = c->wx, cx1 = (ll)c->wx + TRIP_CHUNK_PX - 1;
            if (wx1 >= cx0 && wx0 <= cx1) {
                if (fy - fh <= c->win_top - 1 || fy + fh >= c->win_bottom) exp_strip = 1;
            }
            for (k = 0; k < c->n_haz; k++) {
                ll hx = (ll)c->wx + c->haz[k].x;
                int sweep = c->haz[k].y + (int)(((int32_t)flier_sin((uint8_t)(c->haz[k].phase + (uint8_t)(t.steps * TRIP_SWEEP_STEP))) * c->haz[k].amp) >> 15);
                if (lab((ll)t.px + fx - hx) <= c->haz[k].hw + 2 && lab(fy - sweep) <= c->haz[k].hh + fh) exp_haz = 1;
            }
            if (c->pickup.present && !taken[c->index]) {
                ll px_ = (ll)c->wx + c->pickup.x;
                if (lab((ll)t.px + fx - px_) <= 12 + 2 && lab(fy - c->pickup.y) <= 12 + fh) { exp_pick++; taken[c->index] = 1; }
            }
        }
        exp_hit = (exp_haz || exp_strip) && f.invincible == 0;
        {
            uint8_t inv0 = f.invincible;
            ev = trip_collide(&t, &g, &f);
            (void)inv0;
        }
        CHECK(t.pickups - pk0 == (uint32_t)exp_pick);
        CHECK(t.hits - ht0 == (uint32_t)exp_hit);
        CHECK(((ev & TRIP_EV_HIT) != 0) == (exp_hit != 0));
        CHECK(((ev & TRIP_EV_PICKUP) != 0) == (exp_pick != 0));
        (void)gum0;
        bpick_total += (uint32_t)exp_pick;
        if (exp_hit) { if (exp_haz) (*tot_haz)++; if (exp_strip) (*tot_strip)++; }
        if (g.overflow) break;
    }
    CHECK(t.pickups == bpick_total);
    CHECK(g.overflow == 0);
    /* every taken pickup was removed from its chunk if the chunk is still held */
    for (j = 0; j < g.count; j++) {
        const TripChunk *c = &g.ring[(g.head + j) % TRIP_GEN_RING];
        if (taken[c->index]) CHECK(c->pickup.present == 0);
    }
    /* chunks already scrolled off cannot be touched: no hazard or pickup of a retired chunk reaches a flier box at
     * screen x >= 0 (world x >= px - 2). Strips of the last retired chunk are the one sliver (see findings). */
    {
        const TripChunk *oldest = &g.ring[g.head];
        uint32_t idx;
        for (idx = 0; idx < oldest->index && idx < hist_n; idx++) {
            const TripChunk *c = &hist[idx].c;
            ll right = 0; int k;
            for (k = 0; k < c->n_haz; k++) { ll e = (ll)c->wx + c->haz[k].x + c->haz[k].hw + FLIER_HALF_W; if (e > right) right = e; }
            if (c->pickup.present || hist[idx].c.pickup.x) { ll e = (ll)c->wx + c->pickup.x + 12 + FLIER_HALF_W; if (e > right) right = e; }
            CHECK(right < (ll)oldest->wx);       /* reach ends before the first held chunk, which starts at or before px */
        }
    }
    *tot_pick += t.pickups; *tot_hit += t.hits;
    mix(t.pickups); mix(t.hits); mix(t.gum);
}

static void test_retired(void) {
    /* chunk 0 retired by the scroll: nothing of it is tested any more */
    TripGen g; Trip t; Flier f; uint32_t px;
    tripgen_init(&g, 7);
    for (px = 0; px < 1000; px += 50) tripgen_advance(&g, px);
    CHECK(tripgen_get(&g, 0) == 0);
    trip_init(&t); t.px = 1000;
    fresh(&t, &f, 0, 90);
    t.px = 1000;
    {
        const TripChunk *first = &g.ring[g.head];
        CHECK(first->wx + TRIP_CHUNK_PX > 950);
        CHECK(g.count > 0);
    }
    /* flier at the far-left world position of a retired chunk: put world x of chunk 0 hazards under it by px = 0 */
    t.px = 0; f.x = FL_PX(10); f.y = FL_PX(90);
    CHECK(trip_collide(&t, &g, &f) == 0);   /* ring holds only later chunks: the flier at world x 10 is in no held chunk */
    CHECK(t.hits == 0 && t.pickups == 0);
}

/* Lowest centre (16.16) for a two-balloon hero below rock row top: the gum top (31 above the feet) stays on row top. */
#define HERO_LO(top) (FL_PX((top) + FLIER_CEILING_FEET_Y) - FLIER_HALF_H16_BALLOON)
/* Solid rock (window clamp). Window 40..140, two balloons: the highest centre is the gum-top line (feet 31 under the window top:
 * y 65.5; was the box line 46), the lowest is the box line 133. */
static void test_window_clamp(void) {
    TripGen g; Trip t; Flier f; int32_t lo, hi, v;
    unsigned c0, k0;
    CHECK((FLIER_HALF_H16_BALLOON >> 16) + 1 == 6);
    one_chunk(&g); g.ring[0].win_top = 40; g.ring[0].win_bottom = 140;
    /* hero top: the hit test sees the overlap first, then the clamp pushes out and reflects vy */
    fresh(&t, &f, 100, 44); f.vy = -(2 << 16); v = f.vy;
    CHECK(trip_collide(&t, &g, &f) & TRIP_EV_HIT);
    CHECK(t.hits == 1);
    CHECK(trip_hit_clamp_window(&t, &g, &f) == 1);
    CHECK(f.y == HERO_LO(40));
    CHECK(f.vy == flier_reflect(v) && f.vy > 0);
    /* resting exactly on the box edge: no hit, but the gum would be under the rock, so the clamp pushes down to the gum-top line */
    fresh(&t, &f, 100, 46); f.vy = 0;
    CHECK(!(trip_collide(&t, &g, &f) & TRIP_EV_HIT));
    CHECK(trip_hit_clamp_window(&t, &g, &f) == 1 && f.y == HERO_LO(40));
    /* resting exactly on the gum-top line: no push */
    fresh(&t, &f, 100, 0); f.y = HERO_LO(40); f.vy = 0;
    CHECK(trip_hit_clamp_window(&t, &g, &f) == 0 && f.y == HERO_LO(40));
    /* hero bottom */
    fresh(&t, &f, 100, 136); f.vy = 2 << 16; v = f.vy;
    CHECK(trip_collide(&t, &g, &f) & TRIP_EV_HIT);
    CHECK(trip_hit_clamp_window(&t, &g, &f) == 1);
    CHECK(f.y == FL_PX(133));
    CHECK(f.vy == flier_reflect(v) && f.vy < 0);
    fresh(&t, &f, 100, 133); f.vy = 0;
    CHECK(!(trip_collide(&t, &g, &f) & TRIP_EV_HIT));
    CHECK(trip_hit_clamp_window(&t, &g, &f) == 0 && f.y == FL_PX(133));
    fresh(&t, &f, 100, 134);
    CHECK(trip_collide(&t, &g, &f) & TRIP_EV_HIT);
    CHECK(trip_hit_clamp_window(&t, &g, &f) == 1 && f.y == FL_PX(133));
    /* moving away from the rock keeps its velocity */
    fresh(&t, &f, 100, 44); f.vy = 3 << 16;
    CHECK(trip_hit_clamp_window(&t, &g, &f) == 1 && f.y == HERO_LO(40) && f.vy == (3 << 16));
    /* inside the window: nothing moves */
    fresh(&t, &f, 100, 90); f.vy = -(1 << 16);
    CHECK(trip_hit_clamp_window(&t, &g, &f) == 0 && f.y == FL_PX(90) && f.vy == -(1 << 16));
    /* sentinels: one call per ALIVE call, one clamp per push */
    c0 = g_trip_window_calls; k0 = g_trip_window_clamps;
    fresh(&t, &f, 100, 90); trip_hit_clamp_window(&t, &g, &f);
    fresh(&t, &f, 100, 20); trip_hit_clamp_window(&t, &g, &f);
    fresh(&t, &f, 100, 150); trip_hit_clamp_window(&t, &g, &f);
    CHECK((uint16_t)(g_trip_window_calls - c0) == 3 && (uint16_t)(g_trip_window_clamps - k0) == 2);
    /* defeated fliers fall out through the rock */
    c0 = g_trip_window_calls;
    {
        static const int ys[2] = {20, 170};
        int i, n;
        for (i = 0; i < 2; i++) {
            fresh(&t, &f, 100, ys[i]); f.state = FLIER_FALLING; f.balloons = 0; f.vy = 4 << 16; v = f.vy;
            CHECK(trip_hit_clamp_window(&t, &g, &f) == 0 && f.y == FL_PX(ys[i]) && f.vy == v);
            for (n = 0; n < 600 && f.state != FLIER_GONE; n++) { flier_step(&f, &(FlierInput){0}, FLIER_NO_FLOOR); CHECK(trip_hit_clamp_window(&t, &g, &f) == 0); }
            CHECK(f.state == FLIER_GONE);
        }
        fresh(&t, &f, 100, 20); f.state = FLIER_DROWNED; CHECK(trip_hit_clamp_window(&t, &g, &f) == 0 && f.y == FL_PX(20));
        fresh(&t, &f, 100, 20); f.state = FLIER_GONE; CHECK(trip_hit_clamp_window(&t, &g, &f) == 0 && f.y == FL_PX(20));
    }
    CHECK(g_trip_window_calls == (uint16_t)c0);
    /* two chunks: windows 40..140 and 60..150, the box straddles the seam: the intersection 66..133 */
    memset(&g, 0, sizeof g);
    g.count = 2;
    g.ring[0].win_top = 40; g.ring[0].win_bottom = 140; g.ring[0].wx = 0;
    g.ring[1].win_top = 60; g.ring[1].win_bottom = 150; g.ring[1].wx = TRIP_CHUNK_PX;
    fresh(&t, &f, 100, 90); t.px = TRIP_CHUNK_PX - 100 - 1;          /* world x 191: box 189..193 reaches both chunks */
    CHECK(trip_hit_window(&t, &g, &f, &lo, &hi) && lo == HERO_LO(60) && hi == FL_PX(133));
    f.y = FL_PX(50); f.vy = 0; CHECK(trip_hit_clamp_window(&t, &g, &f) == 1 && f.y == HERO_LO(60));
    f.y = FL_PX(145); CHECK(trip_hit_clamp_window(&t, &g, &f) == 1 && f.y == FL_PX(133));
    fresh(&t, &f, 100, 90); t.px = TRIP_CHUNK_PX - 100 + 10;           /* world x 202: chunk 1 only */
    CHECK(trip_hit_window(&t, &g, &f, &lo, &hi) && lo == HERO_LO(60) && hi == FL_PX(143));
    fresh(&t, &f, 100, 90); t.px = 0;                                   /* world x 100: chunk 0 only */
    CHECK(trip_hit_window(&t, &g, &f, &lo, &hi) && lo == HERO_LO(40) && hi == FL_PX(133));
    /* no hero or rival ever sits with gum under the rock: no gum is the same line with a smaller half height */
    fresh(&t, &f, 100, 50); f.balloons = 0; t.px = 0;
    CHECK(trip_hit_window(&t, &g, &f, &lo, &hi) && lo == FL_PX(40 + FLIER_CEILING_FEET_Y) - FLIER_HALF_H16_NOBAL);
    /* a computer flier keeps its lowered line where the window holds it (window 40..140: y 97.5), else the hero line */
    one_chunk(&g); g.ring[0].win_top = 40; g.ring[0].win_bottom = 140;
    fresh(&t, &f, 100, 50); f.rival = 1;
    CHECK(trip_hit_window(&t, &g, &f, &lo, &hi) && lo == HERO_LO(40) + FL_PX(FLIER_RIVAL_CEILING_DROP) && hi == FL_PX(133));
    f.vy = -(2 << 16);
    CHECK(trip_hit_clamp_window_from(&t, &g, &f, FL_PX(120)) == 1 && f.y == lo && f.vy > 0);   /* rose from below the lowered line */
    f.y = FL_PX(50); f.vy = -(2 << 16);                                /* began above it (spawned there): the hero line, no push down */
    CHECK(trip_hit_clamp_window_from(&t, &g, &f, FL_PX(50)) == 1 && f.y == HERO_LO(40) && f.vy > 0);
    f.y = HERO_LO(40) + FL_PX(10); f.vy = 0;
    CHECK(trip_hit_clamp_window_from(&t, &g, &f, f.y) == 0 && f.y == HERO_LO(40) + FL_PX(10));
    g.ring[0].win_bottom = 40 + 48;                                    /* behaviour change approved by the user: a hard-coded 48 window (TRIP_GAP_MIN is now 120, the game never builds one this small, the fallback stays covered); the lowered the lowered line (y 97.5) is below the floor line (81) */
    fresh(&t, &f, 100, 50); f.rival = 1;
    CHECK(trip_hit_window(&t, &g, &f, &lo, &hi) && lo == HERO_LO(40) && hi == FL_PX(40 + 48 - 7) && lo < hi);
    fresh(&t, &f, 100, 50);                                              /* the hero fits in the smallest window */
    CHECK(trip_hit_window(&t, &g, &f, &lo, &hi) && lo == HERO_LO(40) && lo <= hi);
    memset(&g, 0, sizeof g);
    g.count = 2;
    g.ring[0].win_top = 40; g.ring[0].win_bottom = 140; g.ring[0].wx = 0;
    g.ring[1].win_top = 60; g.ring[1].win_bottom = 150; g.ring[1].wx = TRIP_CHUNK_PX;
    /* no chunk under the flier: nothing */
    fresh(&t, &f, 100, 20); t.px = 5 * TRIP_CHUNK_PX;
    CHECK(trip_hit_window(&t, &g, &f, &lo, &hi) == 0 && trip_hit_clamp_window(&t, &g, &f) == 0 && f.y == FL_PX(20));
}

/* Long guard on the real generator: wherever a flier stands, the window is never empty, and after the clamp the box is out
 * of every rock row of every chunk it touches (brute force over the ring, written out here, not through the function). */
static void test_window_long(uint32_t seed) {
    TripGen g; Trip t; Flier f; Rng r; uint32_t fr; unsigned empty = 0, bad = 0, pushed = 0;
    tripgen_init(&g, seed);
    trip_init(&t);
    flier_init(&f, FL_PX(160), FL_PX(90), 2, 0);
    rng_seed(&r, seed ^ 0xa11);
    for (fr = 0; fr < 6000; fr++) {
        int fx, fy, fh, s, i; int32_t lo, hi;
        t.px += 3; t.steps++;
        tripgen_advance(&g, t.px);
        f.x = (int32_t)((rng_next(&r) % 320u) << 16);
        f.y = (int32_t)((rng_next(&r) % 180u) << 16);
        f.state = FLIER_ALIVE; f.balloons = (rng_next(&r) & 3) ? 2 : (rng_next(&r) & 1);
        f.vy = 0;
        if (!trip_hit_window(&t, &g, &f, &lo, &hi)) empty++;
        pushed += (unsigned)trip_hit_clamp_window(&t, &g, &f);
        fx = (int)(f.x >> 16); fy = (int)(f.y >> 16); fh = (int)(flier_half_h(&f) >> 16) + 1;
        s = g.head;
        for (i = 0; i < g.count; i++, s = (s + 1) % TRIP_GEN_RING) {
            const TripChunk *c = &g.ring[s];
            long wx0 = (long)t.px + fx - FLIER_HALF_W, wx1 = (long)t.px + fx + FLIER_HALF_W;
            if (wx1 >= (long)c->wx && wx0 <= (long)c->wx + TRIP_CHUNK_PX - 1)
                if (fy - fh <= c->win_top - 1 || fy + fh >= c->win_bottom) bad++;
        }
    }
    CHECK(empty == 0);
    CHECK(bad == 0);
    CHECK(pushed > 100);   /* the random heights did hit rock */
}

int main(void) {
    uint32_t pick = 0, hit = 0, haz = 0, strip = 0;
    test_haz_edges();
    test_sweep();
    test_strips();
    test_pickup_once();
    test_invincible();
    test_landing();
    test_island_solid();
    test_retired();
    test_window_clamp();
    test_window_long(1);
    test_window_long(2);
    test_window_long(0xC0FFEE);
    test_long_run(1, &pick, &hit, &haz, &strip);
    test_long_run(2, &pick, &hit, &haz, &strip);
    test_long_run(0xC0FFEE, &pick, &hit, &haz, &strip);
    printf("long run: %u pickups, %u hits (%u by hazards, %u by strips)\n", pick, hit, haz, strip);
    CHECK(pick > 30 && hit > 300 && haz > 30 && strip > 30);   /* the brute-force comparison saw real events */
    mix(pick); mix(hit);
    printf("DIGEST %u\n", digest);
    printf("trip_hit: %d checks, %d failures\n", checks, failures);
    return failures != 0;
}
