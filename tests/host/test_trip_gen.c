/* Gum Trip layout generator (plan T-B5): fairness rules as properties over many seeds and long distances.
 * Prints "DIGEST <n>" over a fixed run so a knob override (-D) can be shown to move the output. */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "../../src/core/trip_gen.h"
#include "../../src/core/trip.h"
#include "../../src/core/flier.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; if (failures <= 400) printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static uint32_t digest;
static void mix(uint32_t v) { digest = (digest ^ v) * 16777619u; }

/* ---- independent solids built from the raw chunk data ---- */
typedef struct { int x0, x1, y0, y1; } Box;   /* inclusive-exclusive, chunk relative x, world y */
static int boxes(const TripChunk *c, Box *b, int with_pickup) {
    int n = 0, i;
    if (c->win_top > 0) { b[n].x0 = 0; b[n].x1 = TRIP_CHUNK_PX; b[n].y0 = 0; b[n].y1 = c->win_top; n++; }
    if (c->win_bottom < TRIP_GEN_WORLD_H) { b[n].x0 = 0; b[n].x1 = TRIP_CHUNK_PX; b[n].y0 = c->win_bottom; b[n].y1 = TRIP_GEN_WORLD_H; n++; }
    for (i = 0; i < c->n_haz; i++) {
        const TripGenHazard *h = &c->haz[i];
        b[n].x0 = h->x - h->hw; b[n].x1 = h->x + h->hw; b[n].y0 = h->y - h->amp - h->hh; b[n].y1 = h->y + h->amp + h->hh; n++;
    }
    if (c->island.present) { b[n].x0 = c->island.x; b[n].x1 = c->island.x + c->island.w; b[n].y0 = c->island.y; b[n].y1 = c->island.y + c->island.h; n++; }
    if (with_pickup && c->pickup.present) {
        /* collection box: pickup 24 x 24 grown by the flier half extents (FLIER_HALF_W, 6 high, 1 px for inclusive boxes) */
        b[n].x0 = c->pickup.x - TRIP_PICKUP_HALF - FLIER_HALF_W - 1; b[n].x1 = c->pickup.x + TRIP_PICKUP_HALF + FLIER_HALF_W + 1;
        b[n].y0 = c->pickup.y - TRIP_PICKUP_HALF - 7; b[n].y1 = c->pickup.y + TRIP_PICKUP_HALF + 7; n++;
    }
    return n;
}
static int ov1(int a0, int a1, int b0, int b1) { return a0 < b1 && b0 < a1; }
/* heights y0 where a box TRIP_PASS_MIN tall is clear of every solid (not the pickup) of one chunk */
static void clear_set(const TripChunk *c, uint8_t *ok) {
    Box b[16]; int n = boxes(c, b, 0), y, i;
    for (y = 0; y + TRIP_PASS_MIN <= TRIP_GEN_WORLD_H; y++) {
        ok[y] = 1;
        for (i = 0; i < n; i++) if (ov1(y, y + TRIP_PASS_MIN, b[i].y0, b[i].y1)) { ok[y] = 0; break; }
    }
}

static void gen_run(TripGen *g, uint32_t seed, uint32_t chunks, TripChunk *out) {
    uint32_t i;
    tripgen_init(g, seed);
    for (i = 0; i < chunks; i++) {
        tripgen_advance(g, i * TRIP_CHUNK_PX);
        out[i] = *tripgen_get(g, i);
    }
}

#define NC 300
static TripChunk A[NC], B[NC];

