#include "trip_pickup.h"
#include "gfx.h"
#include "sprite_slots.h"
#include "vram_layout.h"
#include "core/camera.h"
#include "core/trip_view.h"
#include "core/trip_pickup_fx.h"
#include "gen/trippickup_tables.h"

#define SLOTS TRIP_GEN_RING
_Static_assert(TRIP_PICKUP_COUNT == SLOTS * TRIP_VIEW_PICKUP_COLS, "trip pickup sprite slots are not 2 per ring slot");
_Static_assert(TRIP_PICKUP_SPRITE + TRIP_PICKUP_COUNT <= SPRITE_SLOT_END, "trip pickup sprites exceed the slot table");
_Static_assert(TRIPPICKUP_PICKUP_IDLE_FRAMES == TRIP_VIEW_PICKUP_FRAMES, "pickup idle frame count differs from the view maths");
_Static_assert(TRIPPICKUP_PICKUP_IDLE_TICKS == 4, "pickup idle animation speed is 4 steps per frame in the view maths");
_Static_assert(TRIPPICKUP_PICKUP_COLLECT_FRAMES == TRIP_VIEW_COLLECT_FRAMES, "pickup collect frame count differs from the view maths");
_Static_assert(TRIPPICKUP_PICKUP_COLLECT_TICKS == (1 << TRIP_PICKUP_FX_SHIFT), "pickup collect animation speed is 4 steps per frame in the core");
_Static_assert(TRIPPICKUP_PICKUP_IDLE_FRAMES == 16 && TRIPPICKUP_ANIM_PICKUP_COLLECT == 1, "pickup sheet order: idle then collect");
_Static_assert(TRIPPICKUP_MAX_COLUMNS == TRIP_VIEW_PICKUP_COLS, "pickup frame width differs from the view maths");

volatile u16 g_trip_pickup_draws;
volatile u16 g_trip_pickup_loads;
static u8 g_on;
static TripPickupFx g_fx;   /* collect effect state (core) */
static u32 g_key[SLOTS];   /* chunk wx + 1 shown in the slot, 0 = hidden */
static s8 g_frame[SLOTS];  /* frame loaded in the slot: idle 0..15, collect 16 + frame, -1 = none */
static s16 g_x[SLOTS];     /* last left sent, or CAMERA_COL_HIDDEN */
static u16 g_pairs[SLOTS][TRIP_VIEW_PICKUP_COLS][4]; /* {tile, attribute} x 2 rows per column; the queue keeps the pointer until the flush */

void trip_pickup_load_palettes(void) {
    for (u8 i = 0; i < 16; i++) gfx_pal((u16)(TRIPPICKUP_PAL_SLOT * 16 + i), trippickup_palettes[0][i]);
}

static void hide_slot(int r) {
    if (g_key[r]) for (int c = 0; c < TRIP_VIEW_PICKUP_COLS; c++) gfx_word((u16)(ADDR_SCB3 + TRIP_PICKUP_SPRITE + r * 2 + c), 0);
    g_key[r] = 0; g_frame[r] = -1; g_x[r] = CAMERA_COL_HIDDEN;
}

static void hide_all(void) {
    for (int r = 0; r < SLOTS; r++) hide_slot(r);
}

/* Queue the tiles of one frame of animation anim into the two sprites of ring slot r, with the sprite top. */
static void load_frame(int r, int anim, int frame, int top) {
    const TrippickupFrame *f = &trippickup_frames[trippickup_anims[anim].first_frame + frame];
    for (int c = 0; c < TRIP_VIEW_PICKUP_COLS; c++) {
        u16 *p = g_pairs[r][c];
        u16 sprite = (u16)(TRIP_PICKUP_SPRITE + r * 2 + c);
        for (int row = 0; row < 2; row++) {
            p[row * 2] = trippickup_tile_index[f->tile_offset + c * 2 + row];
            p[row * 2 + 1] = (u16)(TRIPPICKUP_PAL_SLOT << 8);
        }
        gfx_strip_attr(sprite, p, TRIPPICKUP_TILE_BASE, 2);
        gfx_word((u16)(ADDR_SCB3 + sprite), gfx_scb3_word(2, top));
    }
    g_trip_pickup_loads++;
}

void trip_pickup_step(const TripGen *g, uint32_t scroll_px, uint32_t steps, int ready) {
    int frame = trip_view_pickup_frame(steps);
    if (!g_on) {
        gfx_sprite_unchained(TRIP_PICKUP_SPRITE, TRIP_PICKUP_COUNT);
        for (int r = 0; r < SLOTS; r++) { g_key[r] = 1; g_frame[r] = -1; }
        hide_all(); trip_pickup_fx_init(&g_fx); g_on = 1;
    }
    trip_pickup_fx_update(&g_fx, g, steps, g && ready);
    if (!g || !ready) { hide_all(); return; }
    for (int r = 0; r < SLOTS; r++) {
        const TripChunk *ch = trip_view_ring_chunk(g, r, 1);
        int fx = trip_pickup_fx_frame(&g_fx, r, steps);
        int left = fx >= 0 ? trip_pickup_fx_left(&g_fx, r, scroll_px) : CAMERA_COL_HIDDEN;
        int shown = fx >= 0 ? 16 + fx : frame;   /* what the slot should show: collect frames first */
        u32 key = ch ? ch->wx + 1 : 0;
        if (left == CAMERA_COL_HIDDEN) {
            shown = frame;
            left = ch ? trip_view_pickup_left(ch, scroll_px) : CAMERA_COL_HIDDEN;
            fx = -1;
        }
        if (left == CAMERA_COL_HIDDEN) { hide_slot(r); continue; }
        if (key != g_key[r] || shown != g_frame[r]) {
            if (fx >= 0) load_frame(r, TRIPPICKUP_ANIM_PICKUP_COLLECT, fx, trip_pickup_fx_top(&g_fx, r));
            else load_frame(r, TRIPPICKUP_ANIM_PICKUP_IDLE, frame, trip_view_pickup_top(ch) + trip_view_pickup_bob(frame));
            g_key[r] = key; g_frame[r] = (s8)shown; g_x[r] = CAMERA_COL_HIDDEN;
        }
        if (left != g_x[r]) {
            for (int c = 0; c < TRIP_VIEW_PICKUP_COLS; c++)
                gfx_word((u16)(ADDR_SCB4 + TRIP_PICKUP_SPRITE + r * 2 + c), gfx_scb4_word(left + (c << 4)));
            g_x[r] = (s16)left;
        }
        g_trip_pickup_draws++;
    }
}
