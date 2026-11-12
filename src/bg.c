/*
 * Parallax background, hardware glue. BG_PLANE_COUNT planes (sky, far, mid A, mid B, near), each CITY_TABLE_PLANE_COLS
 * columns of 16 px, drawn in slot order so the sky is behind and the near plane in front. Every column is its own
 * sprite (not a sticky chain) with its own top and height, cut to the tile rows that hold art: the LSPC counts a sprite
 * on every line of its height, so empty rows above a low building would cost a slot for nothing. The row range comes
 * from the generated table CITY_TABLE_COL_ROW0 / COL_ROWS (tools/import_bg_sheet.py), the same table the sprite budget
 * model sums (src/core/sprite_budget.c). Tiles, palettes (one per tile, up to three per plane), heights and tops are
 * written once in bg_init. When a plane's x changes, its columns' SCB4 words go out as one generated ramp op
 * (bg_ramp + gfx_scb_ramp, VQ_RAMP): the frame logic does O(1) work per moving plane and the vblank flush generates the
 * words. A camera step is one op per moving plane (four: the sky never moves), a still camera sends none.
 * The plane sizes, tops and factors come from assets/city/city_sheet.json through tools/import_bg_sheet.py.
 */
#include <ngdevkit/neogeo.h>
#include <ngdevkit/ng-video.h>
#include "bg.h"
#include "gfx.h"
#include "core/bg_scroll.h"
#include "sprite_slots.h"
#include "vram_layout.h"

volatile s16 g_bg_plane_x[BG_PLANE_COUNT];
volatile u32 g_bg_x_writes;
/* Camera x of the last bg_update that went through, or no value yet (bg_init): a call with the same camera returns at once, so a still
 * frame costs a compare, not four divides. */
static s32 g_last_u;
static u8 g_last_valid;
/* First palette RAM entry of the city palettes; read by tests/mame/unibios_check.lua through nm. */
const u16 g_bg_pal_first_entry = CITY_PAL_SLOT * 16;

/* Palette word (DRGB, dark bit 0) from 5 bit channels, same layout as tools/sprite_pipeline.py rgb_to_ng. */
#define NG_RGB5(r, g, b) ((u16)((((r) & 1) << 14) | (((g) & 1) << 13) | (((b) & 1) << 12) | (((r) >> 1) << 8) | (((g) >> 1) << 4) | ((b) >> 1)))
#define BG_BACKDROP NG_RGB5(3, 2, 7)       /* #1a1238, "backdrop" in assets/city/city_sheet.json */
#define BG_TRIP_BACKDROP NG_RGB5(14, 10, 20) /* Gum Trip only: the sky plane colour (115,82,165) = snap5 of the sky pixels (tools/import_bg_sheet.py) */