static void check_run(const TripChunk *run, uint32_t n, uint32_t *haz_by_chunk_sum, uint32_t *pk_count, uint32_t *pk_dist_sum, uint32_t *pk_lastx, int *have_last) {
    uint32_t i;
    uint8_t ok_prev[TRIP_GEN_WORLD_H], ok_cur[TRIP_GEN_WORLD_H];
    for (i = 0; i < n; i++) {
        const TripChunk *c = &run[i];
        Box b[16]; int nb, j, k, y, any = 0, runs = 0;
        uint32_t d = trip_density_at(c->wx);
        CHECK(c->index == i && c->wx == i * TRIP_CHUNK_PX);
        /* F1: window at least TRIP_GAP_MIN, inside the world */
        CHECK(c->win_bottom - c->win_top >= TRIP_GAP_MIN);
        CHECK(c->win_top >= 0 && c->win_bottom <= TRIP_GEN_WORLD_H);
        /* window shrinks with density but never below the minimum, never above the start window */
        CHECK(c->win_bottom - c->win_top <= TRIP_GAP_START);
        /* density: hazards asked for are floor or ceiling of trip_density_at / 256, none before the start px */
        CHECK(c->n_req == (d >> 8) || c->n_req == (d >> 8) + 1 || c->n_req == TRIP_GEN_MAX_HAZ);
        if (c->wx <= TRIP_DENSITY_START_PX) CHECK(c->n_req == 0 && c->n_haz == 0);
        if (!c->dropped) CHECK(c->n_haz == c->n_req);
        /* hazard kind follows the distance band, one kind per chunk */
        for (j = 0; j < c->n_haz; j++) {
            uint8_t want = c->wx < TRIP_BAND_VENT_PX ? TRIP_HAZ_COAL : c->wx < TRIP_BAND_CLOUD_PX ? TRIP_HAZ_VENT : TRIP_HAZ_CLOUD;
            CHECK(c->haz[j].kind == want);
            CHECK(c->haz[j].hw == tripgen_haz_hw(want) && c->haz[j].hh == tripgen_haz_hh(want));
            CHECK(c->haz[j].amp == tripgen_haz_amp(want));
        }
        *haz_by_chunk_sum += c->n_haz;
        /* no overlap between any two solids (swept hazard boxes, strips, island), spacing between hazard boxes */
        nb = boxes(c, b, 0);
        for (j = 2 - (c->win_top > 0 ? 0 : 1) - (c->win_bottom < TRIP_GEN_WORLD_H ? 0 : 1); j < nb; j++)
            for (k = 0; k < nb; k++) if (k != j) CHECK(!ov1(b[j].x0, b[j].x1, b[k].x0, b[k].x1) || !ov1(b[j].y0, b[j].y1, b[k].y0, b[k].y1));
        for (j = 0; j < c->n_haz; j++) {
            CHECK(c->haz[j].x - c->haz[j].hw >= 0 && c->haz[j].x + c->haz[j].hw <= TRIP_CHUNK_PX);
            for (k = j + 1; k < c->n_haz; k++) {
                int dx = c->haz[j].x - c->haz[k].x; if (dx < 0) dx = -dx;
                CHECK(dx - c->haz[j].hw - c->haz[k].hw >= TRIP_HAZ_X_GAP);
            }
        }
        /* band: every box position inside [band_top, band_bottom - PASS_MIN] is clear of all solids (brute force from raw
         * boxes), and the band is at least TRIP_PASS_MIN tall. A dead-end pocket above a hazard is allowed. */
        clear_set(c, ok_cur);
        CHECK(c->band_bottom - c->band_top >= TRIP_PASS_MIN);
        for (y = c->band_top; y + TRIP_PASS_MIN <= c->band_bottom; y++) CHECK(ok_cur[y]);
        (void)any; (void)runs;
        /* F3: some flier position (FLIER_HALF_W wide, 11 px half height) overlaps the pickup box and touches no solid;
         * the pickup box itself lies inside the window and clear of every solid. */
        if (c->pickup.present) {
            Box pb[16]; int np = boxes(c, pb, 1), fx, fy, found = 0;
            CHECK(np == nb + 1);
            {
                int px0 = c->pickup.x - TRIP_PICKUP_HALF, px1 = c->pickup.x + TRIP_PICKUP_HALF;
                int py0 = c->pickup.y - TRIP_PICKUP_HALF, py1 = c->pickup.y + TRIP_PICKUP_HALF;
                for (j = 0; j < nb; j++) CHECK(!(ov1(px0, px1, b[j].x0, b[j].x1) && ov1(py0, py1, b[j].y0, b[j].y1)));
                CHECK(px0 >= 0 && px1 <= TRIP_CHUNK_PX && py0 >= c->win_top && py1 <= c->win_bottom);
                for (fx = px0 - FLIER_HALF_W; fx <= px1 + FLIER_HALF_W && !found; fx++)
                    for (fy = py0 - 11; fy <= py1 + 11 && !found; fy++) {
                        int clear = 1;
                        for (j = 0; j < nb && clear; j++)
                            if (ov1(fx - FLIER_HALF_W, fx + FLIER_HALF_W, b[j].x0, b[j].x1) && ov1(fy - 11, fy + 11, b[j].y0, b[j].y1)) clear = 0;
                        if (clear && ov1(fx - FLIER_HALF_W, fx + FLIER_HALF_W, px0, px1) && ov1(fy - 11, fy + 11, py0, py1)) found = 1;
                    }
                CHECK(found);
            }
            /* F4: spacing between consecutive pickups */
            {
                uint32_t wx = c->wx + (uint32_t)c->pickup.x;
                if (*have_last) {
                    uint32_t dd = wx - *pk_lastx;
                    CHECK(dd >= TRIP_PICKUP_SPACING_MIN && dd <= TRIP_PICKUP_SPACING_MAX);
                    *pk_dist_sum += dd; (*pk_count)++;
                }
                *pk_lastx = wx; *have_last = 1;
            }
        }
        /* passability rule: bands of consecutive chunks overlap by >= TRIP_PASS_MIN (brute force on raw solids) */
        if (i > 0) {
            int both = 0;
            for (y = 0; y + TRIP_PASS_MIN <= TRIP_GEN_WORLD_H; y++) if (ok_prev[y] && ok_cur[y]) both = 1;
            CHECK(both);
            {   /* and the overlap is a whole TRIP_PASS_MIN band of box positions: a margin, not a single line */
                int lo = c->band_top > run[i - 1].band_top ? c->band_top : run[i - 1].band_top;
                int hi = c->band_bottom < run[i - 1].band_bottom ? c->band_bottom : run[i - 1].band_bottom;
                CHECK(hi - lo >= TRIP_PASS_MIN);
            }
            /* F2 data side: window centre move within the generator's reach bound */
            {
                int cc = (c->win_top + c->win_bottom) >> 1, pc = (run[i - 1].win_top + run[i - 1].win_bottom) >> 1;
                int dd = cc > pc ? cc - pc : pc - cc;
                CHECK(dd <= TRIP_CENTRE_REACH);
            }
        }
        memcpy(ok_prev, ok_cur, sizeof ok_prev);
    }
}

