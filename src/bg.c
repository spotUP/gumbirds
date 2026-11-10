/*
 * Parallax background, hardware glue. BG_PLANE_COUNT planes (sky, far, mid A, mid B, near), each CITY_TABLE_PLANE_COLS
 * columns of 16 px, drawn in slot order so the sky is behind and the near plane in front. Every column is its own
 * sprite (not a sticky chain) with its own top and height, cut to the tile rows that hold art: the LSPC counts a sprite
 * on every line of its height, so empty rows above a low building would cost a slot for nothing. The row range comes
 * from the generated table CITY_TABLE_COL_ROW0 / COL_ROWS (tools/import_bg_sheet.py), the same table the sprite budget
 * model sums (src/core/sprite_budget.c). Tiles, palettes (one per tile, up to three per plane), heights and tops are
 * written once in bg_init. When a plane's x changes, its columns' SCB4 words go out as one strided run
 * (gfx_scb_run), so a camera step is one op per moving plane (four: the sky never moves), a still camera sends none.
 * The plane sizes, tops and factors come from assets/city/city_sheet.json through tools/import_bg_sheet.py.
 */
#include <ngdevkit/neogeo.h>
#include <ngdevkit/ng-video.h>
#include "bg.h"
#include "gfx.h"
#include "core/arena.h"
#include "core/bg_scroll.h"
#include "sprite_slots.h"
#include "vram_layout.h"

volatile s16 g_bg_plane_x[BG_PLANE_COUNT];
volatile u32 g_bg_x_writes;
/* First palette RAM entry of the city palettes; read by tests/mame/unibios_check.lua through nm. */
const u16 g_bg_pal_first_entry = CITY_PAL_SLOT * 16;

/* Palette word (DRGB, dark bit 0) from 5 bit channels, same layout as tools/sprite_pipeline.py rgb_to_ng. */
#define NG_RGB5(r, g, b) ((u16)((((r) & 1) << 14) | (((g) & 1) << 13) | (((b) & 1) << 12) | (((r) >> 1) << 8) | (((g) >> 1) << 4) | ((b) >> 1)))
#define BG_BACKDROP NG_RGB5(3, 2, 7)       /* #1a1238, "backdrop" in assets/city/city_sheet.json */

static const u8 PLANE_ANIM[BG_PLANE_COUNT] = { CITY_ANIM_SKY, CITY_ANIM_FAR, CITY_ANIM_MIDA, CITY_ANIM_MIDB, CITY_ANIM_NEAR };
static const u8 PLANE_FIRST[BG_PLANE_COUNT] = { BG_SKY_SPRITE, BG_FAR_SPRITE, BG_MIDA_SPRITE, BG_MIDB_SPRITE, BG_NEAR_SPRITE };
static const u8 PLANE_K[BG_PLANE_COUNT] = CITY_TABLE_PLANE_K;
static const u8 PLANE_TOP[BG_PLANE_COUNT] = CITY_TABLE_PLANE_TOP;
static const u8 PLANE_COLS[BG_PLANE_COUNT] = CITY_TABLE_PLANE_COLS;
static const u8 COL_ROW0[BG_SPRITE_END] = CITY_TABLE_COL_ROW0;
static const u8 COL_ROWS[BG_SPRITE_END] = CITY_TABLE_COL_ROWS;

#define BG_MAX_COLS CITY_NEAR_COLS /* widest plane: the near plane (checked below) */
_Static_assert(CITY_SKY_COLS <= BG_MAX_COLS && CITY_FAR_COLS <= BG_MAX_COLS && CITY_MIDA_COLS <= BG_MAX_COLS &&
               CITY_MIDB_COLS <= BG_MAX_COLS, "BG_MAX_COLS holds every plane");

/* The sprite slot map (src/sprite_slots.h, also read by the sprite budget) matches the sheet: width, top and bottom line of
 * every plane, consecutive slots in plane order, ending at BG_SPRITE_END below the object pool. */
