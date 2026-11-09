/*
 * City background: hardware glue. Palettes, static stars/moon/clouds, three scrolling rings.
 * Each ring is BG_RING sprites; slot = world column % 21 and shows art column world % 20. The
 * ring is two sticky chains in sprite order: the leftmost column's slot (head A) through slot
 * BG_RING-1, then slot 0 (head B) through the slot before head A. Per frame a ring gets two SCB4
 * (x) words (heads A and B; the hardware places the sticky followers 16 px apart), not one per
 * column: 63 queued words per frame were more than the vblank flush budget and most of the frame
 * logic (main loop at 30 Hz, thoughts/shared/research/2026-11-09_test-laser-hit-fix.md). When the
 * first visible column advances, the head moves (two SCB3 words) and the one entering column
 * gets its SCB1 tile strip. See
 * thoughts/shared/plans/2026-11-09-city-background.md.
 */
#include <ngdevkit/neogeo.h>
#include <ngdevkit/ng-video.h>
#include "bg.h"
#include "gfx.h"
#include "core/bg_scroll.h"
#include "sprite_slots.h"
#include "vram_layout.h"

volatile u32 g_bg_scroll_px[3];
volatile u32 g_bg_column_writes;
volatile u32 g_bg_rebases; /* runs the scroll continued across (bg_update distance went back), test sentinel */
/* First palette RAM entry of the city palettes; read by tests/mame/unibios_check.lua through nm. */
const u16 g_bg_pal_first_entry = CITY_PAL_SLOT * 16;

/* Palette word (DRGB, dark bit 0) from 5 bit channels, same layout as tools/sprite_pipeline.py rgb_to_ng. */
#define NG_RGB5(r, g, b) ((u16)((((r) & 1) << 14) | (((g) & 1) << 13) | (((b) & 1) << 12) | (((r) >> 1) << 8) | (((g) >> 1) << 4) | ((b) >> 1)))
#define BG_BACKDROP NG_RGB5(3, 2, 7)       /* #1a1238 */
#define BG_LAMP_ON NG_RGB5(31, 7, 9)       /* #ff3a4a, baked into far and mid tiles */
#define BG_LAMP_WHITE 0x7fff               /* corner highlight of the lamp */
#define BG_LAMP_OFF NG_RGB5(7, 4, 8)       /* dark lamp */
#define BG_LAMP_PERIOD 48                  /* frames per blink cycle */
#define BG_LAMP_ON_FRAMES 30
#define BG_STAR_PERIOD 16                  /* frames between star tile swaps */

_Static_assert(BG_FAR_SPRITE + BG_RING_COUNT == BG_MID_SPRITE, "far/mid sprite ranges");
_Static_assert(BG_MID_SPRITE + BG_RING_COUNT == BG_ROOF_SPRITE, "mid/roof sprite ranges");
_Static_assert(BG_ROOF_SPRITE + BG_RING_COUNT == BG_SPRITE_END, "roof sprite range end");
_Static_assert(BG_STAR_SPRITE + BG_STAR_COUNT == BG_SKY_SPRITE, "star/sky sprite ranges");
_Static_assert(BG_SKY_SPRITE + BG_SKY_COUNT == BG_FAR_SPRITE, "sky/far sprite ranges");
_Static_assert(BG_RING_COUNT == BG_RING, "ring size");
_Static_assert(CITY_MAX_COLUMNS == BG_ART_COLS, "city art width");

enum { FRAME_FAR = 0, FRAME_MID = 1, FRAME_ROOF = 2 };
enum { SKY_MOON = 0, SKY_CLOUDS = 1, SKY_DOT = 2, SKY_PLUS = 3 };

typedef struct { u8 frame; u8 first_sprite; u8 top; } Ring;
static const Ring RINGS[BG_LAYER_COUNT] = {
    { FRAME_FAR, BG_FAR_SPRITE, 64 },
    { FRAME_MID, BG_MID_SPRITE, 96 },
    { FRAME_ROOF, BG_ROOF_SPRITE, 176 },
};

