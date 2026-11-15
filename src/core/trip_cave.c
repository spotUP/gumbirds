#include "trip_cave.h"

/* Per piece tile column: roof = max rock depth below the piece top, floor = min first gum row below the piece top, from
 * thoughts/shared/drafts/2026-11-15-trip-cave-v3/heights.json (pieces drawn falling / rising to the right). */
static const uint8_t k_roof[3][3] = { { 16, 16, 16 }, { 20, 28, 32 }, { 25, 41, 48 } };
static const uint8_t k_floor[3][3] = { { 0, 0, 0 }, { 14, 6, 2 }, { 26, 10, 2 } };

int trip_cave_piece_rows(int kind) { return kind + 1; }

static int curve_kind(int d) { return d == 16 ? TRIP_CAVE_S16 : d == 32 ? TRIP_CAVE_S32 : TRIP_CAVE_FLAT; }

void trip_cave_piece(const TripChunk *c, int k, int ceiling, TripCavePiece *p) {
    int own = ceiling ? c->win_top : c->win_bottom;
    p->kind = TRIP_CAVE_FLAT; p->pcol = 0; p->hflip = 0;
    p->y0 = (int16_t)(ceiling ? own - 16 : own);
    if (k < TRIP_CAVE_CURVE_COLS && c->in_known) {             /* leading side: own window narrower than the one before */
        int in = ceiling ? c->in_top : c->in_bottom, d = ceiling ? own - in : in - own;
        if (d > 0 && curve_kind(d)) {
            p->kind = (uint8_t)curve_kind(d); p->pcol = (uint8_t)k;
            p->y0 = (int16_t)(ceiling ? in - 16 : own);
        }
    } else if (k >= TRIP_CAVE_COLS - TRIP_CAVE_CURVE_COLS && c->out_known) { /* trailing side, mirrored */
        int out = ceiling ? c->out_top : c->out_bottom, d = ceiling ? own - out : out - own;
        if (d > 0 && curve_kind(d)) {
            p->kind = (uint8_t)curve_kind(d); p->pcol = (uint8_t)(TRIP_CAVE_COLS - 1 - k); p->hflip = 1;
            p->y0 = (int16_t)(ceiling ? out - 16 : own);
        }
    }
}

int trip_cave_edge(const TripChunk *c, int k, int ceiling) {
    TripCavePiece p;
    trip_cave_piece(c, k, ceiling, &p);
    if (p.kind == TRIP_CAVE_FLAT) return ceiling ? c->win_top : c->win_bottom;
    return p.y0 + (ceiling ? k_roof[p.kind][p.pcol] : k_floor[p.kind][p.pcol]);
}

void trip_cave_span(const TripChunk *c, int x0, int x1, int *top, int *bot) {
    int k;
    if (x0 < 0) x0 = 0;
    if (x1 > TRIP_CHUNK_PX - 1) x1 = TRIP_CHUNK_PX - 1;
    for (k = x0 >> 4; k <= x1 >> 4; k++) {
        int t = trip_cave_edge(c, k, 1), b = trip_cave_edge(c, k, 0);
        if (t > *top) *top = t;
        if (b < *bot) *bot = b;
    }
}
