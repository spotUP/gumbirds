#include "fling_field.h"
#include "gfx.h"
#include "island.h"
#include "sprite_slots.h"
#include "vram_layout.h"
#include "core/game.h"

#define COLS FLFIELD_TURF_COUNT
#define MARKS FLFIELD_MARKER_COUNT
#define LOADS_PER_FRAME 4 /* tile strips queued per frame: bounds the burst at field entry (same bound as trip_strip.c) */
#define TURF_Y 160        /* screen y of the turf top (FLOOR_Y in tools/draw_fling_field.py) */
#define STACK_BOTTOM 227  /* every board stack ends here: top = STACK_BOTTOM - 16 * rows */
#define LINE_X 48         /* left edge of the foul line column; a board m metres out sits at LINE_X + 3 * m */
#define MARK_K 5          /* marker slot of the 50 M mark board */
#define MARK_FLUTTER 4    /* pennant frame changes every 1 << MARK_FLUTTER game frames */
#define PUFF_X 24         /* hero centre x 36 minus 12 */
#define PUFF_Y 131
#define PUFF_TICKS 3      /* game frames per puff frame */
#define TURF_ATTR (FLFIELD_TURF_PAL_SLOT << 8)
#define GEAR_ATTR (FLFIELD_GEAR_PAL_SLOT << 8)
_Static_assert(FLFIELD_BOARD_COUNT + 2 == MARKS, "marker slots: foul line, the boards and the mark board");
_Static_assert(FLFIELD_MARKER_SPRITE + MARKS <= ISLAND_SPRITE + 41, "field markers overrun the island slots");
_Static_assert(FLFIELD_PUFF_SPRITE + FLFIELD_PUFF_COUNT <= SPRITE_SLOT_END, "field puff overruns the slot table");

static const char k_seq[] = "PRQSQPSRPQRSRPSQSRQPRSPQSQRPQSPR"; /* TURF_SEQ in tools/draw_fling_field.py: the column letters repeat every 32 */

static u8 g_on, g_vis, g_ready, g_mood, g_prev, g_mload, g_flut, g_puff_t;
static u16 g_tick;
static u8 g_type[COLS];           /* turf frame loaded in the slot, 0xFF = none */
static u16 g_t3[COLS], g_t4[COLS], g_mw[MARKS], g_m3[MARKS], g_m4[MARKS], g_p3[FLFIELD_PUFF_COUNT], g_p4[FLFIELD_PUFF_COUNT];

static const u16 *tiles_of(u16 frame) { return &flfield_tile_index[flfield_frames[frame].tile_offset]; }

static u16 marker_frame(u8 k) {
    if (!k) return FLFIELD_FOUL_FRAME;
    if (k == MARK_K) return (u16)(FLFIELD_MARK_FIRST + g_flut);
    return (u16)(FLFIELD_BOARD_FIRST + (k < MARK_K ? k - 1 : k - 2));
}

static void load_palettes(u8 mood) {
    const u16 *turf = mood == GAME_MOOD_MOON ? flfield_extra_palettes[FLFIELD_EXTRA_PAL_TURF_MOON] : mood == GAME_MOOD_STORM ? flfield_extra_palettes[FLFIELD_EXTRA_PAL_TURF_STORM] : flfield_palettes[0];
    const u16 *gear = mood == GAME_MOOD_MOON ? flfield_extra_palettes[FLFIELD_EXTRA_PAL_GEAR_MOON] : mood == GAME_MOOD_STORM ? flfield_extra_palettes[FLFIELD_EXTRA_PAL_GEAR_STORM] : flfield_palettes[2];
    for (u8 i = 0; i < 16; i++) { gfx_pal((u16)(FLFIELD_TURF_PAL_SLOT * 16 + i), turf[i]); gfx_pal((u16)(FLFIELD_GEAR_PAL_SLOT * 16 + i), gear[i]); }
}

static void load_marker(u8 k) {
    u16 fr = marker_frame(k), rows = flfield_frames[fr].tiles_h;
    gfx_strip((u16)(FLFIELD_MARKER_SPRITE + k), tiles_of(fr), FLFIELD_TILE_BASE, (u8)rows, GEAR_ATTR);
    g_mw[k] = gfx_scb3_word((u8)rows, STACK_BOTTOM - 16 * (int)rows);
}

static void hide_all(void) {
    for (u8 i = 0; i < COLS; i++) g_t3[i] = 0;
    for (u8 i = 0; i < MARKS; i++) g_m3[i] = 0;
    gfx_scb_run((u16)(ADDR_SCB3 + FLFIELD_TURF_SPRITE), 1, g_t3, COLS);
    gfx_scb_run((u16)(ADDR_SCB3 + FLFIELD_MARKER_SPRITE), 1, g_m3, MARKS);
    for (u8 i = 0; i < FLFIELD_PUFF_COUNT; i++) g_p3[i] = 0;
    gfx_scb_run((u16)(ADDR_SCB3 + FLFIELD_PUFF_SPRITE), 1, g_p3, FLFIELD_PUFF_COUNT);
}

