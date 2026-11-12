/* trip_gen.c - Gum Trip layout generator (plan T-B5). See trip_gen.h for the rules. */
#include <string.h>
#include "trip_gen.h"
#include "trip.h"
#include "flier.h"

#define SLOT_MIN_STEPS ((TRIP_PICKUP_SPACING_MIN + TRIP_SLOT_PX - 1) / TRIP_SLOT_PX)
#define SLOT_MAX_STEPS (TRIP_PICKUP_SPACING_MAX / TRIP_SLOT_PX)
/* 65536 / (density max in 8.8): turns a density value into a 0..65536 fraction with a multiply and a shift. */
#define DENS_RECIP (65536 / (TRIP_DENSITY_MAX * 256))

static const uint8_t k_hw[3] = {9, 9, 17};    /* coal C 18x18, vent B 18x28, cloud A 34x26: fitted to the measured art (user decision 2026-11-11) */
static const uint8_t k_hh[3] = {9, 14, 13};

uint8_t tripgen_haz_hw(uint8_t kind) { return k_hw[kind]; }
uint8_t tripgen_haz_hh(uint8_t kind) { return k_hh[kind]; }
uint8_t tripgen_haz_amp(uint8_t kind) {
    return kind == TRIP_HAZ_COAL ? TRIP_COAL_AMP : kind == TRIP_HAZ_VENT ? TRIP_VENT_AMP : TRIP_CLOUD_AMP;
}

/* Value in [0, n), n <= 65535, no division. */
static uint32_t rngr(Rng *r, uint32_t n) { return ((rng_next(r) >> 16) * n) >> 16; }

static int imax(int a, int b) { return a > b ? a : b; }
static int imin(int a, int b) { return a < b ? a : b; }
static int iabs(int a) { return a < 0 ? -a : a; }

