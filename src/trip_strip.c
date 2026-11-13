#include "trip_strip.h"
#include "gfx.h"
#include "sprite_slots.h"
#include "vram_layout.h"
#include "core/camera.h"
#include "core/trip_view.h"
#include "gen/tripstrip_tables.h"

#define COLS TRIP_VIEW_STRIP_COLS
#define ALL (2 * COLS)
#define ROWS TRIP_VIEW_STRIP_MAX_ROWS
/* Column pairs (floor and ceiling) whose tiles are built and queued in one frame: bounds the CPU time and the queue of the burst at run
 * start (a full ring in one frame ran 176 lines of the 224 and overran the next frame). The strip is shown once every column in view is
 * loaded. Structural performance bound, not a gameplay tunable. */
/* Measured (tests/mame/trip_check.lua, logic end by phase): 6 loads/frame peaked at 183.9 lines in the second hold frame, 4 gives 164.8, 3 gives
 * 155.2 but shows the strip 5 frames after ready (limit 4). */
#define LOADS_PER_FRAME 4
_Static_assert(TRIP_STRIP_COUNT == ALL, "trip strip sprite slots are not 2 x the ring");
_Static_assert(TRIP_STRIP_SPRITE + TRIP_STRIP_COUNT <= SPRITE_SLOT_END, "trip strip sprites exceed the slot table");
_Static_assert(TRIPSTRIP_STEP_TICKS == 5, "the trip strip animation speed is 5 ticks per frame");

volatile u16 g_trip_strip_draws;
static u8 g_on;
static u8 g_vis;            /* 1 while the strip sprites are shown (course ready); tiles are loaded ahead during the run-start hold */
static TripStripRing g_ring;
static u32 g_key[COLS];     /* world column + 1 loaded in the slot, 0 = hidden */
static struct { u8 head, count, valid; u32 made; } g_scan; /* generator state at the last scan that left nothing pending */
static s16 g_x[COLS];       /* last x sent per slot, or CAMERA_COL_HIDDEN */
static u16 g_scb3[ALL];     /* SCB3 word per sprite (0 = hidden), written to the chip only while g_vis */
static u16 g_scb4[ALL];     /* SCB4 word per sprite: floor slots first, then ceiling (a hidden column keeps its last x) */
static u16 g_pairs[ALL][ROWS * 2]; /* {tile, attribute} per row; the queue keeps the pointer until the flush */

void trip_strip_load_palettes(void) {
    for (u8 i = 0; i < 16; i++) gfx_pal((u16)(TRIPSTRIP_PAL_SLOT * 16 + i), tripstrip_palettes[0][i]);
}

static void hide_sprites(void) {
    for (u16 i = 0; i < ALL; i++) { gfx_word((u16)(ADDR_SCB3 + TRIP_STRIP_SPRITE + i), 0); g_scb3[i] = 0; }
    for (u8 s = 0; s < COLS; s++) { g_key[s] = 0; g_x[s] = CAMERA_COL_HIDDEN; }
    g_vis = 0; g_scan.valid = 0;
}

static void hide_all(void) {
    hide_sprites();
    g_ring.valid = 0;
}

/* Boot: the SCB2 size words never change and SCB3 starts at 0, so a play frame never queues them (the first Gum Trip frame carried 88
 * of these words, 44 SCB3 + 44 SCB2, with nothing visible changing). Nothing else writes sprites TRIP_STRIP_SPRITE..+ALL. */
void trip_strip_init(void) {
    hide_all();
    gfx_sprite_unchained(TRIP_STRIP_SPRITE, ALL);
}