/* Visible objects at a scroll position: hazards and pickups whose box touches [scroll, scroll + 320). */
static void visible(const TripGen *g, uint32_t scroll, int *haz, int *pk) {
    uint32_t i;
    *haz = 0; *pk = 0;
    for (i = 0; i < (uint32_t)g->count; i++) {
        const TripChunk *c = &g->ring[(g->head + i) % TRIP_GEN_RING];
        int j;
        for (j = 0; j < c->n_haz; j++) {
            int64_t x0 = (int64_t)c->wx + c->haz[j].x - c->haz[j].hw, x1 = (int64_t)c->wx + c->haz[j].x + c->haz[j].hw;
            if (x1 > (int64_t)scroll && x0 < (int64_t)scroll + 320) (*haz)++;
        }
        if (c->pickup.present) {
            int64_t x0 = (int64_t)c->wx + c->pickup.x - 12, x1 = x0 + 24;
            if (x1 > (int64_t)scroll && x0 < (int64_t)scroll + 320) (*pk)++;
        }
    }
}

/* TP7 guard (enemy teleport hunt): the flier floor path relies on two neighbouring chunk islands never leaving a narrow
 * crack between them at different heights. For every pair of consecutive chunks that both hold an island: if the horizontal
 * gap between them is under 2 * FLIER_HALF_W (a flier cannot fit through), the tops differ by at most 8 px. 3 seeds x 10000 chunks. */