/* Try one layout of a chunk. Returns 1 and fills c when the band overlaps the previous one, else 0 (c is scratch). */
static int try_layout(TripGen *g, TripChunk *c, uint32_t d, int n, int top_side, int pk_slot, const uint8_t *slots) {
    int kind = c->wx < TRIP_BAND_VENT_PX ? TRIP_HAZ_COAL : c->wx < TRIP_BAND_CLOUD_PX ? TRIP_HAZ_VENT : TRIP_HAZ_CLOUD;
    int hw = k_hw[kind], hh = k_hh[kind], amp = tripgen_haz_amp((uint8_t)kind);
    int swept = 2 * (hh + amp);
    int base = TRIP_GAP_START - (int)(((uint32_t)(TRIP_GAP_START - TRIP_GAP_MIN) * d * DENS_RECIP) >> 16);
    int island = (n == 0 || top_side) && (int)rngr(&g->rng, 100) < TRIP_ISLAND_PCT;
    int isl_h = island ? TRIP_ISLAND_H : 0;
    int need = n ? swept + TRIP_PASS_MIN + isl_h : 0;
    int gap, wt, lo_rel, hi_rel, i, pk_isl;
    int slack[TRIP_GEN_MAX_HAZ];
    int ov, shift, centre, wb;

    if (base < TRIP_GAP_MIN) base = TRIP_GAP_MIN;
    gap = imax(base, need);
    lo_rel = 0;
    hi_rel = gap - isl_h;
    for (i = 0; i < n; i++) {
        slack[i] = (int)rngr(&g->rng, (uint32_t)(gap - need + 1));
        if (top_side) lo_rel = imax(lo_rel, slack[i] + swept);
        else hi_rel = imin(hi_rel, gap - slack[i] - swept);
    }
    if (c->index == 0) {
        wt = (TRIP_GEN_WORLD_H - gap) >> 1;
    } else {
        wt = (int)g->prev_centre - (gap >> 1) + (int)rngr(&g->rng, 2 * TRIP_WIN_STEP_MAX + 1) - TRIP_WIN_STEP_MAX;
        wt = imax(0, imin(wt, TRIP_GEN_WORLD_H - gap));
        ov = imin(wt + hi_rel, g->prev_band_bottom) - imax(wt + lo_rel, g->prev_band_top);
        if (ov < TRIP_PASS_MIN) {
            shift = TRIP_PASS_MIN - ov;
            wt += (wt + lo_rel < g->prev_band_top) ? shift : -shift;
            wt = imax(0, imin(wt, TRIP_GEN_WORLD_H - gap));
            ov = imin(wt + hi_rel, g->prev_band_bottom) - imax(wt + lo_rel, g->prev_band_top);
            if (ov < TRIP_PASS_MIN) return 0;
        }
        centre = wt + (gap >> 1);
        if (iabs(centre - g->prev_centre) > TRIP_CENTRE_REACH) return 0;
    }
    wb = wt + gap;
    c->win_top = (int16_t)wt;
    c->win_bottom = (int16_t)wb;
    c->band_top = (int16_t)(wt + lo_rel);
    c->band_bottom = (int16_t)(wt + hi_rel);
    c->haz_top = (uint8_t)top_side;
    c->n_haz = (uint8_t)n;
    for (i = 0; i < n; i++) {
        TripGenHazard *h = &c->haz[i];
        int room = TRIP_SLOT_PX - 2 * hw - TRIP_HAZ_X_GAP;
        h->kind = (uint8_t)kind;
        h->hw = (uint8_t)hw;
        h->hh = (uint8_t)hh;
        h->amp = (uint8_t)amp;
        h->phase = (uint8_t)rngr(&g->rng, 256);
        h->x = (int16_t)(slots[i] * TRIP_SLOT_PX + hw + TRIP_HAZ_X_GAP / 2 + (int)rngr(&g->rng, (uint32_t)(room + 1)));
        h->y = (int16_t)(top_side ? wt + slack[i] + hh + amp : wb - slack[i] - hh - amp);
    }
    if (island) {
        int lo_x = 0;
        int w = TRIP_ISLAND_W_MIN + 16 * (int)rngr(&g->rng, 3); /* 64, 80 or 96: widths with island art */
        c->island.present = 1;
        c->island.w = (uint8_t)w;
        c->island.h = TRIP_ISLAND_H;
        c->island.y = (int16_t)(wb - TRIP_ISLAND_H);
        /* Wider, higher-varying windows (walls step 1) put neighbouring islands at different heights: when the tops differ
         * by more than 8 px the two islands keep a horizontal gap of at least two flier widths, so no crack a flier cannot
         * fit through forms between them (the TP7 rule in test_trip_gen.c). One draw either way. */
        if (g->prev_isl_end > 0 && iabs(c->island.y - g->prev_isl_y) > 8) lo_x = imax(0, g->prev_isl_end - TRIP_CHUNK_PX + 2 * FLIER_HALF_W);
        c->island.x = (int16_t)(lo_x + (int)rngr(&g->rng, (uint32_t)(TRIP_CHUNK_PX - w - lo_x + 1)));
    }
    if (pk_slot >= 0) {
        int span, ylo;
        pk_isl = island ? TRIP_ISLAND_H : 0;
        ylo = wt + TRIP_PICKUP_CLEAR + TRIP_PICKUP_HALF;
        span = (wb - pk_isl - TRIP_PICKUP_CLEAR - TRIP_PICKUP_HALF) - ylo;
        c->pickup.present = 1;
        c->pickup.x = (int16_t)(pk_slot * TRIP_SLOT_PX + TRIP_SLOT_PX / 2);
        c->pickup.y = (int16_t)(ylo + (int)rngr(&g->rng, (uint32_t)(span + 1)));
    }
    return 1;
}