/* Queues the tiles of one strip column and its SCB3 word. */
static void load(u8 slot, int ceiling, u32 j, const TripChunk *ch) {
    TripStripCell cells[ROWS];
    int top, rows = trip_view_strip_column(ch, j, ceiling, cells, &top);
    u16 sprite = (u16)(TRIP_STRIP_SPRITE + slot + (ceiling ? COLS : 0));
    u16 *p = g_pairs[slot + (ceiling ? COLS : 0)];
    if (!rows) { g_scb3[sprite - TRIP_STRIP_SPRITE] = 0; if (g_vis) gfx_word((u16)(ADDR_SCB3 + sprite), 0); return; }
    for (int i = 0; i < rows; i++) {
        u16 attr = (u16)((TRIPSTRIP_PAL_SLOT << 8) | cells[i].flip);
        u16 tile;
        if (cells[i].role == TRIP_STRIP_FILL) tile = tripstrip_tile_index[0];
        else { tile = tripstrip_tile_index[cells[i].role == TRIP_STRIP_RIM_A ? 1 : 9]; attr |= 0x08; } /* rim: 8 frame auto-animation */
        p[i * 2] = tile; p[i * 2 + 1] = attr;
    }
    gfx_strip_attr(sprite, p, TRIPSTRIP_TILE_BASE, (u8)rows);
    g_scb3[sprite - TRIP_STRIP_SPRITE] = gfx_scb3_word((u8)rows, top);
    if (g_vis) gfx_word((u16)(ADDR_SCB3 + sprite), g_scb3[sprite - TRIP_STRIP_SPRITE]);
}

/* Tiles are queued as soon as a chunk covers a column, also in the run-start hold while the course is not ready (a full ring in one
 * frame would overflow the vram queue and stall a frame); the sprites are shown (SCB3 and SCB4 sent) only when ready. */
void trip_strip_step(const TripGen *g, uint32_t scroll_px, int ready) {
    u32 j0;
    u8 moved = 0, loads = LOADS_PER_FRAME, pending = 0;
    u8 same;
    if (!g) { if (g_on) { hide_all(); g_on = 0; } g_scan.valid = 0; return; }
    g_on = 1;
    if (!ready && g_vis) hide_all();
    j0 = scroll_px >> 4;
    if (trip_view_strip_advance(&g_ring, j0)) hide_sprites();
    same = g_scan.valid && g->head == g_scan.head && g->count == g_scan.count && g->made == g_scan.made;
    for (int k = 0; k < COLS; k++) {
        u8 s = (u8)trip_view_strip_slot(&g_ring, k);
        u32 j = j0 + (u32)k;
        int sx = trip_view_screen_x(j << 4, scroll_px);
        int on = sx > -16 && sx < TRIP_VIEW_SCREEN_W;
        /* same chunks as the last full scan and the slot already holds this column: the lookup would answer "covered" again */
        const TripChunk *ch = (on && !(same && g_key[s] == j + 1)) ? trip_view_strip_chunk(g, j, 1) : 0;
        u32 key = (ch || (on && same && g_key[s] == j + 1)) ? j + 1 : 0;
        if (key != g_key[s]) {
            if (key && !loads) { /* over the frame budget: the slot stays hidden until a later frame loads it */
                pending = 1; g_scb3[s] = g_scb3[COLS + s] = 0; g_key[s] = 0; g_x[s] = CAMERA_COL_HIDDEN;
                if (g_vis) { gfx_word((u16)(ADDR_SCB3 + TRIP_STRIP_SPRITE + s), 0); gfx_word((u16)(ADDR_SCB3 + TRIP_STRIP_SPRITE + COLS + s), 0); }
                continue;
            }
            if (key) { load(s, 0, j, ch); load(s, 1, j, ch); loads--; }
            else {
                g_scb3[s] = g_scb3[COLS + s] = 0;
                if (g_vis) { gfx_word((u16)(ADDR_SCB3 + TRIP_STRIP_SPRITE + s), 0); gfx_word((u16)(ADDR_SCB3 + TRIP_STRIP_SPRITE + COLS + s), 0); }
            }
            g_key[s] = key;
        }
        if (!key) { g_x[s] = CAMERA_COL_HIDDEN; continue; }
        if (sx != g_x[s]) { g_scb4[s] = g_scb4[COLS + s] = gfx_scb4_word(sx); g_x[s] = (s16)sx; moved = 1; }
    }
    g_scan.head = g->head; g_scan.count = g->count; g_scan.made = g->made; g_scan.valid = !pending;
    if (ready && !g_vis && !pending) { /* every column in view is loaded: show them */
        g_vis = 1; moved = 1;
        gfx_scb_run((u16)(ADDR_SCB3 + TRIP_STRIP_SPRITE), 1, g_scb3, ALL);
    }
    if (g_vis && moved) gfx_scb_run((u16)(ADDR_SCB4 + TRIP_STRIP_SPRITE), 1, g_scb4, ALL);
    g_trip_strip_draws += (u16)(ready != 0);
}