#define CHECK_PLANE(N, n) \
    _Static_assert(BG_##N##_COUNT == CITY_##N##_COLS && BG_##N##_Y0 == CITY_##N##_TOP && BG_##N##_Y1 == CITY_##N##_BOTTOM, \
                   "src/sprite_slots.h " #n " plane differs from assets/city/city_sheet.json")
CHECK_PLANE(SKY, sky);
CHECK_PLANE(FAR, far);
CHECK_PLANE(MIDA, mid A);
CHECK_PLANE(MIDB, mid B);
CHECK_PLANE(NEAR, near);
_Static_assert(BG_SKY_SPRITE == 0, "the sky is the first sprite");
_Static_assert(BG_SKY_SPRITE + BG_SKY_COUNT == BG_FAR_SPRITE, "sky/far sprite ranges");
_Static_assert(BG_FAR_SPRITE + BG_FAR_COUNT == BG_MIDA_SPRITE, "far/mid A sprite ranges");
_Static_assert(BG_MIDA_SPRITE + BG_MIDA_COUNT == BG_MIDB_SPRITE, "mid A/mid B sprite ranges");
_Static_assert(BG_MIDB_SPRITE + BG_MIDB_COUNT == BG_NEAR_SPRITE, "mid B/near sprite ranges");
_Static_assert(BG_NEAR_SPRITE + BG_NEAR_COUNT == BG_SPRITE_END, "near sprite range end");
_Static_assert(BG_SPRITE_END <= POOL_SPRITE_BASE, "background sprites overlap the object pool");
_Static_assert(CITY_CAM_MAX == ARENA_CAM_MAX, "the importer camera range (tools/import_bg_sheet.py) matches the arena");
_Static_assert(CITY_ANIM_COUNT == BG_PLANE_COUNT, "one animation per plane");

/* {tile, attribute} of every entry of city_tile_index, built once: the attribute carries the tile's own palette. */
static u16 g_pairs[sizeof city_tile_index / sizeof city_tile_index[0]][2];

void bg_load_palettes(void) {
    for (int p = 0; p < CITY_PALETTE_COUNT; p++)
        for (int i = 0; i < 16; i++)
            gfx_pal((CITY_PAL_SLOT + p) * 16 + i, city_palettes[p][i]);
    /* The backdrop is the LAST palette RAM entry, not entry 0 (verified by snapshot, plan B2). */
    gfx_pal(4095, BG_BACKDROP);
}

void bg_init(void) {
    for (u16 i = 0; i < sizeof city_tile_index / sizeof city_tile_index[0]; i++) {
        g_pairs[i][0] = city_tile_index[i];
        g_pairs[i][1] = (u16)((CITY_PAL_SLOT + city_tile_pal[i]) << 8);
    }
    for (u8 p = 0; p < BG_PLANE_COUNT; p++) {
        const CityFrame *f = &city_frames[city_anims[PLANE_ANIM[p]].first_frame];
        u8 first = PLANE_FIRST[p], rows = (u8)f->tiles_h;
        for (u8 c = 0; c < f->tiles_w; c++) {
            u8 slot = (u8)(first + c), n = COL_ROWS[slot];
            gfx_word((u16)(ADDR_SCB2 + slot), 0xFFF);
            if (!n) { gfx_word((u16)(ADDR_SCB3 + slot), 0); continue; } /* nothing to draw: height 0 hides the sprite */
            gfx_strip_attr(slot, g_pairs[f->tile_offset + c * rows + COL_ROW0[slot]], CITY_TILE_BASE, n);
            gfx_word((u16)(ADDR_SCB3 + slot), gfx_scb3_word(n, (u16)(PLANE_TOP[p] + 16 * COL_ROW0[slot])));
        }
        g_bg_plane_x[p] = 0x7FFF; /* no x written yet: the next bg_update sends all planes */
    }
}

void bg_update(u8 cam_px) {
    u16 words[BG_MAX_COLS];
    for (u8 p = 0; p < BG_PLANE_COUNT; p++) {
        int x = bg_plane_x(cam_px, PLANE_K[p]);
        if (x == g_bg_plane_x[p]) continue;
        for (u8 c = 0; c < PLANE_COLS[p]; c++) words[c] = gfx_scb4_word(x + c * BG_COL_PX);
        gfx_scb_run((u16)(ADDR_SCB4 + PLANE_FIRST[p]), 1, words, PLANE_COLS[p]);
        g_bg_plane_x[p] = (s16)x;
        g_bg_x_writes++;
    }
}
