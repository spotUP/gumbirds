#include "logo.h"
#include "gfx.h"
#include "sprite_slots.h"
#include "vram_layout.h"
#include "gen/logo_sprites.h"

_Static_assert(LOGO_STRIP_COUNT + LOGO_PIECE_MAX <= LOGO_COUNT, "logo sprite slots are fewer than strips plus the most pieces of one frame");
_Static_assert(LOGO_SPRITE + LOGO_COUNT + TITLE_SOOT_COUNT <= TRIP_STRIP_SPRITE + TRIP_STRIP_COUNT, "logo and title Sootlings leave the Gum Trip strip range (the shared range)");
_Static_assert(LOGO_STRIP_MAX_H <= 5, "strip height buffer");

enum { FRAME_MS_PER_VIDEO_FRAME = 17, SCB1_FLIP_X = 1, SCB1_FLIP_Y = 2 };

static const u16 STRIP_X[] = LOGO_TABLE_STRIP_X;
static const u16 STRIP_Y[] = LOGO_TABLE_STRIP_Y;
static const u8 STRIP_H[] = LOGO_TABLE_STRIP_H;
static const u16 STRIP_OFFSET[] = LOGO_TABLE_STRIP_OFFSET;
static const u16 FRAME_TILES[] = LOGO_TABLE_FRAME_TILES;
static const u16 FRAME_MS[] = LOGO_FRAME_MS;
static const u16 PIECE_FIRST[] = LOGO_TABLE_PIECE_FIRST;
static const u16 PIECE_REF[] = LOGO_TABLE_PIECE_REF;
static const u16 PIECE_X[] = LOGO_TABLE_PIECE_X;
static const u16 PIECE_Y[] = LOGO_TABLE_PIECE_Y;
static const u16 PALETTE[16] = LOGO_TABLE_PALETTE_MOON;

volatile u16 g_logo_draws;
volatile u16 g_logo_frame;
static int g_frame, g_acc, g_loaded = -1, g_shown;
static uint16_t g_ticks;

void logo_load_palettes(void) {
    for (u8 i = 1; i < 16; i++) gfx_pal((u16)(LOGO_PAL_SLOT * 16 + i), PALETTE[i - 1]);
}

static u16 ref_attr(u16 ref) {
    return (u16)((LOGO_PAL_SLOT << 8) | ((ref & LOGO_REF_FLIP_X) ? SCB1_FLIP_X : 0) | ((ref & LOGO_REF_FLIP_Y) ? SCB1_FLIP_Y : 0));
}

static void hide(void) {
    for (int c = 0; c < LOGO_COUNT; c++) gfx_word((u16)(ADDR_SCB3 + LOGO_SPRITE + c), 0);
    g_loaded = -1; g_shown = 0;
}

/* gfx_strip_attr keeps the pointer until the flush: the pairs live in static RAM, never on the stack. */
static u16 g_pairs[LOGO_STRIP_COUNT][LOGO_STRIP_MAX_H * 2];
static u16 g_piece_pairs[LOGO_PIECE_MAX][2];

/* Tiles of frame f into the strips and pieces; positions follow in logo_step. */
static void load_frame(int f) {
    const u16 *refs = &FRAME_TILES[f * LOGO_FRAME_TILES];
    for (int i = 0; i < LOGO_STRIP_COUNT; i++) {
        u16 *pairs = g_pairs[i];
        for (int r = 0; r < STRIP_H[i]; r++) { u16 ref = refs[STRIP_OFFSET[i] + r]; pairs[r * 2] = (u16)(ref & LOGO_REF_TILE); pairs[r * 2 + 1] = ref_attr(ref); }
        gfx_strip_attr((u16)(LOGO_SPRITE + i), pairs, LOGO_TILE_BASE, STRIP_H[i]);
    }
    int n = PIECE_FIRST[f + 1] - PIECE_FIRST[f];
    for (int k = 0; k < LOGO_PIECE_MAX; k++) {
        u16 sprite = (u16)(LOGO_SPRITE + LOGO_STRIP_COUNT + k);
        if (k < n) {
            u16 ref = PIECE_REF[PIECE_FIRST[f] + k], *pair = g_piece_pairs[k];
            pair[0] = (u16)(ref & LOGO_REF_TILE); pair[1] = ref_attr(ref);
            gfx_strip_attr(sprite, pair, LOGO_TILE_BASE, 1);
            gfx_word((u16)(ADDR_SCB3 + sprite), gfx_scb3_word(1, PIECE_Y[PIECE_FIRST[f] + k]));
            gfx_word((u16)(ADDR_SCB4 + sprite), gfx_scb4_word(PIECE_X[PIECE_FIRST[f] + k]));
        } else gfx_word((u16)(ADDR_SCB3 + sprite), 0);
    }
}

void logo_step(int active) {
    if (!active) { if (g_shown) hide(); g_frame = 0; g_acc = 0; g_ticks = 0; return; }
    if (!g_shown) {
        gfx_sprite_unchained(LOGO_SPRITE, LOGO_COUNT); /* every sprite is placed on its own */
        for (int i = 0; i < LOGO_STRIP_COUNT; i++) {
            gfx_word((u16)(ADDR_SCB3 + LOGO_SPRITE + i), gfx_scb3_word(STRIP_H[i], STRIP_Y[i]));
            gfx_word((u16)(ADDR_SCB4 + LOGO_SPRITE + i), gfx_scb4_word(STRIP_X[i]));
        }
        g_shown = 1; g_loaded = -1;
    } else {
        g_acc += FRAME_MS_PER_VIDEO_FRAME;
        while (g_acc >= FRAME_MS[g_frame]) { g_acc -= FRAME_MS[g_frame]; g_frame = (g_frame + 1) % LOGO_FRAME_COUNT; g_ticks++; }
    }
    if (g_loaded != g_frame) { load_frame(g_frame); g_loaded = g_frame; }
    g_logo_frame = (u16)g_frame; g_logo_draws++;
}

void logo_reset(void) { g_shown = 0; g_loaded = -1; g_frame = 0; g_acc = 0; g_ticks = 0; }

uint16_t logo_ticks(void) { return g_ticks; }
