#include "stadium_hw.h"
#include "gfx.h"
#include "sprite_slots.h"
#include "vram_layout.h"
#include "core/game.h"
#include "core/stadium.h"
#include "../build/gen/stadium_sprites.h"
#include "../build/gen/stadium_layout.h"

#define COLS_MAX STADIUM_FLING_COLS
#define GROUP_ROWS 8
#define FIRST BG_FAR_SPRITE            /* the stands own the parallax plane slots 21..110 (bg_stadium_planes hides the planes) */
#define TOWER_SPRITES 4
#define LOADS_PER_FRAME 4              /* palettes and strips queued per frame: bounds the burst at entry */
#define G1_TOP 32                      /* screen y of group 1 (plane row 2) */
#define STILL_X (-8)                   /* 336 px stands centred on the 320 px screen */
#define DYN 10
#define PAL_BASE (STADIUM_PAL_SLOT + STADIUM_PALETTE_COUNT)
_Static_assert(FIRST + 2 * COLS_MAX + TOWER_SPRITES <= SPRITE_RESERVED + 111, "stands overrun the parallax plane slots");
_Static_assert(STADIUM_TILE_BASE + STADIUM_TILE_COUNT <= 0x10000, "stand tile numbers need the attribute's tile high bits");

/* dynamic cells: {group, row} of far row 0 top/seat, far row 1 top/seat, near row 0, near row 1, near row 2 */
static const u8 k_dyn[DYN][2] = {{1, 0}, {1, 1}, {0, 3}, {0, 4}, {1, 3}, {1, 4}, {0, 6}, {0, 7}, {1, 5}, {1, 6}};

static Stadium g_st;
static u8 g_on, g_vis, g_ready, g_mood, g_fling, g_cols, g_load, g_phase, g_passes, g_step, g_warm;
static u16 g_pairs[2][21][GROUP_ROWS][2];          /* strip pairs {tile, attribute}: the queue reads them at flush time, so they stay */
static u16 g_tpairs[TOWER_SPRITES][2][2];
static u16 g_cell[COLS_MAX][DYN], g_dig[STADIUM_DIGITS];
static u16 g_s3[2 * COLS_MAX + TOWER_SPRITES], g_s4[2 * COLS_MAX + TOWER_SPRITES];

static u16 attr_of(u8 pal, u8 flip) { return (u16)(((PAL_BASE + pal) << 8) | (flip ? 1 : 0)); }

static void build_pairs(u8 mood) {
    for (u8 g = 0; g < 2; g++)
        for (u8 c = 0; c < 21; c++)
            for (u8 r = 0; r < GROUP_ROWS; r++) {
                u8 p = ST_LP[mood][g][c][r];
                g_pairs[g][c][r][0] = ST_LT[mood][g][c][r];
                g_pairs[g][c][r][1] = attr_of(p & 127, p >> 7);
            }
    for (u8 t = 0; t < TOWER_SPRITES; t++) {
        u8 side = t & 1;     /* left or right half of the 32 px tower */
        g_tpairs[t][0][0] = ST_TOWER_TILE[side];
        g_tpairs[t][1][0] = ST_TOWER_TILE[2 + side];
        g_tpairs[t][0][1] = g_tpairs[t][1][1] = attr_of(ST_TOWER_PAL[mood], 0);
    }
}

static void hide_all(void) {
    for (u8 i = 0; i < 2 * COLS_MAX + TOWER_SPRITES; i++) g_s3[i] = 0;
    gfx_scb_run((u16)(ADDR_SCB3 + FIRST), 1, g_s3, 2 * COLS_MAX + TOWER_SPRITES);
}

static u16 sprite_of(u8 g, u8 c) { return (u16)(FIRST + g * g_cols + c); }
static void put(u8 g, u8 c, u8 row, u16 tile) { gfx_vram_word((u16)(ADDR_SCB1 + sprite_of(g, c) * 64 + row * 2), (u16)(STADIUM_TILE_BASE + tile)); }

static void write_column(u8 c) {
    u8 cc = (u8)(c % 21), storm = g_mood == GAME_MOOD_STORM;
    StadiumCell v[DYN / 2];
    v[0] = stadium_far(&g_st, 0, cc);
    v[1] = stadium_far(&g_st, 1, cc);
    v[2] = stadium_near(&g_st, 0, cc, storm);
    v[3] = stadium_near(&g_st, 1, cc, storm);
    v[4] = stadium_near(&g_st, 2, cc, storm);
    for (u8 k = 0; k < DYN; k++) {
        u16 t = (k & 1) ? v[k >> 1].bot : v[k >> 1].top;
        if (g_cell[c][k] != t) { put(k_dyn[k][0], c, k_dyn[k][1], t); g_cell[c][k] = t; }
    }
}