u8 fling_field_loaded(void) { return g_ready; }

void fling_field_step(const GgFling *f, u8 mood, int on, int show, int markers) {
    u8 loads = LOADS_PER_FRAME, pending = 0;
    u32 scroll, j0;
    if (!f || !on) {
        if (g_on) { hide_all(); g_on = g_vis = g_ready = 0; island_relayout(); }
        return;
    }
    if (!g_on) {
        g_on = 1; g_vis = 0; g_mood = 0xFF; g_mload = 0; g_puff_t = 0xFF; g_tick = 0; g_flut = 0; g_prev = f->phase;
        for (u8 i = 0; i < COLS; i++) g_type[i] = 0xFF;
        gfx_sprite_unchained(FLFIELD_TURF_SPRITE, COLS);
        gfx_sprite_unchained(FLFIELD_MARKER_SPRITE, MARKS);
        gfx_sprite_unchained(FLFIELD_PUFF_SPRITE, FLFIELD_PUFF_COUNT);
        hide_all();
    }
    if (mood != g_mood) { load_palettes(mood); g_mood = mood; }
    g_tick++;
    scroll = f->phase >= GF_FLIGHT ? (u32)(f->x >> 16) : 0;
    j0 = scroll >> 4;
    for (u32 j = j0; j < j0 + COLS; j++) {
        u8 s = (u8)(j % COLS), t = (u8)(k_seq[j & 31] - 'P');
        if (g_type[s] != t) {
            if (!loads) { pending = 1; g_t3[s] = 0; continue; }
            gfx_strip((u16)(FLFIELD_TURF_SPRITE + s), tiles_of((u16)(FLFIELD_TURF_FIRST + t)), FLFIELD_TILE_BASE, 4, TURF_ATTR);
            g_type[s] = t; loads--;
        }
        g_t3[s] = gfx_scb3_word(4, TURF_Y);
        g_t4[s] = gfx_scb4_word((int)(j * 16) - (int)scroll);
    }
    while (markers && loads && g_mload < MARKS) { load_marker(g_mload++); loads--; }   /* Toss Gum draws the turf only: no foul line, boards, mark flag */
    if (markers && g_mload < MARKS) pending = 1;
    if (markers && g_mload >= MARKS && g_flut != (u8)((g_tick >> MARK_FLUTTER) & 1) && loads) { g_flut ^= 1; load_marker(MARK_K); }
    for (u8 k = 0; k < MARKS; k++) {
        int x = LINE_X + 3 * (k ? 10 * k : 0) - (int)scroll;
        g_m3[k] = markers && x > -16 && x < 320 && k < g_mload ? g_mw[k] : 0;
        g_m4[k] = gfx_scb4_word(x);
    }
    /* landing puff: starts on the touch-down edge (a foul has no flight, so none) */
    if (g_prev == GF_FLIGHT && f->phase == GF_LANDED) g_puff_t = 0;
    g_prev = f->phase;
    if (g_puff_t != 0xFF) {
        u8 fr = (u8)(g_puff_t / PUFF_TICKS);
        if (fr >= FLFIELD_PUFF_FRAMES) { g_puff_t = 0xFF; for (u8 c = 0; c < FLFIELD_PUFF_COUNT; c++) g_p3[c] = 0; }
        else {
            if (!(g_puff_t % PUFF_TICKS))
                for (u8 c = 0; c < FLFIELD_PUFF_COUNT; c++) gfx_strip((u16)(FLFIELD_PUFF_SPRITE + c), tiles_of((u16)(FLFIELD_PUFF_FIRST + fr)) + c * 2, FLFIELD_TILE_BASE, 2, TURF_ATTR);
            for (u8 c = 0; c < FLFIELD_PUFF_COUNT; c++) { g_p3[c] = gfx_scb3_word(2, PUFF_Y); g_p4[c] = gfx_scb4_word(PUFF_X + 16 * c); }
            g_puff_t++;
        }
    }
    g_ready = !pending;
    if (show && !pending) g_vis = 1;
    if (!show) { if (g_vis) hide_all(); g_vis = 0; }
    if (g_vis) {
        gfx_scb_run((u16)(ADDR_SCB3 + FLFIELD_TURF_SPRITE), 1, g_t3, COLS);
        gfx_scb_run((u16)(ADDR_SCB4 + FLFIELD_TURF_SPRITE), 1, g_t4, COLS);
        gfx_scb_run((u16)(ADDR_SCB3 + FLFIELD_MARKER_SPRITE), 1, g_m3, MARKS);
        gfx_scb_run((u16)(ADDR_SCB4 + FLFIELD_MARKER_SPRITE), 1, g_m4, MARKS);
        gfx_scb_run((u16)(ADDR_SCB3 + FLFIELD_PUFF_SPRITE), 1, g_p3, FLFIELD_PUFF_COUNT);
        gfx_scb_run((u16)(ADDR_SCB4 + FLFIELD_PUFF_SPRITE), 1, g_p4, FLFIELD_PUFF_COUNT);
    }
}
