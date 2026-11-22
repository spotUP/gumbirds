/* rain.c - storm rain drops, cut table playback and the lightning timer. See rain.h. */
#include "rain.h"
#include "gen/rain_tiles.h"
#include "gen/fix_font.h"
#include <string.h>

#define H 224
#define RAIN_FAR_FIRST 0
static const uint8_t SPAWN_N[6] = RAIN_SPAWN_N;
static const uint8_t *const SPAWN_TAB[6] = RAIN_SPAWN_TAB;
static const uint8_t GAP_SEC[7] = { 7, 11, 5, 13, 9, 6, 12 };
static const uint8_t FLASH_Q[5] = { 0, 16, 7, 13, 4 }; /* 32nds toward white: levels 0.5, 0.22, 0.4, 0.12 */

uint16_t rain_gap_frames(uint8_t i) { return (uint16_t)(GAP_SEC[i % 7] * 60); }

void rain_init(Rain *r, uint8_t pal_slot) {
    memset(r, 0, sizeof *r);
    r->pal = pal_slot;
    r->timer = rain_gap_frames(0);
    r->rng = 1;
}

static uint8_t gust_now(uint16_t gm) {
    uint8_t g = 0;
    for (uint8_t i = 0; i < RAIN_GUSTS; i++) if (rain_gust_start[i] <= gm) g = rain_gust_kind[i];
    return g;
}

static void drop_add(Rain *r, uint8_t kind, uint8_t col, uint8_t row0, uint8_t rows) {
    if (r->n >= RAIN_MAX_DROPS) return;
    RainDrop *d = &r->drop[r->n++];
    d->px = (int16_t)(col * 8 + rain_move[kind][2]);
    d->py = (int16_t)(row0 * 8);
    d->kind = kind;
    d->end_row = (uint8_t)(row0 + rows);
    d->acc = 0;
}

static uint16_t CELLW;
#define CELL(t) ((uint16_t)(CELLW | (RAIN_FIX_BASE + (t))))
#define BLANK ((uint16_t)FIXFONT_BLANK)
/* a cell rain may take: the blank tile in any palette (gfx_fix_tile blanks with the caller's slot), or never written since vq_init */
#define FREE(w) (((w) & 0x0FFFu) == BLANK || (w) == 0xFFFFu)
static const uint32_t BIT[32] = {
    1ul << 0, 1ul << 1, 1ul << 2, 1ul << 3, 1ul << 4, 1ul << 5, 1ul << 6, 1ul << 7, 1ul << 8, 1ul << 9, 1ul << 10,
    1ul << 11, 1ul << 12, 1ul << 13, 1ul << 14, 1ul << 15, 1ul << 16, 1ul << 17, 1ul << 18, 1ul << 19, 1ul << 20,
    1ul << 21, 1ul << 22, 1ul << 23, 1ul << 24, 1ul << 25, 1ul << 26, 1ul << 27, 1ul << 28, 1ul << 29, 1ul << 30, 1ul << 31 };

/* vq_fix_put without the bounds check and the shifts: fi is a fix_want index the caller knows is on screen */
static inline void put(VramQueue *q, uint16_t fi, uint16_t cell) {
    q->fix_want[fi] = cell;
    q->fix_dirty[fi >> 5] |= BIT[fi & 31];
    q->fix_any = 1;
}

static void release_all(Rain *r, VramQueue *q) {
    CELLW = (uint16_t)(r->pal << 12);
    for (uint16_t i = 0; i < r->n_list; i++) {
        uint16_t c = r->list[i];
        if (r->own[c] && q->fix_want[c] == CELL(r->own[c] - 1)) put(q, c, BLANK);
        r->own[c] = 0;
    }
    r->n_list = 0;
}

