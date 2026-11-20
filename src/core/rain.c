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

static void put(VramQueue *q, uint16_t idx, uint16_t cell) { vq_fix_put(q, (uint8_t)(idx / RAIN_ROWS), (uint8_t)(idx % RAIN_ROWS + 2), cell); }
static uint16_t want(const VramQueue *q, uint16_t idx) { return q->fix_want[(idx / RAIN_ROWS) * VQ_FIX_ROWS + idx % RAIN_ROWS + 2]; }

static void release_all(Rain *r, VramQueue *q) {
    CELLW = (uint16_t)(r->pal << 12);
    for (uint16_t i = 0; i < r->n_list; i++) {
        uint16_t c = r->list[i];
        if (r->own[c] && want(q, c) == CELL(r->own[c] - 1)) put(q, c, BLANK);
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
    else if (r->timer && --r->timer == 0) { r->flash_t = 1; r->burst_n = 0; r->gap = (uint8_t)((r->gap + 1) % 7); r->timer = rain_gap_frames(r->gap); }
    /* spawn: far entries fire at frame == gm % TAB, near at frame * 2 == gm % NEAR_TAB; the kind is the gust now */
    uint16_t gm = (uint16_t)(f % RAIN_LOOP);
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
    /* cells: far first, near wins a shared cell */
    uint32_t hud = rain_hud_rows[mode];
    uint16_t cells[RAIN_MAX_DROPS * 3], n_cells = 0;
    for (uint8_t pass = 0; pass < 2; pass++) {
        for (uint8_t i = 0; i < r->n; i++) {
            RainDrop *d = &r->drop[i];
            if ((d->kind >= 3) != pass) continue;
            const uint8_t *cut = &rain_cut[((d->kind * 8 + (d->px & 7)) * 2 + ((d->py & 7) >> 2)) * 9];
            uint8_t n = rain_cut_n[(d->kind * 8 + (d->px & 7)) * 2 + ((d->py & 7) >> 2)];
            for (uint8_t k = 0; k < n; k++) {
                int16_t c = (int16_t)((d->px >> 3) + cut[k * 3]), row = (int16_t)((d->py >> 3) + cut[k * 3 + 1]);
                if (c < 0 || c >= RAIN_COLS || row < 0 || row >= RAIN_ROWS || (hud >> row & 1u)) continue;
                uint16_t idx = (uint16_t)(c * RAIN_ROWS + row);
                if (!r->now[idx]) cells[n_cells++] = idx;
                r->now[idx] = (uint8_t)(cut[k * 3 + 2] + 1);
            }
        }
    }
    /* blank cells that stopped holding rain, then write the new ones: only blank cells (or ours) are taken */
    for (uint16_t i = 0; i < r->n_list; i++) {
        uint16_t c = r->list[i];
        if (r->now[c]) continue;
        if (want(q, c) == CELL(r->own[c] - 1)) put(q, c, BLANK);
        r->own[c] = 0;
    }
    r->n_list = 0;
    for (uint16_t i = 0; i < n_cells; i++) {
        uint16_t c = cells[i], w = want(q, c);
        uint8_t t = r->now[c];
        r->now[c] = 0;
        if (w != CELL(t - 1) && w != BLANK) { r->own[c] = 0; continue; } /* text or HUD owns it */
        if (w != CELL(t - 1)) put(q, c, CELL(t - 1));
        r->own[c] = t;
        r->list[r->n_list++] = c;
    }
    /* advance */
    uint8_t keep = 0;
    for (uint8_t i = 0; i < r->n; i++) {
        RainDrop d = r->drop[i];
        d.px = (int16_t)(d.px - rain_move[d.kind][0]);
        d.py = (int16_t)(d.py + rain_move[d.kind][1]);
        if (scroll_px > 0) { /* extra left steps of this drop's own lattice step (2 near, 1 far per px of speed) */
            int16_t step = (int16_t)(rain_move[d.kind][0] * (d.kind >= 3 ? 2 : 1));
            d.acc = (int16_t)(d.acc + scroll_px);
            while (d.acc >= step) { d.acc = (int16_t)(d.acc - step); d.px = (int16_t)(d.px - step); }
        }
        int16_t end = (int16_t)(d.end_row * 8);
        if (d.py < (end < H ? end : H) && d.px > -16) r->drop[keep++] = d;
    }
    r->n = keep;
}

uint8_t rain_flash_index(const Rain *r) {
    uint8_t t = r->flash_t ? (uint8_t)(r->flash_t - 1) : 255;
    if (t < 4) return 1;
    if (t < 8) return 2;
    if (t >= 16 && t < 20) return 3;
    if (t >= 20 && t < 24) return 4;
    return 0;
}

uint8_t rain_burst_palette(const Rain *r) { return (uint8_t)(r->flash_t && r->flash_t - 1 < RAIN_BURST_PAL_FRAMES); }

uint16_t rain_flash_color(uint16_t c, uint8_t idx) {
    uint16_t q = FLASH_Q[idx > 4 ? 0 : idx];
    uint16_t ch[3] = { (uint16_t)((((c >> 8) & 0xF) << 1) | ((c >> 14) & 1)), (uint16_t)((((c >> 4) & 0xF) << 1) | ((c >> 13) & 1)), (uint16_t)(((c & 0xF) << 1) | ((c >> 12) & 1)) };
    for (uint8_t i = 0; i < 3; i++) ch[i] = (uint16_t)(ch[i] + (31 - ch[i]) * q / 32);
    return (uint16_t)((c & 0x8000) | ((ch[0] & 1) << 14) | ((ch[1] & 1) << 13) | ((ch[2] & 1) << 12) | ((ch[0] >> 1) << 8) | ((ch[1] >> 1) << 4) | (ch[2] >> 1));
}
