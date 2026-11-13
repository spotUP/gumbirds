#include "gum.h"
#include "gfx.h"
#include "sprite_slots.h"
#include "vram_layout.h"
#include "core/gum_view.h"
#include "gen/sootling_sprites.h"

_Static_assert(GUM_COUNT >= GUM_MAX_COLUMNS, "gum sprite slots are fewer than the widest gum frame");
_Static_assert(GUM_VIEW_BIRD_FRAMES * SOOTLING_ANIM_COUNT == SOOTLING_FRAME_COUNT, "gum_view offset table differs from the player animation (both Sootling animations are the same length)");
_Static_assert(GUM_SHEET_WOBBLE_FRAMES == GUM_VIEW_WOBBLE_SHEET, "wobble frame count differs from the sheet");
_Static_assert(GUM_SHEET_POP_FRAMES == GUM_VIEW_POP_SHEET, "pop frame count differs from the sheet");
_Static_assert(GUM_ANIM_POP_LARGE == 16 && GUM_ANIM_POP_SMALL == 17 && GUM_ANIM_LEVEL16 == 0, "gum sheet order: level16..level1, pop_large, pop_small");

volatile u16 g_gum_draws;
volatile u16 g_gum_loads;
static u8 g_last_level;   /* level of the previous frame */
static int g_pop_t = -1;  /* frames since the pop started, -1 = none */
static u8 g_pop_anim;
static int g_key = -1;    /* anim << 8 | frame loaded into the slots, -1 = none (hidden) */

void gum_load_palettes(void) {
    for (u8 i = 0; i < 16; i++) gfx_pal((u16)(GUM_PAL_SLOT * 16 + i), gum_palettes[0][i]);
}

static void hide(void) {
    for (int c = 0; c < GUM_COUNT; c++) gfx_word((u16)(ADDR_SCB3 + GUM_SPRITE + c), 0);
    g_key = -1;
}

void gum_step(int active, uint16_t gum, uint32_t frame, int drawn, uint8_t bird_frame, int flip, int cx, int top) {
    uint8_t level = active ? gum_view_level(gum) : 0;
    if (!active) { g_pop_t = -1; g_last_level = 0; hide(); return; }
    if (level > 0) g_pop_t = -1;
    else if (g_last_level > 0) { g_pop_t = 0; g_pop_anim = gum_view_anim(g_last_level, GUM_STATE_POP); }
    else if (g_pop_t >= 0 && gum_view_pop_done((uint32_t)++g_pop_t)) g_pop_t = -1;
    g_last_level = level;
    uint8_t anim, sheet;
    if (g_pop_t >= 0) { anim = g_pop_anim; sheet = gum_view_frame(GUM_STATE_POP, (uint32_t)g_pop_t); }
    else if (level > 0) { anim = gum_view_anim(level, GUM_STATE_WOBBLE); sheet = gum_view_frame(GUM_STATE_WOBBLE, frame); }
    else { hide(); return; }
    GumOffset o = gum_view_offset(bird_frame, flip);
    if (!drawn || !o.show) { hide(); return; }
    const GumFrame *f = &gum_frames[gum_anims[anim].first_frame + sheet];
    int key = (anim << 8) | sheet;
    if (key != g_key) {
        gfx_sprite_strips(GUM_SPRITE, f->tiles_w, f->tiles_h, &gum_tile_index[f->tile_offset], GUM_TILE_BASE, (u16)((GUM_PAL_SLOT + f->palette) << 8));
        if (f->tiles_w < GUM_COUNT) gfx_word((u16)(ADDR_SCB3 + GUM_SPRITE + f->tiles_w), 0); /* ends the chain: no stale second column */
        g_key = key; g_gum_loads++;
    }
    /* The bubble hangs on the bird's string: o.dy puts its bottom edge on the string top, o.dx its string column on the bird's. */
    gfx_sprite_place(GUM_SPRITE, f->tiles_w, f->tiles_h, cx - f->tiles_w * 8 + o.dx, top - f->tiles_h * 16 + o.dy);
    g_gum_draws++;
}
