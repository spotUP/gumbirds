#include "splash.h"
#include "gfx.h"
#include "core/camera.h"
#include "sprite_slots.h"
#include "vram_layout.h"
#include "core/splash_view.h"
#include "gen/splash_sprites.h"

_Static_assert(SPLASH_COUNT >= SPLASH_MAX_COLUMNS, "splash sprite slots are fewer than the widest splash frame");
_Static_assert(SPLASH_FRAME_COUNT == 2 * SPLASH_FRAMES && SPLASH_ANIM_COUNT == 2, "splash sheet: water and lava, SPLASH_FRAMES frames each");
_Static_assert(SPLASH_ANIM_WATER == 0 && SPLASH_ANIM_LAVA == 1, "splash sheet order: water, lava");

volatile u16 g_splash_draws;
static Splash g_splash;
static int g_key = -1;  /* anim << 8 | frame loaded into the slots, -1 = none (hidden) */

void splash_load_palettes(void) {
    for (u8 p = 0; p < SPLASH_PALETTE_COUNT; p++)
        for (u8 i = 0; i < 16; i++) gfx_pal((u16)((SPLASH_PAL_SLOT + p) * 16 + i), splash_palettes[p][i]);
}

static void hide(void) {
    for (int c = 0; c < SPLASH_COUNT; c++) gfx_word((u16)(ADDR_SCB3 + SPLASH_SPRITE + c), 0);
    g_key = -1;
}

void splash_update(int active, int start, uint8_t kind, int32_t x, int cam_px) {
    if (!active) { g_splash.active = 0; hide(); return; }
    splash_step(&g_splash, start, kind, x);
    if (!g_splash.active) { if (g_key >= 0) hide(); return; }
    int sx = camera_screen_x((int)g_splash.x - SPLASH_ANCHOR_X, cam_px, 48);
    if (!camera_visible(sx, 48)) { hide(); return; }
    u8 anim = g_splash.kind == HZ_LAVA ? SPLASH_ANIM_LAVA : SPLASH_ANIM_WATER;
    u8 sheet = splash_frame(&g_splash);
    const SplashFrame *f = &splash_frames[splash_anims[anim].first_frame + sheet];
    int key = (anim << 8) | sheet;
    if (key != g_key) {
        gfx_sprite_strips(SPLASH_SPRITE, f->tiles_w, f->tiles_h, &splash_tile_index[f->tile_offset], SPLASH_TILE_BASE, (u16)((SPLASH_PAL_SLOT + f->palette) << 8));
        g_key = key;
    }
    gfx_sprite_place(SPLASH_SPRITE, f->tiles_w, f->tiles_h, sx, splash_top(g_splash.kind));
    g_splash_draws++;
}
