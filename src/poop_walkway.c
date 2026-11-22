#include "poop_walkway.h"
#include "gfx.h"
#include "island.h"
#include "sprite_slots.h"
#include "vram_layout.h"
#include "core/game.h"

#define COLS PWALK_STRIP_COLUMNS
#define BAND_ROWS 4        /* 64 px */
#define LOADS_PER_FRAME 4  /* tile strips queued per frame: bounds the burst at entry (same bound as fling_field.c) */
#define SHADOW_DX 8        /* shadow cell is 16 wide: centre it on the walker */
#define SHADOW_DY 14       /* cell top = feet - 14: the dither rows start 13 px into the 16 px cell, one above the feet row */
#define STRIP_ATTR (PWALK_PAL_SLOT << 8)
_Static_assert(PWALK_STRIP_COLUMNS * 16 == PM_W, "the band covers the 320 px screen");
_Static_assert(PWALK_STRIP_SPRITE + PWALK_STRIP_COUNT + PWALK_SHADOW_COUNT <= ISLAND_SPRITE + ISLAND_COUNT, "walkway overruns the island slots");
_Static_assert(PWALK_SHADOW_COUNT == PM_WALKERS, "one shadow per walker slot");
_Static_assert(PM_BAND_Y + 64 == 224 && PM_LANE_FEET_FRONT <= 224, "walkers stand inside the band");

static u8 g_on, g_vis, g_ready, g_mood, g_loaded;
static u16 g_t3[COLS], g_t4[COLS], g_s3[PWALK_SHADOW_COUNT], g_s4[PWALK_SHADOW_COUNT];

static const u16 *tiles_of(u16 frame) { return &pwalk_tile_index[pwalk_frames[frame].tile_offset]; }

static void load_palette(u8 mood) {
    const u16 *pal = mood == GAME_MOOD_MOON ? pwalk_palettes[0] : mood == GAME_MOOD_STORM ? pwalk_extra_palettes[PWALK_EXTRA_PAL_STORM] : pwalk_extra_palettes[PWALK_EXTRA_PAL_DUSK];
    for (u8 i = 0; i < 16; i++) gfx_pal((u16)(PWALK_PAL_SLOT * 16 + i), pal[i]);
}

static void hide_all(void) {
    for (u8 i = 0; i < COLS; i++) g_t3[i] = 0;
    for (u8 i = 0; i < PWALK_SHADOW_COUNT; i++) g_s3[i] = 0;
    gfx_scb_run((u16)(ADDR_SCB3 + PWALK_STRIP_SPRITE), 1, g_t3, COLS);
    gfx_scb_run((u16)(ADDR_SCB3 + PWALK_SHADOW_SPRITE), 1, g_s3, PWALK_SHADOW_COUNT);
}

u8 poop_walkway_loaded(void) { return g_ready; }

void poop_walkway_step(const GgPoop *p, u8 mood, int on, int show) {
    u8 loads = LOADS_PER_FRAME;
    if (!p || !on) {
        if (g_on) { hide_all(); g_on = g_vis = g_ready = 0; island_relayout(); }
        return;
    }
    if (!g_on) {
        g_on = 1; g_vis = 0; g_mood = 0xFF; g_loaded = 0;
        gfx_sprite_unchained(PWALK_STRIP_SPRITE, COLS);
        gfx_sprite_unchained(PWALK_SHADOW_SPRITE, PWALK_SHADOW_COUNT);
        hide_all();
        for (u8 i = 0; i < COLS; i++) { g_t3[i] = gfx_scb3_word(BAND_ROWS, PM_BAND_Y); g_t4[i] = gfx_scb4_word(16 * i); }
    }
    if (mood != g_mood) { load_palette(mood); g_mood = mood; }
    while (loads && g_loaded < COLS + PWALK_SHADOW_COUNT) {
        if (g_loaded < COLS) gfx_strip((u16)(PWALK_STRIP_SPRITE + g_loaded), tiles_of((u16)(PWALK_STRIP_FIRST + g_loaded)), PWALK_TILE_BASE, BAND_ROWS, STRIP_ATTR);
        else gfx_strip((u16)(PWALK_SHADOW_SPRITE + g_loaded - COLS), tiles_of(PWALK_SHADOW_FRAME), PWALK_TILE_BASE, 1, STRIP_ATTR);
        g_loaded++; loads--;
    }
    g_ready = g_loaded >= COLS + PWALK_SHADOW_COUNT;
    for (u8 k = 0; k < PWALK_SHADOW_COUNT; k++) {
        const PmWalker *w = &p->w[k];
        int x = (w->x8 >> 3) - SHADOW_DX;
        g_s3[k] = w->live && x > -16 && x < 320 ? gfx_scb3_word(1, pm_lane_feet(w->lane) - SHADOW_DY) : 0;
        g_s4[k] = gfx_scb4_word(x);
    }
    if (show && g_ready) g_vis = 1;
    if (!show) { if (g_vis) hide_all(); g_vis = 0; }
    if (g_vis) {
        for (u8 i = 0; i < COLS; i++) g_t3[i] = gfx_scb3_word(BAND_ROWS, PM_BAND_Y);
        gfx_scb_run((u16)(ADDR_SCB3 + PWALK_STRIP_SPRITE), 1, g_t3, COLS);
        gfx_scb_run((u16)(ADDR_SCB4 + PWALK_STRIP_SPRITE), 1, g_t4, COLS);
        gfx_scb_run((u16)(ADDR_SCB3 + PWALK_SHADOW_SPRITE), 1, g_s3, PWALK_SHADOW_COUNT);
        gfx_scb_run((u16)(ADDR_SCB4 + PWALK_SHADOW_SPRITE), 1, g_s4, PWALK_SHADOW_COUNT);
    }
}
