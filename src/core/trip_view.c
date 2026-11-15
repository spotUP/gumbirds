#include "trip_view.h"
#include "trip_cave_fade.h"
#include "trip_hit.h"
#include "camera.h"
#include "trip_cave.h"

int trip_view_screen_x(uint32_t wx, uint32_t scroll_px) {
    return (int)(int32_t)(wx - scroll_px);
}

void trip_view_haz_xy(const TripChunk *c, int i, uint32_t scroll_px, uint32_t steps, int *x, int *y) {
    const TripGenHazard *h = &c->haz[i];
    *x = trip_view_screen_x(c->wx + (uint32_t)(int32_t)h->x, scroll_px);
    *y = trip_hit_haz_y(h, steps);
}

int trip_view_meter_step(int gum) {
    if (gum < 0) gum = 0;
    if (gum > TRIP_VIEW_GUM_MAX) gum = TRIP_VIEW_GUM_MAX;
    return (gum + 127) >> 7;
}

int trip_view_meter_cell(int step, int c) {
    int v = step - (c << 1);
    return v < 0 ? 0 : (v > 2 ? 2 : v);
}

int trip_view_warning(int step) {
    return step <= 2;
}

/* Columns of a sprite block (left edge sx, cols columns of 16 px) that lie on screen. */
static int cols_on_screen(int sx, int cols) {
    int k, n = 0;
    for (k = 0; k < cols; k++) {
        int l = sx + (k << 4);
        if (l + 16 > 0 && l < TRIP_VIEW_SCREEN_W) n++;
    }
    return n;
}

/* s-th oldest held chunk, no modulo */
static const TripChunk *ring_at(const TripGen *g, int s) {
    int n = g->head + s;
    if (n >= TRIP_GEN_RING) n -= TRIP_GEN_RING;
    return &g->ring[n];
}

TripViewLine trip_view_line_sprites(const TripGen *g, uint32_t scroll_px, uint32_t steps, int y) {
    TripViewLine r;
    int s, i, k;
    uint32_t base = scroll_px & ~15u;   /* strip columns are 16 px aligned in the world */
    r.haz = r.pickup = r.island = r.strip = r.strip_rim = 0;
    for (s = 0; s < TRIP_GEN_RING; s++) {
        const TripChunk *c;
        if (s >= g->count) break;
        c = ring_at(g, s);
        for (i = 0; i < c->n_haz; i++) {
            TripViewHaz v;
            if (trip_view_haz_art(c, i, scroll_px, steps, &v) && y >= v.top && y < v.top + (v.rows << 4)) r.haz += cols_on_screen(v.left, v.cols);
        }
        if (c->pickup.present) {
            int top = trip_view_pickup_top(c);
            /* lines the idle bob and the collect effect (top 4 lines lower) can reach: the slot holds one or the other */
            if (y >= top + TRIP_VIEW_PICKUP_BOB_MIN && y < top + (TRIP_VIEW_PICKUP_TOP_OFF - TRIP_VIEW_COLLECT_TOP_OFF) + TRIP_VIEW_PICKUP_SPRITE_H)
                r.pickup += cols_on_screen(trip_view_screen_x(c->wx + (uint32_t)(int32_t)c->pickup.x, scroll_px) -
                                           TRIP_VIEW_PICKUP_LEFT_OFF, TRIP_VIEW_PICKUP_COLS);
        }
        if (c->island.present && y >= c->island.y && y < c->island.y + TRIP_VIEW_ISLAND_H)
            r.island += cols_on_screen(trip_view_screen_x(c->wx + (uint32_t)(int32_t)c->island.x, scroll_px),
                                       (c->island.w + 15) >> 4);
    }
    /* Strip ring: 22 columns from the 16 px aligned scroll (only those with screen x in -15..319 count); a column is drawn when the chunk under it has a strip on y. */
    for (k = 0; k < TRIP_VIEW_STRIP_COLS; k++) {
        uint32_t wx = base + ((uint32_t)k << 4);
        int full = 0, rim = 0;
        if (wx + 16 <= scroll_px || wx >= scroll_px + TRIP_VIEW_SCREEN_W) continue;   /* screen x outside -15..319: not on any line */
        for (s = 0; s < g->count; s++) {
            const TripChunk *c = ring_at(g, s);
            if (wx + 16 > c->wx && wx < c->wx + TRIP_CHUNK_PX) {   /* column overlaps the chunk */
                if (y < c->win_top) {
                    full = 1;
                    if (y >= c->win_top - TRIP_VIEW_RIM_LINES) rim = 1;
                } else if (y >= c->win_bottom) {
                    full = 1;
                    if (y < c->win_bottom + TRIP_VIEW_RIM_LINES) rim = 1;
                }
            }
        }
        r.strip += full;
        r.strip_rim += rim;
    }
    r.sum = r.haz + r.pickup + r.island + r.strip;
    r.sum_rim = r.haz + r.pickup + r.island + r.strip_rim;
    return r;
}

