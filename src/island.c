#include "island.h"
#include "gfx.h"
#include "sprite_slots.h"
#include "vram_layout.h"
#include "core/camera.h"
#include "core/island_layout.h"
#include "core/stage.h"
#include "gen/island_tables.h"

_Static_assert(ISLAND_SPRITE + ISLAND_COUNT <= POOL_SPRITE_BASE, "island sprites overlap the object pool");
_Static_assert(BG_SPRITE_END <= ISLAND_SPRITE, "island sprites overlap the background planes");
_Static_assert(ISLAND_PIECE_W == 16, "islands are drawn one 16 px sprite per column");

volatile u16 g_island_draws;
static u8 g_shown, g_loaded;
static u16 g_tiles[ISLAND_COUNT]; /* tile of each column, relative to ISLAND_TILE_BASE; the queue dedupes by this pointer */

/* First sprite of island i: the columns of the islands before it. */
static u16 first_sprite(int i) {
    u16 s = ISLAND_SPRITE;
    for (int k = 0; k < i; k++) s = (u16)(s + island_columns(stage_platforms[k].w));
    return s;
}

/* Tiles and chain words go to VRAM once, on the first call (attract): a 41 column burst on the first PLAYING frame made the
   first camera scroll write late (tests/mame/scroll_check.lua). The head height stays 0, so nothing shows until place(). */
static void load(void) {
    for (int i = 0; i < STAGE_PLATFORM_COUNT; i++) {
        u16 first = first_sprite(i);
        int cols = island_columns(stage_platforms[i].w);
        for (int c = 0; c < cols; c++) {
            int anim = island_piece_anim(stage_platforms[i].w, c);
            const IslandFrame *f = &island_frames[island_anims[anim].first_frame];
            /* a swapping piece starts its run of 8 consecutive tiles at its first frame (the 8-aligned tile) */
            u16 attr = (u16)((ISLAND_PAL_SLOT + f->palette) << 8);
            if (island_anim_swaps(anim)) attr |= 0x08; /* bit 3: 8-frame auto-animation, as hazard.c */
            g_tiles[first - ISLAND_SPRITE + c] = island_tile_index[f->tile_offset];
            gfx_sprite_strips((u16)(first + c), 1, 1, &g_tiles[first - ISLAND_SPRITE + c], ISLAND_TILE_BASE, attr);
        }
        gfx_sprite_chain(first, (u8)cols); /* the chain words never change: sent once here, not per frame (frame logic budget) */
    }
}

static void hide(void) {
    for (int i = 0; i < STAGE_PLATFORM_COUNT; i++)
        gfx_word((u16)(ADDR_SCB3 + first_sprite(i)), 0); /* height 0 hides the head and the sticky columns after it */
}

/* The top of an island sprite is the stage y minus the line row of the art (ISLAND_LINE_ROW): the drawn line is the floor. */
static void place(int cam_px) {
    for (int i = 0; i < STAGE_PLATFORM_COUNT; i++) {
        const StagePlatform *p = &stage_platforms[i];
        u16 first = first_sprite(i);
        gfx_word((u16)(ADDR_SCB3 + first), gfx_scb3_word(1, p->y - ISLAND_LINE_ROW));
        gfx_word((u16)(ADDR_SCB4 + first), gfx_scb4_word(camera_screen_x(p->x, cam_px, p->w)));
    }
}

void island_autoanim_baseline(void) { gfx_autoanim_speed(ISLAND_STEP_FRAMES); }

void island_step(u8 playing, int cam_px) {
    if (!g_loaded) { load(); island_autoanim_baseline(); g_loaded = 1; }
    if (playing) {
        place(cam_px);
        g_island_draws++;
    } else if (g_shown) {
        hide();
    }
    g_shown = playing;
}