#define TP7_CHUNKS 10000
static TripChunk T7[TP7_CHUNKS];
static void test_tp7_island_cracks(void) {
    static TripGen g;
    uint32_t seed, i, pairs = 0;
    for (seed = 1; seed <= 3; seed++) {
        gen_run(&g, seed, TP7_CHUNKS, T7);
        for (i = 1; i < TP7_CHUNKS; i++) {
            const TripChunk *p = &T7[i - 1], *c = &T7[i];
            int gap, dy;
            if (!p->island.present || !c->island.present) continue;
            gap = (TRIP_CHUNK_PX + c->island.x) - (p->island.x + p->island.w);
            dy = c->island.y - p->island.y;
            if (dy < 0) dy = -dy;
            pairs++;
            CHECK(!(gap < 2 * FLIER_HALF_W && dy > 8));
        }
    }
    CHECK(pairs > 1000);
}

/* WP4 (walls step 1, gap 144 -> 120): at full density a hazard never widens the window, and a measured bound on how long a
 * flier can hold one height through consecutive hazard chunks. Mirrors the independent solids of boxes(). */
#define HOLD_HALF 7        /* flier half height used by the other tests in this file (boxes(), pickup grown by 7) */
static int hold_abs_max, hold_rel_max, hold_runs_seen;
static void test_wp4_walls(void) {
    TripGen g; uint32_t seed; uint32_t i;
    for (seed = 9000; seed < 9300; seed++) {
        uint8_t abs_ok[TRIP_GEN_WORLD_H], rel_ok[TRIP_GEN_WORLD_H];
        int abs_len = 0, rel_len = 0;
        gen_run(&g, seed, NC, A);
        for (i = 0; i < NC; i++) {
            const TripChunk *c = &A[i];
            int gap = c->win_bottom - c->win_top, y, k, hz = 0, any_clear;
            if (c->wx <= TRIP_DENSITY_FULL_PX) { abs_len = rel_len = 0; continue; }
            if (c->n_haz) {
                int need = TRIP_PASS_MIN + (c->island.present ? TRIP_ISLAND_H : 0), mx = 0;
                for (k = 0; k < c->n_haz; k++) { int sw = 2 * (c->haz[k].hh + c->haz[k].amp); if (sw > mx) mx = sw; }
                need += mx;
                CHECK(need <= gap);                      /* hazards never widen the window */
            }
            CHECK(gap >= TRIP_GAP_MIN && gap <= TRIP_GAP_MIN + 1); /* full density: the smallest window; the integer reciprocal DENS_RECIP (85, not 85.33) leaves the base one row above MIN */
            if (!c->n_haz) { abs_len = rel_len = 0; continue; }
            /* absolute height y (flier centre) and height relative to the window top r: clear of every swept hazard box */
            if (abs_len == 0) memset(abs_ok, 1, sizeof abs_ok);
            if (rel_len == 0) memset(rel_ok, 1, sizeof rel_ok);
            any_clear = 0;
            for (y = 0; y < TRIP_GEN_WORLD_H; y++) {
                int a = abs_ok[y], r = y < TRIP_GEN_WORLD_H ? rel_ok[y] : 0;
                int ya = y, yr = c->win_top + y;          /* rel index y is an offset from win_top */
                (void)yr;
                if (a) {
                    if (ya - HOLD_HALF < c->win_top || ya + HOLD_HALF > c->win_bottom) a = 0;
                    for (k = 0; a && k < c->n_haz; k++) {
                        int y0 = c->haz[k].y - c->haz[k].amp - c->haz[k].hh, y1 = c->haz[k].y + c->haz[k].amp + c->haz[k].hh;
                        if (ov1(ya - HOLD_HALF, ya + HOLD_HALF, y0, y1)) a = 0;
                    }
                    if (c->island.present && ov1(ya - HOLD_HALF, ya + HOLD_HALF, c->island.y, c->island.y + c->island.h)) a = 0;
                }
                if (r) {
                    int yy = c->win_top + y;
                    if (y - HOLD_HALF < 0 || y + HOLD_HALF > gap) r = 0;
                    for (k = 0; r && k < c->n_haz; k++) {
                        int y0 = c->haz[k].y - c->haz[k].amp - c->haz[k].hh, y1 = c->haz[k].y + c->haz[k].amp + c->haz[k].hh;
                        if (ov1(yy - HOLD_HALF, yy + HOLD_HALF, y0, y1)) r = 0;
                    }
                    if (c->island.present && ov1(yy - HOLD_HALF, yy + HOLD_HALF, c->island.y, c->island.y + c->island.h)) r = 0;
                }
                abs_ok[y] = (uint8_t)a; rel_ok[y] = (uint8_t)r; hz += a;
                any_clear |= a;
            }
            (void)hz; (void)any_clear;
            {
                int ya = 0, yr = 0;
                for (y = 0; y < TRIP_GEN_WORLD_H; y++) { ya |= abs_ok[y]; yr |= rel_ok[y]; }
                abs_len = ya ? abs_len + 1 : 0;
                rel_len = yr ? rel_len + 1 : 0;
                if (!ya) memset(abs_ok, 1, sizeof abs_ok);
                if (!yr) memset(rel_ok, 1, sizeof rel_ok);
                if (abs_len > hold_abs_max) hold_abs_max = abs_len;
                if (rel_len > hold_rel_max) hold_rel_max = rel_len;
                hold_runs_seen++;
            }
        }
    }
    printf("WP4 hold-one-height at full density: longest run of consecutive hazard chunks with one absolute height clear %d, one window-relative height clear %d (%d hazard chunks checked)\n",
           hold_abs_max, hold_rel_max, hold_runs_seen);
}