int trip_view_island_cols(int w) {
    return (w + 15) >> 4;
}

const TripChunk *trip_view_ring_chunk(const TripGen *g, int r, int ready) {
    int off = r - (int)g->head;
    if (!ready) return 0;
    if (off < 0) off += TRIP_GEN_RING;
    return off < (int)g->count ? &g->ring[r] : 0;
}

int trip_view_pickup_left(const TripChunk *c, uint32_t scroll_px) {
    int sx;
    if (!c->pickup.present) return CAMERA_COL_HIDDEN;
    sx = trip_view_screen_x(c->wx + (uint32_t)(int32_t)c->pickup.x, scroll_px) - TRIP_VIEW_PICKUP_LEFT_OFF;
    return (sx > -(TRIP_VIEW_PICKUP_COLS << 4) && sx < TRIP_VIEW_SCREEN_W) ? sx : CAMERA_COL_HIDDEN;
}

int trip_view_pickup_top(const TripChunk *c) { return c->pickup.y - TRIP_VIEW_PICKUP_TOP_OFF; }

/* Per kind (TripHazKind order coal, vent, cloud): sprite columns, rows, hit box centre inside the cell, frame count. From
 * assets/triphaz/triphaz_sheet.json (src/trip_haz.c asserts it against the generated tables). */
static const struct { uint8_t cols, rows, cx, cy, frames; } k_haz_art[3] = {
    { 2, 2, 13, 18, 24 },  /* coal  32 x 32 */
    { 2, 3, 16, 18, 16 },  /* vent  32 x 48; cy 18 = hit box centre (box 9 x 14, user approved) */
    { 3, 3, 25, 20, 24 },  /* cloud 48 x 48 */
};

int trip_view_haz_frame_count(int kind) { return k_haz_art[kind].frames; }

int trip_view_haz_frame(int kind, uint32_t steps) {
    uint32_t n = steps >> TRIP_VIEW_HAZ_TICKS_SHIFT, t;
    if (k_haz_art[kind].frames == 16) return (int)(n & 15);
    t = n >> 3;                       /* 24 = 8 * 3: n mod 24 = (n & 7) + 8 * ((n >> 3) mod 3) */
    while (t > 3) t = (t >> 2) + (t & 3); /* 4 = 1 mod 3: the base 4 digit sum keeps t mod 3 */
    if (t == 3) t = 0;
    return (int)((n & 7) + (t << 3));
}

int trip_view_haz_art(const TripChunk *c, int i, uint32_t scroll_px, uint32_t steps, TripViewHaz *out) {
    int hx, hy, kind;
    if (!c || i < 0 || i >= c->n_haz) return 0;
    kind = c->haz[i].kind;
    trip_view_haz_xy(c, i, scroll_px, steps, &hx, &hy);
    out->kind = kind;
    out->cols = k_haz_art[kind].cols;
    out->rows = k_haz_art[kind].rows;
    out->left = hx - k_haz_art[kind].cx;
    out->top = hy - k_haz_art[kind].cy;
    out->frame = trip_view_haz_frame(kind, steps);
    return out->left > -(out->cols << 4) && out->left < TRIP_VIEW_SCREEN_W;
}