void rain_step(Rain *r, VramQueue *q, uint8_t active, uint8_t mode, int16_t scroll_px) {
    if (!active) {
        if (r->was_active) { release_all(r, q); rain_init(r, r->pal); }
        return;
    }
    r->was_active = 1;
    CELLW = (uint16_t)(r->pal << 12);
    uint16_t f = r->frame++;
    /* lightning: a countdown over the typed gaps; the flash starts the burst */
    if (r->flash_t) { if (++r->flash_t > RAIN_BURST_FRAMES) r->flash_t = 0; }
    else if (r->timer && --r->timer == 0) { r->flash_t = 1; r->burst_n = 0; r->gap = (uint8_t)(r->gap == 6 ? 0 : r->gap + 1); r->timer = rain_gap_frames(r->gap); }
    /* spawn: far entries fire at frame == gm % TAB, near at frame * 2 == gm % NEAR_TAB; the kind is the gust now */
    uint16_t gm = (uint16_t)(f & (RAIN_LOOP - 1));
    uint8_t gust = gust_now(gm);
    for (uint8_t near = 0; near < 2; near++) {
        uint8_t t = (uint8_t)(near * 3 + gust), kind = t;
        uint16_t ph = near ? (uint16_t)(gm % RAIN_NEAR_TAB) : (uint16_t)(gm % RAIN_TAB);
        const uint8_t *e = SPAWN_TAB[t];
        for (uint8_t i = 0; i < SPAWN_N[t]; i++, e += 4)
            if ((near ? e[0] * 2u : e[0]) == ph) drop_add(r, kind, e[1], e[2], e[3]);
    }
    if (r->flash_t && r->flash_t - 1 < RAIN_BURST_FRAMES) {
        uint8_t bt = (uint8_t)(r->flash_t - 1);
        const uint8_t *e = rain_burst_spawn;
        for (uint8_t i = 0; i < RAIN_BURST_N; i++, e += 4) if (e[0] == bt) drop_add(r, 5, e[1], e[2], e[3]);
    }
    /* cells: one pass over the drops (cells, then advance). Far drops never replace a near cell; near wins a shared cell (now[] bit 7). */
    static uint8_t rok[256 + 4], ok_mode = 0xFF; /* row_ok padded: a drop row0 is a byte, cut rows add up to 2 */
    if (ok_mode != mode) {
        uint32_t hud = rain_hud_rows[mode];
        for (uint8_t y = 0; y < RAIN_ROWS; y++) rok[y] = (uint8_t)!(hud >> y & 1u);
        ok_mode = mode;
    }
    /* pointer walks and native-width locals: the struct-copy and byte-counter form spilled to the stack and cost ~90 raster lines a storm frame */
    uint8_t *now = r->now, *own = r->own;
    uint16_t *want = q->fix_want;
    uint16_t cells[RAIN_MAX_DROPS * 3], *cp = cells;
    const RainDrop *s = r->drop, *se = s + r->n;
    RainDrop *o = r->drop; /* kept drops are written back in place, o never passes s */
    for (; s < se; s++) {
        unsigned kind = s->kind;
        int px = s->px, py = s->py;
        unsigned near = kind >= 3, flag = near << 7;
        unsigned ci = ((kind << 3 | (px & 7)) << 1) | ((py >> 2) & 1);
        const RainCut *cut = &rain_cutw[ci * 3];
        int c0 = px >> 3, r0 = py >> 3;
        uint8_t *nb = now + (c0 << 5) + r0 + 2;
        const uint8_t *rk = rok + r0;
        unsigned inside = (unsigned)c0 < RAIN_COLS - 1; /* every cut column is 0 or 1: no column test needed */
        for (unsigned k = rain_cut_n[ci]; k; k--, cut++) {
            if (!rk[cut->dr]) continue;
            if (!inside && (unsigned)(c0 + cut->dc) >= RAIN_COLS) continue;
            uint8_t *np = nb + cut->off;
            unsigned v = *np;
            if (!v) *cp++ = (uint16_t)(np - now);
            if (!v || near || !(v & 0x80)) *np = (uint8_t)(cut->t1 | flag);
        }
        const int8_t *mv = rain_move[kind];
        int acc = s->acc;
        px -= mv[0];
        py += mv[1];
        if (scroll_px > 0) { /* extra left steps of this drop's own lattice step (2 near, 1 far per px of speed) */
            int step = near ? mv[0] * 2 : mv[0];
            acc += scroll_px;
            while (acc >= step) { acc -= step; px -= step; }
        }
        int end = s->end_row * 8;
        if (py < (end < H ? end : H) && px > -16) {
            uint8_t er = s->end_row;
            o->px = (int16_t)px; o->py = (int16_t)py; o->kind = (uint8_t)kind; o->end_row = er; o->acc = (int16_t)acc;
            o++;
        }
    }
    r->n = (uint8_t)(o - r->drop);
    /* blank cells that stopped holding rain, then write the new ones: only free cells (or ours) are taken */
    const uint16_t cwb = CELLW;
    for (const uint16_t *lp = r->list, *le = lp + r->n_list; lp < le; lp++) {
        unsigned c = *lp;
        if (now[c]) continue;
        if (want[c] == (uint16_t)(cwb | (RAIN_FIX_BASE + own[c] - 1))) put(q, (uint16_t)c, BLANK);
        own[c] = 0;
    }
    uint16_t *lo = r->list;
    for (const uint16_t *ip = cells; ip < cp; ip++) {
        unsigned c = *ip, w = want[c];
        unsigned t = now[c] & 0x7F;
        unsigned cw = (uint16_t)(cwb | (RAIN_FIX_BASE + t - 1));
        now[c] = 0;
        if (w != cw) {
            if (!FREE(w) && !(own[c] && w == (uint16_t)(cwb | (RAIN_FIX_BASE + own[c] - 1)))) { own[c] = 0; continue; } /* text or HUD owns it */
            put(q, (uint16_t)c, (uint16_t)cw);
        }
        own[c] = (uint8_t)t;
        *lo++ = (uint16_t)c;
    }
    uint16_t nl = (uint16_t)(lo - r->list);
    r->n_list = nl;
}

uint8_t rain_flash_index(const Rain *r) {
    uint8_t t = r->flash_t ? (uint8_t)(r->flash_t - 1) : 255;
    if (t < 4) return 1;
    if (t < 8) return 2;
    if (t >= 16 && t < 20) return 3;
    if (t >= 20 && t < 24) return 4;
    return 0;
}

uint8_t rain_burst_active(const Rain *r) { return (uint8_t)(r->flash_t && r->flash_t - 1 < RAIN_BURST_PAL_FRAMES); }

uint16_t rain_flash_color(uint16_t c, uint8_t idx) {
    uint16_t q = FLASH_Q[idx > 4 ? 0 : idx];
    uint16_t ch[3] = { (uint16_t)((((c >> 8) & 0xF) << 1) | ((c >> 14) & 1)), (uint16_t)((((c >> 4) & 0xF) << 1) | ((c >> 13) & 1)), (uint16_t)(((c & 0xF) << 1) | ((c >> 12) & 1)) };
    for (uint8_t i = 0; i < 3; i++) ch[i] = (uint16_t)(ch[i] + (31 - ch[i]) * q / 32);
    return (uint16_t)((c & 0x8000) | ((ch[0] & 1) << 14) | ((ch[1] & 1) << 13) | ((ch[2] & 1) << 12) | ((ch[0] >> 1) << 8) | ((ch[1] >> 1) << 4) | (ch[2] >> 1));
}