/* Star positions (star pixel); same list as STARS in assets/city/draw_city.py. */
typedef struct { u16 x, y; } StarPos;
static const StarPos STARS[BG_STAR_COUNT] = {
    {12, 34}, {30, 70}, {52, 30}, {70, 84}, {96, 40}, {118, 66}, {134, 32}, {150, 56},
    {172, 38}, {186, 74}, {200, 30}, {214, 58}, {292, 36}, {304, 80}, {8, 92}, {160, 86},
};
#define STAR_TILE_OFFSET 8 /* star pixel position inside its 16x16 tile */
#define MOON_X 208
#define MOON_Y 32
#define CLOUDS_X 16
#define CLOUDS_Y 48

static u32 g_prev_first[BG_LAYER_COUNT];
static u8 g_prev_head[BG_LAYER_COUNT]; /* slot of the leftmost column (chain head A) last written */
static int g_valid;
static u16 g_lamp_far[2], g_lamp_mid[2]; /* palette entry numbers of lamp on and white; 0 = none */

static u16 pal_entry(u8 pal) { return (u16)((CITY_PAL_SLOT + pal) * 16); }

static const CityFrame *frame_of(u8 sky_k_or_layer, int sky) {
    return &city_frames[sky ? city_anims[CITY_ANIM_SKY].first_frame + sky_k_or_layer : sky_k_or_layer];
}

static void find_lamp(const CityFrame *f, u16 out[2]) {
    out[0] = out[1] = 0;
    for (int i = 1; i < 16; i++) {
        u16 w = city_palettes[f->palette][i];
        if (w == BG_LAMP_ON) out[0] = (u16)(pal_entry(f->palette) + i);
        else if (w == BG_LAMP_WHITE) out[1] = (u16)(pal_entry(f->palette) + i);
    }
}

/* Lamp palette and star tiles change on a state flip only; -1 forces the first write (bg_load_palettes, bg_init). */
static int g_lamp_state = -1, g_star_state = -1;

void bg_load_palettes(void) {
    g_lamp_state = -1;
    for (int p = 0; p < CITY_PALETTE_COUNT; p++)
        for (int i = 0; i < 16; i++)
            gfx_pal((CITY_PAL_SLOT + p) * 16 + i, city_palettes[p][i]);
    /* The backdrop is the LAST palette RAM entry, not entry 0 (verified by snapshot, plan B2). */
    gfx_pal(4095, BG_BACKDROP);
    find_lamp(frame_of(FRAME_FAR, 0), g_lamp_far);
    find_lamp(frame_of(FRAME_MID, 0), g_lamp_mid);
}

/* Place `cols` columns of frame f at sprite slot `first`, top left (x, y); first column carries position. */
static void place_block(u8 first, const CityFrame *f, int x, int y) {
    u16 attr = (u16)((CITY_PAL_SLOT + f->palette) << 8);
    gfx_sprite_block(first, (u8)f->tiles_w, (u8)f->tiles_h, &city_tile_index[f->tile_offset], CITY_TILE_BASE, attr, x, y);
}

static void star_tile(int i, int plus) {
    const CityFrame *f = frame_of(plus ? SKY_PLUS : SKY_DOT, 1);
    gfx_scb1_word((u16)(BG_STAR_SPRITE + i), (u16)(CITY_TILE_BASE + city_tile_index[f->tile_offset]));
}

void bg_init(void) {
    for (int i = 0; i < BG_STAR_COUNT; i++) {
        place_block((u8)(BG_STAR_SPRITE + i), frame_of(SKY_DOT, 1), STARS[i].x - STAR_TILE_OFFSET, STARS[i].y - STAR_TILE_OFFSET);
    }
    place_block(BG_SKY_SPRITE, frame_of(SKY_MOON, 1), MOON_X, MOON_Y);
    place_block(BG_SKY_SPRITE + 5, frame_of(SKY_CLOUDS, 1), CLOUDS_X, CLOUDS_Y);
    for (int l = 0; l < BG_LAYER_COUNT; l++) /* SCB3 (heads, sticky) is written by update_ring */
        for (int s = 0; s < BG_RING; s++) gfx_word((u16)(ADDR_SCB2 + RINGS[l].first_sprite + s), 0xFFF);
    g_valid = 0;
    g_lamp_state = g_star_state = -1;
}

static void write_column(int layer, u32 world_col) {
    const Ring *r = &RINGS[layer];
    const CityFrame *f = frame_of(r->frame, 0);
    u32 slot = bg_ring_slot(world_col), art = bg_art_col(world_col);
    u16 attr = (u16)((CITY_PAL_SLOT + f->palette) << 8);
    gfx_strip((u16)(r->first_sprite + slot), &city_tile_index[f->tile_offset + art * f->tiles_h], CITY_TILE_BASE, (u8)f->tiles_h, attr);
    g_bg_column_writes++;
}