void stadium_hw_scores(u8 p1, u8 p2) { stadium_set_scores(&g_st, p1, p2); }
void stadium_hw_finish(int winner) { stadium_finish(&g_st, winner); }
void stadium_hw_wave(void) { stadium_wave(&g_st); }
u8 stadium_hw_loaded(void) { return g_ready; }

void stadium_hw_step(int on, int show, u8 mood, int fling, int scroll) {
    u8 loads = LOADS_PER_FRAME, npal, nstrip, units;
    int x0;
    if (!on) {
        if (g_on) { hide_all(); g_on = g_vis = g_ready = 0; }
        return;
    }
    if (mood > GAME_MOOD_STORM) mood = GAME_MOOD_MOON;
    if (!g_on || mood != g_mood || (u8)(fling != 0) != g_fling) {
        if (!g_on) { stadium_reset(&g_st); stadium_wave(&g_st); g_step = 0; g_warm = 0; }
        g_on = 1; g_vis = g_ready = 0; g_mood = mood; g_fling = (u8)(fling != 0); g_cols = fling ? STADIUM_FLING_COLS : STADIUM_COLS;
        g_load = g_phase = g_passes = 0;
        for (u8 c = 0; c < COLS_MAX; c++) for (u8 k = 0; k < DYN; k++) g_cell[c][k] = 0;
        for (u8 i = 0; i < STADIUM_DIGITS; i++) g_dig[i] = 0xFFFF;
        build_pairs(mood);
        gfx_sprite_unchained(FIRST, (u8)(2 * g_cols + TOWER_SPRITES));
        hide_all();
    }
    npal = ST_PAL_COUNT[mood];
    nstrip = (u8)(2 * g_cols + TOWER_SPRITES);
    units = (u8)(npal + nstrip);
    while (loads && g_load < units) {
        if (g_load < npal) {
            const u16 *p = stadium_extra_palettes[ST_PAL_FIRST[mood] + g_load];
            for (u8 i = 0; i < 16; i++) gfx_pal((u16)((PAL_BASE + ST_PAL_FIRST[mood] + g_load) * 16 + i), p[i]);
        } else {
            u8 s = (u8)(g_load - npal);
            if (s < 2 * g_cols) gfx_strip_attr((u16)(FIRST + s), &g_pairs[s / g_cols][(s % g_cols) % 21][0][0], STADIUM_TILE_BASE, GROUP_ROWS);
            else gfx_strip_attr((u16)(FIRST + s), &g_tpairs[s - 2 * g_cols][0][0], STADIUM_TILE_BASE, 2);
        }
        g_load++; loads--;
    }
    if (g_warm < STADIUM_FAR_ROWS * STADIUM_COLS) { stadium_far_warm(g_warm / STADIUM_COLS, g_warm % STADIUM_COLS); g_warm++; }   /* one cell a frame from entry */
    if (g_load >= units) {
        /* one crowd step per STADIUM_STEP_FRAMES frames; each frame rewrites the columns of its phase (c % 3 == phase) */
        if (!g_phase) stadium_step(&g_st);
        for (u8 c = g_phase; c < g_cols; c += STADIUM_STEP_FRAMES) write_column(c);
        if (++g_phase >= STADIUM_STEP_FRAMES) { g_phase = 0; if (g_passes < 2) g_passes++; }
        uint16_t d[STADIUM_DIGITS];
        stadium_digit_tiles(&g_st, d);
        for (u8 i = 0; i < STADIUM_DIGITS; i++)
            if (g_dig[i] != d[i]) { put(0, ST_DIGIT_COL[i], 1, d[i]); g_dig[i] = d[i]; }
        g_ready = g_passes >= 1;
    }
    if (show && g_ready) g_vis = 1;
    if (!show) { if (g_vis) hide_all(); g_vis = 0; }
    if (!g_vis) return;
    x0 = fling ? stadium_fling_x(scroll) : STILL_X;
    for (u8 c = 0; c < g_cols; c++) {
        g_s3[c] = gfx_scb3_word(GROUP_ROWS, 0);
        g_s3[g_cols + c] = gfx_scb3_word(GROUP_ROWS, G1_TOP);
        g_s4[c] = g_s4[g_cols + c] = gfx_scb4_word(x0 + 16 * c);
    }
    for (u8 t = 0; t < TOWER_SPRITES; t++) {
        g_s3[2 * g_cols + t] = gfx_scb3_word(2, 0);
        g_s4[2 * g_cols + t] = gfx_scb4_word(x0 + ST_TOWER_X[t >> 1] + 16 * (t & 1));
    }
    gfx_scb_run((u16)(ADDR_SCB3 + FIRST), 1, g_s3, (u8)(2 * g_cols + TOWER_SPRITES));
    gfx_scb_run((u16)(ADDR_SCB4 + FIRST), 1, g_s4, (u8)(2 * g_cols + TOWER_SPRITES));
}