static const u8 PLANE_ANIM[BG_PLANE_COUNT] = { CITY_ANIM_SKY, CITY_ANIM_FAR, CITY_ANIM_MIDA, CITY_ANIM_MIDB, CITY_ANIM_NEAR };
static const u8 PLANE_FIRST[BG_PLANE_COUNT] = { BG_SKY_SPRITE, BG_FAR_SPRITE, BG_MIDA_SPRITE, BG_MIDB_SPRITE, BG_NEAR_SPRITE };
static const u8 PLANE_K[BG_PLANE_COUNT] = CITY_TABLE_PLANE_K;
static const u8 PLANE_TOP[BG_PLANE_COUNT] = CITY_TABLE_PLANE_TOP;
static const u8 PLANE_COLS[BG_PLANE_COUNT] = CITY_TABLE_PLANE_COLS;
static const u8 COL_ROW0[BG_SPRITE_TOTAL] = CITY_TABLE_COL_ROW0;
static const u8 COL_ROWS[BG_SPRITE_TOTAL] = CITY_TABLE_COL_ROWS;

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
_Static_assert(BG_SKY_SPRITE == SPRITE_RESERVED + 1, "the sky follows the reserved sprite 0");
_Static_assert(BG_SKY_SPRITE + BG_SKY_COUNT == BG_FAR_SPRITE, "sky/far sprite ranges");
_Static_assert(BG_FAR_SPRITE + BG_FAR_COUNT == BG_MIDA_SPRITE, "far/mid A sprite ranges");
_Static_assert(BG_MIDA_SPRITE + BG_MIDA_COUNT == BG_MIDB_SPRITE, "mid A/mid B sprite ranges");
_Static_assert(BG_MIDB_SPRITE + BG_MIDB_COUNT == BG_NEAR_SPRITE, "mid B/near sprite ranges");
_Static_assert(BG_NEAR_SPRITE + BG_NEAR_COUNT == BG_SPRITE_END, "near sprite range end");
_Static_assert(BG_SPRITE_END <= POOL_SPRITE_BASE, "background sprites overlap the object pool");
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
            u8 slot = (u8)(first + c), n = COL_ROWS[slot - BG_SKY_SPRITE];
            gfx_word((u16)(ADDR_SCB2 + slot), 0xFFF);
            if (!n) { gfx_word((u16)(ADDR_SCB3 + slot), 0); continue; } /* nothing to draw: height 0 hides the sprite */
            gfx_strip_attr(slot, g_pairs[f->tile_offset + c * rows + COL_ROW0[slot - BG_SKY_SPRITE]], CITY_TILE_BASE, n);
            gfx_word((u16)(ADDR_SCB3 + slot), gfx_scb3_word(n, (u16)(PLANE_TOP[p] + 16 * COL_ROW0[slot - BG_SKY_SPRITE])));
        }
        g_bg_plane_x[p] = 0x7FFF; /* no x written yet: the next bg_update sends all planes */
        g_last_valid = 0;
    }
}

/* Gum Trip drops the planes in BG_TRIP_HIDDEN_MASK (far, near): hide = SCB3 height 0 for each of their columns, show = bg_init's word.
 * Trip also swaps the backdrop (palette RAM entry 4095) to the sky colour, so the tiles the importer blanked (sky behind far, mid B behind
 * near) show sky instead of dark. Written on a change only, so a hidden plane costs no per-line sprites and no VRAM writes per frame. */
void bg_trip_planes(u8 trip) {
    static u8 hidden = 0;
    u8 want = trip ? BG_TRIP_HIDDEN_MASK : 0, diff = (u8)(want ^ hidden);
    if (!diff) return;
    hidden = want;
    gfx_pal(4095, trip ? BG_TRIP_BACKDROP : BG_BACKDROP);
    for (u8 p = 0; p < BG_PLANE_COUNT; p++) {
        const CityFrame *f;
        if (!(diff & (1u << p))) continue;
        f = &city_frames[city_anims[PLANE_ANIM[p]].first_frame];
        for (u8 c = 0; c < f->tiles_w; c++) {
            u8 slot = (u8)(PLANE_FIRST[p] + c), n = COL_ROWS[slot - BG_SKY_SPRITE];
            if (!n) continue;
            gfx_word((u16)(ADDR_SCB3 + slot), (want & (1u << p)) ? 0 : gfx_scb3_word(n, (u16)(PLANE_TOP[p] + 16 * COL_ROW0[slot - BG_SKY_SPRITE])));
        }
    }
}

/* unwrapped_px = camera_unwrapped_px: plane offset = floor(px * k / 16) mod plane width (src/core/bg_scroll.c, one 16 bit divide per
 * plane, no libgcc call). The SCB4 words of a plane go out only when its offset changed. */
void bg_update(s32 unwrapped_px) {
    BgRamp ramp;
    if (g_last_valid && unwrapped_px == g_last_u) return;
    g_last_u = unwrapped_px;
    g_last_valid = 1;
    for (u8 p = 0; p < BG_PLANE_COUNT; p++) {
        u16 width = (u16)(PLANE_COLS[p] * BG_COL_PX);
        u32 off = bg_loop_offset((u32)unwrapped_px, PLANE_K[p], width);
        if (-(int)off == g_bg_plane_x[p]) continue;
        bg_ramp(off, width, &ramp);
        gfx_scb_ramp((u16)(ADDR_SCB4 + PLANE_FIRST[p]), PLANE_COLS[p], ramp.split, ramp.v1, ramp.v2);
        g_bg_plane_x[p] = (s16)-(int)off;
        g_bg_x_writes++;
    }
}
