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
static u8 g_next = HZ_WATER; /* kind of the next strip: main.c passes it from world_hazard (src/core/world.h) */
static u8 g_restart;  /* a new round: hide the strip and start the next kind in the same step */
static int g_placed_cam = -1; /* camera the columns were last placed for: place() is a pure function of it (-1: unknown) */
static u8 g_running;

#define BANK_SPRITE(b) ((u16)(HAZARD_SPRITE + (b) * HAZARD_STRIP_COLS))

void hazard_load_palettes(void) {
    for (u8 p = 0; p < HAZARD_PALETTE_COUNT; p++)
        for (u8 i = 0; i < 16; i++) gfx_pal((u16)((HAZARD_PAL_SLOT + p) * 16 + i), hazard_palettes[p][i]);
}

static const u16 k_hidden[HAZARD_COUNT]; /* SCB3 height 0 hides a column */

/* Banks of kind g_pre_kind already loaded (hidden) by hazard_preload; start() loads only the rest. */
static u8 g_pre_kind = 0xFF, g_pre_banks;

/* The flush's bank swap writes the SCB3 show words directly, so the queue shadow does not know them. They go out as one run,
 * not one word op per column (96 ops on a round restart were about 105 lines of logic and skipped the flush,
 * thoughts/spot/2026-11-12-test-scroll-diagnosis.md). Only the shown bank's 24 words differ from the shadow: the swap writes the show word there and 0 (the shadow value) to the
 * other bank, and before the first swap both banks hold 0. So forget and send just that bank (half the words of the round
 * restart's hide, thoughts/spot/reports/vblank-demo.md Part 5). The other bank's words are deduped or, when unknown, sent. */
static void hide_banks(void) {
    gfx_swap_disarm();
    gfx_scb_forget((u16)(ADDR_SCB3 + BANK_SPRITE(gfx_swap_shown())), HAZARD_STRIP_COLS);
    gfx_scb_run((u16)(ADDR_SCB3 + HAZARD_SPRITE), 1, k_hidden, HAZARD_COUNT);
}

void hazard_init(void) {
    hazard_load_palettes();
    gfx_scb_forget((u16)(ADDR_SCB3 + HAZARD_SPRITE), HAZARD_COUNT); /* VRAM may be reset: both banks unknown */
    hide_banks();
    g_hazard_kind = 0xFF;
    g_running = 0;
    g_pre_kind = 0xFF; /* a BIOS return may have reset VRAM: no preloaded bank is trusted */
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

/* The tiles of one bank (SCB1 and the hidden size words): the heavy part of a strip start, about 26 raster lines a bank (MAME). */
/* One variant per group of 4 columns, cycling through nv: the group's 4 x ROWS tiles are contiguous in the frame's run of
 * hazard_tile_index, so each group is queued straight from ROM (no copy). The variant is a counter, not (c / 4) % nv: that `%` on
 * an int is a libgcc __modsi3 call per column, a large part of the ~38 lines a bank cost on the demo rematch restart
 * (thoughts/spot/reports/vblank-demo.md, Parts 3 and 4). */
_Static_assert(HAZARD_STRIP_COLS % 4 == 0, "hazard variants come in groups of 4 columns");
static void load_bank(u8 kind, u8 b) {
    u8 nv = k_variants[kind], v = 0;
    const HazardFrame *f[HAZARD_STRIP_COLS / 4];
    for (u8 g = 0; g < HAZARD_STRIP_COLS / 4; g++) {
        f[g] = &hazard_frames[hazard_anims[k_first_anim[kind] + 2 * v + b].first_frame];
        if (++v == nv) v = 0;
    }
    u16 attr = (u16)(((HAZARD_PAL_SLOT + f[HAZARD_STRIP_COLS / 4 - 1]->palette) << 8) | 0x08); /* bit 3: 8-frame auto-animation; the last column's palette */
    /* the first frame's tile of each cell is the base of the cell's run of 8 consecutive frames */
    for (u8 g = 0; g < HAZARD_STRIP_COLS / 4; g++)
        gfx_sprite_strips((u16)(BANK_SPRITE(b) + 4 * g), 4, HAZARD_STRIP_ROWS, &hazard_tile_index[f[g]->tile_offset], HAZARD_TILE_BASE, attr);
    gfx_sprite_unchained(BANK_SPRITE(b), HAZARD_STRIP_COLS);
    gfx_scb_run((u16)(ADDR_SCB3 + BANK_SPRITE(b)), 1, k_hidden, HAZARD_STRIP_COLS); /* deduped: hide_banks sent them since the last swap */
}

void hazard_preload(void) {
    u8 kind = hazard_kind_now();
    if (g_running || g_restart) return;
    if (kind != g_pre_kind) { g_pre_kind = kind; g_pre_banks = 0; }
    if (g_pre_banks < 2) load_bank(kind, g_pre_banks++);
}

u8 hazard_preloaded(void) { return g_running || (g_pre_kind == hazard_kind_now() && g_pre_banks == 2); }

static void start(int cam_px) {
    u8 kind = hazard_kind_now(); /* the strip is hidden here, so this is the kind of the next match */
    for (u8 b = (kind == g_pre_kind) ? g_pre_banks : 0; b < 2; b++) load_bank(kind, b);
    g_pre_banks = 2; /* both banks of this kind now sit in VRAM (only hazard.c writes these sprites): a restart of the same kind, such as CLEAR to the bonus stage, loads nothing */
    g_pre_kind = kind;
    for (u8 c = 0; c < HAZARD_STRIP_COLS; c++) g_col_x[c] = CAMERA_COL_HIDDEN;
    g_placed_cam = -1;
    place(cam_px);
    gfx_autoanim_speed(k_step_frames[kind]);
    gfx_swap_arm(BANK_SPRITE(0), BANK_SPRITE(1), HAZARD_STRIP_COLS, gfx_scb3_word(HAZARD_STRIP_ROWS, HAZARD_STRIP_TOP_Y));
    g_hazard_kind = kind;
    g_hazard_matches++;
}

u8 hazard_kind_now(void) { return g_hazard_kind != 0xFF ? g_hazard_kind : g_next; }

static u8 g_trip_anim;
void hazard_trip_anim(u8 trip) {
    if (trip && !g_trip_anim) { gfx_autoanim_speed(TRIPSTRIP_STEP_TICKS); g_trip_anim = 1; }
    else if (!trip && g_trip_anim) { island_autoanim_baseline(); g_trip_anim = 0; }
}

u8 hazard_owns_anim(void) { return g_hazard_kind != 0xFF || g_trip_anim; }

void hazard_game_restart(u8 kind) { g_next = kind; g_restart = 0; }
void hazard_round_restart(u8 kind) { g_next = kind; g_restart = 1; }

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
