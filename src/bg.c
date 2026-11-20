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
 * Moods (GAME_MOOD_*, BG_MOOD_COUNT in all): moon (city_*), dusk (dusk_*) and storm (storm_*) share the plane layout (same
 * columns, rows and tops: checked below and in tests/host/test_bg.c) and differ in tiles, palettes and backdrop. All palette
 * sets stay loaded (CITY_PAL_SLOT, DUSK_PAL_SLOT, STORM_PAL_SLOT), so a mood change sends no palette words but the backdrop: bg_set_mood hides every column (one SCB3 run),
 * bg_update rewrites BG_MOOD_COLS_PER_FRAME strips per frame, then shows the columns again (one run).
 */
#include <ngdevkit/neogeo.h>
#include <ngdevkit/ng-video.h>
#include <string.h>
#include "bg.h"
#include "gfx.h"
#include "core/bg_scroll.h"
#include "sprite_slots.h"
#include "vram_layout.h"
#include "gen/city_tables.h"
#include "gen/dusk_tables.h"
#include "gen/storm_tables.h"
#include "core/game.h"
#include "core/rain.h"

volatile s16 g_bg_plane_x[BG_PLANE_COUNT];
volatile u32 g_bg_x_writes;
/* Camera x of the last bg_update that went through, or no value yet (bg_init): a call with the same camera returns at once, so a still
 * frame costs a compare, not four divides. */
static s32 g_last_u;
static u8 g_last_valid;
/* First palette RAM entry of the city palettes; read by tests/mame/unibios_check.lua through nm. */
const u16 g_bg_pal_first_entry = CITY_PAL_SLOT * 16;
/* First palette RAM entry of the dusk palettes; read by tests/mame/mood_check.lua through nm. */
const u16 g_bg_dusk_pal_first_entry = DUSK_PAL_SLOT * 16;
const u16 g_bg_storm_pal_first_entry = STORM_PAL_SLOT * 16; /* the same for the storm palettes */
volatile u8 g_bg_mood;
volatile u8 g_bg_mood_busy;
volatile u16 g_bg_mood_changes;

/* Palette word (DRGB, dark bit 0) from 5 bit channels, same layout as tools/sprite_pipeline.py rgb_to_ng. */
#define NG_RGB5(r, g, b) ((u16)((((r) & 1) << 14) | (((g) & 1) << 13) | (((b) & 1) << 12) | (((r) >> 1) << 8) | (((g) >> 1) << 4) | ((b) >> 1)))
/* Per mood: the backdrop ("backdrop" in the sheet json) and the Gum Trip backdrop (the sky plane colour), from tools/import_bg_sheet.py MOODS. */
static const u16 BACKDROP[BG_MOOD_COUNT] = { NG_RGB5(CITY_BACKDROP_R5, CITY_BACKDROP_G5, CITY_BACKDROP_B5),
                                            NG_RGB5(DUSK_BACKDROP_R5, DUSK_BACKDROP_G5, DUSK_BACKDROP_B5),
                                            NG_RGB5(STORM_BACKDROP_R5, STORM_BACKDROP_G5, STORM_BACKDROP_B5) };
static const u16 TRIP_BACKDROP[BG_MOOD_COUNT] = { NG_RGB5(CITY_TRIP_R5, CITY_TRIP_G5, CITY_TRIP_B5),
                                                 NG_RGB5(DUSK_TRIP_R5, DUSK_TRIP_G5, DUSK_TRIP_B5),
                                                 NG_RGB5(STORM_TRIP_R5, STORM_TRIP_G5, STORM_TRIP_B5) };
_Static_assert(BG_MOOD_COUNT == 3 && GAME_MOOD_STORM == 2, "one tile set per built mood: moon, dusk, storm");
_Static_assert(sizeof dusk_tile_index == sizeof city_tile_index, "dusk planes cut like the moon planes");
_Static_assert(sizeof storm_tile_index == sizeof city_tile_index, "storm planes cut like the moon planes");
_Static_assert(DUSK_ANIM_SKY == CITY_ANIM_SKY && DUSK_ANIM_FAR == CITY_ANIM_FAR && DUSK_ANIM_MIDA == CITY_ANIM_MIDA &&
               DUSK_ANIM_MIDB == CITY_ANIM_MIDB && DUSK_ANIM_NEAR == CITY_ANIM_NEAR, "same plane order in every mood");