static void make_chunk(TripGen *g, TripChunk *c) {
    uint32_t d = trip_density_at(g->next_wx);
    int n_req, i, j, pk_slot = -1, top, tries;
    uint8_t order[TRIP_SLOTS], slots[TRIP_GEN_MAX_HAZ], tmp;
    int free_n = 0;

    memset(c, 0, sizeof *c);
    c->index = g->next_index;
    c->wx = g->next_wx;
    if (c->index == 0) d = 0;                                 /* plan F5: no hazard in the first chunk */
    n_req = (int)(d >> 8);
    if ((int)rngr(&g->rng, 256) < (int)(d & 255)) n_req++;
    if (n_req > TRIP_GEN_MAX_HAZ) n_req = TRIP_GEN_MAX_HAZ;
    if (n_req > TRIP_SLOTS - 1) n_req = TRIP_SLOTS - 1;
    if (g->pk_chunk == c->index) pk_slot = g->pk_slot;
    for (i = 0; i < TRIP_SLOTS; i++) if (i != pk_slot) order[free_n++] = (uint8_t)i;
    for (i = 0; i < free_n - 1; i++) {                       /* partial shuffle: first n_req entries are the slots */
        j = i + (int)rngr(&g->rng, (uint32_t)(free_n - i));
        tmp = order[i]; order[i] = order[j]; order[j] = tmp;
    }
    for (i = 0; i < n_req; i++) slots[i] = order[i];
    top = (int)(rngr(&g->rng, 2));
    c->n_req = (uint8_t)n_req;
    for (tries = 0; tries < 3; tries++) {
        TripChunk scratch;
        int nn = tries < 2 ? n_req : 0;                      /* last resort: no hazards */
        memset(&scratch, 0, sizeof scratch);
        scratch.index = c->index;
        scratch.wx = c->wx;
        if (try_layout(g, &scratch, d, nn, tries == 1 ? !top : top, pk_slot, slots)) {
            scratch.n_req = c->n_req;
            scratch.dropped = (uint8_t)(nn != n_req);
            *c = scratch;
            break;
        }
        if (tries == 2) {                                    /* even the plain window failed: window on the old band */
            int gap = TRIP_GAP_MIN, wt = imax(0, imin(g->prev_band_top, TRIP_GEN_WORLD_H - gap));
            memset(&scratch, 0, sizeof scratch);
            scratch.index = c->index; scratch.wx = c->wx; scratch.n_req = c->n_req; scratch.dropped = 1;
            scratch.win_top = (int16_t)wt; scratch.win_bottom = (int16_t)(wt + gap);
            scratch.band_top = scratch.win_top; scratch.band_bottom = scratch.win_bottom;
            if (pk_slot >= 0) {
                scratch.pickup.present = 1;
                scratch.pickup.x = (int16_t)(pk_slot * TRIP_SLOT_PX + TRIP_SLOT_PX / 2);
                scratch.pickup.y = (int16_t)(wt + (gap >> 1));
            }
            *c = scratch;
        }
    }
    if (c->dropped) g->drops++;
    if (c->pickup.present) {                                 /* next pickup: 6..9 slots on (plan section 5: 256..448 px) */
        int steps = SLOT_MIN_STEPS + (int)rngr(&g->rng, SLOT_MAX_STEPS - SLOT_MIN_STEPS + 1);
        int s = g->pk_slot + steps;
        uint32_t ch = g->pk_chunk;
        while (s >= TRIP_SLOTS) { s -= TRIP_SLOTS; ch++; }
        g->pk_slot = (uint8_t)s;
        g->pk_chunk = ch;
    }
    g->prev_band_top = c->band_top;
    g->prev_band_bottom = c->band_bottom;
    g->prev_centre = (int16_t)((c->win_top + c->win_bottom) >> 1);
    g->prev_isl_end = c->island.present ? (int16_t)(c->island.x + c->island.w) : 0;
    g->prev_isl_y = c->island.y;
}

/* Generate the next chunk into the ring (caller checked there is room). */
static void build_next(TripGen *g) {
    int slot = g->head + g->count;
    if (slot >= TRIP_GEN_RING) slot -= TRIP_GEN_RING;
    make_chunk(g, &g->ring[slot]);
    g->count++;
    g->made++;
    g->next_index++;
    g->next_wx += TRIP_CHUNK_PX;
}

void tripgen_init(TripGen *g, uint32_t seed) {
    memset(g, 0, sizeof *g);
    rng_seed(&g->rng, seed ^ 0x7A1B9E3Du);
    g->pk_chunk = 0;
    g->pk_slot = TRIP_FIRST_PICKUP_SLOT;
    /* builds NO chunk: the first screen is built by game_step_trip hold steps, one chunk per frame, never in the heavy
     * frame that resets the game and draws the first screen (frame time budget) */
}

int tripgen_covers(const TripGen *g, uint32_t scroll_px) {
    return g->next_wx >= scroll_px + 320u;
}

void tripgen_advance(TripGen *g, uint32_t scroll_px) {
    while (g->count > 0 && g->ring[g->head].wx + TRIP_CHUNK_PX <= scroll_px) {
        g->head = (uint8_t)(g->head + 1 == TRIP_GEN_RING ? 0 : g->head + 1);
        g->count--;
    }
    /* at most one chunk per call: one build is a fraction of the frame margin, three in one frame overran vblank */
    if (g->next_wx < scroll_px + 320u + TRIP_GEN_AHEAD_PX) {
        if (g->count == TRIP_GEN_RING) { g->overflow++; return; }
        build_next(g);
    }
}

const TripChunk *tripgen_get(const TripGen *g, uint32_t index) {
    int i;
    for (i = 0; i < g->count; i++) {
        int slot = g->head + i;
        if (slot >= TRIP_GEN_RING) slot -= TRIP_GEN_RING;
        if (g->ring[slot].index == index) return &g->ring[slot];
    }
    return 0;
}
