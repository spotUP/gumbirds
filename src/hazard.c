#include "hazard.h"
#include "gfx.h"
#include "sprite_slots.h"
#include "vram_layout.h"
#include "bg_stars.h"

_Static_assert(HAZARD_COUNT == 2 * HAZARD_STRIP_COLS, "hazard slots: two banks of one strip");
_Static_assert(HAZARD_TILE_COUNT % 8 == 0, "hazard tiles come in groups of 8");

static const u8 k_variants[HAZARD_KINDS] = HAZARD_TABLE_VARIANTS;
static const u8 k_step_frames[HAZARD_KINDS] = HAZARD_TABLE_STEP_FRAMES;
static const u8 k_first_anim[HAZARD_KINDS] = HAZARD_TABLE_FIRST_ANIM;

volatile u8 g_hazard_kind = 0xFF;
volatile u16 g_hazard_matches;
static u8 g_running;
static u16 g_tiles[2][HAZARD_STRIP_COLS * HAZARD_STRIP_ROWS];

#define BANK_SPRITE(b) ((u16)(HAZARD_SPRITE + (b) * HAZARD_STRIP_COLS))

void hazard_load_palettes(void) {
    for (u8 p = 0; p < HAZARD_PALETTE_COUNT; p++)
        for (u8 i = 0; i < 16; i++) gfx_pal((u16)((HAZARD_PAL_SLOT + p) * 16 + i), hazard_palettes[p][i]);
}

static void hide_banks(void) {
    gfx_swap_disarm();
    gfx_word_push((u16)(ADDR_SCB3 + BANK_SPRITE(0)), 0); /* height 0 hides the head and the sticky columns after it */
    gfx_word_push((u16)(ADDR_SCB3 + BANK_SPRITE(1)), 0);
}

void hazard_init(void) {
    hazard_load_palettes();
    hide_banks();
    g_hazard_kind = 0xFF;
    g_running = 0;
}

static void start(void) {
    u8 kind = hazard_kind_for_match(g_hazard_matches);
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
        gfx_sprite_chain(BANK_SPRITE(b), HAZARD_STRIP_COLS);
        gfx_word((u16)(ADDR_SCB4 + BANK_SPRITE(b)), gfx_scb4_word(0));
        gfx_word_push((u16)(ADDR_SCB3 + BANK_SPRITE(b)), 0);
    }
    gfx_autoanim_speed(k_step_frames[kind]);
    gfx_swap_arm(BANK_SPRITE(0), BANK_SPRITE(1), gfx_scb3_word(HAZARD_STRIP_ROWS, HAZARD_STRIP_Y));
    g_hazard_kind = kind;
    g_hazard_matches++;
}

void hazard_step(u8 match_running) {
    if (match_running && !g_running) start();
    else if (!match_running && g_running) {
        hide_banks();
        gfx_autoanim_speed(BG_STAR_STEP_FRAMES); /* the stars have the counter to themselves again */
        g_hazard_kind = 0xFF;
    }
    g_running = match_running;
}