int main(void) {
    static TripGen g, g2;
    uint32_t seed, i, hz_sum, pkc, pks, last;
    int have, haz_vis_max = 0, pk_vis_max = 0;
    uint32_t drop_chunks = 0, all_chunks = 0;

    test_tp7_island_cracks();
    test_wp4_walls();

    /* ---- numbers from the plan ---- */
    CHECK(TRIP_CHUNK_PX == 192 && TRIP_GAP_MIN == 120 && TRIP_GAP_START == 144 && /* behaviour change approved by the user */ TRIP_PICKUP_SPACING_MIN == 256 && TRIP_PICKUP_SPACING_MAX == 448);
    CHECK(TRIP_DENSITY_MAX <= TRIP_GEN_MAX_HAZ && TRIP_DENSITY_MAX <= TRIP_SLOTS - 1);
    CHECK(TRIP_CHUNK_PX == TRIP_SLOTS * TRIP_SLOT_PX);
    /* behaviour change approved by the user: hit boxes COAL 9/9, VENT 9/14, CLOUD 17/13 (was 36x26, 20x20, 16x14) */
    CHECK(tripgen_haz_hw(TRIP_HAZ_CLOUD) * 2 == 34 && tripgen_haz_hh(TRIP_HAZ_CLOUD) * 2 == 26);   /* A 34x26 */
    CHECK(tripgen_haz_hw(TRIP_HAZ_VENT) * 2 == 18 && tripgen_haz_hh(TRIP_HAZ_VENT) * 2 == 28);     /* B 18x28 */
    CHECK(tripgen_haz_hw(TRIP_HAZ_COAL) * 2 == 18 && tripgen_haz_hh(TRIP_HAZ_COAL) * 2 == 18);     /* C 18x18 */

    /* ---- sweep: 1500 seeds x 300 chunks (57600 px, past full density at 8000) ---- */
    hz_sum = pkc = pks = 0;
    for (seed = 1; seed <= 1500; seed++) {
        last = 0; have = 0;
        gen_run(&g, seed, NC, A);
        check_run(A, NC, &hz_sum, &pkc, &pks, &last, &have);
        CHECK(g.overflow == 0);
        drop_chunks += g.drops; all_chunks += g.made;
        /* F5: first chunk has no hazard and exactly one pickup, no island-free requirement */
        CHECK(A[0].n_haz == 0 && A[0].pickup.present && A[0].pickup.x == TRIP_FIRST_PICKUP_SLOT * TRIP_SLOT_PX + TRIP_SLOT_PX / 2);
        /* F6: same seed, same course byte for byte */
        if (seed <= 200) {
            gen_run(&g2, seed, NC, B);
            CHECK(memcmp(A, B, sizeof A) == 0);
            mix(seed); mix((uint32_t)A[40].win_top); mix((uint32_t)A[200].haz[0].x); mix((uint32_t)A[200].haz[0].y);
            mix((uint32_t)A[200].win_bottom); mix((uint32_t)A[199].island.y); mix((uint32_t)A[199].pickup.y); mix(g2.count); mix(g.count);
        }
    }
    CHECK(pkc > 100000);
    /* F4 mean ratio gain/decay per px: pickup 256 gain per mean spacing against 0.5 gum per frame at speed v */
    {
        double mean = (double)pks / (double)pkc;
        double r_start = (GUM_PICKUP / mean) / ((double)(0.5) / (TRIP_SCROLL_START / 65536.0));
        double r_cap = (GUM_PICKUP / mean) / ((double)(0.5) / (TRIP_SCROLL_MAX / 65536.0));
        printf("pickup mean spacing %.1f px, gain/decay at start %.3f, at cap %.3f\n", mean, r_start, r_cap);
        CHECK(mean >= 330.0 && mean <= 390.0);
        CHECK(r_start >= 1.05 && r_cap >= 1.35);   /* plan section 5: about 1.1 to 1.5 */
    }
    printf("hazards per chunk mean over sweep %.3f, dropped chunks %u of %u\n", (double)hz_sum / (1500.0 * NC), drop_chunks, all_chunks);
    CHECK(drop_chunks * 100 <= all_chunks);       /* fallback is the rare case: under 1 percent */

    /* different seeds differ */
    {
        int same = 0;
        for (seed = 1; seed <= 400; seed++) {
            gen_run(&g, seed, 60, A); gen_run(&g2, seed + 1, 60, B);
            if (memcmp(A, B, sizeof(TripChunk) * 60) == 0) same++;
        }
        CHECK(same == 0);
    }

    /* density follows trip_density_at: mean n_req per chunk at fixed distances over many seeds */
    {
        uint32_t idx[5] = {10, 20, 30, 60, 250};  /* chunks at 1920 .. 48000 px */
        int k;
        for (k = 0; k < 5; k++) {
            uint32_t sum = 0, s, want = trip_density_at(idx[k] * TRIP_CHUNK_PX);
            for (s = 1; s <= 1500; s++) { gen_run(&g, s, idx[k] + 1, A); sum += A[idx[k]].n_req; }
            {
                double mean = (double)sum / 1500.0, w = (double)want / 256.0;
                CHECK(mean > w - 0.08 && mean < w + 0.08);
                if (k == 4) CHECK(mean > 2.9);
            }
        }
        for (i = 0; i < 8; i++) CHECK(trip_density_at((uint32_t)i * TRIP_CHUNK_PX) <= trip_density_at((uint32_t)(i + 1) * TRIP_CHUNK_PX));
    }

    /* kinds appear: all three occur in the long run, in band order, windows shrink toward TRIP_GAP_MIN */
    {
        int seen[3] = {0, 0, 0}, mn = 999;
        gen_run(&g, 77, NC, A);
        for (i = 0; i < NC; i++) {
            if (A[i].n_haz) seen[A[i].haz[0].kind]++;
            if (A[i].wx > TRIP_DENSITY_FULL_PX && !A[i].n_haz) { int w = A[i].win_bottom - A[i].win_top; if (w < mn) mn = w; }
        }
        CHECK(seen[0] > 0 && seen[1] > 0 && seen[2] > 0);
        CHECK(mn >= TRIP_GAP_MIN);
    }

    /* long distance: 30 seeds x 40000 chunks (7.7 million px), same checks, 32-bit chunk numbers climb */
    for (seed = 5000; seed < 5030; seed++) {
        uint32_t c0, hs = 0, a = 0, b2 = 0, l = 0; int h = 0;
        uint8_t okp[TRIP_GEN_WORLD_H], okc[TRIP_GEN_WORLD_H];
        tripgen_init(&g, seed);
        for (c0 = 0; c0 < 40000; c0++) {
            const TripChunk *c;
            tripgen_advance(&g, c0 * TRIP_CHUNK_PX);
            c = tripgen_get(&g, c0);
            CHECK(c && c->index == c0);
            if (c0 % 500 == 0 || c0 < 3) {       /* property sampling to keep the run short */
                int y, both = 0;
                CHECK(c->win_bottom - c->win_top >= TRIP_GAP_MIN);
                clear_set(c, okc);
                if (c0 > 0) {
                    for (y = 0; y + TRIP_PASS_MIN <= TRIP_GEN_WORLD_H; y++) if (okp[y] && okc[y]) both = 1;
                }
                (void)both;
            }
            clear_set(c, okc);
            if (c0 > 0) { int y, both = 0; for (y = 0; y + TRIP_PASS_MIN <= TRIP_GEN_WORLD_H; y++) if (okp[y] && okc[y]) both = 1; CHECK(both); }
            memcpy(okp, okc, sizeof okp);
            hs += c->n_haz;
        }
        (void)a; (void)b2; (void)l; (void)h;
        CHECK(g.overflow == 0);
        CHECK(g.drops * 100 <= g.made);
        CHECK((double)hs / 40000.0 > 2.5);
    }

    /* Frame budget (symptom: game logic ended after vblank on the first Gum Trip frame, chunks built in the heavy
     * frame that starts the run). Init builds no chunk; no tripgen call builds more than one chunk; the first screen
     * is covered after 2 calls (the run-start hold), before any scroll step; and every later frame has the chunks
     * covering its screen, at the cap speed. */
    {
        uint32_t px, frac, before, calls_with_build = 0;
        for (seed = 31; seed < 71; seed++) {
            tripgen_init(&g, seed);
            CHECK(g.made == 0 && g.count == 0 && !tripgen_covers(&g, 0));       /* init builds no chunk at all */
            before = g.made;
            tripgen_advance(&g, 0);
            CHECK(g.made - before == 1 && !tripgen_covers(&g, 0));              /* one chunk per call: 192 px of 320 */
            before = g.made;
            tripgen_advance(&g, 0);
            CHECK(g.made - before == 1 && tripgen_covers(&g, 0));               /* hold length 2: chunks 0 and 1 cover x 0..319 */
            CHECK(tripgen_get(&g, 0) != 0 && tripgen_get(&g, 1) != 0);
            before = g.made;
            tripgen_advance(&g, 100000);                                         /* a huge jump still builds at most one */
            CHECK(g.made - before <= 1);
            tripgen_init(&g, seed);
            px = 0; frac = 0;
            tripgen_advance(&g, 0); tripgen_advance(&g, 0);                      /* the run-start hold */
            for (i = 0; i < 30000; i++) {
                uint32_t sp = trip_speed_at(px), x;
                CHECK(tripgen_covers(&g, px));                                   /* before the scroll step of this frame */
                frac += sp; px += frac >> 16; frac &= 0xFFFF;
                before = g.made;
                tripgen_advance(&g, px);
                CHECK(g.made - before <= 1);                                     /* no call builds more than one chunk */
                calls_with_build += g.made - before;
                CHECK(tripgen_covers(&g, px));
                for (x = px / TRIP_CHUNK_PX; x <= (px + 319) / TRIP_CHUNK_PX; x++) CHECK(tripgen_get(&g, x) != 0);
            }
        }
        CHECK(calls_with_build > 100);
    }

    /* F7 and ring: scroll at the maximum speed, one advance per frame, and in steps of 16 px; no overflow, visible
     * object counts inside the pool budget (hazards 8, pickups 10) */
    {
        uint32_t px, frac = 0;
        for (seed = 9001; seed <= 9040; seed++) {
            tripgen_init(&g, seed);
            px = 0; frac = 0;
            for (i = 0; i < 60000; i++) {
                int hv, pv;
                uint32_t sp = trip_speed_at(px);
                frac += sp; px += frac >> 16; frac &= 0xFFFF;
                tripgen_advance(&g, px);
                visible(&g, px, &hv, &pv);
                if (hv > haz_vis_max) haz_vis_max = hv;
                if (pv > pk_vis_max) pk_vis_max = pv;
                CHECK(g.count <= TRIP_GEN_RING);
                CHECK(tripgen_get(&g, px / TRIP_CHUNK_PX) != 0);
            }
            CHECK(g.overflow == 0);
            tripgen_init(&g, seed);
            for (px = 0; px < 2000000; px += 16) { tripgen_advance(&g, px); CHECK(tripgen_get(&g, px / TRIP_CHUNK_PX) != 0); }
            CHECK(g.overflow == 0);
        }
        printf("max visible hazards %d (budget 8), pickups %d (budget 10)\n", haz_vis_max, pk_vis_max);
        CHECK(haz_vis_max <= 8 && pk_vis_max <= 10);
    }

    /* F2 physics: the flier itself. Holding flap (alternating the button) from the lower world must climb at least the
     * reach bound within one chunk of scroll at the cap speed, with 25 percent margin; without flap it must sink the
     * bound within the same span. */
    {
        Flier f; FlierInput in; int fr, climbed = 0, sunk = 0;
        int span = (int)((TRIP_CHUNK_PX << 16) / TRIP_SCROLL_MAX);    /* frames per chunk at the cap speed */
        flier_init(&f, FL_PX(160), FL_PX(170), 2, 0);
        in.dir = 0;
        for (fr = 0; fr < span; fr++) {
            in.flap = (uint8_t)(fr & 1);
            flier_step(&f, &in, FLIER_NO_FLOOR);
            if (170 - (f.y >> 16) > climbed) climbed = 170 - (int)(f.y >> 16);
        }
        flier_init(&f, FL_PX(160), FL_PX(10), 2, 0);
        in.flap = 0;
        for (fr = 0; fr < span; fr++) {
            flier_step(&f, &in, FLIER_NO_FLOOR);
            if ((int)(f.y >> 16) - 10 > sunk) sunk = (int)(f.y >> 16) - 10;
        }
        printf("flier climbs %d px, sinks %d px in %d frames; reach bound %d\n", climbed, sunk, span, TRIP_CENTRE_REACH);
        CHECK(climbed * 4 >= TRIP_CENTRE_REACH * 5);
        CHECK(sunk * 4 >= TRIP_CENTRE_REACH * 5);
    }

    mix((uint32_t)hz_sum); mix(drop_chunks);
    printf("DIGEST %u\n", digest);
    printf("trip_gen: %d checks, %d failures\n", checks, failures);
    return failures != 0;
}