int trip_view_pickup_bob(int frame) {
    static const int8_t bob[TRIP_VIEW_PICKUP_FRAMES] = { -2, -1, 0, 1, 3, 3, 3, 2, 1, 0, -1, -1, -2, -2, -2, -2 }; /* draft README */
    return bob[frame & (TRIP_VIEW_PICKUP_FRAMES - 1)];
}

int trip_view_pickup_frame(uint32_t steps) { return (int)((steps >> 2) & (TRIP_VIEW_PICKUP_FRAMES - 1)); }

int trip_view_island_col_x(const TripChunk *c, int col, uint32_t scroll_px) {
    int sx;
    if (!c->island.present || col < 0 || col >= trip_view_island_cols(c->island.w)) return CAMERA_COL_HIDDEN;
    sx = trip_view_screen_x(c->wx + (uint32_t)(int32_t)c->island.x + (uint32_t)(col << 4), scroll_px);
    return (sx > -16 && sx < TRIP_VIEW_SCREEN_W) ? sx : CAMERA_COL_HIDDEN;
}

const TripChunk *trip_view_strip_chunk(const TripGen *g, uint32_t j, int ready) {
    uint32_t wx = j << 4;
    int r;
    for (r = 0; r < TRIP_GEN_RING; r++) {
        const TripChunk *ch = trip_view_ring_chunk(g, r, ready);
        /* trailing curve columns wait until the next chunk's window is known */
        if (ch && wx >= ch->wx && wx - ch->wx < TRIP_CHUNK_PX)
            return (wx - ch->wx >= 16 * (TRIP_CAVE_COLS - TRIP_CAVE_CURVE_COLS) && !ch->out_known) ? 0 : ch;
    }
    return 0;
}

/* Fade cell d rows past a flat piece (0 = first row past it). Floor: TRIP_STRIP_FILL_ROWS fill rows, fade A, fade B, solid gum.
 * Roof: fade A, fade B, black. Fade A/B cells follow world column j (floor 2 cells, roof 4), as the flat fade draft places them. */
static void flat_fade(TripStripCell *e, int d, uint32_t j, int ceiling) {
    e->frame = 0; e->cell = 0; e->flip = 0;
    if (ceiling) {
        e->role = TRIP_STRIP_ROOF;
        e->frame = d == 0 ? TRIP_ROOF_FADE_A : d == 1 ? TRIP_ROOF_FADE_B : TRIP_ROOF_BLACK;
        if (d < 2) e->cell = (uint8_t)(j & 3);
    } else if (d < TRIP_STRIP_FILL_ROWS) e->role = TRIP_STRIP_FILL;
    else {
        d -= TRIP_STRIP_FILL_ROWS;
        e->role = TRIP_STRIP_FLOOR_FADE;
        e->frame = d == 0 ? TRIP_FLOOR_FADE_A : d == 1 ? TRIP_FLOOR_FADE_B : TRIP_FLOOR_SOLID;
        if (d < 2) e->cell = (uint8_t)(j & 1);
    }
}

/* Cell r rows away from the window edge of a curve piece (floor: down from the piece top, roof: up from the piece bottom), from the
 * sloped fade lookup of trip_cave_fade.h. */