_Static_assert(STORM_ANIM_SKY == CITY_ANIM_SKY && STORM_ANIM_FAR == CITY_ANIM_FAR && STORM_ANIM_MIDA == CITY_ANIM_MIDA &&
               STORM_ANIM_MIDB == CITY_ANIM_MIDB && STORM_ANIM_NEAR == CITY_ANIM_NEAR, "same plane order in every mood");

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
                   "src/sprite_slots.h " #n " plane differs from assets/city/city_sheet.json"); \
    _Static_assert(DUSK_##N##_COLS == CITY_##N##_COLS && DUSK_##N##_TOP == CITY_##N##_TOP && DUSK_##N##_BOTTOM == CITY_##N##_BOTTOM, \
                   #n " plane: dusk differs from the moon"); \
    _Static_assert(STORM_##N##_COLS == CITY_##N##_COLS && STORM_##N##_TOP == CITY_##N##_TOP && STORM_##N##_BOTTOM == CITY_##N##_BOTTOM, \
                   #n " plane: storm differs from the moon")
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

#define BG_TILE_REFS (sizeof city_tile_index / sizeof city_tile_index[0])
/* {tile, attribute} of every tile_index entry per mood, built once: the attribute carries the tile's own palette. The queue
 * reads the pairs at flush time, so they stay here for good. */
static u16 g_pairs[BG_MOOD_COUNT][BG_TILE_REFS][2];
static const u16 TILE_BASE[BG_MOOD_COUNT] = { CITY_TILE_BASE, DUSK_TILE_BASE, STORM_TILE_BASE };
/* Mood change: g_want is the mood asked for, g_step the next column to rewrite while g_bg_mood_busy. */
static u8 g_want, g_step;
static u8 g_hidden; /* planes bg_trip_planes hides (BG_TRIP_HIDDEN_MASK bits) */
static u8 g_stadium; /* 1: the stadium owns sprite slots 21..110, planes far..near stay hidden (sky stays) */
#define STADIUM_HIDDEN_MASK 0x1E /* plane bits 1..4 */
/* Pop Drop sky (bg_pop_sky): the sky and cloud sprites take slots 1..POP_SLOTS_END over, so planes far..near stay hidden while it is on or being undone. */
enum { POP_OFF, POP_ON, POP_RESTORE };
static u8 g_pop, g_pop_drawn;
static u8 hidden_mask(void) { return (u8)(g_hidden | ((g_stadium || g_pop) ? STADIUM_HIDDEN_MASK : 0)); }
static u16 g_scb3_show[BG_SPRITE_TOTAL], g_scb3_out[BG_SPRITE_TOTAL];
static const u16 g_scb3_zero[BG_SPRITE_TOTAL];
/* Strips per frame while the mood changes: at most 9 x 7 rows of tile pairs. The show run (every column's SCB3 word, about 31
 * lines) gets a frame of its own after the last strips; 9 per frame keeps it on the same frame as 8 with the show folded in. */
#define BG_MOOD_COLS_PER_FRAME 9

/* Mood change fade (src/core/bg_scroll.c BgFade): the mood on screen dims to black, the tiles swap in the dark, the new mood brightens.
 * g_pal_lvl is the level each resident palette was last written at; fade_sync rewrites at most BG_FADE_PALS_PER_FRAME palettes (2 x 16
 * words, plus the backdrop: under the 112 word flush limit) whose level differs from the wanted one. The mood whose palettes are the
 * visible ones (fade_vis) follows the fade level, every other set stays whole, so a set left dark by the fade is restored in the dark. */
#define BG_FADE_PALS_PER_FRAME 2
/* A palette here costs about 35 raster lines (16 faded words, MAME: 2 took 69 lines on the stage 9 world change frame, which also
 * ran the stage start; logic then ended past line 224). A palette starts only before line 170 (raw LSPC 0x110 + 170), so the frame
 * still ends in time; the levels left behind are written on the next frames (fade_sync rewrites whatever differs). */
#define BG_FADE_LATE_RAW (0x110u + 170u)
/* Raw lines 0x1F0 and up are the vblank the frame starts in: early, not late. The raw line alone cannot tell a frame that wrapped
 * past the next vblank (raw 0xF8-0x10F again) from one that starts in vblank: gfx_frame_wrapped does (demo rematch, frame 736). */
static u8 fade_late(void) {
    u16 l = VQ_RASTER_LINE(*REG_LSPCMODE);
    return gfx_frame_wrapped() || (l >= BG_FADE_LATE_RAW && l < 0x1F0u);
}
#define BG_PAL_TOTAL (CITY_PALETTE_COUNT + DUSK_PALETTE_COUNT + STORM_PALETTE_COUNT)
static BgFade g_fade;
static u8 g_pal_lvl[BG_PAL_TOTAL];
static const u16 (*const MOOD_PALS[BG_MOOD_COUNT])[16] = { city_palettes, dusk_palettes, storm_palettes };
static const u8 MOOD_PAL_SLOT[BG_MOOD_COUNT] = { CITY_PAL_SLOT, DUSK_PAL_SLOT, STORM_PAL_SLOT };
static const u8 MOOD_PAL_COUNT[BG_MOOD_COUNT] = { CITY_PALETTE_COUNT, DUSK_PALETTE_COUNT, STORM_PALETTE_COUNT };

static u8 fade_vis(void) { return g_fade.phase == BGF_OUT ? g_bg_mood : g_want; }
static u8 fade_level(void) { return g_fade.phase == BGF_IDLE ? BG_FADE_MAX : g_fade.level; }
static u8 g_dark; /* video_init: the backdrop stays black until the screen fade-up, so the BIOS return shows no blue while it blocks */
static u16 backdrop_color(void) { return bg_fade_color((g_hidden ? TRIP_BACKDROP : BACKDROP)[fade_vis()], fade_level()); }
static void backdrop_put(void) { gfx_pal(4095, g_dark ? 0 : backdrop_color()); }
void bg_backdrop_dark(u8 on) { g_dark = on; if (!on) backdrop_put(); }
/* One frame of palette writes; returns 1 when every palette (and nothing else) is at its wanted level. */
static u8 fade_sync(void) {
    u8 vis = fade_vis(), lvl = fade_level(), written = 0, base = 0;
    for (u8 m = 0; m < BG_MOOD_COUNT; m++) {
        for (u8 p = 0; p < MOOD_PAL_COUNT[m]; p++) {
            u8 i = (u8)(base + p), want = m == vis ? lvl : BG_FADE_MAX;
            if (g_pal_lvl[i] == want) continue;
            if (written >= BG_FADE_PALS_PER_FRAME || fade_late()) return 0; /* a late frame: next frame */
            for (u8 c = 0; c < 16; c++) gfx_pal((u16)((MOOD_PAL_SLOT[m] + p) * 16 + c), bg_fade_color(MOOD_PALS[m][p][c], want));
            g_pal_lvl[i] = want;
            written++;
        }
        base = (u8)(base + MOOD_PAL_COUNT[m]);
    }
    return 1;
}

void bg_load_palettes(void) {
    for (int p = 0; p < CITY_PALETTE_COUNT; p++)
        for (int i = 0; i < 16; i++)
            gfx_pal((CITY_PAL_SLOT + p) * 16 + i, city_palettes[p][i]);
    for (int p = 0; p < DUSK_PALETTE_COUNT; p++)
        for (int i = 0; i < 16; i++)
            gfx_pal((DUSK_PAL_SLOT + p) * 16 + i, dusk_palettes[p][i]);
    for (int p = 0; p < STORM_PALETTE_COUNT; p++)
        for (int i = 0; i < 16; i++)
            gfx_pal((STORM_PAL_SLOT + p) * 16 + i, storm_palettes[p][i]);
    /* The backdrop is the LAST palette RAM entry, not entry 0 (verified by snapshot, plan B2). */
    gfx_pal(4095, g_dark ? 0 : BACKDROP[g_bg_mood]);
    for (u8 i = 0; i < BG_PAL_TOTAL; i++) g_pal_lvl[i] = BG_FADE_MAX;
}

/* Strip of the column in sprite `slot`, mood m: the tiles of its drawn rows (none for a 0 row column). */
static void column_strip(u8 m, u8 slot) {
    u8 i = (u8)(slot - BG_SKY_SPRITE), n = COL_ROWS[i], p = 0;
    const CityFrame *f;
    if (!n || g_pop == POP_ON) return; /* the Pop Drop sky owns these tiles */
    while (p + 1 < BG_PLANE_COUNT && slot >= PLANE_FIRST[p + 1]) p++;
    f = &city_frames[city_anims[PLANE_ANIM[p]].first_frame]; /* geometry is the same in both moods (asserts above) */
    gfx_strip_attr(slot, g_pairs[m][f->tile_offset + (slot - PLANE_FIRST[p]) * f->tiles_h + COL_ROW0[i]], TILE_BASE[m], n);
}

void bg_init(void) {
    g_pop = POP_OFF;
    g_pop_drawn = 0;
    for (u16 i = 0; i < BG_TILE_REFS; i++) {
        g_pairs[GAME_MOOD_MOON][i][0] = city_tile_index[i];
        g_pairs[GAME_MOOD_MOON][i][1] = (u16)((CITY_PAL_SLOT + city_tile_pal[i]) << 8);
        g_pairs[GAME_MOOD_DUSK][i][0] = dusk_tile_index[i];
        g_pairs[GAME_MOOD_DUSK][i][1] = (u16)((DUSK_PAL_SLOT + dusk_tile_pal[i]) << 8);
        g_pairs[GAME_MOOD_STORM][i][0] = storm_tile_index[i];
        g_pairs[GAME_MOOD_STORM][i][1] = (u16)((STORM_PAL_SLOT + storm_tile_pal[i]) << 8);
    }
    for (u8 p = 0; p < BG_PLANE_COUNT; p++) {
        for (u8 c = 0; c < PLANE_COLS[p]; c++) {
            u8 slot = (u8)(PLANE_FIRST[p] + c), i = (u8)(slot - BG_SKY_SPRITE), n = COL_ROWS[i];
            g_scb3_show[i] = n ? gfx_scb3_word(n, (u16)(PLANE_TOP[p] + 16 * COL_ROW0[i])) : 0; /* 0 rows: height 0 hides the sprite */
            gfx_word((u16)(ADDR_SCB2 + slot), 0xFFF);
            column_strip(g_bg_mood, slot);
            gfx_word((u16)(ADDR_SCB3 + slot), (hidden_mask() & (1u << p)) ? 0 : g_scb3_show[i]); /* a BIOS return inside Gum Trip keeps far and near hidden */
        }
        g_bg_plane_x[p] = 0x7FFF; /* no x written yet: the next bg_update sends all planes */
        g_last_valid = 0;
    }
    g_want = g_bg_mood; /* a change cut short restarts on the next bg_set_mood: the planes are whole and shown meanwhile */
    g_bg_mood_busy = 0;
    if (g_fade.phase != BGF_IDLE) { g_fade.phase = BGF_IN; g_bg_mood_busy = 1; } /* a fade cut short brightens the mood on screen */
    backdrop_put();
}

/* The tile swap, run while the planes are black: hide every column, then mood_step rewrites the strips. */
static void swap_begin(void) {
    g_step = 0;
    gfx_scb_run((u16)(ADDR_SCB3 + BG_SKY_SPRITE), 1, g_scb3_zero, BG_SPRITE_TOTAL);
}

/* A mood change fades the planes out first (they stay lit meanwhile), swaps the tiles in the dark, fades back in. */
void bg_set_mood(u8 mood, u8 cut) {
    if (mood >= BG_MOOD_COUNT) return;
    if (cut) { /* world hidden: swap at once at full colour (DARK at level max), the entry hold waits for it */
        if (mood == g_want && (g_fade.phase == BGF_IDLE || (g_fade.phase != BGF_OUT && g_fade.level == BG_FADE_MAX))) return;
        g_want = mood;
        g_bg_mood_busy = 1;
        g_fade.phase = BGF_DARK;
        g_fade.level = BG_FADE_MAX;
        swap_begin();
        backdrop_put();
        return;
    }
    if (g_fade.phase == BGF_OUT && mood == g_bg_mood) { /* asked for the mood on screen again: brighten, nothing was swapped */
        g_want = mood;
        bg_fade_abort(&g_fade);
        return;
    }
    if (mood == g_want) return;
    g_want = mood;
    g_step = 0; /* a swap already in flight starts its strips again for the new mood */
    g_bg_mood_busy = 1;
    if (g_fade.phase == BGF_IN || g_fade.phase == BGF_IDLE) bg_fade_start(&g_fade); /* IN: dim again from the level reached */
}

/* Every column's SCB3 word: the show words, planes in hidden_mask at height 0. */
static void show_run(void) {
    if (hidden_mask())
        for (u8 p = 0; p < BG_PLANE_COUNT; p++)
            for (u8 c = 0; c < PLANE_COLS[p]; c++) {
                u8 i = (u8)(PLANE_FIRST[p] + c - BG_SKY_SPRITE);
                g_scb3_out[i] = (hidden_mask() & (1u << p)) ? 0 : g_scb3_show[i];
            }
    gfx_scb_run((u16)(ADDR_SCB3 + BG_SKY_SPRITE), 1, hidden_mask() ? g_scb3_out : g_scb3_show, BG_SPRITE_TOTAL); /* nothing hidden: the show words as they are */
}

/* One frame of a mood change: BG_MOOD_COLS_PER_FRAME strips, or once all are sent the show run (planes Gum Trip hides stay at height 0). */
static void mood_step(void) {
    if (g_step < BG_SPRITE_TOTAL) {
        u8 end = (u8)(g_step + BG_MOOD_COLS_PER_FRAME);
        if (end > BG_SPRITE_TOTAL) end = BG_SPRITE_TOTAL;
        /* a late frame (live play under the swap) stops after one strip; the rest go out on the next frames */
        for (u8 first = g_step; g_step < end && (g_step == first || !fade_late()); g_step++) column_strip(g_want, (u8)(BG_SKY_SPRITE + g_step));
        return;
    }
    show_run();
    g_bg_mood = g_want;
    g_bg_mood_changes++;
    bg_fade_swapped(&g_fade); /* busy until the fade in has written the last palette */
}

u8 bg_dark(void) { return g_fade.phase == BGF_DARK; }

u8 bg_bare(void) { return g_fade.phase == BGF_DARK && g_fade.level == BG_FADE_MAX; }

/* One frame of a mood change: the fade level, its palette words, and the tile swap while dark. */
static void change_step(void) {
    if (bg_fade_step(&g_fade)) swap_begin();
    u8 synced = fade_sync();
    if (g_fade.phase == BGF_DARK) mood_step();
    bg_fade_settle(&g_fade, synced);
    if (g_fade.phase == BGF_IDLE) g_bg_mood_busy = 0;
    backdrop_put();
}

/* Gum Trip drops the planes in BG_TRIP_HIDDEN_MASK (far, near): hide = SCB3 height 0 for each of their columns, show = bg_init's word.
 * Trip also swaps the backdrop (palette RAM entry 4095) to the sky colour, so the tiles the importer blanked (sky behind far, mid B behind
 * near) show sky instead of dark. Written on a change only, so a hidden plane costs no per-line sprites and no VRAM writes per frame. */
static void planes_apply(u8 before) {
    u8 diff = (u8)(before ^ hidden_mask()), want = hidden_mask();
    if (!diff) return;
    if (g_fade.phase == BGF_DARK) return; /* every column is hidden now; the show run at the end of the swap reads hidden_mask */
    for (u8 p = 0; p < BG_PLANE_COUNT; p++) {
        if (!(diff & (1u << p))) continue;
        for (u8 c = 0; c < PLANE_COLS[p]; c++) {
            u8 slot = (u8)(PLANE_FIRST[p] + c), i = (u8)(slot - BG_SKY_SPRITE);
            if (COL_ROWS[i]) gfx_word((u16)(ADDR_SCB3 + slot), (want & (1u << p)) ? 0 : g_scb3_show[i]);
        }
    }
}

void bg_trip_planes(u8 trip) {
    u8 before = hidden_mask(), want = trip ? BG_TRIP_HIDDEN_MASK : 0;
    if (want == g_hidden) return;
    g_hidden = want;
    backdrop_put();
    planes_apply(before);
}

void bg_stadium_planes(u8 on) {
    u8 before = hidden_mask();
    on = on ? 1 : 0;
    if (on == g_stadium) return;
    g_stadium = on;
    planes_apply(before);
}

/* ---- Pop Drop sky: one static sky (14 rows x 20 columns, slots 1..20) and cloud groups that drift up with the platforms.
 * Cloud i is a chained row of tiles; its layer (popdropsky CL) moves at 2, 4 or 6 px while the platforms move 9 and repeats every
 * 128, 256 or 384 lines, so a 128 line layer shows a cloud twice (two groups). The tiles and x words go out once; per frame only
 * the group head SCB3 words (height, y) change. ---- */
#define POP_SKY_ROWS 14
#define POP_LAYERS 3
#define POP_GROUPS_MAX 12
#define POP_SCREEN_H 224
static const u16 POP_PERIOD[POP_LAYERS] = { 128, 256, 384 };
static const u8 POP_SPEED[POP_LAYERS] = { 2, 4, 6 };
#define POP_PLATFORM_SPEED 9
static const u8 POP_CLOUD_CX_LAYER[POPDROPSKY_CLOUDS] = POPDROPSKY_TABLE_CL;
static const s16 POP_CLOUD_CX[POPDROPSKY_CLOUDS] = POPDROPSKY_TABLE_CX;
static const s16 POP_CLOUD_CY[POPDROPSKY_CLOUDS] = POPDROPSKY_TABLE_CY;
static struct { u8 slot, cols, cloud; u8 copy; } g_pop_group[POP_GROUPS_MAX];
static u8 g_pop_groups, g_pop_slots_end, g_pop_step;
static u16 g_pop_pos[POP_LAYERS], g_pop_acc[POP_LAYERS];
static u32 g_pop_last;

static void pop_layout(void) {
    u8 slot = BG_SKY_SPRITE + BG_SKY_COUNT;
    g_pop_groups = 0;
    for (u8 i = 0; i < POPDROPSKY_CLOUDS; i++) {
        u16 per = POP_PERIOD[POP_CLOUD_CX_LAYER[i]];
        u8 cols = popdropsky_frames[1 + i].tiles_w, copies = 1;
        while (copies * per < POP_SCREEN_H + 16) copies++;
        for (u8 k = 0; k < copies; k++) {
            g_pop_group[g_pop_groups].slot = slot;
            g_pop_group[g_pop_groups].cols = cols;
            g_pop_group[g_pop_groups].cloud = i;
            g_pop_group[g_pop_groups].copy = k;
            g_pop_groups++;
            slot = (u8)(slot + cols);
        }
    }
    g_pop_slots_end = slot;
}

/* Head word of every cloud group: y = (CY - pos) wrapped into [-16, period - 16), the copy k one period lower. */
static void pop_heads(void) {
    for (u8 g = 0; g < g_pop_groups; g++) {
        u8 i = g_pop_group[g].cloud, l = POP_CLOUD_CX_LAYER[i];
        int t = POP_CLOUD_CY[i] - (int)g_pop_pos[l] + 16;
        while (t < 0) t += POP_PERIOD[l];
        while (t >= (int)POP_PERIOD[l]) t -= POP_PERIOD[l];
        gfx_word((u16)(ADDR_SCB3 + g_pop_group[g].slot), gfx_scb3_word(1, t - 16 + g_pop_group[g].copy * POP_PERIOD[l]));
    }
}

static void pop_draw(void) {
    const PopdropskyFrame *f = &popdropsky_frames[0];
    gfx_sprite_strips(BG_SKY_SPRITE, BG_SKY_COUNT, POP_SKY_ROWS, popdropsky_tile_index + f->tile_offset, POPDROPSKY_TILE_BASE,
                      (u16)((POPDROPSKY_PAL_SLOT + f->palette) << 8));
    gfx_sprite_place(BG_SKY_SPRITE, BG_SKY_COUNT, POP_SKY_ROWS, 0, 0);
    for (u8 g = 0; g < g_pop_groups; g++) {
        u8 i = g_pop_group[g].cloud;
        f = &popdropsky_frames[1 + i];
        gfx_sprite_strips(g_pop_group[g].slot, g_pop_group[g].cols, 1, popdropsky_tile_index + f->tile_offset, POPDROPSKY_TILE_BASE,
                          (u16)((POPDROPSKY_PAL_SLOT + f->palette) << 8));
        gfx_sprite_chain(g_pop_group[g].slot, g_pop_group[g].cols);
        gfx_word((u16)(ADDR_SCB4 + g_pop_group[g].slot), gfx_scb4_word(POP_CLOUD_CX[i]));
    }
    pop_heads();
    g_pop_drawn = 1;
}

/* Undo: the arena strips of slots 1..g_pop_slots_end come back BG_MOOD_COLS_PER_FRAME per frame, then every SCB3 word. */
static void pop_restore_step(void) {
    u8 end = (u8)(g_pop_step + BG_MOOD_COLS_PER_FRAME), total = (u8)(g_pop_slots_end - BG_SKY_SPRITE);
    if (end > total) end = total;
    for (; g_pop_step < end; g_pop_step++) column_strip(g_bg_mood, (u8)(BG_SKY_SPRITE + g_pop_step));
    if (g_pop_step < total) return;
    g_pop = POP_OFF;
    g_pop_drawn = 0;
    show_run();
    for (u8 p = 0; p < BG_PLANE_COUNT; p++) g_bg_plane_x[p] = 0x7FFF; /* the sky's SCB4 words were overwritten: send all planes */
    g_last_valid = 0;
}

void bg_pop_sky(u8 on, u32 dist) {
    if (!on) {
        if (g_pop != POP_ON) return;
        g_pop = POP_RESTORE;
        g_pop_step = 0;
        return;
    }
    if (g_pop != POP_ON) {
        u8 before = hidden_mask();
        pop_layout();
        g_pop = POP_ON;
        g_pop_drawn = 0;
        g_pop_last = dist;
        for (u8 l = 0; l < POP_LAYERS; l++) g_pop_pos[l] = g_pop_acc[l] = 0;
        planes_apply(before);
    }
    if (!g_pop_drawn) {
        if (g_bg_mood_busy) return; /* a mood swap rewrites the tiles first; the sky goes up when it is done */
        pop_draw();
        return;
    }
    if (dist > g_pop_last) {
        u16 delta = (u16)(dist - g_pop_last > 1024 ? 1024 : dist - g_pop_last); /* 1/16 px; platforms move 9 px per frame at most */
        for (u8 l = 0; l < POP_LAYERS; l++) {
            g_pop_acc[l] = (u16)(g_pop_acc[l] + delta * POP_SPEED[l]);
            while (g_pop_acc[l] >= 16 * POP_PLATFORM_SPEED) { g_pop_acc[l] = (u16)(g_pop_acc[l] - 16 * POP_PLATFORM_SPEED); if (++g_pop_pos[l] >= POP_PERIOD[l]) g_pop_pos[l] = 0; }
        }
    }
    g_pop_last = dist;
    pop_heads();
}

/* Lightning (src/core/rain.c): the storm planes lift toward white at the flash level. fade_sync only runs during a mood change, so
 * this is its own idle-time sync: at most BG_FADE_PALS_PER_FRAME palettes a frame (the flush limit), a late frame waits, so a level
 * spreads over 4 frames. g_pal_flash is the level each storm palette (and the backdrop, entry STORM_PALETTE_COUNT) was last written at. */
static u8 g_flash, g_pal_flash[STORM_PALETTE_COUNT + 1];
void bg_flash(u8 idx) { g_flash = idx; }
static void flash_sync(void) {
    u8 want = g_flash, written = 0;
    if (g_bg_mood != GAME_MOOD_STORM) { memset(g_pal_flash, 0, sizeof g_pal_flash); return; }
    if (g_pal_flash[STORM_PALETTE_COUNT] != want) { gfx_pal(4095, g_dark ? 0 : rain_flash_color((g_hidden ? TRIP_BACKDROP : BACKDROP)[GAME_MOOD_STORM], want)); g_pal_flash[STORM_PALETTE_COUNT] = want; }
    for (u8 p = 0; p < STORM_PALETTE_COUNT; p++) {
        if (g_pal_flash[p] == want) continue;
        if (written >= BG_FADE_PALS_PER_FRAME || fade_late()) return;
        for (u8 c = 0; c < 16; c++) gfx_pal((u16)((STORM_PAL_SLOT + p) * 16 + c), rain_flash_color(storm_palettes[p][c], want));
        g_pal_flash[p] = want;
        written++;
    }
}

/* unwrapped_px = camera_unwrapped_px: plane offset = floor(px * k / 16) mod plane width (src/core/bg_scroll.c, one 16 bit divide per
 * plane, no libgcc call). The SCB4 words of a plane go out only when its offset changed. */
void bg_update(s32 unwrapped_px) {
    BgRamp ramp;
    if (g_bg_mood_busy) { memset(g_pal_flash, 0, sizeof g_pal_flash); change_step(); } /* the change rewrites every palette plain */
    else flash_sync();
    if (g_pop == POP_RESTORE && !g_bg_mood_busy) pop_restore_step();
    if (g_pop) return; /* the sky sprites are not the planes: no plane x words */
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
