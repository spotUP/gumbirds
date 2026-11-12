#include "hazard.h"
#include "gen/tripstrip_tables.h"
#include "gfx.h"
#include "sprite_slots.h"
#include "vram_layout.h"
#include "island.h"
#include "core/camera.h"

_Static_assert(HAZARD_COUNT == 2 * HAZARD_STRIP_COLS, "hazard slots: two banks of one strip");
_Static_assert(HAZARD_TILE_COUNT % 8 == 0, "hazard tiles come in groups of 8");

static const u8 k_variants[HAZARD_KINDS] = HAZARD_TABLE_VARIANTS;
static const u8 k_step_frames[HAZARD_KINDS] = HAZARD_TABLE_STEP_FRAMES;
static const u8 k_first_anim[HAZARD_KINDS] = HAZARD_TABLE_FIRST_ANIM;

static s16 g_col_x[HAZARD_STRIP_COLS]; /* last x sent per column (both banks), or CAMERA_COL_HIDDEN before the first place() */
volatile u8 g_hazard_kind = 0xFF;
volatile u16 g_hazard_matches;
static u16 g_round;   /* round of the running game, 0 for the first: picks the kind (hazard_kind_for_round) */
static u8 g_restart;  /* a new round: hide the strip and start the next kind in the same step */
static int g_placed_cam = -1; /* camera the columns were last placed for: place() is a pure function of it (-1: unknown) */
static u8 g_running;
static u16 g_tiles[2][HAZARD_STRIP_COLS * HAZARD_STRIP_ROWS];

#define BANK_SPRITE(b) ((u16)(HAZARD_SPRITE + (b) * HAZARD_STRIP_COLS))

void hazard_load_palettes(void) {
    for (u8 p = 0; p < HAZARD_PALETTE_COUNT; p++)
        for (u8 i = 0; i < 16; i++) gfx_pal((u16)((HAZARD_PAL_SLOT + p) * 16 + i), hazard_palettes[p][i]);
}

static const u16 k_hidden[HAZARD_COUNT]; /* SCB3 height 0 hides a column */

/* The flush's bank swap writes the SCB3 show words directly, so the queue shadow does not know them: forget the 48 words and
 * send them as one run (22 + 48 * 4 us in the flush, about 7 lines of logic). One word op per column, twice on a round restart
 * (here and in start), was 96 ops and about 105 lines of logic: the restart frame ran past vblank start and the flush was
 * skipped (thoughts/spot/2026-11-12-test-scroll-diagnosis.md). */
static void hide_banks(void) {
    gfx_swap_disarm();
    gfx_scb_forget((u16)(ADDR_SCB3 + HAZARD_SPRITE), HAZARD_COUNT);
    gfx_scb_run((u16)(ADDR_SCB3 + HAZARD_SPRITE), 1, k_hidden, HAZARD_COUNT);
}

void hazard_init(void) {
    hazard_load_palettes();
    hide_banks();
    g_hazard_kind = 0xFF;
    g_running = 0;
}

/* Each column sits on the ring at camera_parked_column_x; both banks share the x. Hidden columns are parked at x 320, not
 * hidden by height 0: the bank swap writes the show word to every column of the shown bank. gfx_word drops a word equal to
 * its shadow, but g_col_x skips even the call: a still camera writes nothing. */
static void place(int cam_px) {
    static u16 words[HAZARD_STRIP_COLS];
    u8 moved = 0;
    if (cam_px == g_placed_cam) return;
    g_placed_cam = cam_px;
    int sx0 = camera_screen_x(0, cam_px, 16); /* the one camera dependent value; column c is sx0 + 16 c, one wrap test (camera_strip_parked_x) */
    for (u8 c = 0; c < HAZARD_STRIP_COLS; c++, sx0 += 16) {
        int sx = camera_strip_parked_x(sx0);
        if (sx != g_col_x[c]) { g_col_x[c] = (s16)sx; moved = 1; }
        words[c] = gfx_scb4_word(sx);
    }
    /* One strided run per bank (the columns are adjacent SCB4 words): the queue dedupes against its shadow and sends the span
     * first..last changed as one op, 4 us a word instead of 15 us (queue overflow with one op per word, ring run M). */
    if (moved)
        for (u8 b = 0; b < 2; b++) gfx_scb_run((u16)(ADDR_SCB4 + BANK_SPRITE(b)), 1, words, HAZARD_STRIP_COLS);
}

static void start(int cam_px) {
    u8 kind = hazard_kind_now(); /* the strip is hidden here, so this is the kind of the next match */
    u8 nv = k_variants[kind];
    u16 attr = 0;
    for (u8 b = 0; b < 2; b++) {
        for (u8 c = 0; c < HAZARD_STRIP_COLS; c++) {
            u8 anim = (u8)(k_first_anim[kind] + 2 * ((c / 4) % nv) + b);
            const HazardFrame *f = &hazard_frames[hazard_anims[anim].first_frame];
            /* the first frame's tile of each cell is the base of the cell's run of 8 consecutive frames */
            for (u8 r = 0; r < HAZARD_STRIP_ROWS; r++)
                g_tiles[b][c * HAZARD_STRIP_ROWS + r] = hazard_tile_index[f->tile_offset + (c % 4) * HAZARD_STRIP_ROWS + r];
            attr = (u16)(((HAZARD_PAL_SLOT + f->palette) << 8) | 0x08); /* bit 3: 8-frame auto-animation */
        }
        gfx_sprite_strips(BANK_SPRITE(b), HAZARD_STRIP_COLS, HAZARD_STRIP_ROWS, g_tiles[b], HAZARD_TILE_BASE, attr);
        gfx_sprite_unchained(BANK_SPRITE(b), HAZARD_STRIP_COLS);
        gfx_scb_run((u16)(ADDR_SCB3 + BANK_SPRITE(b)), 1, k_hidden, HAZARD_STRIP_COLS); /* deduped: hide_banks sent them since the last swap */
    }
    for (u8 c = 0; c < HAZARD_STRIP_COLS; c++) g_col_x[c] = CAMERA_COL_HIDDEN;
    g_placed_cam = -1;
    place(cam_px);
    gfx_autoanim_speed(k_step_frames[kind]);
    gfx_swap_arm(BANK_SPRITE(0), BANK_SPRITE(1), HAZARD_STRIP_COLS, gfx_scb3_word(HAZARD_STRIP_ROWS, HAZARD_STRIP_TOP_Y));
    g_hazard_kind = kind;
    g_hazard_matches++;
}

u8 hazard_kind_now(void) { return g_hazard_kind != 0xFF ? g_hazard_kind : hazard_kind_for_round(g_round); }

static u8 g_trip_anim;
void hazard_trip_anim(u8 trip) {
    if (trip && !g_trip_anim) { gfx_autoanim_speed(TRIPSTRIP_STEP_TICKS); g_trip_anim = 1; }
    else if (!trip && g_trip_anim) { island_autoanim_baseline(); g_trip_anim = 0; }
}

void hazard_game_restart(void) { g_round = 0; g_restart = 0; }
void hazard_round_restart(void) { g_round++; g_restart = 1; }

void hazard_step(u8 match_running, int cam_px) {
    if (g_restart) {
        g_restart = 0;
        if (g_running) { hide_banks(); g_hazard_kind = 0xFF; g_running = 0; }
    }
    if (match_running && !g_running) start(cam_px);
    else if (match_running) place(cam_px);
    else if (!match_running && g_running) {
        hide_banks();
        island_autoanim_baseline(); /* the islands animate all match long: the counter returns to their speed */
        g_hazard_kind = 0xFF;
    }
    g_running = match_running;
}