static void update_ring(int layer, u32 distance) {
    const Ring *r = &RINGS[layer];
    u32 s = bg_scroll_px(distance, (BgLayer)layer), first = bg_first_col(s);
    u32 n = bg_columns_to_write(g_prev_first[layer], first, g_valid);
    u32 first_slot = bg_ring_slot(first);
    if (n == BG_RING) {
        for (u32 slot = 0; slot < BG_RING; slot++) write_column(layer, bg_slot_world_col_at(first, first_slot, slot));
    } else if (n == 1) {
        write_column(layer, first + BG_RING - 1);
    }
    g_prev_first[layer] = first;
    /* Chain heads: slot 0 (always, the sprite before it belongs to another ring) and first_slot. */
    u16 head = (u16)((((496 - r->top) & 0x1FF) << 7) | frame_of(r->frame, 0)->tiles_h);
    if (!g_valid) {
        for (u32 slot = 1; slot < BG_RING; slot++) gfx_word((u16)(ADDR_SCB3 + r->first_sprite + slot), 1 << 6);
        gfx_word((u16)(ADDR_SCB3 + r->first_sprite), head);
    } else if (g_prev_head[layer] != first_slot && g_prev_head[layer] != 0) {
        gfx_word((u16)(ADDR_SCB3 + r->first_sprite + g_prev_head[layer]), 1 << 6);
    }
    gfx_word((u16)(ADDR_SCB3 + r->first_sprite + first_slot), head);
    g_prev_head[layer] = (u8)first_slot;
    gfx_word((u16)(ADDR_SCB4 + r->first_sprite + first_slot), (u16)((bg_slot_x(s, first) & 0x1FF) << 7));
    if (first_slot != 0)
        gfx_word((u16)(ADDR_SCB4 + r->first_sprite), (u16)((bg_slot_x(s, bg_slot_world_col_at(first, first_slot, 0)) & 0x1FF) << 7));
    g_bg_scroll_px[layer] = s;
}

static void lamp_set(const u16 e[2], int on) {
    if (e[0]) gfx_pal(e[0], on ? BG_LAMP_ON : BG_LAMP_OFF);
    if (e[1]) gfx_pal(e[1], on ? BG_LAMP_WHITE : BG_LAMP_OFF);
}

/* The scroll runs on the distance of all runs so far, so it never jumps back when a new run starts at distance 0.
 * A jump makes every ring column change (bg_columns_to_write = BG_RING): 63 column strips, about 780 VRAM words,
 * which take three vblank flushes, so for the first frames of a run the rings showed the old scroll and half
 * written columns (make test-scroll, thoughts/spot/todos.md scroll entry). */
static u32 g_dist_base, g_dist_last;

void bg_update(u32 distance, u32 frame) {
    if (distance < g_dist_last) { g_dist_base += g_dist_last; g_bg_rebases++; }
    g_dist_last = distance;
    u32 total = g_dist_base + distance;
    for (int l = 0; l < BG_LAYER_COUNT; l++) update_ring(l, total);
    g_valid = 1;
    /* frame % period without a 32-bit `%` (libgcc call) per frame: step the phases while frame advances by 1. */
    static u32 prev_frame;
    static u8 lamp_t, star_t, star_ph;
    if (frame == prev_frame + 1 && g_lamp_state >= 0) {
        if (++lamp_t == BG_LAMP_PERIOD) lamp_t = 0;
        if (++star_t == BG_STAR_PERIOD) { star_t = 0; star_ph ^= 1; }
    } else {
        lamp_t = (u8)(frame % BG_LAMP_PERIOD);
        star_t = (u8)(frame % BG_STAR_PERIOD);
        star_ph = (u8)((frame / BG_STAR_PERIOD) & 1);
    }
    prev_frame = frame;
    int on = lamp_t < BG_LAMP_ON_FRAMES;
    if (on != g_lamp_state) {
        lamp_set(g_lamp_far, on);
        lamp_set(g_lamp_mid, on);
        g_lamp_state = on;
    }
    int phase = star_ph;
    if (phase != g_star_state) {
        for (int i = 0; i < BG_STAR_COUNT; i++) star_tile(i, (phase + i) & 1);
        g_star_state = phase;
    }
}