static void curve_cell(TripStripCell *e, const TripCavePiece *p, int r, int ceiling) {
    int prow = trip_cave_piece_rows(p->kind), k = p->kind == TRIP_CAVE_S16 ? 0 : 1;
    int v = r < TRIP_FADE_ROWS ? (ceiling ? trip_fade_roof : trip_fade_floor)[k][p->pcol][r] : TRIP_FADE_END;
    e->flip = p->hflip ? TRIP_STRIP_HFLIP : 0; e->frame = 0; e->cell = 0;
    if (v == TRIP_FADE_PIECE) {
        if (ceiling) { e->role = TRIP_STRIP_ROOF; e->frame = k ? TRIP_ROOF_S32 : TRIP_ROOF_S16; e->cell = (uint8_t)(p->pcol * prow + prow - 1 - r); }
        else { e->role = k ? TRIP_STRIP_FS32 : TRIP_STRIP_FS16; e->cell = (uint8_t)(p->pcol * prow + r); }
    } else if (v == TRIP_FADE_FILL) e->role = TRIP_STRIP_FILL;
    else if (v == TRIP_FADE_END) { e->flip = 0; e->role = ceiling ? TRIP_STRIP_ROOF : TRIP_STRIP_FLOOR_FADE; e->frame = ceiling ? TRIP_ROOF_BLACK : TRIP_FLOOR_SOLID; }
    else { e->role = ceiling ? TRIP_STRIP_ROOF : TRIP_STRIP_FLOOR_FADE; e->frame = ceiling ? TRIP_ROOF_SLOPED : TRIP_FLOOR_SLOPED; e->cell = (uint8_t)v; }
}

int trip_view_strip_column(const TripChunk *c, uint32_t j, int ceiling, TripStripCell *cells, int *top) {
    TripCavePiece p;
    int k = (int)((j << 4) - c->wx) >> 4, prow = 0, rows, i, edge;
    trip_cave_piece(c, k, ceiling, &p);
    prow = trip_cave_piece_rows(p.kind);
    if (ceiling) {
        edge = p.y0 + 16 * prow;   /* piece bottom */
        rows = edge > 0 ? (edge + 15) >> 4 : 0;
        if (rows > TRIP_VIEW_STRIP_MAX_ROWS) rows = TRIP_VIEW_STRIP_MAX_ROWS;
        *top = edge - (rows << 4);
        for (i = 0; i < rows; i++) {
            int r = rows - 1 - i;   /* rows up from the piece bottom */
            TripStripCell *e = &cells[i];
            if (p.kind != TRIP_CAVE_FLAT) curve_cell(e, &p, r, 1);
            else if (r == 0) {
                e->role = TRIP_STRIP_ROOF; e->flip = 0; e->cell = (uint8_t)(j & 3);
                e->frame = (uint8_t)((((j >> 2) * 2654435761u) >> 31) ? TRIP_ROOF_RIM_B : TRIP_ROOF_RIM_A);
            } else flat_fade(e, r - 1, j, 1);
        }
    } else {
        edge = p.y0;
        rows = edge < TRIP_VIEW_STRIP_BOTTOM ? (TRIP_VIEW_STRIP_BOTTOM - (edge > 0 ? edge : 0) + 15) >> 4 : 0;
        if (rows > TRIP_VIEW_STRIP_MAX_ROWS) rows = TRIP_VIEW_STRIP_MAX_ROWS;
        *top = edge;
        for (i = 0; i < rows; i++) {
            TripStripCell *e = &cells[i];
            if (p.kind != TRIP_CAVE_FLAT) curve_cell(e, &p, i, 0);
            else if (i == 0) { e->role = (uint8_t)(TRIP_STRIP_LIP + (j & 3)); e->frame = 0; e->cell = 0; e->flip = 0; }
            else flat_fade(e, i - 1, j, 0);
        }
    }
    return rows;
}

int trip_view_strip_advance(TripStripRing *r, uint32_t j0) {
    int jumped = 0;
    if (!r->valid || j0 < r->j0 || j0 - r->j0 > TRIP_VIEW_STRIP_COLS) { r->s0 = 0; jumped = 1; }
    else {
        uint32_t d = j0 - r->j0;
        while (d--) { if (++r->s0 == TRIP_VIEW_STRIP_COLS) r->s0 = 0; }
    }
    r->j0 = j0; r->valid = 1;
    return jumped;
}

int trip_view_strip_slot(const TripStripRing *r, int k) {
    int s = r->s0 + k;
    return s >= TRIP_VIEW_STRIP_COLS ? s - TRIP_VIEW_STRIP_COLS : s;
}
