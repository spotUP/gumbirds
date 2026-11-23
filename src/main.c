/*
 * main.c - Neo Geo glue for Gumbirds: vblank loop, joypad, backup RAM, fix-layer drawing.
 * All game logic lives in src/core (host tested). Nothing here decides gameplay.
 */
#include <string.h>
#include <ngdevkit/neogeo.h>
#include "core/fastdiv.h"
#include <ngdevkit/ng-fix.h>
#include <ngdevkit/ng-video.h>
#include <ngdevkit/bios-ram.h>
#include "core/stage.h"
#include "core/world.h"
#include "core/camera.h"
#include "core/bg_scroll.h"
#include "core/flier.h"
#include "core/flow.h"
#include "core/banner.h"
#include "core/result_view.h"
#include "gen/result_scene.h"
#include "core/obstacle_view.h"
#include "core/obj_pool.h"
#include "core/flier_view.h"
#include "core/trip_view.h"
#include "gen/triphaz_tables.h"
#include "gen/tripmeter.h"
#include "gen/attract_icons.h"
#include "core/attract_overlay.h"
#include "gen/arcade_sprites.h"
#include "gen/arcade_tables.h"
#include "core/arc_view.h"
#include "gen/trippickup_tables.h"
#include "gen/tosspose_tables.h"
#include "gen/gumbubble_tables.h"
#include "gen/gumleak_tables.h"
#include "gen/countdown_tables.h"
#include "gen/rulecard_tiles.h"
#include "gen/flingmeter_tiles.h"
#include "gen/inputprompt_tiles.h"
#include "core/input_prompt.h"
#include "gen/rain_tiles.h"
#include "core/rain.h"
#include "gfx.h"
#include "sprite_slots.h"
#include "vram_layout.h"
#include "bg.h"
#include "hazard.h"
#include "island.h"
#include "trip_strip.h"
#include "fling_field.h"
#include "poop_walkway.h"
#include "stadium_hw.h"
#include "gum.h"
#include "core/gum_view.h"
#include "splash.h"
#include "core/splash_view.h"
#include "logo.h"
#include "trip_pickup.h"
#include "sound.h"
#include "core/sound_events.h"
#include "snd_commands.h"

/* Palette 0 = white text, palette 1 = yellow (highlight). Entry 0 of a palette is transparent; the backdrop is the last palette RAM entry (bg.c). */
#define PAL_TEXT FIXFONT_PAL_WHITE
#define PAL_HIGH FIXFONT_PAL_GOLD

/* Hiscore image in battery backed RAM (.bss.bram at 0x100000). */
u8 _backup_ram g_hiscore_image[SCORE_IMAGE_SIZE];

/* RAM sentinel for the headless test: counts main loop frames. Address in the ELF map. */
volatile u32 g_frame_counter;

/* RAM sentinel for the headless reachability test (make test-reach): counts backup RAM image writes. */
volatile u32 g_hiscore_saves;

/* RAM sentinel for make test-score: draw_table calls per GameMode (0 arena, 1 Gum Trip), proves each table was drawn. */
volatile u32 g_table_mode_draws[2];

/* RAM sentinel for make test-reach: the seconds value the name entry countdown drew last (0xff = never drawn). */
volatile u8 g_name_seconds_shown = 0xff;

static Flow g_flow;

/*
 * The fliers are the
 * Sootling set (assets/flier/sootling_sheet.png), drawn below. Tile bases and palette slots come from vram_layout.h,
 * sprite slots from sprite_slots.h. A multi-column frame is several hardware sprites: the first has position and
 * height, the others are sticky (SCB3 bit 6) and follow it 16 px apart.
 * Register sequence copied from ngdevkit-examples 03-sprite-animation/main.c:54-84.
 * Y register = 496 - screen top (wraps at 512), X register = screen x.
 */
/* SOOT_COLUMNS, SOOT_SPRITE_W and SOOT_BOX_DX live in vram_layout.h (shared with tests/mame/camera_probe.c). A Sootling frame
 * is 2 tile columns wide and 2 tiles high (24 x 32 art centred in a 32 x 32 sprite): the 4 px hit box is art columns 10..13,
 * sprite columns 14..17, so the sprite left is the flier centre x - FLIER_HALF_W - SOOT_BOX_DX. */
#define SOOT_FLIP 1     /* SCB1 attribute bit 0: horizontal flip; a mirrored frame also draws its columns in reverse order (soot_strips) */
_Static_assert(SOOTLING_FRAME_COUNT == 2 * SOOTLING_FRAMES, "sheet: SOOTLING_FRAMES frames per palette (player, computer)");
_Static_assert(SOOT_COLUMNS == SOOTLING_MAX_COLUMNS && SOOT_SPRITE_W >= SOOTLING_ART_W && SOOT_SPRITE_W - SOOTLING_ART_W < 16, "Sootling frames are 2 columns wide, art padded to whole tiles");
_Static_assert(SOOTLING_BOX_LAST_COL - SOOTLING_BOX_FIRST_COL + 1 == 2 * FLIER_HALF_W, "art hit box columns must equal the 4 px gameplay box");
_Static_assert(SOOTLING_BOX_FIRST_COL + 2 * FLIER_HALF_W + SOOTLING_BOX_FIRST_COL == SOOTLING_ART_W, "art is centred on the hit box (a mirrored frame keeps the box)");
_Static_assert(SOOTLING_ART_H == 32 && SOOTLING_FEET_ROW == SOOTLING_ART_H - 1, "frame is 32 px tall with the feet on its last row");
_Static_assert(SOOTLING_ART_W == 24 && SOOTLING_ART_H == 32, "small Sootling sheet is 24 x 32 (stale sheet?)");
_Static_assert(FLIER_GUM_BOTTOM < FLIER_GUM_TOP && FLIER_GUM_TOP < SOOTLING_ART_H, "gum box lies inside the art rows above the feet");
_Static_assert(FLIER_FEET_H < FLIER_GUM_BOTTOM && 2 * FLIER_FEET_HALF_W <= SOOTLING_ART_W, "feet box fits in the art");
_Static_assert(FLIER_GUM_HALF_W1 < FLIER_GUM_HALF_W2 && FLIER_GUM_HALF_W2 <= SOOTLING_ART_W / 2, "gum boxes fit the art width");
_Static_assert(2 * FLIER_BODY_HALF_W <= SOOTLING_ART_W && FLIER_BODY_HALF_W < FLIER_GUM_HALF_W2, "body box fits the art and the gum rim is wider");
_Static_assert(FLIER_BODY_TOP == FLIER_GUM_BOTTOM && FLIER_PAIR_LEVEL_PX > 0 && FLIER_PAIR_LEVEL_PX < FLIER_GUM_TOP - FLIER_GUM_BOTTOM, "body top meets the gum bottom; the level band is smaller than the gum height");
_Static_assert((FLIER_HALF_H16_BALLOON >> 15) <= SOOTLING_ART_H, "body box (2 x half height) fits the frame");

/* Clip table and per frame ticks come from frames.json through the build (sootling_tables.h). */
static const u8 k_clip_first[SOOTLING_CLIP_COUNT] = SOOTLING_TABLE_CLIP_FIRST;
static const u8 k_clip_count[SOOTLING_CLIP_COUNT] = SOOTLING_TABLE_CLIP_COUNT;
static const u8 k_clip_loop[SOOTLING_CLIP_COUNT] = SOOTLING_TABLE_CLIP_LOOP;
static const u8 k_frame_ticks[SOOTLING_FRAMES] = SOOTLING_TABLE_FRAME_TICKS;
static const u8 k_frame_sway[SOOTLING_FRAMES] = SOOTLING_TABLE_SWAY;
static const FlierClips k_clips = {
    k_clip_first, k_clip_count, k_clip_loop, k_frame_ticks,
    SOOTLING_CLIP_FLAP, SOOTLING_CLIP_FLY, SOOTLING_CLIP_SETTLE, SOOTLING_CLIP_IDLE_FRONT, SOOTLING_CLIP_PUMP,
    SOOTLING_CLIP_INFLATE, SOOTLING_CLIP_FALL, SOOTLING_CLIP_POP2, SOOTLING_CLIP_POP1,
    SOOTLING_CLIP_WALK, SOOTLING_CLIP_LAND, SOOTLING_CLIP_BREATHE,
    k_frame_sway, SOOTLING_CLIP_FLAP_R, SOOTLING_CLIP_FLAP_L, SOOTLING_CLIP_BREATHE_FRONT
};
static FlierAnim g_hero_anim[HUMANS]; /* per human: [1] steps the P2 body drawn from pool objects P2_OBJ_BODY / P2_OBJ_CHUTE */

/* Test sentinels (tests/mame/flier_check.lua): first tile number last written to the sprite registers for the player
 * and for a computer flier (0 until drawn, player 0 again while hidden), and computer draws so far. g_soot_range holds
 * {first Sootling tile, tile count, palette slot of the player palette, then those three sentinels in that order}. */
volatile u16 g_blink_hidden, g_blink_shown; /* test sentinels: hero frames hidden / drawn while the blink test runs */
volatile u16 g_blink_pool[2]; /* test sentinels: pool flier frames hidden / drawn by the protected blink */
volatile u16 g_soot_range[10] = { SOOT_TILE_BASE, SOOTLING_TILE_COUNT, SOOT_PAL_SLOT, 0, 0, 0, GUM_TILE_BASE, GUM_TILE_COUNT, 0, 0 };
#define g_cpu_gum_tile g_soot_range[8]   /* first tile of the last computer gum bubble placed (pool_show_gum), 0 until drawn */
#define g_cpu_gum_draws g_soot_range[9]  /* computer gum bubbles placed so far */
/* Test hook (tests/mame/flier_check.lua): what hero_show last chose for the player: clip, sheet frame, ticks on that frame. */
volatile u16 g_soot_view[3];
#define g_soot_player_tile g_soot_range[3]
#define g_soot_cpu_tile g_soot_range[4]
#define g_soot_cpu_draws g_soot_range[5]

static void soot_load_palettes(void) {
    for (int p = 0; p < SOOTLING_PALETTE_COUNT; p++)
        for (int i = 0; i < 16; i++)
            gfx_pal((SOOT_PAL_SLOT + p) * 16 + i, sootling_palettes[p][i]);
    for (int i = 0; i < 16; i++) gfx_pal(SOOT_P2_PAL_SLOT * 16 + i, sootling_extra_palettes[0][i]);
    for (int i = 0; i < 16; i++) {   /* Tug Gum: pose palette per seat (the partners take the darker team shade), then the strand */
        gfx_pal(TUGPOSE_PAL_SLOT * 16 + i, tugpose_palettes[0][i]);
        for (int p = 0; p < TUGPOSE_EXTRA_PALETTE_COUNT; p++) gfx_pal((TUGPOSE_PAL_SLOT + 1 + p) * 16 + i, tugpose_extra_palettes[p][i]);
        gfx_pal((TUGPOSE_PAL_SLOT + 4) * 16 + i, tugpose_palettes[1][i]);
    }
    for (int i = 0; i < 16; i++) {   /* Toss Gum: pose palette per seat, then the violet standing body */
        gfx_pal(TOSSPOSE_PAL_SLOT * 16 + i, tosspose_palettes[0][i]);
        for (int p = 0; p < TOSSPOSE_EXTRA_PALETTE_COUNT; p++) gfx_pal((TOSSPOSE_PAL_SLOT + 1 + p) * 16 + i, tosspose_extra_palettes[p][i]);
    }
}

/* Camera x of the frame the view is drawing (game_camera_px): the one value every world object is placed with. Test
 * sentinel for tests/mame/camera_check.lua. 0 outside play. */
volatile u16 g_cam_px; /* wrapped camera x 0..383 (camera_px) */
volatile s32 g_cam_unwrapped; /* camera_unwrapped_px: what the looping background planes are fed (0 outside play) */
/* Test sentinel for the MAME checks: round_end, round_timer, round_start, hero visible (game_flier_visible). */
volatile u16 g_round_end_s[4];
volatile u16 g_banner_calls, g_banner_cells; /* round clear banner draws, for the MAME tests */
/* Round start text on the fix layer: phase drawn (RS_*) and the round number shown, so the cells are written and cleared once. */
static u8 g_rs_drawn = RS_NONE;
static const GgCard *g_card_up;
static u8 g_howto_up; /* PARTY how-to overlay (fix rows HOWTO_ROW..) is on screen */
#define HOWTO_ROW 22
#define MODE_LABEL_ROW 29 /* last visible fix row, left safe column: the credits plate sits at columns 28..37 */
#define BLOW_TEXT_ROW 5
#define BLOW_TEXT_W 30
#define MODE_LABEL_COL 2
#define MODE_LABEL_W 17   /* longest name: RULE OF THE ROUND */
static u32 g_blow_key = 0xFFFFFFFFu; /* Big Blow text on screen (phase, tickets, last attempt); reset with the fix layer */
static u8 g_mode_key = 0xFF; /* mode label on screen: 0 none, else mode + 1 or 8 + party rule */
static u8 g_stage_key = 0xFF; /* arcade HUD stage text: 0 none, 254 bonus, else stage number; 0xFF = not drawn since the last clear */
static u8 g_over_up; /* GAME OVER text drawn since the last clear */
static u8 g_cont_key[HUMANS] = { 0xFF, 0xFF }; /* arcade continue plate per side on the fix layer: 0 none, else 1 + seconds left (+ 0x80 with a credit) */
static u8 g_banner_up; /* the round clear banner is on the fix layer */
#define BANNER_ROWS_PER_FRAME 2
static u8 g_banner_pending; /* rows still to draw: the panel opens a few rows per frame to stay inside vblank */
static int g_banner_last; /* banner frame drawn last */
static u16 g_banner_shadow[BANNER_W * BANNER_H]; /* cell last sent: only changed cells cost vblank time */
/* Result screen (core/result_view.h): the fix layer is redrawn once (RES_FILL_PER_FRAME cells a frame), then one dirty region a frame. */
#define RES_FILL_PER_FRAME 80
static u16 g_res_shadow[RESV_W * RESV_H];
static u8 g_res_up, g_res_col, g_res_row, g_res_pend;
static u8 g_hl_up; /* a highlighted table is on the fix layer outside the table state */
static u16 g_res_filled;
/* Result screen sprites behind the windows of the fix scene (draw_result_fx): setup stage, frames loaded (0xFF none), sky cycle steps. */
static u8 g_resfx_stage, g_resfx_bub[RES_SLOTS], g_resfx_wheel[5], g_resfx_crank, g_resfx_sky, g_resfx_star;
static int g_rs_num;
/* Fix layer cell of the off screen marker last drawn (col 0xFF: none). */
static u8 g_edge_col[HUMANS] = { 0xFF, 0xFF }, g_edge_row[HUMANS];

static u8 g_p2_shown;   /* player 2's body is on screen this frame (pool_sync_p2), drawn or on its dark blink half: its bubble and jet draw */
static struct { u8 drawn, frame, flip; int cx, top; } g_gum_pose[HUMANS];   /* where the player is drawn this frame: the gum bubble sits on it (src/gum.c) */
static u8 g_hero_chute_up; /* the player's parachute sprites are shown */
static void hero_hide(void) {
    g_gum_pose[0].drawn = 0;
    gfx_word(ADDR_SCB3 + HERO_SPRITE, 0); /* height 0 hides the sprite and the sticky ones after it */
    if (g_hero_chute_up) { gfx_word(ADDR_SCB3 + HERO_CHUTE_SPRITE, 0); g_hero_chute_up = 0; }
    g_soot_player_tile = 0;
}

/* Sheet frame of a clip frame: anim 0 is the player palette, anim 1 the computer palette (SOOTLING_ANIM_*). */
static u8 soot_frame(u8 anim, u8 clip_frame) {
    return (u8)(sootling_anims[anim].first_frame + clip_frame);
}

/* Queue the tile columns of a frame. A mirrored frame draws its columns in reverse order (the flip bit mirrors each
 * tile only); one strip per column, from the const table, since the queue keeps the pointers. */
static void soot_strips(u16 slot, const SootlingFrame *f, const u16 *tiles, int flip, u16 attr) {
    for (u8 c = 0; c < SOOT_COLUMNS; c++)
        gfx_sprite_strips((u16)(slot + c), 1, f->tiles_h, tiles + (flip ? SOOT_COLUMNS - 1 - c : c) * f->tiles_h,
                          SOOT_TILE_BASE, attr);
}

/* Dead bodies in front of the spike art: DEAD_BODY_COUNT / DEAD_BODY_COLUMNS bodies, each owned by the hero or by one
 * computer flier. A claimed body is drawn here instead of in its normal slot; releasing hides its sprites. */
#define DEAD_BODIES (DEAD_BODY_COUNT / DEAD_BODY_COLUMNS)
#define DEAD_OWNER_NONE 0xFF
#define DEAD_OWNER_HERO(h) ((u8)(h))
#define DEAD_OWNER_CPU(i) ((u8)(HUMANS + (i)))
_Static_assert(DEAD_BODY_SPRITE == SPRITE_SLOT_END && DEAD_BODY_SPRITE + DEAD_BODY_COUNT <= 381, "dead body slots must end at the 381 hardware sprites");
_Static_assert(DEAD_BODY_COLUMNS == SOOT_COLUMNS, "a dead body holds one Sootling frame");
_Static_assert(SOOTLING_ART_H <= FLIER_ART_H, "the removal rule (FLIER_ART_H) covers the tallest Sootling frame");
static u8 g_dead_owner[DEAD_BODIES] = { DEAD_OWNER_NONE, DEAD_OWNER_NONE };
volatile u16 g_dead_front_mask; /* test sentinel: bit n set while dead body slot n draws a body */

static void dead_hide(int d) {
    for (u8 c = 0; c < DEAD_BODY_COLUMNS; c++) gfx_word((u16)(ADDR_SCB3 + DEAD_BODY_SPRITE + d * DEAD_BODY_COLUMNS + c), 0);
    g_dead_owner[d] = DEAD_OWNER_NONE;
    g_dead_front_mask &= (u16)~(1u << d);
}
static void dead_release(u8 owner) {
    if (!g_dead_front_mask) return; /* no body slot owned (the usual frame): skip the owner scan */
    for (int d = 0; d < DEAD_BODIES; d++) if (g_dead_owner[d] == owner) dead_hide(d);
}
/* Slot index of the owner's body (claimed now if one is free), -1 when none is free: the body then keeps its normal slot. */
static int dead_claim(u8 owner) {
    for (int d = 0; d < DEAD_BODIES; d++) if (g_dead_owner[d] == owner) { g_dead_front_mask |= (u16)(1u << d); return d; }
    for (int d = 0; d < DEAD_BODIES; d++) if (g_dead_owner[d] == DEAD_OWNER_NONE) {
        g_dead_owner[d] = owner; g_dead_front_mask |= (u16)(1u << d); return d;
    }
    return -1;
}
static void dead_release_all(void) {
    for (int d = 0; d < DEAD_BODIES; d++) dead_hide(d);
}

/* Parachute over a flier in state PARACHUTE: 32x32 art, left edge = the body sprite left, top = feet - 46 (anchor -4,-14 over the 24x32 body, 4 px pad). */
static void chute_strips(u16 slot, const ChuteFrame *f, int flip, int pal_slot) {
    const u16 *tiles = &chute_tile_index[f->tile_offset];
    u16 attr = (u16)(pal_slot << 8 | (flip ? SOOT_FLIP : 0));
    for (u8 c = 0; c < f->tiles_w; c++)
        gfx_sprite_strips((u16)(slot + c), 1, f->tiles_h, tiles + (flip ? f->tiles_w - 1 - c : c) * f->tiles_h, CHUTE_TILE_BASE, attr);
}
static void chute_place(u16 slot, u8 anim, u8 n, int flip, int left, int top) {
    const ChuteFrame *f = &chute_frames[chute_anims[anim].first_frame + n];
    chute_strips(slot, f, flip, CHUTE_PAL_SLOT + f->palette);
    gfx_sprite_place(slot, f->tiles_w, f->tiles_h, left, top);
}

/* Toss Gum and Tug Gum seat their birds: screen space, pose cells in place of the body, no arena gum. */
static u8 seated(const Game *g) { return g->gg_toss || g->gg_tug; }
/* Toss Gum pose (tools/make_toss_sheet.py): one 32x32 cell in the body's own two sprite columns, left edge = the body sprite left, top = feet - 32.
 * The birds on the right and front seats (2, 3) face left. Palette = TOSSPOSE_PAL_SLOT + seat. */
static void tosspose_strips(u16 slot, u8 pose, u8 seat) {
    const TossposeFrame *f = &tosspose_frames[pose];
    const u16 *tiles = &tosspose_tile_index[f->tile_offset];
    int flip = seat >= 2;
    u16 attr = (u16)((TOSSPOSE_PAL_SLOT + seat) << 8 | (flip ? SOOT_FLIP : 0));
    for (u8 c = 0; c < f->tiles_w; c++)
        gfx_sprite_strips((u16)(slot + c), 1, f->tiles_h, tiles + (flip ? f->tiles_w - 1 - c : c) * f->tiles_h, TOSSPOSE_TILE_BASE, attr);
}
/* Tug Gum pose (tools/make_tug_sheet.py): the same cell rules as the toss pose. Palette = TUGPOSE_PAL_SLOT + seat. */
static void tugpose_strips(u16 slot, u8 pose, u8 seat) {
    const TugposeFrame *f = &tugpose_frames[pose];
    const u16 *tiles = &tugpose_tile_index[f->tile_offset];
    int flip = seat >= 2;
    u16 attr = (u16)((TUGPOSE_PAL_SLOT + seat) << 8 | (flip ? SOOT_FLIP : 0));
    for (u8 c = 0; c < f->tiles_w; c++)
        gfx_sprite_strips((u16)(slot + c), 1, f->tiles_h, tiles + (flip ? f->tiles_w - 1 - c : c) * f->tiles_h, TUGPOSE_TILE_BASE, attr);
}
_Static_assert(SOOT_COLUMNS == 2, "a toss pose is two columns wide and draws in the body columns");
static const u8 g_toss_ax[GT_POSE_COUNT] = TOSSPOSE_TABLE_ANCHOR_X, g_toss_ay[GT_POSE_COUNT] = TOSSPOSE_TABLE_ANCHOR_Y;
/* Test probe (tests/mame/party_toss_check.lua): the screen wing gum point of each seat's pose cell as drawn, and the knot as drawn (x, y, pose). */
volatile s16 g_toss_wing[GT_SEATS][2], g_toss_knot[3];
static void toss_wing_mark(u8 seat, u8 pose, int left, int top) {
    g_toss_wing[seat][0] = (s16)(left + (seat >= 2 ? 31 - g_toss_ax[pose] : g_toss_ax[pose]));
    g_toss_wing[seat][1] = (s16)(top + g_toss_ay[pose]);
}
/* Pool body code for a flier in Toss Gum: seat << 4 | pose + 1 (low nibble 0 = standing body), 0 outside Toss Gum and for a bird on no seat. */
static u8 toss_pose_code(const Game *g, const Flier *fl) {
    if (g->gg_tug) {   /* bit 6 = Tug Gum cell */
        for (u8 s = 0; s < GTG_SEATS; s++) if (game_tug_flier(g, s) == fl) return (u8)(0x40 | s << 4 | (gg_tug_pose(&g->tug, s) + 1));
        return 0;
    }
    if (!g->gg_toss) return 0;
    for (u8 s = 0; s < GT_SEATS; s++) if (game_toss_flier(g, s) == fl) return (u8)(s << 4 | (gg_toss_pose(&g->toss, s) + 1));
    return 0;
}

static void hero_show(const Game *g, int cam_px) {
    const Flier *fl = &g->hero[0];
    int feet = (int)((fl->y + flier_half_h(fl)) >> 16);
    if (!game_flier_visible(g) || !flier_body_visible(fl) || (feet > SCREEN_H && fl->state < FLIER_FALLING)) { hero_hide(); dead_release(DEAD_OWNER_HERO(0)); return; }
    int flip;
    u8 shown = flier_anim_step(&g_hero_anim[0], fl, &k_clips, &flip);
    if (arc_pump_in_window(&g->hpump[0]) && fl->state == FLIER_ALIVE) shown = flier_pump_frame(&k_clips, arc_pump_progress(&g->hpump[0])); /* landed from a parachute: pump frame */
    g_soot_view[0] = g_hero_anim[0].clip;
    g_soot_view[1] = shown;
    g_soot_view[2] = g_hero_anim[0].tick;
    const SootlingFrame *f = &sootling_frames[soot_frame(SOOTLING_ANIM_PLAYER, shown)];
    const u16 *tiles = &sootling_tile_index[f->tile_offset];
    g_soot_player_tile = (u16)(SOOT_TILE_BASE + tiles[0]);
    int top = feet - f->tiles_h * 16;
    int sx = camera_screen_x((int)(fl->x >> 16) - FLIER_HALF_W - SOOT_BOX_DX, cam_px, SOOT_COLUMNS * 16);
    if (!camera_visible(sx, SOOT_COLUMNS * 16)) { hero_hide(); dead_release(DEAD_OWNER_HERO(0)); return; }
    g_gum_pose[0].frame = shown; g_gum_pose[0].flip = (u8)flip; g_gum_pose[0].cx = sx + SOOT_COLUMNS * 8; g_gum_pose[0].top = top;
    /* Protected blink: the animation above keeps stepping, only the body sprites go dark (a protected flier is never FALLING); the bubble stays. */
    if (!flier_view_visible(fl, g->frame)) { hero_hide(); g_gum_pose[0].drawn = 1; g_soot_player_tile = (u16)(SOOT_TILE_BASE + tiles[0]); g_blink_hidden++; return; }   /* hero_hide clears the tile sentinel; the clip under test keeps it */
    g_blink_shown++;
    int left = sx;
    u16 attr = (u16)(((SOOT_PAL_SLOT + f->palette) << 8) | (flip ? SOOT_FLIP : 0));
    u16 slot = HERO_SPRITE;
    if (g->mode != GAME_MODE_TRIP && flier_body_front(fl)) {
        int d = dead_claim(DEAD_OWNER_HERO(0));
        if (d >= 0) { hero_hide(); slot = (u16)(DEAD_BODY_SPRITE + d * DEAD_BODY_COLUMNS); }
    } else dead_release(DEAD_OWNER_HERO(0));
    g_gum_pose[0].drawn = 1;
    int pose = g->gg_toss ? gg_toss_pose(&g->toss, 0) : g->gg_tug ? gg_tug_pose(&g->tug, 0) : -1;   /* player 1 stands on seat 0 */
    if (pose >= 0) {
        if (g->gg_tug) tugpose_strips(slot, (u8)pose, 0); else tosspose_strips(slot, (u8)pose, 0);
        gfx_sprite_place(slot, SOOT_COLUMNS, 2, left, feet - 32);
        if (!g->gg_tug) toss_wing_mark(0, (u8)pose, left, feet - 32);
    } else {
        soot_strips(slot, f, tiles, flip, attr);
        gfx_sprite_place(slot, SOOT_COLUMNS, f->tiles_h, left, top);
    }
    if (fl->state == FLIER_PARACHUTE) {
        chute_place(HERO_CHUTE_SPRITE, CHUTE_ANIM_PLAYER, (u8)((g->frame / CHUTE_FRAME_TICKS) & 7), flip, left, feet - 46);
        g_hero_chute_up = 1;
    } else if (g_hero_chute_up) { gfx_word(ADDR_SCB3 + HERO_CHUTE_SPRITE, 0); g_hero_chute_up = 0; }
}

/*
 * Obstacle-sheet sprites. Tiles follow the logo tiles in the C-ROM (Makefile cat order), palettes follow the fix-layer
 * palettes. They draw through the object pool (src/core/obj_pool.h): each pool object holds a sprite run (POOL_COLS
 * hardware sprites from POOL_SPRITE_BASE, sprite_slots.h); the animation index of an object is its type. Live users:
 * the computer fliers (pool_sync_cpus) and the pool stress test hook. The arena platforms are the island sprites (src/island.c).
 */
_Static_assert(POOL_SPRITE_COUNT == POOL_SPRITES, "pool sprite range size");
_Static_assert(GUM_SPRITE + GUM_COUNT <= SPLASH_SPRITE && SPLASH_SPRITE + SPLASH_COUNT <= GUM_P2_SPRITE && GUM_P2_SPRITE + GUM_COUNT <= ISLAND_SPRITE, "player 2 gum sprites overlap the splash or the islands");
_Static_assert(ROOST_SPRITE >= HERO_SPRITE + HERO_SPRITE_COUNT && ROOST_SPRITE + ROOST_COUNT <= DEAD_BODY_SPRITE, "roost marker sprites must sit above the pool and the hero, below the dead bodies");
_Static_assert(BG_SPRITE_END <= GUM_SPRITE && GUM_SPRITE + GUM_COUNT <= ISLAND_SPRITE, "gum sprites overlap the background or the islands");
_Static_assert(ISLAND_SPRITE + ISLAND_COUNT <= POOL_SPRITE_BASE, "island sprites overlap the object pool");
/* Player 2 draws from the last two pool objects (body, parachute), claimed in pool_sync_p2; the computer fliers allocate
 * from the low end of the free list and never need more than a body and a parachute each. */
#define P2_OBJ_BODY (POOL_MAX - 2)
#define P2_OBJ_CHUTE (POOL_MAX - 1)
#define CHUTE_ANIM_PLAYER2 CHUTE_ANIM_PLAYER /* same frames as the player, the P2 palette (CHUTE_P2_PAL_SLOT) swaps the colours */
_Static_assert(4 * STAGE_SPAWN_COUNT + HUMANS <= POOL_MAX - 2, "computer fliers plus parachutes, gum bubbles and air jets, plus the player jets, would reach the P2 pool objects");
_Static_assert(GUM_COUNT <= POOL_COLS, "a gum bubble object fits a pool sprite run");
_Static_assert(POOL_SPRITE_BASE + POOL_SPRITE_COUNT <= HERO_SPRITE, "object pool sprites overlap hero");
_Static_assert(HERO_SPRITE + HERO_SPRITE_COUNT <= HAZARD_SPRITE, "hero overlaps hazard sprites");
_Static_assert(SPRITE_SLOT_END <= 381, "sprite slots exceed the 381 hardware sprites");
_Static_assert(OBS_MAX_COLUMNS <= POOL_COLS, "obstacle frame wider than a pool sprite run");
_Static_assert(OBS_ANIM_VENT == OB_VENT && OBS_ANIM_CABLE == OB_CABLE &&
               OBS_ANIM_DRONE == OB_DRONE && OBS_ANIM_BOT == OB_BOT, "obstacle sheet order");

static void obs_load_palettes(void) {
    for (int p = 0; p < OBS_PALETTE_COUNT; p++)
        for (int i = 0; i < 16; i++)
            gfx_pal((OBS_PAL_SLOT + p) * 16 + i, obs_palettes[p][i]);
}

static void island_load_palettes(void) {
    for (int p = 0; p < ISLAND_PALETTE_COUNT; p++)
        for (int i = 0; i < 16; i++) {
            gfx_pal((ISLAND_PAL_SLOT + STAGE_LOOK_ROOF * ISLAND_PALETTE_COUNT + p) * 16 + i, island_palettes[p][i]);
            gfx_pal((ISLAND_PAL_SLOT + STAGE_LOOK_GARDEN * ISLAND_PALETTE_COUNT + p) * 16 + i, island_garden_palettes[p][i]);
            gfx_pal((ISLAND_PAL_SLOT + STAGE_LOOK_DECK * ISLAND_PALETTE_COUNT + p) * 16 + i, island_deck_palettes[p][i]);
        }
}

/* Height 0 and not sticky hides a sprite on its own. */
static void obs_hide_slot(int slot) {
    gfx_word(ADDR_SCB3 + slot, 0);
}

static void text(u8 x, u8 y, u8 pal, const char *s);
/* Gum Games rules card, owner-picked layout A "banner and strip" (thoughts/shared/drafts/2026-11-17-rules-card): the name and goal
 * banner on top, a strip of three control cells at the bottom, and between them the example: a power and an angle bar on the fix
 * layer, a Sootling on a slab in the arcade element slots (the countdown that shares them starts when the card goes).
 * The text comes from flow.c gg_cards. The button and bar tiles take the attract icon palette slot while the card is up: the fix
 * layer reaches palettes 0..15 only, the icons show in the demo only and the card in play only, so one slot serves both. */
#define CARD_BANNER_ROW 3  /* panel rows 3..7 */
#define CARD_STRIP_ROW 20  /* panel rows 20..28 */
#define CARD_BAR_ROW 9     /* power bar; angle bar two rows down, its caret under it */
#define CARD_BAR_COL 10
#define CARD_BAR_CELLS 6
#define CARD_BIRD_X 44     /* example Sootling art, screen px */
#define CARD_BIRD_Y 104
#define CARD_TICKS 16      /* video frames per example frame; the last frame holds CARD_HOLD */
#define CARD_HOLD 42
#define CARD_NONE 0xFF
enum { CARD_PROP_SLAB, CARD_PROP_NEEDLE_20, CARD_PROP_NEEDLE_45, CARD_PROP_GUM, CARD_PROP_DOT };
_Static_assert(RULECARD_FRAME_COUNT == 5, "the rules card sheet holds slab, two needles, gum, dot");
/* step = lit control cell; press / hold = button of cell 0 / 1 down (hold = A locking the swinging angle); power = lit bar cells; caret = angle bar cell or CARD_NONE;
 * bird = Sootling sheet frame (mash 0 / 1, watch 2, aim 16, spit 40); needle = prop or 0; gums = gum trail length */
static const struct { u8 step, press, hold, power, caret, bird, needle, gums; } card_frames[] = {
    {0, 1, 0, 2, CARD_NONE, 0, 0, 0}, {0, 0, 0, 4, CARD_NONE, 1, 0, 0}, {0, 1, 0, 6, CARD_NONE, 0, 0, 0},
    {1, 0, 1, 6, 1, 16, CARD_PROP_NEEDLE_20, 0}, {1, 0, 1, 6, 3, 16, CARD_PROP_NEEDLE_45, 0},
    {2, 0, 0, 6, 3, 40, 0, 3}, {2, 0, 0, 6, 3, 2, 0, 7}};
#define CARD_FRAMES ((u8)(sizeof card_frames / sizeof card_frames[0]))
#define CARD_GUMS 7
static const short card_gum[CARD_GUMS][2] = {{40, 2}, {62, -14}, {86, -26}, {112, -34}, {140, -36}, {168, -32}, {196, -22}}; /* from the bird's corner */
_Static_assert(2 + 3 + 1 + CARD_GUMS <= ARC_ELEM_COUNT, "the rules card example needs more sprites than the arcade element slots");
static u8 g_card_k = CARD_NONE;     /* example frame on the fix layer; reset with the card */
static u8 g_card_scene = CARD_NONE; /* example frame in the sprites */
/* The attract icon palette slot (fix palette 0..15, no spare slot is left) holds one of four palettes at a time: the attract icons, the rules card
 * colours, the power meter pink set, or the meter hot set that flashes at full power. Whoever draws sets it; the fix layer reset restores the icons. */
enum { SLOT_ATTRACT, SLOT_CARD, SLOT_METER, SLOT_HOT };
static u8 g_slot_pal;
static void slot_pal(u8 w) {
    if (w == g_slot_pal) return;
    g_slot_pal = w;
    const u16 *p = w == SLOT_CARD ? rulecard_fix_palette : w == SLOT_METER ? flingmeter_palette : w == SLOT_HOT ? flingmeter_hot_palette : attract_icon_palette;
    for (u8 i = 0; i < 16; i++) gfx_pal((u16)(ATTRACT_PAL_SLOT * 16 + i), p[i]);
}

/* Gum Games power meter (owner pick C, tools/flingmeter_art.py): a two tile tall gum tube of METER_CELLS cells, METER_STEPS counted presses
 * (half a cell each), and for Gum Fling the angle dial. Only the cells whose tile changes are written. */
#define METER_STEPS 32u
#define METER_CELLS 16u
#define METER_COL 12   /* first tube cell; the end caps sit one column outside */
#define METER_ROW 25   /* top tile row of the first tube; the rival tube of Burst Race sits two rows above */
#define METER_NONE 0xFF
#define DIAL_COL 7
#define DIAL_ROW 24
static u8 g_meter_n[2] = { METER_NONE, METER_NONE };   /* steps on screen per tube; METER_NONE = not drawn since the last reset */
static u8 g_dial_i = METER_NONE;                       /* dial needle on screen (flingmeter_dial row) */
static u8 g_meter_tick;

static void meter_put(u8 x, u8 y, u8 id) { gfx_fix_tile(x, y, ATTRACT_PAL_SLOT, id == FLINGMETER_BLANK ? (u16)FIXFONT_BLANK : (u16)(FLINGMETER_FIX_BASE + id)); }
static void meter_plaque(u8 x, u8 y, const uint8_t *t) { for (u8 i = 0; i < 8; i++) meter_put((u8)(x + (i & 3)), (u8)(y + (i >> 2)), t[i]); }
static u8 meter_cell(u8 c, u8 n) {
    int front = n ? (n - 1) / 2 : -1;
    if (c < front) return (FLINGMETER_GUM_B_MASK >> c) & 1 ? FLINGMETER_GUM_B : FLINGMETER_GUM_A;
    if (c == front) return (n & 1) ? FLINGMETER_FRONT4 : FLINGMETER_FRONT8;
    return c == 8 ? FLINGMETER_EMPTY_MAJOR : (c & 3) ? FLINGMETER_EMPTY : FLINGMETER_EMPTY_TICK;
}
static void meter_tube(u8 row, u8 s, u8 n) {
    if (n > METER_STEPS) n = METER_STEPS;
    u8 old = g_meter_n[s];
    if (old == METER_NONE) {
        meter_put(METER_COL - 1, row, flingmeter_cell[FLINGMETER_CAP_L * 2]);
        meter_put(METER_COL - 1, (u8)(row + 1), flingmeter_cell[FLINGMETER_CAP_L * 2 + 1]);
        meter_put(METER_COL + METER_CELLS, row, flingmeter_cell[FLINGMETER_CAP_R * 2]);
        meter_put(METER_COL + METER_CELLS, (u8)(row + 1), flingmeter_cell[FLINGMETER_CAP_R * 2 + 1]);
    }
    for (u8 c = 0; c < METER_CELLS; c++) {
        u8 k = meter_cell(c, n);
        if (old != METER_NONE && k == meter_cell(c, old)) continue;
        meter_put((u8)(METER_COL + c), row, flingmeter_cell[k * 2]);
        meter_put((u8)(METER_COL + c), (u8)(row + 1), flingmeter_cell[k * 2 + 1]);
    }
    g_meter_n[s] = n;
}
static void meter_flash(u8 full) { slot_pal(full && (g_meter_tick++ & 4) ? SLOT_HOT : SLOT_METER); if (!full) g_meter_tick = 0; }
static void meter_dial(u8 deg) {
    u8 best = 0;
    for (u8 i = 1; i < FLINGMETER_DIAL_COUNT; i++) if ((deg > flingmeter_dial_deg[i] ? deg - flingmeter_dial_deg[i] : flingmeter_dial_deg[i] - deg) < (deg > flingmeter_dial_deg[best] ? deg - flingmeter_dial_deg[best] : flingmeter_dial_deg[best] - deg)) best = i;
    if (best == g_dial_i) return;
    g_dial_i = best;
    for (u8 i = 0; i < 9; i++) meter_put((u8)(DIAL_COL + i % 3), (u8)(DIAL_ROW + i / 3), flingmeter_dial[best * 9 + i]);
}
/* Input prompts (owner pick A, tools/inputprompt_art.py): button caps and a stick in the bottom corners, rows 24..25, P1 growing right from column 1
 * and P2 growing left from column 38 (clear of the meter at columns 11..29 and the dial at 6..10). src/core/input_prompt.c decides what shows for each
 * event phase; this only draws. Own palette slot: the attract slot holds the meter palette during events. Cache: per slot 0 = blank, else 1 + cell. */
#define PROMPT_ROW 24
#define PROMPT_STICK_CODE 10   /* cache codes 1..9 are caps (letter * 3 + state), 10..12 the stick states */
static u8 g_prompt_code[2][IP_MAX_ITEMS];
static void prompt_put(u8 x, u8 code) {
    const uint8_t *t = !code ? 0 : code < PROMPT_STICK_CODE ? &inputprompt_cap[(code - 1) * 4] : &inputprompt_stick[(code - PROMPT_STICK_CODE) * 4];
    for (u8 i = 0; i < 4; i++) {
        u8 id = t ? t[i] : INPUTPROMPT_BLANK;
        gfx_fix_tile((u8)(x + (i & 1)), (u8)(PROMPT_ROW + (i >> 1)), PROMPT_PAL_SLOT, id == INPUTPROMPT_BLANK ? (u16)FIXFONT_BLANK : (u16)(INPUTPROMPT_FIX_BASE + id));
    }
}
static void prompt_side(u8 s, u8 ev, u8 phase, u8 on, u16 tick) {
    InputPrompt p = { 0, IP_STYLE_NONE, 0 };
    uint8_t kind[IP_MAX_ITEMS];
    if (on) p = input_prompt_for(ev, phase);
    u8 n = input_prompt_items(&p, kind);
    for (u8 slot = 0; slot < IP_MAX_ITEMS; slot++) {
        u8 code = 0;
        if (slot < n) {   /* P2 reads right to left so its first slot is the screen edge */
            u8 k = kind[s ? n - 1 - slot : slot], st = input_prompt_state(&p, k, tick);
            code = k == IP_ITEM_STICK ? (u8)(PROMPT_STICK_CODE + st - IP_STICK_NEUTRAL) : (u8)(1 + k * 3 + st);
        }
        if (code == g_prompt_code[s][slot]) continue;
        g_prompt_code[s][slot] = code;
        prompt_put((u8)(s ? 37 - 3 * slot : 1 + 3 * slot), code);
    }
}
/* Who is prompted and in which phase, per event; the events only keep their own phase. */
static void draw_prompts(const Game *g, u8 show) {
    u8 ev = IP_BLOW, ph = 0, p1 = 0, p2 = 0;
    if (show) {
        p1 = 1;
        if (g->gg_toss) { ev = IP_TOSS; ph = g->toss.phase; p1 = g->toss.carrier == 0; p2 = g->toss.humans == 2 && g->toss.carrier == 2; }
        else if (g->gg_fling) { ev = IP_FLING; ph = g->fling.phase; p1 = g->fling.seq.turn == 0; p2 = g->fling.seq.players == 2 && g->fling.seq.turn == 1 && !g->cpu_level;
            if (ph == GF_AIM && g->fling.t < GF_AIM_HOLD_FRAMES) p1 = p2 = 0; }   /* aim hold: A is ignored, so no A prompt yet */
        else if (g->gg_gather) { ev = IP_GATHER; ph = g->res.active ? IP_PHASE_OFF : IP_PHASE_PLAY; }
        else if (g->gg_poop) { ev = IP_POOP; ph = g->poop.phase; p2 = g->players == 2; }
        else if (g->gg_pop) { ev = IP_POP; ph = g->pop.phase; p2 = g->players == 2; }
        else if (g->gg_dash) { ev = IP_DASH; ph = g->dash.done ? IP_PHASE_OFF : IP_PHASE_PLAY; p2 = g->dash.two && !g->dash.p2_is_cpu; }
        else if (g->gg_race) { ev = IP_RACE; ph = g->race.phase; p2 = g->race.players == 2; }
        else { ev = IP_BLOW; ph = g->blow.phase; p2 = g->players == 2; }
    }
    prompt_side(0, ev, ph, p1, g->frame);
    prompt_side(1, ev, ph, p2, g->frame);
}
static void prompt_reset(void) { memset(g_prompt_code, 0, sizeof g_prompt_code); }
static void meter_reset(void) { g_meter_n[0] = g_meter_n[1] = g_dial_i = METER_NONE; g_meter_tick = 0; if (g_slot_pal >= SLOT_METER) slot_pal(SLOT_ATTRACT); memset(g_prompt_code, 0, sizeof g_prompt_code); }

static u8 card_frame(u16 t) {
    u16 p = (u16)(t % ((CARD_FRAMES - 1) * CARD_TICKS + CARD_HOLD)) / CARD_TICKS;
    return (u8)(p < CARD_FRAMES ? p : CARD_FRAMES - 1);
}

static void card_palette(u8 on) {
    if (on) slot_pal(SLOT_CARD);
    else if (g_slot_pal == SLOT_CARD) slot_pal(SLOT_ATTRACT);
}

static void card_panel(u8 y0, u8 y1, u8 pal) {
    static const u16 tile[3][3] = {
        {FIXFONT_FRAME_TL, FIXFONT_FRAME_T, FIXFONT_FRAME_TR}, {FIXFONT_FRAME_L, FIXFONT_PLATE_FILL, FIXFONT_FRAME_R}, {FIXFONT_FRAME_BL, FIXFONT_FRAME_B, FIXFONT_FRAME_BR}};
    for (u8 y = y0; y <= y1; y++)
        for (u8 x = 1; x <= 38; x++) gfx_fix_tile(x, y, pal, tile[y == y0 ? 0 : y == y1 ? 2 : 1][x == 1 ? 0 : x == 38 ? 2 : 1]);
}

static void card_line(u8 row, u8 pal, const char *s) {
    u8 n = 0;
    while (s[n]) n++;
    gfx_text_plated((u8)((VQ_FIX_COLS - n) / 2), row, pal, s);
}

/* The parts that stay: panels, name, goal, bar labels, angle bar, rules, skip prompt. */
static void card_draw(const GgCard *c) {
    static const u8 angle[CARD_BAR_CELLS] = {RULECARD_FIX_BAR_FOUL, RULECARD_FIX_BAR_SAFE, RULECARD_FIX_BAR_SAFE, RULECARD_FIX_BAR_SAFE, RULECARD_FIX_BAR_SAFE, RULECARD_FIX_BAR_FOUL};
    card_panel(CARD_BANNER_ROW, CARD_BANNER_ROW + 4, FIXFONT_PAL_PINK);
    for (u8 i = 0; i < GG_PICK_COUNT; i++)
        if (flow_gg_card(flow_gg_event(i)) == c) card_line(CARD_BANNER_ROW + 1, FIXFONT_PAL_PINK, flow_gg_name(i));
    card_line(CARD_BANNER_ROW + 3, PAL_TEXT, c->goal);
    gfx_text_plated(CARD_BAR_COL - 6, CARD_BAR_ROW, PAL_TEXT, "POWER");
    gfx_text_plated(CARD_BAR_COL - 6, CARD_BAR_ROW + 2, PAL_TEXT, "ANGLE");
    for (u8 i = 0; i < CARD_BAR_CELLS; i++) gfx_fix_tile((u8)(CARD_BAR_COL + i), CARD_BAR_ROW + 2, ATTRACT_PAL_SLOT, (u16)(RULECARD_FIX_BASE + angle[i]));
    card_panel(CARD_STRIP_ROW, CARD_STRIP_ROW + 8, PAL_TEXT);
    card_line(CARD_STRIP_ROW + 4, PAL_HIGH, c->rule[0]);
    card_line(CARD_STRIP_ROW + 5, PAL_TEXT, c->rule[1]);
    card_line(CARD_STRIP_ROW + 7, FIXFONT_PAL_DIM, "PRESS A TO SKIP");
}

static void card_clear(void) {
    gfx_center_blank(CARD_BANNER_ROW, 5, 38, PAL_TEXT);
    gfx_center_blank(CARD_STRIP_ROW, 9, 38, PAL_TEXT);
    for (u8 r = 0; r < 4; r++) text(CARD_BAR_COL - 6, (u8)(CARD_BAR_ROW + r), PAL_TEXT, "            ");
}

/* The parts the example moves: the button caps, the lit step, the power bar, the angle caret. */
static void card_animate(const GgCard *c, u8 k) {
    static const u8 cell[3] = {2, 15, 27};
    if (k == g_card_k) return;
    g_card_k = k;
    for (u8 i = 0; i < 3; i++) {
        u8 on = card_frames[k].step == i, down = (i == 0 && card_frames[k].press) || (i == 1 && card_frames[k].hold);
        u16 b = (u16)(RULECARD_FIX_BASE + (down ? RULECARD_FIX_BUTTON_DOWN : RULECARD_FIX_BUTTON_UP));
        for (u8 q = 0; q < 4; q++) gfx_fix_tile((u8)(cell[i] + (q & 1)), (u8)(CARD_STRIP_ROW + 1 + (q >> 1)), ATTRACT_PAL_SLOT, (u16)(b + q));
        gfx_text_plated((u8)(cell[i] + 3), CARD_STRIP_ROW + 1, on ? PAL_TEXT : FIXFONT_PAL_DIM, c->step[i][0]);
        gfx_text_plated((u8)(cell[i] + 3), CARD_STRIP_ROW + 2, on ? PAL_HIGH : FIXFONT_PAL_DIM, c->step[i][1]);
    }
    for (u8 i = 0; i < CARD_BAR_CELLS; i++) {
        gfx_fix_tile((u8)(CARD_BAR_COL + i), CARD_BAR_ROW, ATTRACT_PAL_SLOT, (u16)(RULECARD_FIX_BASE + (i < card_frames[k].power ? RULECARD_FIX_BAR_POWER : RULECARD_FIX_BAR_EMPTY)));
        text((u8)(CARD_BAR_COL + i), CARD_BAR_ROW + 3, PAL_HIGH, i == card_frames[k].caret ? "^" : " ");
    }
}

static void card_prop(u16 slot, u8 prop, int x, int y) {
    const RulecardFrame *f = &rulecard_frames[prop];
    gfx_sprite_strips(slot, 1, f->tiles_h, &rulecard_tile_index[f->tile_offset], RULECARD_TILE_BASE, (u16)(RULECARD_PAL_SLOT << 8));
    gfx_sprite_place(slot, 1, f->tiles_h, x, y);
}

/* The example in the arcade element slots: Sootling (2 columns), 3 slabs, needle, gum trail. Written when the frame changes
 * only; all the slots are parked when the card goes, before the countdown takes them. */
static void card_scene_step(u8 up, u16 t) {
    u8 k = up ? card_frame(t) : CARD_NONE;
    u16 slot = ARC_ELEM_SPRITE;
    if (k == g_card_scene) return;
    g_card_scene = k;
    if (k != CARD_NONE) {
        const SootlingFrame *f = &sootling_frames[soot_frame(SOOTLING_ANIM_PLAYER, card_frames[k].bird)];
        soot_strips(slot, f, &sootling_tile_index[f->tile_offset], 0, (u16)((SOOT_PAL_SLOT + f->palette) << 8));
        gfx_sprite_place(slot, SOOT_COLUMNS, f->tiles_h, CARD_BIRD_X - f->pad_left, CARD_BIRD_Y);
        slot += SOOT_COLUMNS;
        for (u8 i = 0; i < 3; i++) card_prop(slot++, CARD_PROP_SLAB, CARD_BIRD_X - 12 + i * 16, CARD_BIRD_Y + 32);
        if (card_frames[k].needle) card_prop(slot++, card_frames[k].needle, CARD_BIRD_X + 24, CARD_BIRD_Y + 2);
        for (u8 i = 0; i < card_frames[k].gums; i++)
            card_prop(slot++, i + 1 == card_frames[k].gums ? CARD_PROP_GUM : CARD_PROP_DOT, CARD_BIRD_X + card_gum[i][0], CARD_BIRD_Y + card_gum[i][1]);
    }
    while (slot < ARC_ELEM_SPRITE + ARC_ELEM_COUNT) obs_hide_slot(slot++);
}

static ObjPool g_pool;
/* Test hook: tests/mame/vblank_check.lua sets it to fill the pool with drifting objects while PLAYING (max object
 * count frame-time check). Nothing in the game sets it. */
volatile u8 g_pool_stress;
/* Sentinels for the headless test (addresses from the ELF map): frames the pool view drew at least one object, live
 * objects drawn in the last frame. */
volatile u16 g_pool_frames;
volatile u8 g_pool_live;
#define POOL_F_STRESS 0x02
#define POOL_F_HERO 0x04 /* computer flier: type is a FlierPose, drawn from the Sootling computer row */
#define POOL_F_FLIP 0x08 /* computer flier faces left: mirrored */
#define POOL_F_TRIPHAZ 0x10    /* Gum Trip hazard (objects 0..TRIP_VIEW_HAZ_OBJECTS-1, claimed for the whole trip): type = TripHazKind, x/y = art left/top in screen px (16.16), anim = frame */
#define POOL_F_TRIPHAZ_ON 0x20 /* the hazard is shown this frame */
#define POOL_F_BLINK 0x80      /* protected flier on its dark half period this frame (flier_view_visible): hidden, not drawn */
#define POOL_F_SCREEN 0x40     /* flier x is already in screen space (Gum Trip rivals): drawn with camera 0 */
_Static_assert(TRIPHAZ_MAX_COLUMNS <= POOL_COLS, "Gum Trip hazard frames must fit a pool run");
_Static_assert(TRIP_VIEW_HAZ_OBJECTS <= POOL_MAX - 12, "Gum Trip hazards leave objects 20..31 for rivals");
_Static_assert(TRIPHAZ_CLOUD_FRAMES == 24 && TRIPHAZ_VENT_FRAMES == 16 && TRIPHAZ_COAL_FRAMES == 24, "hazard frame counts differ from trip_view_haz_frame");
_Static_assert(TRIPHAZ_CLOUD_TICK_HZ == 60 && TRIPHAZ_CLOUD_HIT_X0 == 7 && TRIPHAZ_CLOUD_HIT_Y0 == 8 && TRIPHAZ_VENT_HIT_X0 == 8 && TRIPHAZ_VENT_HIT_Y0 == 10 &&
               TRIPHAZ_COAL_HIT_X0 == 5 && TRIPHAZ_COAL_HIT_Y0 == 11, "hazard hit box offsets differ from the view maths (k_haz_art)");
volatile u16 g_trip_haz_draws; /* Gum Trip hazard objects placed (one per shown hazard per frame): the test's proof the code ran */
static u8 g_haz_claimed;
_Static_assert(SOOT_COLUMNS <= POOL_COLS, "Sootling frames must fit a pool run");

/* Animation frame whose SCB1 tile strips object i's run holds, + 1 (0: unknown). Strips are not deduped by the
 * queue and cost most of the vblank budget (vq_cost), so a moving object only requeues them on a frame change. */
static u8 g_pool_drawn[POOL_MAX];
_Static_assert(OBS_FRAME_COUNT < 255 && SOOTLING_FRAMES < 127, "pool frame cache holds frame index + 1 (+ 128 mirrored) in a byte");

/* Columns object i's sticky chain (SCB2 + column SCB3) and hidden spare columns were sent for (0: unknown). A hide
 * zeroes every column's SCB3, so it clears this too; an animation frame of the same width keeps the chain. */
static u8 g_pool_cols[POOL_MAX];

static void pool_hide_run(u8 i) {
    u16 s = obj_pool_sprite(&g_pool, i);
    g_pool_drawn[i] = 0;
    g_pool_cols[i] = 0;
    for (u8 c = 0; c < POOL_COLS; c++) obs_hide_slot(s + c);
}

static void pool_hide_all(void) {
    for (int s = 0; s < POOL_SPRITE_COUNT; s++) obs_hide_slot(POOL_SPRITE_BASE + s);
    for (u8 i = 0; i < POOL_MAX; i++) { g_pool_drawn[i] = 0; g_pool_cols[i] = 0; }
}

static u8 g_cpu_obj[STAGE_SPAWN_COUNT]; /* pool index of computer flier i, POOL_NONE when not drawn */
static u8 g_rival_obj[TRIP_RIVAL_MAX];  /* pool index of Gum Trip rival i, POOL_NONE when not drawn */

static u8 g_gum_obj[STAGE_SPAWN_COUNT];   /* third pool object of computer flier i: its gum bubble (type 0xC0 | wobble sheet frame, anim = bird frame), POOL_NONE when not drawn */
static u8 g_leak_obj[STAGE_SPAWN_COUNT];   /* air-jet pool object of a leaking computer bubble, POOL_NONE otherwise */
static u8 g_rival_leak_obj[TRIP_RIVAL_MAX];
static u8 g_human_leak_obj[HUMANS];        /* air jet of a leaking player bubble (hardware sprites 111/116, src/gum.c): a pool object type 0xF0 | leak frame, anim = player, x = gum level, y = frame */
static u8 g_rival_gum_obj[TRIP_RIVAL_MAX]; /* the same for Gum Trip rival i */
static u8 g_chute_obj[STAGE_SPAWN_COUNT]; /* second pool object of computer flier i: its parachute (type 0x80 | frame), POOL_NONE when not drawn */

static void pool_reset(void) {
    for (int i = 0; i < STAGE_SPAWN_COUNT; i++) g_chute_obj[i] = g_gum_obj[i] = g_leak_obj[i] = POOL_NONE;
    for (int i = 0; i < TRIP_RIVAL_MAX; i++) g_rival_gum_obj[i] = g_rival_leak_obj[i] = POOL_NONE;
    for (int i = 0; i < HUMANS; i++) g_human_leak_obj[i] = POOL_NONE;
    for (int i = 0; i < STAGE_SPAWN_COUNT; i++) g_cpu_obj[i] = POOL_NONE;
    for (int i = 0; i < TRIP_RIVAL_MAX; i++) g_rival_obj[i] = POOL_NONE;
    obj_pool_init(&g_pool, POOL_SPRITE_BASE);
    g_haz_claimed = 0;
}

static void pool_free_all(void) {
    for (int i = 0; i < STAGE_SPAWN_COUNT; i++) g_chute_obj[i] = g_gum_obj[i] = g_leak_obj[i] = POOL_NONE;
    for (int i = 0; i < TRIP_RIVAL_MAX; i++) g_rival_gum_obj[i] = g_rival_leak_obj[i] = POOL_NONE;
    for (int i = 0; i < HUMANS; i++) g_human_leak_obj[i] = POOL_NONE;
    for (int i = 0; i < STAGE_SPAWN_COUNT; i++) g_cpu_obj[i] = POOL_NONE;
    for (int i = 0; i < TRIP_RIVAL_MAX; i++) g_rival_obj[i] = POOL_NONE;
    for (int i = POOL_MAX - 1; i >= 0; i--) obj_pool_free(&g_pool, (u8)i); /* descending: the free list ends up 0..31 again, so P2_OBJ_BODY / P2_OBJ_CHUTE stay at its tail */
    g_haz_claimed = 0;
}

/* Computer fliers: one pool object each while on screen (anchor: centre x, feet y). type = sheet frame of the clip (flier_anim_step), flags POOL_F_FLIP when facing left. */
static FlierAnim g_cpu_anim[STAGE_SPAWN_COUNT];
/* A computer flier that bounced on spikes draws from a dead body slot (in front of the spike art) instead of a pool object. */
static int body_show_front(const Game *g, const Flier *c, FlierAnim *an, u8 owner, u8 sheet_anim, int pal_slot) {
    if (g->mode == GAME_MODE_TRIP || !flier_body_front(c)) { dead_release(owner); return 0; }
    int d = dead_claim(owner);
    if (d < 0) return 0;
    int flip;
    u8 shown = flier_anim_step(an, c, &k_clips, &flip);
    const SootlingFrame *f = &sootling_frames[soot_frame(sheet_anim, shown)];
    const u16 *tiles = &sootling_tile_index[f->tile_offset];
    int feet = (int)((c->y + flier_half_h(c)) >> 16);
    int sx = camera_screen_x((int)(c->x >> 16) - FLIER_HALF_W - SOOT_BOX_DX, g_cam_px, SOOT_COLUMNS * 16);
    u16 slot = (u16)(DEAD_BODY_SPRITE + d * DEAD_BODY_COLUMNS);
    if (!camera_visible(sx, SOOT_COLUMNS * 16)) { dead_release(owner); return 1; }
    soot_strips(slot, f, tiles, flip, (u16)(((pal_slot ? pal_slot : SOOT_PAL_SLOT + f->palette) << 8) | (flip ? SOOT_FLIP : 0)));
    gfx_sprite_place(slot, SOOT_COLUMNS, f->tiles_h, sx, feet - f->tiles_h * 16);
    return 1;
}
static int cpu_show_front(const Game *g, int i) {
    return body_show_front(g, &g->cpu[i], &g_cpu_anim[i], DEAD_OWNER_CPU(i), SOOTLING_ANIM_CPU, 0);
}

/* The parachute of computer flier i: a pool object of its own (flags POOL_F_HERO, type 0x80 | frame) while the body is drawn here in state PARACHUTE. */
static void chute_obj_set(const Game *g, u8 k, int flip, const Flier *c, int32_t feet);
static void chute_obj_sync(const Game *g, int i, int want, int flip, const Flier *c, int32_t feet) {
    u8 k = g_chute_obj[i];
    if (!want) { if (k != POOL_NONE) { obj_pool_free(&g_pool, k); g_chute_obj[i] = POOL_NONE; } return; }
    if (k == POOL_NONE) {
        k = obj_pool_alloc(&g_pool, 0, 0, 0, 0, 0);
        if (k == POOL_NONE) return;
        g_pool.obj[k].flags |= POOL_F_HERO;
        g_chute_obj[i] = k;
    }
    chute_obj_set(g, k, flip, c, feet);
}
static void chute_obj_set(const Game *g, u8 k, int flip, const Flier *c, int32_t feet) {
    PoolObj *p = &g_pool.obj[k];
    p->type = (u8)(0x80 | ((g->frame / CHUTE_FRAME_TICKS) & 7));
    p->x = c->x; p->y = feet;
    if (flip) p->flags |= POOL_F_FLIP; else p->flags &= (u8)~POOL_F_FLIP;
    if (flier_view_visible(c, g->frame)) p->flags &= (u8)~POOL_F_BLINK; else p->flags |= POOL_F_BLINK;
}

_Static_assert(GUM_PUMP_STROKES == ARC_PUMP_STAGES, "one bubble beat per pump stage (the chin stroke)");
/* Bubble level while its owner pumps (grows 1..16 with a swell per stroke, gum_view_pump_level); 16 otherwise. */
static u8 pump_level(const ArcPump *pp, int alive) {
    return alive && arc_pump_in_window(pp) ? gum_view_pump_level(pp->frame, arc_pump_frames(pp), GUM_VIEW_LEVELS) : (u8)GUM_VIEW_LEVELS;
}

/* The gum bubble of a computer flier or rival: a pool object of its own (POOL_F_HERO, type 0xC0 | wobble sheet frame, anim = the body's sheet frame) beside the body.
 * The bubble is always full size, like the player's in the arena; gum_view_offset decides per body frame whether it shows (pool_show_gum). */
#define GUM_OBJ_POP_OVER 255
_Static_assert(GUM_VIEW_POP_SHEET * GUM_POP_FRAMES < GUM_OBJ_POP_OVER, "the pop clock of a pool bubble fits a byte");
static u8 g_sync_ticks = 1;       /* game frames one gum_obj_sync call stands for: 2 for a staggered rival (pool_sync_cpus) */
static u8 g_gum_pop_t[POOL_MAX];   /* per bubble object: game frames since its pop started (level 0), GUM_OBJ_POP_OVER = none */
static void gum_obj_sync(u8 *slot, int want, const Game *g, const PoolObj *body, int leaking, u8 level, int burst) {
    u8 k = *slot;
    if (!want) { if (k != POOL_NONE) { obj_pool_free(&g_pool, k); *slot = POOL_NONE; } return; }
    if (k == POOL_NONE) {
        k = obj_pool_alloc(&g_pool, 0, 0, 0, 0, 0);
        if (k == POOL_NONE) return;
        *slot = k;
        g_pool.obj[k].anim_tick = 0; g_gum_pop_t[k] = GUM_OBJ_POP_OVER;   /* a bubble first seen on a dead body does not pop again */
    }
    PoolObj *p = &g_pool.obj[k];
    p->flags = (u8)(p->flags | POOL_F_HERO);
    /* never POOL_F_BLINK: the bubble stays drawn while its body blinks */
    p->flags = (u8)((p->flags & ~(POOL_F_FLIP | POOL_F_BLINK | POOL_F_SCREEN)) | (body->flags & (POOL_F_FLIP | POOL_F_SCREEN)));
    p->type = (u8)(0xC0 | gum_view_frame(GUM_STATE_WOBBLE, (uint32_t)gum_view_wobble_clock(g->frame, leaking)));
    p->anim = body->type;
    /* anim_tick: bubble level 1..16 (pool_show_gum / pool_show_leak), 0 = burst: the pop plays on g_gum_pop_t, then nothing */
    if (!burst) p->anim_tick = level;
    else { if (p->anim_tick) g_gum_pop_t[k] = 0; else if (g_gum_pop_t[k] < GUM_OBJ_POP_OVER) g_gum_pop_t[k] = (u8)(g_gum_pop_t[k] + g_sync_ticks < GUM_OBJ_POP_OVER ? g_gum_pop_t[k] + g_sync_ticks : GUM_OBJ_POP_OVER); p->anim_tick = 0; }
    p->x = body->x; p->y = body->y;
}

_Static_assert(GUM_WOBBLE_FRAMES == 2 * GUM_LEAK_TICK, "double-speed wobble steps once per leak frame");
_Static_assert(GUM_LEAK_FRAMES <= 2 * GUM_WOBBLE_FRAMES, "pool_show_leak folds a leak frame to a wobble frame with one subtract");

/* Air jet of a leaking computer bubble: pool object type 0xE0 | leak frame, anim = body frame, placed from the bubble object it follows. */
static void leak_obj_sync(u8 *slot, u8 *gslot, int want, const Game *g, const PoolObj *body, u8 level) {
    u8 k = *slot;
    if (!want || *gslot == POOL_NONE) { if (k != POOL_NONE) { obj_pool_free(&g_pool, k); *slot = POOL_NONE; } return; }
    if (k == POOL_NONE) {
        k = obj_pool_alloc(&g_pool, 0, 0, 0, 0, 0);
        if (k == POOL_NONE) return;
        *slot = k;
    }
    if (*slot < *gslot) {   /* a lower sprite index draws behind: the jet must sit above its bubble, so swap the two objects (and their draw caches) */
        u8 t = *slot; *slot = *gslot; *gslot = t;
        g_pool_drawn[*slot] = g_pool_drawn[*gslot] = 0; g_pool_cols[*slot] = g_pool_cols[*gslot] = 0;
        gum_obj_sync(gslot, 1, g, body, 1, level, 0);
        k = *slot;
    }
    PoolObj *p = &g_pool.obj[k];
    p->flags = (u8)((p->flags | POOL_F_HERO) & ~(POOL_F_FLIP | POOL_F_BLINK | POOL_F_SCREEN));
    p->flags = (u8)(p->flags | (body->flags & (POOL_F_FLIP | POOL_F_SCREEN)));   /* no blink, like its bubble */
    p->type = (u8)(0xE0 | gum_view_leak_frame(g->frame));
    p->anim = body->type; p->anim_tick = level;
    p->x = body->x; p->y = body->y;
}

static void pool_sync_cpus(const Game *g) {
    int slots = g->mode == GAME_MODE_ARCADE ? STAGE_SPAWN_COUNT : CPU_MAX; /* arena runs 3 slots: the extra arcade slots cost frame time in the arena worst case */
    for (int i = 0; i < slots; i++) {
        const Flier *c = &g->cpu[i];
        u8 k = g_cpu_obj[i];
        int32_t feet = c->y + flier_half_h(c); /* once: used by the visibility test and the pool y */
        int visible = i < g->cpu_count && flier_body_visible(c) && (c->state >= FLIER_FALLING || (int)(feet >> 16) <= SCREEN_H);
        /* Stagger: rival i runs the full sync (animation, gum, leak, chute state) on frames where (frame + i) is even and on the
           others only follows its body, so every object still moves each frame; the state it shows lags at most one frame. */
        if (visible && k != POOL_NONE && ((g->frame + (u32)i) & 1u)) {
            PoolObj *p = &g_pool.obj[k];
            p->x = c->x; p->y = feet;
            u8 o = g_chute_obj[i];
            if (o != POOL_NONE) { g_pool.obj[o].x = c->x; g_pool.obj[o].y = feet; }
            o = g_gum_obj[i];
            if (o != POOL_NONE) { g_pool.obj[o].x = c->x; g_pool.obj[o].y = feet; }
            o = g_leak_obj[i];
            if (o != POOL_NONE) { g_pool.obj[o].x = c->x; g_pool.obj[o].y = feet; }
            continue;
        }
        if (!visible) dead_release(DEAD_OWNER_CPU(i));
        if (!visible || cpu_show_front(g, i)) {
            if (k != POOL_NONE) { obj_pool_free(&g_pool, k); g_cpu_obj[i] = POOL_NONE; }
            chute_obj_sync(g, i, 0, 0, c, feet);
            gum_obj_sync(&g_gum_obj[i], 0, g, 0, 0, 0, 0);
            leak_obj_sync(&g_leak_obj[i], &g_gum_obj[i], 0, g, 0, 0);
            continue;
        }
        if (k == POOL_NONE) {
            k = obj_pool_alloc(&g_pool, 0, 0, 0, 0, 0);
            if (k == POOL_NONE) continue;
            flier_anim_init(&g_cpu_anim[i]);
            g_pool.obj[k].flags |= POOL_F_HERO;
            g_cpu_obj[i] = k;
        }
        PoolObj *p = &g_pool.obj[k];
        int flip;
        p->type = flier_anim_step_n(&g_cpu_anim[i], c, &k_clips, &flip, 2); /* sheet frame (2 ticks: stepped every other frame); the player palette offset is added in pool_show_hero */
        if (arc_pump_in_window(&g->pump[i]) && c->state == FLIER_ALIVE) p->type = flier_pump_frame(&k_clips, arc_pump_progress(&g->pump[i])); /* sitting rival: pump frame */
        if (flip) p->flags |= POOL_F_FLIP; else p->flags &= (u8)~POOL_F_FLIP;
        /* toss birds stand in screen space (game_flier_cam_px 0), like their bubble and the hero */
        if (seated(g)) p->flags |= POOL_F_SCREEN; else p->flags &= (u8)~POOL_F_SCREEN;
        p->anim = toss_pose_code(g, c);
        p->x = c->x;
        p->y = feet;
        if (flier_view_visible(c, g->frame)) p->flags &= (u8)~POOL_F_BLINK; else p->flags |= POOL_F_BLINK;
        chute_obj_sync(g, i, c->state == FLIER_PARACHUTE, flip, c, feet);
        u8 lvl = pump_level(&g->pump[i], c->state == FLIER_ALIVE);
        g_sync_ticks = 2;
        gum_obj_sync(&g_gum_obj[i], !seated(g), g, p, gum_view_leaks_balloons(c->balloons), lvl, flier_gum_burst(c));   /* Toss Gum has its own bubble: no arena gum on the birds */
        leak_obj_sync(&g_leak_obj[i], &g_gum_obj[i], !seated(g) && gum_view_leaks_balloons(c->balloons), g, p, lvl);
        g_sync_ticks = 1;
    }
}

/* Player 2: body and parachute in pool objects P2_OBJ_BODY / P2_OBJ_CHUTE, claimed once P2 has joined and kept until the
 * world is left (pool_free_all). A hidden P2 keeps the objects with POOL_F_BLINK set, so a computer flier never allocates
 * them. A bounced body draws from a dead body slot instead (owner DEAD_OWNER_HERO(1)). */
static u8 g_p2_cpu;   /* 1 = the P2 body object shows the Burst Race computer bird */
static void pool_sync_p2(const Game *g) {
    g_p2_shown = 0;
    if (g->gg_pop || g->gg_poop) {   /* Pop Drop and Poop the Man draw both birds themselves */
        if (obj_pool_is_live(&g_pool, P2_OBJ_BODY)) { g_pool.obj[P2_OBJ_BODY].flags |= POOL_F_BLINK; g_pool.obj[P2_OBJ_CHUTE].flags |= POOL_F_BLINK; }
        return;
    }
    if (g->players < 2 && !g->gg_race && !g->gg_gather && !(g->gg_dash && g->dash.two)) return;
    u8 cpu = (g->gg_race || g->gg_dash || g->gg_gather) && g->players < 2;   /* Burst Race against the computer: the rival sheet and palette */
    if (cpu != g_p2_cpu) { g_p2_cpu = cpu; g_pool_drawn[P2_OBJ_BODY] = 0; }
    const Flier *fl = &g->hero[1];
    if (!obj_pool_is_live(&g_pool, P2_OBJ_BODY)) {
        if (!obj_pool_claim(&g_pool, P2_OBJ_BODY) || !obj_pool_claim(&g_pool, P2_OBJ_CHUTE)) return;
        g_pool.obj[P2_OBJ_BODY].flags |= POOL_F_HERO | POOL_F_BLINK;
        g_pool.obj[P2_OBJ_CHUTE].flags |= POOL_F_HERO | POOL_F_BLINK;
        g_pool.obj[P2_OBJ_CHUTE].type = 0x80;
        flier_anim_init(&g_hero_anim[1]);
    }
    PoolObj *b = &g_pool.obj[P2_OBJ_BODY], *ch = &g_pool.obj[P2_OBJ_CHUTE];
    int32_t feet = fl->y + flier_half_h(fl);
    int visible = game_flier_visible(g) && flier_body_visible(fl) && (fl->state >= FLIER_FALLING || (int)(feet >> 16) <= SCREEN_H);
    if (!visible) dead_release(DEAD_OWNER_HERO(1));
    if (!visible || body_show_front(g, fl, &g_hero_anim[1], DEAD_OWNER_HERO(1), SOOTLING_ANIM_PLAYER, SOOT_P2_PAL_SLOT)) {
        b->flags |= POOL_F_BLINK; ch->flags |= POOL_F_BLINK;
        return;
    }
    int flip;
    b->type = flier_anim_step(&g_hero_anim[1], fl, &k_clips, &flip);
    if (arc_pump_in_window(&g->hpump[1]) && fl->state == FLIER_ALIVE) b->type = flier_pump_frame(&k_clips, arc_pump_progress(&g->hpump[1]));
    if (flip) b->flags |= POOL_F_FLIP; else b->flags &= (u8)~POOL_F_FLIP;
    if (seated(g)) b->flags |= POOL_F_SCREEN; else b->flags &= (u8)~POOL_F_SCREEN;   /* screen space, see pool_sync_cpus */
    b->anim = toss_pose_code(g, fl);
    b->x = fl->x; b->y = feet;
    if (flier_view_visible(fl, g->frame)) b->flags &= (u8)~POOL_F_BLINK; else b->flags |= POOL_F_BLINK;
    g_p2_shown = 1;
    if (fl->state == FLIER_PARACHUTE) chute_obj_set(g, P2_OBJ_CHUTE, flip, fl, feet);
    else ch->flags |= POOL_F_BLINK;
}

/* Gum Trip rivals: the same drawing as a computer flier, one pool object each while active (object 20 + rival index,
 * claimed from the free list). Rival x is screen space, so the object carries POOL_F_SCREEN. */
_Static_assert(TRIP_RIVAL_MAX <= 12, "Gum Trip rivals fit pool objects 20..31");
static FlierAnim g_rival_anim[TRIP_RIVAL_MAX];
static void pool_sync_rivals(const Game *g) {
    for (int i = 0; i < TRIP_RIVAL_MAX; i++) {
        const TripRival *r = &g->trip_rivals.r[i];
        const Flier *c = &r->f;
        u8 k = g_rival_obj[i];
        int feet = (int)((c->y + flier_half_h(c)) >> 16);
        if (!r->active || !flier_body_visible(c) || (feet > SCREEN_H && c->state < FLIER_FALLING)) {
            if (k != POOL_NONE) { obj_pool_free(&g_pool, k); g_rival_obj[i] = POOL_NONE; }
            gum_obj_sync(&g_rival_gum_obj[i], 0, g, 0, 0, 0, 0);
            leak_obj_sync(&g_rival_leak_obj[i], &g_rival_gum_obj[i], 0, g, 0, 0);
            continue;
        }
        if (k == POOL_NONE) {
            k = (u8)(TRIP_RIVAL_OBJ_BASE + i);
            if (!obj_pool_claim(&g_pool, k)) continue;
            flier_anim_init(&g_rival_anim[i]);
            g_pool.obj[k].flags |= POOL_F_HERO | POOL_F_SCREEN;
            g_rival_obj[i] = k;
        }
        PoolObj *p = &g_pool.obj[k];
        int flip;
        p->type = flier_anim_step(&g_rival_anim[i], c, &k_clips, &flip);
        if (flip) p->flags |= POOL_F_FLIP; else p->flags &= (u8)~POOL_F_FLIP;
        p->x = c->x;
        p->y = (int32_t)(c->y + flier_half_h(c));
        if (flier_view_visible(c, g->frame)) p->flags &= (u8)~POOL_F_BLINK; else p->flags |= POOL_F_BLINK;
        gum_obj_sync(&g_rival_gum_obj[i], 1, g, p, gum_view_leaks_balloons(c->balloons), GUM_VIEW_LEVELS, flier_gum_burst(c));   /* rivals do not pump */
        leak_obj_sync(&g_rival_leak_obj[i], &g_rival_gum_obj[i], gum_view_leaks_balloons(c->balloons), g, p, GUM_VIEW_LEVELS);
    }
}

/* Player bubble jet (look only): leaking = Gum Trip gum below half for player 1, one balloon left in the arena and arcade. */
static int human_leaks(const Game *g, int pl) {
    if (g->mode == GAME_MODE_TRIP) return pl == 0 && game_trip_ready(g) && gum_view_leaks_gum(g->trip.gum);
    return gum_view_leaks_balloons(g->hero[pl].balloons);
}
/* Arena / arcade bubble level of a human: full, or growing while that human pumps after a parachute landing; 0 once it burst (last balloon, dead). */
static u8 human_bubble_level(const Game *g, int pl) { return flier_gum_burst(&g->hero[pl]) ? 0 : pump_level(&g->hpump[pl], g->hero[pl].state == FLIER_ALIVE); }   /* 0: gum_step plays the pop */
/* Burst Race bubble of side s: the pump size on the same 1..16 levels (at least 1, so the bubble shows from the first frame); gum_step takes it as a gum value; 0 once this side won the heat: gum_step plays the pop. */
static uint16_t race_gum(const Game *g, int s) { if (gg_race_bursts(&g->race, s)) return 0; uint16_t v = (uint16_t)(g->race.size[s] * (GUM_MAX / GG_BLOW_MAX)); return v ? v : 1; }
/* Big Blow is GAME_MODE_GUM with no other event flag. */
static int is_big_blow(const Game *g) { return g->mode == GAME_MODE_GUM && !(g->gg_race || g->gg_pop || g->gg_poop || g->gg_dash || g->gg_gather || g->gg_fling || g->gg_toss || g->gg_tug); }
static uint16_t blow_gum(const Game *g) { if (g->blow.phase == GG_BLOW_BURST || (g->blow.phase >= GG_BLOW_RESULT && g->blow.burst)) return 0;   /* burst stays set into the next attempt: only the burst and its result screen count */ uint16_t v = (uint16_t)(g->blow.size * (GUM_MAX / GG_BLOW_MAX)); return v ? v : 1; }
static void human_leak_sync(const Game *g) {
    for (int pl = 0; pl < HUMANS; pl++) {
        int want = (g->mode == GAME_MODE_TRIP ? pl == 0 : (pl == 0 || g->players == 2)) && human_leaks(g, pl);
        u8 *slot = &g_human_leak_obj[pl];
        if (!want) { if (*slot != POOL_NONE) { obj_pool_free(&g_pool, *slot); *slot = POOL_NONE; } continue; }
        if (*slot == POOL_NONE) {
            *slot = obj_pool_alloc(&g_pool, 0, 0, 0, 0, 0);
            if (*slot == POOL_NONE) continue;
        }
        PoolObj *p = &g_pool.obj[*slot];
        p->flags = (u8)(p->flags | POOL_F_HERO);
        p->type = (u8)(0xF0 | gum_view_leak_frame(g->frame));
        p->anim = (u8)pl;
        p->x = g->mode == GAME_MODE_TRIP ? gum_view_level(g->trip.gum) : human_bubble_level(g, pl);
        p->y = (int32_t)g->frame;
    }
}

/* Test hook body (g_pool_stress): fill every free object with a drone or bot drifting left at 1 to 1.9 px per frame
 * with a small vertical drift; they wrap at the left edge and bounce between y 40 and 208. */
static void pool_stress(void) {
    static u8 seed;
    u8 k;
    while ((k = obj_pool_alloc(&g_pool, (u8)(OB_DRONE + (seed & 1)), 0,
                               obj_pool_fp((int16_t)(64 + ((seed * 37) & 127))),
                               -(65536 + (int32_t)(seed & 7) * 8192), (int32_t)((seed & 3) - 1) * 16384)) != POOL_NONE) {
        g_pool.obj[k].flags |= POOL_F_STRESS;
        g_pool.obj[k].x = obj_pool_fp((int16_t)(k * 10)); /* spread over the screen by index */
        seed++;
    }
    obj_pool_step(&g_pool);
    PoolObj *p = g_pool.obj;
    for (u8 i = 0; i < POOL_MAX; i++, p++) {
        if (!(p->flags & POOL_F_STRESS)) continue;
        if (p->x < obj_pool_fp(-48)) p->x += obj_pool_fp(368);
        if ((p->y < obj_pool_fp(40) && p->vy < 0) || (p->y > obj_pool_fp(208) && p->vy > 0)) p->vy = -p->vy;
    }
}

/* Head SCB3 (height, y) and SCB4 (x) of every pool object go out as two strided runs (gfx_scb_run, stride
 * POOL_COLS): two queue ops per frame instead of up to two per object. A hidden or free object's head SCB3 is 0 (as
 * pool_hide_run and pool_hide_all write it); its x stays the last one sent. */
static u16 g_pool_scb4[POOL_MAX];

/* Same run layout as an obstacle, with the Sootling frame table, tile base and the computer palette. */
/* Parachute object (type 0x80 | frame): same left edge and flip rule as the body, top = feet - 46. */
static void pool_show_chute(PoolObj *p, u8 i, u16 *scb3) {
    int p2 = i == P2_OBJ_CHUTE;
    if (p->flags & POOL_F_BLINK) { if (g_pool_drawn[i]) pool_hide_run(i); return; }
    const ChuteFrame *f = &chute_frames[chute_anims[p2 ? CHUTE_ANIM_PLAYER2 : CHUTE_ANIM_CPU].first_frame + (p->type & 7)];
    int flip = (p->flags & POOL_F_FLIP) != 0;
    int x = camera_screen_x(obj_pool_px(p->x) - FLIER_HALF_W - SOOT_BOX_DX, (p->flags & POOL_F_SCREEN) ? 0 : g_cam_px, f->tiles_w * 16);
    u16 slot = obj_pool_sprite(&g_pool, i);
    if (!camera_visible(x, f->tiles_w * 16)) { pool_hide_run(i); return; }
    u8 key = (u8)(p->type + (flip ? 128 : 0) + 1); /* type already holds bit 7, so the mirror state goes in via +1 wrap: frame and mirror differ */
    if (g_pool_drawn[i] != key) {
        chute_strips(slot, f, flip, p2 ? CHUTE_P2_PAL_SLOT : CHUTE_PAL_SLOT + f->palette);
        if (g_pool_cols[i] != f->tiles_w) { gfx_sprite_chain(slot, f->tiles_w); g_pool_cols[i] = f->tiles_w; }
        g_pool_drawn[i] = key;
    }
    scb3[i] = gfx_scb3_word(f->tiles_h, obj_pool_px(p->y) - 46);
    g_pool_scb4[i] = gfx_scb4_word(x);
}

/* Gum bubble object (type 0xC0 | wobble frame): the player's placement (src/gum.c) from the body's pose: centre x of the body sprite, body sprite top. */
static void pool_show_gum(PoolObj *p, u8 i, u16 *scb3) {
    int flip = (p->flags & POOL_F_FLIP) != 0;
    GumOffset o = gum_view_offset(p->anim, flip);
    int lvl = p->anim_tick, pop = lvl == 0 && !gum_view_pop_done(g_gum_pop_t[i]);   /* level 0: the burst (gum_obj_sync), full size pop art */
    if (!gum_view_draws(pop, (uint8_t)lvl, o.show)) { if (g_pool_drawn[i]) pool_hide_run(i); return; }
    const SootlingFrame *bf = &sootling_frames[soot_frame(SOOTLING_ANIM_CPU, p->anim)];
    int sheet = pop ? gum_view_frame(GUM_STATE_POP, g_gum_pop_t[i]) : (p->type & 7);
    const GumFrame *f = &gum_frames[gum_anims[gum_view_anim((uint8_t)(pop ? GUM_VIEW_LEVELS : lvl), pop ? GUM_STATE_POP : GUM_STATE_WOBBLE)].first_frame + sheet];
    int bx = camera_screen_x(obj_pool_px(p->x) - FLIER_HALF_W - SOOT_BOX_DX, (p->flags & POOL_F_SCREEN) ? 0 : g_cam_px, SOOT_COLUMNS * 16);
    int x = bx + SOOT_COLUMNS * 8 - f->tiles_w * 8 + o.dx;
    if (!camera_visible(x, f->tiles_w * 16)) { if (g_pool_drawn[i]) pool_hide_run(i); return; }
    u16 slot = obj_pool_sprite(&g_pool, i);
    u8 key = (u8)(sheet + 1 + lvl * 8);   /* level 0: pop frame 0..6 */   /* level 1..16 and wobble frame 0..5 */
    if (g_pool_drawn[i] != key) {
        gfx_sprite_strips(slot, f->tiles_w, f->tiles_h, &gum_tile_index[f->tile_offset], GUM_TILE_BASE, (u16)((GUM_PAL_SLOT + f->palette) << 8));
        if (g_pool_cols[i] != f->tiles_w) { gfx_sprite_chain(slot, f->tiles_w); g_pool_cols[i] = f->tiles_w; }
        g_pool_drawn[i] = key;
    }
    g_cpu_gum_tile = (u16)(GUM_TILE_BASE + gum_tile_index[f->tile_offset]);
    g_cpu_gum_draws++;
    scb3[i] = gfx_scb3_word(f->tiles_h, obj_pool_px(p->y) - bf->tiles_h * 16 - f->tiles_h * 16 + o.dy);
    g_pool_scb4[i] = gfx_scb4_word(x);
}

/* Air jet (type 0xE0 | leak frame; 0xF0 = a player's bubble, pose from gum_step's inputs): anchored on the bubble cell's rim for the
 * wobble frame and gum level, mirrored with the body. Computer bubbles are level 16. */
static void pool_show_leak(PoolObj *p, u8 i, u16 *scb3) {
    static const int8_t ax_t[] = GUMLEAK_TABLE_ANCHOR_DX, ay_t[] = GUMLEAK_TABLE_ANCHOR_DY;
    if (p->flags & POOL_F_BLINK) { if (g_pool_drawn[i]) pool_hide_run(i); return; }
    int lf = p->type & 15, x, y, cw, ax, ay, flip;
    const GumleakFrame *l = &gumleak_frames[lf];
    if (p->type & 0x10) {   /* player bubble: the same cell gum_step places, from the pose of this frame */
        int pl = p->anim, cx, top;
        u8 fr;
        if (pl == 0) { if (!g_gum_pose[0].drawn) goto hide; fr = g_gum_pose[0].frame; flip = g_gum_pose[0].flip; cx = g_gum_pose[0].cx; top = g_gum_pose[0].top; }
        else {   /* player 2's pose is only set in pool_show_hero, which can run after this object: derive it from the body object */
            const PoolObj *b = &g_pool.obj[P2_OBJ_BODY];
            if (!g_p2_shown) goto hide;
            fr = b->type; flip = (b->flags & POOL_F_FLIP) != 0;
            cx = camera_screen_x(obj_pool_px(b->x) - FLIER_HALF_W - SOOT_BOX_DX, (b->flags & POOL_F_SCREEN) ? 0 : g_cam_px, SOOT_COLUMNS * 16) + SOOT_COLUMNS * 8;
            top = obj_pool_px(b->y) - sootling_frames[soot_frame(SOOTLING_ANIM_PLAYER, fr)].tiles_h * 16;
        }
        GumLeakPose gp;
        if (!gum_leak_pose((uint8_t)p->x, (uint32_t)p->y, fr, flip, cx, top, &gp)) goto hide;
        ax = ax_t[gp.idx]; ay = ay_t[gp.idx]; cw = gp.w;
        x = gp.x + ax;
        y = gp.y + ay;
    } else {
        flip = (p->flags & POOL_F_FLIP) != 0;
        GumOffset o = gum_view_offset(p->anim, flip);
        if (!o.show) goto hide;
        int wob = lf >= GUM_WOBBLE_FRAMES ? lf - GUM_WOBBLE_FRAMES : lf;   /* lf < 2 * GUM_WOBBLE_FRAMES (leak frames); a 32 bit % is a libgcc call */
        const SootlingFrame *bf = &sootling_frames[soot_frame(SOOTLING_ANIM_CPU, p->anim)];
        int lvl = p->anim_tick, row = (GUM_VIEW_LEVELS - lvl) * GUM_VIEW_WOBBLE_SHEET + wob;   /* anchor row as gum_leak_pose */
        const GumFrame *f = &gum_frames[gum_anims[gum_view_anim((uint8_t)lvl, GUM_STATE_WOBBLE)].first_frame + wob];
        int bx = camera_screen_x(obj_pool_px(p->x) - FLIER_HALF_W - SOOT_BOX_DX, (p->flags & POOL_F_SCREEN) ? 0 : g_cam_px, SOOT_COLUMNS * 16);
        cw = f->tiles_w * 16; ax = ax_t[row];
        x = bx + SOOT_COLUMNS * 8 - cw / 2 + o.dx + ax;
        y = obj_pool_px(p->y) - bf->tiles_h * 16 - f->tiles_h * 16 + o.dy + ay_t[row];
    }
    if (!camera_visible(x, l->tiles_w * 16)) goto hide;
    /* the hole and jet never mirror with the bird's facing (owner 2026-11-17); flip only moves the bubble */
    u16 slot = obj_pool_sprite(&g_pool, i);
    u8 key = (u8)(lf + 1);
    if (g_pool_drawn[i] != key) {
        const u16 *t = &gumleak_tile_index[l->tile_offset];
        u16 attr = (u16)((GUM_PAL_SLOT + l->palette) << 8);
        /* one strip per column straight from the const table: the queue keeps the tile pointer, a stack copy would be read after return */
        for (int c = 0; c < l->tiles_w; c++)
            gfx_sprite_strips((u16)(slot + c), 1, l->tiles_h, t + c * l->tiles_h, GUMLEAK_TILE_BASE, attr);
        if (g_pool_cols[i] != l->tiles_w) { gfx_sprite_chain(slot, l->tiles_w); g_pool_cols[i] = l->tiles_w; }
        g_pool_drawn[i] = key;
    }
    scb3[i] = gfx_scb3_word(l->tiles_h, y);
    g_pool_scb4[i] = gfx_scb4_word(x);
    return;
hide:
    if (g_pool_drawn[i]) pool_hide_run(i);
}

static u8 g_pool_pose[POOL_MAX];   /* toss_pose_code the strips of a body object hold; a change redraws them (the pose and the seat palette are not in the g_pool_drawn key) */
static void pool_show_hero(PoolObj *p, u8 i, u16 *scb3) {
    if ((p->type & 0xE0) == 0xE0) { pool_show_leak(p, i, scb3); return; }
    if ((p->type & 0xC0) == 0xC0) { pool_show_gum(p, i, scb3); return; }
    if (p->type & 0x80) { pool_show_chute(p, i, scb3); return; }
    if (p->flags & POOL_F_BLINK) { g_blink_pool[0]++; if (g_pool_drawn[i]) pool_hide_run(i); return; } /* the animation kept stepping in the sync; the hide costs queue words once */
    g_blink_pool[1]++;
    int p2 = i == P2_OBJ_BODY && !g_p2_cpu;
    u8 fi = soot_frame(p2 ? SOOTLING_ANIM_PLAYER : SOOTLING_ANIM_CPU, p->type);
    const SootlingFrame *f = &sootling_frames[fi];
    int flip = (p->flags & POOL_F_FLIP) != 0;
    int x = camera_screen_x(obj_pool_px(p->x) - FLIER_HALF_W - SOOT_BOX_DX, (p->flags & POOL_F_SCREEN) ? 0 : g_cam_px, SOOT_COLUMNS * 16);
    int top = obj_pool_px(p->y) - f->tiles_h * 16;
    /* the bubble pose is set on the dark blink half too (g_p2_shown tells a blink from a hidden player 2): the bubble stays */
    if (i == P2_OBJ_BODY && g_p2_shown && camera_visible(x, SOOT_COLUMNS * 16)) { g_gum_pose[1].drawn = 1; g_gum_pose[1].frame = p->type; g_gum_pose[1].flip = (u8)flip; g_gum_pose[1].cx = x + SOOT_COLUMNS * 8; g_gum_pose[1].top = top; }
    if (p->flags & POOL_F_BLINK) { g_blink_pool[0]++; if (g_pool_drawn[i]) pool_hide_run(i); return; } /* the animation kept stepping in the sync; the hide costs queue words once */
    g_blink_pool[1]++;
    u16 slot = obj_pool_sprite(&g_pool, i);
    if (!camera_visible(x, SOOT_COLUMNS * 16)) { pool_hide_run(i); return; }
    const u16 *tiles = &sootling_tile_index[f->tile_offset];
    u8 key = (u8)(p->type + 1 + (flip ? 128 : 0)); /* frame and mirror state the strips hold; the computer palette only, so the clip frame is unique */
    u8 seat = (p->anim >> 4) & 3;   /* seat (toss_pose_code); bit 6 = Tug Gum cell */
    if (g_pool_pose[i] != p->anim) { g_pool_pose[i] = p->anim; g_pool_drawn[i] = 0; }
    if (p->anim & 15) {
        if (!g_pool_drawn[i]) {
            if (p->anim & 0x40) tugpose_strips(slot, (u8)((p->anim & 15) - 1), seat); else tosspose_strips(slot, (u8)((p->anim & 15) - 1), seat);
            if (g_pool_cols[i] != SOOT_COLUMNS) { gfx_sprite_chain(slot, SOOT_COLUMNS); g_pool_cols[i] = SOOT_COLUMNS; }
            g_pool_drawn[i] = 0xFF;
        }
        scb3[i] = gfx_scb3_word(2, obj_pool_px(p->y) - 32);
        g_pool_scb4[i] = gfx_scb4_word(x);
        if (!(p->anim & 0x40)) toss_wing_mark(seat, (u8)((p->anim & 15) - 1), x, obj_pool_px(p->y) - 32);
        return;
    }
    if (g_pool_drawn[i] != key) {
        /* Toss Gum: the birds on seats 2 and 3 stand in gold and violet */
        soot_strips(slot, f, tiles, flip, (u16)(((p2 || seat == 2 ? SOOT_P2_PAL_SLOT : seat == 3 ? SOOT_VIOLET_PAL_SLOT : SOOT_PAL_SLOT + f->palette) << 8) | (flip ? SOOT_FLIP : 0)));
        if (g_pool_cols[i] != SOOT_COLUMNS) { gfx_sprite_chain(slot, SOOT_COLUMNS); g_pool_cols[i] = SOOT_COLUMNS; }
        g_pool_drawn[i] = key;
    }
    g_soot_cpu_tile = (u16)(SOOT_TILE_BASE + tiles[0]);
    g_soot_cpu_draws++;
    scb3[i] = gfx_scb3_word(f->tiles_h, top);
    g_pool_scb4[i] = gfx_scb4_word(x);
}

/* Gum Trip hazards: the first TRIP_VIEW_HAZ_OBJECTS pool objects are claimed for the trip (rivals take the free ones after them);
 * object r * 3 + i is hazard i of the chunk in ring slot r. Pool run = hardware sprites POOL_SPRITE_BASE + 3 * object. */
static void pool_sync_trip(const Game *g, int ready) {
    if (!g_haz_claimed) {
        for (u8 k = 0; k < TRIP_VIEW_HAZ_OBJECTS; k++) if (obj_pool_claim(&g_pool, k)) g_pool.obj[k].flags |= POOL_F_TRIPHAZ;
        g_haz_claimed = 1;
    }
    for (u8 r = 0; r < TRIP_GEN_RING; r++) {
        const TripChunk *ch = trip_view_ring_chunk(&g->trip_gen, r, ready);
        for (u8 i = 0; i < TRIP_VIEW_HAZ_PER_CHUNK; i++) {
            PoolObj *p = &g_pool.obj[r * TRIP_VIEW_HAZ_PER_CHUNK + i];
            TripViewHaz v;
            if (!(p->flags & POOL_F_TRIPHAZ)) continue;
            if (!trip_view_haz_art(ch, i, g->trip.px, g->trip.steps, &v)) { p->flags &= (u8)~POOL_F_TRIPHAZ_ON; continue; }
            p->flags |= POOL_F_TRIPHAZ_ON;
            p->type = (u8)v.kind;
            p->anim = (u8)v.frame;
            p->x = (int32_t)v.left << 16;
            p->y = (int32_t)v.top << 16;
        }
    }
}

static void pool_show_haz(PoolObj *p, u8 i, u16 *scb3) {
    static const u8 k_anim[3] = { TRIPHAZ_ANIM_COAL, TRIPHAZ_ANIM_VENT, TRIPHAZ_ANIM_CLOUD };
    if (!(p->flags & POOL_F_TRIPHAZ_ON)) { if (g_pool_drawn[i]) pool_hide_run(i); return; }
    u8 fi = (u8)(triphaz_anims[k_anim[p->type]].first_frame + p->anim);
    const TriphazFrame *f = &triphaz_frames[fi];
    u16 slot = obj_pool_sprite(&g_pool, i);
    if (g_pool_drawn[i] != (u8)(fi + 1)) {
        gfx_sprite_strips(slot, f->tiles_w, f->tiles_h, &triphaz_tile_index[f->tile_offset], TRIPHAZ_TILE_BASE, (u16)((TRIPHAZ_PAL_SLOT + f->palette) << 8));
        if (g_pool_cols[i] != f->tiles_w) {
            gfx_sprite_chain(slot, f->tiles_w);
            for (u8 c = f->tiles_w; c < POOL_COLS; c++) obs_hide_slot(slot + c);
            g_pool_cols[i] = f->tiles_w;
        }
        g_pool_drawn[i] = (u8)(fi + 1);
    }
    scb3[i] = gfx_scb3_word(f->tiles_h, obj_pool_px(p->y));
    g_pool_scb4[i] = gfx_scb4_word(obj_pool_px(p->x));
    g_trip_haz_draws++;
}

static void pool_show(void) {
    u16 scb3[POOL_MAX];
    u32 m = obj_pool_take_hidden(&g_pool);
    g_gum_pose[1].drawn = 0;   /* set again by pool_show_hero when the player 2 body is drawn */
    for (u8 i = 0; m; i++, m >>= 1) if (m & 1) pool_hide_run(i);
    PoolObj *p = g_pool.obj;
    u8 top = 0; /* objects 0..top-1 go out in the runs: above the last live one every head SCB3 is already 0 (pool_hide_run) and x unchanged */
    u8 left = g_pool.live; /* the walk stops after the last live object */
    for (u8 i = 0; i < POOL_MAX && left; i++, p++) {
        scb3[i] = 0;
        if (!(p->flags & POOL_F_LIVE)) continue;
        top = (u8)(i + 1);
        left--;
        if (p->flags & POOL_F_TRIPHAZ) { pool_show_haz(p, i, scb3); continue; }
        if (p->flags & POOL_F_HERO) { pool_show_hero(p, i, scb3); continue; }
        const ObsAnim *a = &obs_anims[p->type];
        obj_pool_anim(p, obstacle_view_ticks(p->type), a->frame_count);
        u8 fi = (u8)(a->first_frame + p->anim);
        const ObsFrame *f = &obs_frames[fi];
        /* world objects go through the camera; the stress hook's drifters live in screen space */
        int w = f->tiles_w * 16;
        int x = (p->flags & POOL_F_STRESS) ? obj_pool_px(p->x) - f->pad_left
                                           : camera_screen_x(obj_pool_px(p->x) - f->pad_left, g_cam_px, w);
        u16 slot = obj_pool_sprite(&g_pool, i);
        if ((p->flags & POOL_F_STRESS) ? x + f->pad_left >= SCREEN_W : !camera_visible(x, w)) { pool_hide_run(i); continue; }
        int top = obj_pool_px(p->y) - f->tiles_h * 16; /* art bottom = anchor */
        u16 attr = (u16)((OBS_PAL_SLOT + f->palette) << 8);
        if (g_pool_drawn[i] != (u8)(fi + 1)) {
            /* Everything of the run that does not move: tiles, the sticky chain and the hidden spare columns. Tiles
             * change with the frame, the chain only with the width (a hide clears both caches), so a moving object
             * costs just its two run words. */
            gfx_sprite_strips(slot, f->tiles_w, f->tiles_h, &obs_tile_index[f->tile_offset], OBS_TILE_BASE, attr);
            if (g_pool_cols[i] != f->tiles_w) {
                gfx_sprite_chain(slot, f->tiles_w);
                for (u8 c = f->tiles_w; c < POOL_COLS; c++) obs_hide_slot(slot + c);
                g_pool_cols[i] = f->tiles_w;
            }
            g_pool_drawn[i] = (u8)(fi + 1);
        }
        scb3[i] = gfx_scb3_word(f->tiles_h, top);
        g_pool_scb4[i] = gfx_scb4_word(x);
    }
    if (top) { /* the run walk cost about 18 raster lines for all POOL_MAX words; the arcade uses only the first few objects */
        gfx_scb_run(ADDR_SCB3 + POOL_SPRITE_BASE, POOL_COLS, scb3, top);
        gfx_scb_run(ADDR_SCB4 + POOL_SPRITE_BASE, POOL_COLS, g_pool_scb4, top);
    }
    g_pool_live = g_pool.live;
    if (g_pool.live) g_pool_frames++;
}

/* Arcade stage elements (src/core/arc_view.h): vent, spark, flipper, grabber, hatch, in the ARC_ELEM_SPRITE columns. Which frame and where
 * is core logic (arc_view_build); here the blocks become strips. Slots are filled from the top of the range down: a higher sprite draws
 * in front, so the bodies (built first) draw over the sparks and still win the slots when the range runs out. The rest are hidden every
 * frame (gfx_word drops unchanged words), which also covers a mode, stage or state change and the arena. */
_Static_assert(ARCADE_VENT_ART_W == 32 && ARCADE_SPARK_ART_W == 16 && ARCADE_FLIPPER_ART_W == 40 && ARCADE_GRABBER_ART_W == 40 && ARCADE_GRABBER_ART_H == 44,
               "arcade art sizes differ from ARC_VIEW_W/H in core/arc_view.h");
_Static_assert(ARCADE_VENT_FRAMES == ARCADE_PIECE_BODY_A_COUNT && ARCADE_SPARK_FRAMES == ARCADE_PIECE_SPARK_A_COUNT && ARCADE_FLIPPER_FRAMES == ARCADE_PIECE_FLIPPER_A_COUNT &&
               ARCADE_GRABBER_FRAMES == ARC_GRAB_FRAMES && ARCADE_PIECE_HATCH_COUNT == 1 && ARCADE_PIECE_WARN_COUNT == 19, "arcade frame counts differ from arc_view");
_Static_assert(ARCADE_MAX_COLUMNS <= 3, "arcade frames are at most 3 columns (ARC_VIEW_COLS)");
static const u8 k_arc_anim[ARCV_PIECES] = { ARCADE_ANIM_VENT, ARCADE_ANIM_STORM, ARCADE_ANIM_PLAYER, ARCADE_ANIM_PLAYER, ARCADE_ANIM_STORM, ARCADE_ANIM_VENT };
static const u8 k_arc_first[ARCV_PIECES] = { ARCADE_PIECE_BODY_A_FIRST, ARCADE_PIECE_SPARK_A_FIRST, ARCADE_PIECE_FLIPPER_A_FIRST, ARCADE_PIECE_GRABBER_A_FIRST, ARCADE_PIECE_HATCH_FIRST, ARCADE_PIECE_WARN_FIRST };
/* Vent glow: entries 1..5 (outline and metal) of the vent body's own palette line, one row per heat step, written on a step change only. */
static const u16 k_vent_heat[] = ARCADE_TABLE_VENT_HEAT;
_Static_assert(sizeof k_vent_heat / sizeof k_vent_heat[0] == ARC_VIEW_HEAT_STEPS * 5, "vent_heat table differs from arc_view heat steps");
static u8 g_arc_heat; /* step the vent line holds (0: the sheet colours, as loaded) */
static u16 g_arc_tick;
static u8 g_arc_dirty; /* slots may hold element sprites: hide them once after the last draw, not every frame (vblank budget) */
/* Like g_pool_drawn: arcade frame index + 1 whose strips and sticky chain column c holds as a block start (0: unknown or not a start). Every
 * column in use is rewritten each frame and the free ones are hidden, so a start column that still holds the same frame holds its whole block. */
static u8 g_arc_drawn[ARC_ELEM_COUNT];
static ArcSprite g_arc_last[ARC_VIEW_MAX]; /* blocks and camera of the last placement: the same again places the same words, so the loop is skipped */
static int g_arc_last_n = -1, g_arc_last_cam;
/* Per block index of the last placement: frame index, columns used before it, columns it took (0: not placed). A block equal to last
 * time with the same columns before it lands in the same slot with the same frame, so its strips, chain and SCB3 word still hold
 * (the other blocks of a frame use disjoint slots); it is skipped, or with a moved camera gets only its SCB4 word. */
static u8 g_arc_fi[ARC_VIEW_MAX], g_arc_u0[ARC_VIEW_MAX], g_arc_add[ARC_VIEW_MAX];
static u8 g_arc_used = ARC_ELEM_COUNT; /* columns used last frame (top of the range); the ones below are already hidden */
_Static_assert(ARCADE_FRAME_COUNT < 255, "arc frame cache holds frame index + 1 in a byte");

static void arcade_elems_forget(void) {
    for (u8 c = 0; c < ARC_ELEM_COUNT; c++) g_arc_drawn[c] = 0;
    g_arc_used = ARC_ELEM_COUNT;
    g_arc_dirty = 1;
    g_arc_last_n = -1;
}

static int arc_blocks_same(const ArcSprite *b, int n) {
    const ArcSprite *l = g_arc_last;
    for (; n > 0; n--, b++, l++) if (b->x != l->x || b->y != l->y || b->piece != l->piece || b->frame != l->frame) return 0;
    return 1;
}

static void arcade_elems_step(const Game *g) {
    ArcSprite blocks[ARC_VIEW_MAX];
    int n = 0, used = 0;
    if (!g && !g_arc_dirty) return;
    g_arc_dirty = g != 0;
    if (g) n = arc_view_build(&g->elems, g_arc_tick++, blocks);
    u8 heat = g ? (u8)arc_view_heat(&g->elems) : 0;
    if (heat != g_arc_heat) {
        for (u8 c = 0; c < 5; c++) gfx_pal((u16)((ARCADE_PAL_SLOT + arcade_frames[arcade_anims[ARCADE_ANIM_VENT].first_frame].palette) * 16 + 1 + c), k_vent_heat[heat * 5 + c]);
        g_arc_heat = heat;
    }
    if (!g) g_arc_last_n = -1;
    else if (n == g_arc_last_n && g_arc_last_cam == (int)g_cam_px && arc_blocks_same(blocks, n)) return;
    int cam_same = g_arc_last_cam == (int)g_cam_px;
    for (int i = 0; i < n; i++) {
        const ArcSprite *b = &blocks[i], *l = &g_arc_last[i];
        int same = i < g_arc_last_n && b->x == l->x && b->y == l->y && b->piece == l->piece && b->frame == l->frame;
        int keep = same && g_arc_add[i] && g_arc_u0[i] == used;
        if (keep && cam_same) { used += g_arc_add[i]; continue; }
        u8 fi = same ? g_arc_fi[i] : (u8)(arcade_anims[k_arc_anim[b->piece]].first_frame + k_arc_first[b->piece] + b->frame);
        const ArcadeFrame *f = &arcade_frames[fi];
        int w = f->tiles_w * 16, sx = camera_screen_x(b->x - f->pad_left, g_cam_px, w);
        g_arc_fi[i] = fi;
        g_arc_u0[i] = (u8)used;
        g_arc_add[i] = 0;
        if (used + f->tiles_w > ARC_ELEM_COUNT || !camera_visible(sx, w)) continue;
        int s = ARC_ELEM_COUNT - used - f->tiles_w;
        u16 slot = (u16)(ARC_ELEM_SPRITE + s);
        if (!keep) {
            if (g_arc_drawn[s] != (u8)(fi + 1)) {
                gfx_sprite_strips(slot, f->tiles_w, f->tiles_h, &arcade_tile_index[f->tile_offset], ARCADE_TILE_BASE, (u16)((ARCADE_PAL_SLOT + f->palette) << 8));
                gfx_sprite_chain(slot, f->tiles_w);
                g_arc_drawn[s] = (u8)(fi + 1);
                for (int c = 1; c < f->tiles_w; c++) g_arc_drawn[s + c] = 0;
            }
            gfx_word((u16)(ADDR_SCB3 + slot), gfx_scb3_word(f->tiles_h, b->y - f->pad_top));
        }
        gfx_word((u16)(ADDR_SCB4 + slot), gfx_scb4_word(sx));
        g_arc_add[i] = f->tiles_w;
        used += f->tiles_w;
    }
    for (int i = ARC_ELEM_COUNT - g_arc_used; i < ARC_ELEM_COUNT - used; i++) { obs_hide_slot(ARC_ELEM_SPRITE + i); g_arc_drawn[i] = 0; }
    g_arc_used = (u8)used;
    if (g) { memcpy(g_arc_last, blocks, (size_t)n * sizeof blocks[0]); g_arc_last_n = n; g_arc_last_cam = (int)g_cam_px; }
}

/* Bonus stage: bubbles (Gum Trip pickup art, 2 sprite columns each) in the first slots of the shared strip range, in the order of the live
 * bubbles (at most ARC_BONUS_LIVE_MAX at once, 2 slots each); then the 4 gum nozzles in front of them and their mouth puffs (2 columns each);
 * the floor strip in the island slots (the bonus layout draws no islands, island_layout.c), 2 columns per 32 px tile. Arcade art, palette ARCADE_ANIM_NOZZLE. */
#define BONUS_NOZZLE_SPRITE (ARC_BONUS_SPRITE + 2 * ARC_BONUS_LIVE_MAX)
#define BONUS_PUFF_SPRITE (BONUS_NOZZLE_SPRITE + 2 * ARC_NOZZLE_COUNT)
#define BONUS_FLOOR_TILES (ARC_BONUS_WORLD_W / 32)
_Static_assert(BONUS_PUFF_SPRITE + 2 * ARC_NOZZLE_COUNT <= ARC_BONUS_SPRITE + TRIP_STRIP_COUNT, "bonus sprites exceed the shared strip range");
_Static_assert(ARC_BONUS_COUNT >= 2 * ARC_BONUS_LIVE_MAX && 2 * BONUS_FLOOR_TILES <= ISLAND_COUNT, "bonus sprite slot counts");
_Static_assert(ARCADE_PIECE_NOZZLE0_COUNT == 1 && ARCADE_PIECE_FLOOR_COUNT == 1 && ARCADE_PIECE_PUFF_COUNT == 13 && ARCADE_PUFF_TOTAL_TICKS == ARC_BONUS_PUFF_FRAMES, "bonus art frame counts");
_Static_assert(ARC_BONUS_PUFF_FRAMES <= ARC_BONUS_SPAWN_MIN, "a nozzle cannot fire again inside its burst");
static const u8 k_puff_ticks[ARCADE_PIECE_PUFF_COUNT] = ARCADE_TABLE_PUFF_FRAME_TICKS;
/* Art frame of the burst after e elapsed ticks (e < ARC_BONUS_PUFF_FRAMES). */
static int puff_frame(int e) { int f = 0; while (e >= k_puff_ticks[f]) e -= k_puff_ticks[f++]; return f; }
_Static_assert(TRIPPICKUP_PICKUP_IDLE_FRAMES == ARC_VIEW_BUBBLE_FRAMES, "pickup idle frame count differs from arc_view bubbles");
static u8 g_bonus_dirty;
static int g_bonus_cam = -1; /* camera the floor and nozzles were last placed for; -1 = place them again */
static const u16 k_bonus_hidden[48]; /* SCB3 height 0 */

static void bonus_piece(u16 slot, int piece, int x, int y) {
    const ArcadeFrame *f = &arcade_frames[arcade_anims[ARCADE_ANIM_NOZZLE].first_frame + piece];
    int w = f->tiles_w * 16, sx = camera_screen_x(x - f->pad_left, g_cam_px, w);
    if (!camera_visible(sx, w)) { for (int c = 0; c < f->tiles_w; c++) obs_hide_slot(slot + c); return; }
    gfx_sprite_strips(slot, f->tiles_w, f->tiles_h, &arcade_tile_index[f->tile_offset], ARCADE_TILE_BASE, (u16)((ARCADE_PAL_SLOT + f->palette) << 8));
    gfx_sprite_place(slot, f->tiles_w, f->tiles_h, sx, y - f->pad_top);
}

#define BONUS_STATIC_COLS (2 * BONUS_FLOOR_TILES + 2 * ARC_NOZZLE_COUNT)
#define BONUS_COL_UNKNOWN (CAMERA_COL_HIDDEN - 1)
static s16 g_bonus_cx[BONUS_STATIC_COLS]; /* screen x last sent per floor / nozzle column, CAMERA_COL_HIDDEN, or BONUS_COL_UNKNOWN */
static u16 g_bonus_scb4[BONUS_STATIC_COLS];
static const u16 *g_bonus_bub_tiles[ARC_BONUS_LIVE_MAX]; /* tiles last queued per bubble slot: an unchanged frame skips gfx_sprite_strips (its dedupe cost 2 raster lines a bubble) */
static u16 g_bonus_bub_on; /* bit i: bubble slot i is shown and its two columns are chained */
static u8 g_bonus_puff_on; /* bit k: nozzle k's puff sprite is shown */

/* The floor tiles and nozzles never move except with the camera: like island.c, strips and size words go out once, then per camera step
 * one camera_screen_x per piece, SCB3 only when a column enters or leaves the screen and one run op for the SCB4 x words (the per-piece
 * gfx_sprite_place of every frame cost about 60 raster lines of the logic budget when the camera scrolled). */
static void bonus_static_place(void) {
    int idx = 0, piece, moved = 0, first;
    /* The bonus floor shares the island slots: the island reload of the bonus layout parks them all on its first step, and the
       camera does not move until the player does, so placing before the load ends left the floor off screen until the first move. */
    if (!island_loaded()) { g_bonus_cam = -1; return; }
    first = g_bonus_cam < 0;
    if (g_bonus_cam == (int)g_cam_px) return;
    g_bonus_cam = (int)g_cam_px;
    if (first) for (idx = 0; idx < BONUS_STATIC_COLS; idx++) g_bonus_cx[idx] = BONUS_COL_UNKNOWN;
    idx = 0;
    for (piece = 0; piece < BONUS_FLOOR_TILES + ARC_NOZZLE_COUNT; piece++) {
        int fl = piece < BONUS_FLOOR_TILES, k = piece - BONUS_FLOOR_TILES;
        const ArcadeFrame *f = &arcade_frames[arcade_anims[ARCADE_ANIM_NOZZLE].first_frame + (fl ? ARCADE_PIECE_FLOOR_FIRST : ARCADE_PIECE_NOZZLE0_FIRST + k)];
        u16 slot = (u16)(fl ? ISLAND_SPRITE + 2 * piece : BONUS_NOZZLE_SPRITE + 2 * k);
        int y = (fl ? ARC_FLOOR_Y : arc_nozzle_top(k)) - f->pad_top;
        int sx0 = camera_screen_x((fl ? 32 * piece : arc_nozzle_x(k)) - f->pad_left, g_cam_px, 16);
        if (first) {
            gfx_sprite_strips(slot, f->tiles_w, f->tiles_h, &arcade_tile_index[f->tile_offset], ARCADE_TILE_BASE, (u16)((ARCADE_PAL_SLOT + f->palette) << 8));
            gfx_sprite_unchained(slot, f->tiles_w);
        }
        for (int c = 0; c < f->tiles_w; c++, idx++, sx0 += 16) {
            int sx = camera_strip_x(sx0);
            s16 *last = &g_bonus_cx[idx];
            if (sx == *last) continue;
            if (sx == CAMERA_COL_HIDDEN) {
                gfx_word((u16)(ADDR_SCB3 + slot + c), 0);
            } else {
                if (*last == CAMERA_COL_HIDDEN || *last == BONUS_COL_UNKNOWN) gfx_word((u16)(ADDR_SCB3 + slot + c), gfx_scb3_word(f->tiles_h, y));
                g_bonus_scb4[idx] = gfx_scb4_word(sx);
                moved = 1;
            }
            *last = (s16)sx;
        }
    }
    if (moved) {
        gfx_scb_run((u16)(ADDR_SCB4 + ISLAND_SPRITE), 1, g_bonus_scb4, (u8)(2 * BONUS_FLOOR_TILES));
        gfx_scb_run((u16)(ADDR_SCB4 + BONUS_NOZZLE_SPRITE), 1, g_bonus_scb4 + 2 * BONUS_FLOOR_TILES, (u8)(2 * ARC_NOZZLE_COUNT));
    }
}

static void arcade_bonus_step(const Game *g) {
    ArcSprite blocks[ARC_BONUS_LIVE_MAX];
    static u16 bub3[ARC_BONUS_LIVE_MAX], bub4[ARC_BONUS_LIVE_MAX]; /* head SCB3 / SCB4 per bubble slot, sent as two strided runs (as pool_show) */
    int n = 0;
    if (!g && !g_bonus_dirty) return;
    if (!g) { /* the bonus is over: park the bubble, nozzle, puff and floor slots (two runs, once) */
        gfx_scb_run((u16)(ADDR_SCB3 + ARC_BONUS_SPRITE), 1, k_bonus_hidden, (u8)(BONUS_PUFF_SPRITE + 2 * ARC_NOZZLE_COUNT - ARC_BONUS_SPRITE));
        gfx_scb_run((u16)(ADDR_SCB3 + ISLAND_SPRITE), 1, k_bonus_hidden, 2 * BONUS_FLOOR_TILES);
        g_bonus_dirty = 0;
        g_bonus_cam = -1;
        g_bonus_puff_on = 0;
        g_bonus_bub_on = 0;
        for (int i = 0; i < ARC_BONUS_LIVE_MAX; i++) g_bonus_bub_tiles[i] = 0;
        for (int i = 0; i < BONUS_STATIC_COLS; i++) g_bonus_cx[i] = BONUS_COL_UNKNOWN;
        return;
    }
    g_bonus_dirty = 1;
    n = arc_view_bonus_build(&g->bonus, blocks);
    for (int i = 0; i < ARC_BONUS_LIVE_MAX; i++) {
        u16 slot = (u16)(ARC_BONUS_SPRITE + 2 * i);
        bub3[i] = 0;
        if (i < n) {
            const ArcSprite *b = &blocks[i];
            const TrippickupFrame *f = &trippickup_frames[trippickup_anims[TRIPPICKUP_ANIM_PICKUP_IDLE].first_frame + b->frame];
            int sx = camera_screen_x(b->x, g_cam_px, 32);
            if (camera_visible(sx, 32)) {
                const u16 *tl = &trippickup_tile_index[f->tile_offset];
                if (g_bonus_bub_tiles[i] != tl) { gfx_sprite_strips(slot, 2, 2, tl, TRIPPICKUP_TILE_BASE, (u16)(TRIPPICKUP_PAL_SLOT << 8)); g_bonus_bub_tiles[i] = tl; }
                if (!(g_bonus_bub_on & (1u << i))) { gfx_sprite_chain(slot, 2); g_bonus_bub_on |= 1u << i; } /* the chain words go out once, then 2 words a frame */
                bub3[i] = gfx_scb3_word(2, b->y);
                bub4[i] = gfx_scb4_word(sx);
                continue;
            }
        }
        if (g_bonus_bub_on & (1u << i)) { obs_hide_slot(slot); obs_hide_slot(slot + 1); g_bonus_bub_on &= ~(1u << i); g_bonus_bub_tiles[i] = 0; }
    }
    gfx_scb_run((u16)(ADDR_SCB3 + ARC_BONUS_SPRITE), 2, bub3, ARC_BONUS_LIVE_MAX);
    gfx_scb_run((u16)(ADDR_SCB4 + ARC_BONUS_SPRITE), 2, bub4, ARC_BONUS_LIVE_MAX);
    bonus_static_place();
    for (int k = 0; k < ARC_NOZZLE_COUNT; k++) {
        int top = arc_nozzle_top(k), x = arc_nozzle_x(k), p = g->bonus.puff[k];
        if (p) { bonus_piece((u16)(BONUS_PUFF_SPRITE + 2 * k), ARCADE_PIECE_PUFF_FIRST + puff_frame(ARC_BONUS_PUFF_FRAMES - p), x, top - 24); g_bonus_puff_on |= (u8)(1 << k); }
        else if (g_bonus_puff_on & (1 << k)) { obs_hide_slot((u16)(BONUS_PUFF_SPRITE + 2 * k)); obs_hide_slot((u16)(BONUS_PUFF_SPRITE + 2 * k + 1)); g_bonus_puff_on &= (u8)~(1 << k); }
    }
}

/* Roost Rule marker (PARTY): the bonus bubble art floating over the roost island; g = the playing Game with the rule, or 0 to park it. */
static const u16 *g_roost_tiles;
static u8 g_roost_on;
static void roost_marker_step(const Game *g) {
    int x, top, w;
    if (g && game_roost_rect(g, &x, &top, &w)) {
        int fr = (int)((g->frame >> 2) & (TRIPPICKUP_PICKUP_IDLE_FRAMES - 1));
        int sx = camera_screen_x(x + w / 2 - 16, g_cam_px, 32);
        if (camera_visible(sx, 32)) {
            const TrippickupFrame *f = &trippickup_frames[trippickup_anims[TRIPPICKUP_ANIM_PICKUP_IDLE].first_frame + fr];
            const u16 *tl = &trippickup_tile_index[f->tile_offset];
            u16 s3 = gfx_scb3_word(2, top - 40), s4 = gfx_scb4_word(sx);
            if (g_roost_tiles != tl) { gfx_sprite_strips(ROOST_SPRITE, 2, 2, tl, TRIPPICKUP_TILE_BASE, (u16)(TRIPPICKUP_PAL_SLOT << 8)); g_roost_tiles = tl; }
            if (!g_roost_on) { gfx_sprite_chain(ROOST_SPRITE, 2); g_roost_on = 1; }
            gfx_scb_run((u16)(ADDR_SCB3 + ROOST_SPRITE), 1, &s3, 1);
            gfx_scb_run((u16)(ADDR_SCB4 + ROOST_SPRITE), 1, &s4, 1);
            return;
        }
    }
    if (g_roost_on) { obs_hide_slot(ROOST_SPRITE); obs_hide_slot(ROOST_SPRITE + 1); g_roost_on = 0; g_roost_tiles = 0; }
}

/* Toss Gum bubble (PARTY): the gum bubble B over the carrier's head, one 16x16 sprite in the Roost marker slot (the rules never run together).
 * g = the playing Game, or 0 to park it. The 12-step sequence in gumbubble_tables.h loops; the fuse speeds the wobble up as it runs low. */
static const u8 g_tossb_cell[GUMBUBBLE_SEQ_COUNT] = GUMBUBBLE_TABLE_SEQ_CELL;
static const s8 g_tossb_dx[GUMBUBBLE_SEQ_COUNT] = GUMBUBBLE_TABLE_SEQ_DX;
static const s8 g_tossb_dy[GUMBUBBLE_SEQ_COUNT] = GUMBUBBLE_TABLE_SEQ_DY;
static const u8 g_tossb_ticks[GUMBUBBLE_SEQ_COUNT] = GUMBUBBLE_TABLE_SEQ_TICKS;
static u8 g_tossb_on;
static u8 g_tossb_cell_shown = 0xFF;
static s16 g_tossb_x, g_tossb_y;     /* the gum knot (bottom centre of the bubble cell), arena pixels */
static s16 g_tossb_x0, g_tossb_y0;   /* where the knot left the wing: start of the arc */
static u8 g_tossb_live, g_tossb_arc;
/* The gum point on the wing of the bird on a seat, for a pose cell. */
static void toss_anchor(const Game *g, u8 seat, int pose, int *x, int *y) {
    const Flier *f = game_toss_flier(g, seat);
    u8 ax = g_toss_ax[pose];
    *x = (int)(f->x >> 16) - FLIER_HALF_W - SOOT_BOX_DX + (seat >= 2 ? 31 - ax : ax);
    *y = (int)((f->y + flier_half_h(f)) >> 16) - 32 + g_toss_ay[pose];
}
static int toss_slide(int from, int to) { int d = to - from; return from + (d > 6 ? 6 : d < -6 ? -6 : d); }
/* The knot never jumps: on a wing it slides to the pose's gum point (6 px a frame at most), in the air it flies a 46 px high arc from where
 * it left the wing to the catch point of the target, and the catch poses take it over from there. */
static void toss_bubble_step(const Game *g) {
    const GgToss *tt = g && g->gg_toss ? &g->toss : 0;
    if (tt && (tt->phase == GT_HOLD || tt->phase == GT_FLIGHT)) {
        int t = (int)fd_umod(g->frame * (1u + (tt->fuse < 150u) + (tt->fuse < 60u)), GUMBUBBLE_LOOP_TICKS), k = 0, sx, x, y, pose = -1;
        while (k < GUMBUBBLE_SEQ_COUNT - 1 && t >= g_tossb_ticks[k]) { t -= g_tossb_ticks[k]; k++; }
        if (tt->phase == GT_FLIGHT && tt->t >= GT_RELEASE_FRAME) {
            int n = GT_FLIGHT_FRAMES - GT_RELEASE_FRAME, a = tt->t - GT_RELEASE_FRAME + 1;
            if (!g_tossb_arc) { g_tossb_arc = 1; g_tossb_x0 = g_tossb_x; g_tossb_y0 = g_tossb_y; }
            if (a > n) a = n;
            toss_anchor(g, tt->target, GT_POSE_CATCH, &x, &y);
            g_tossb_x = (s16)(g_tossb_x0 + (x - g_tossb_x0) * a / n);
            g_tossb_y = (s16)(g_tossb_y0 + (y - g_tossb_y0) * a / n - 4 * 46 * a * (n - a) / (n * n));
        } else {
            pose = gg_toss_pose(tt, tt->carrier);
            toss_anchor(g, tt->carrier, pose < 0 ? GT_POSE_CARRY : pose, &x, &y);
            g_tossb_x = (s16)(g_tossb_live ? toss_slide(g_tossb_x, x) : x);
            g_tossb_y = (s16)(g_tossb_live ? toss_slide(g_tossb_y, y) : y);
            g_tossb_arc = 0;
        }
        g_tossb_live = 1;
        sx = camera_screen_x(g_tossb_x - 8 + g_tossb_dx[k], game_flier_cam_px(g), 16);   /* Toss Gum birds live in screen space: camera 0 */
        if (camera_visible(sx, 16)) {
            g_toss_knot[0] = (s16)(sx + 8 - g_tossb_dx[k]); g_toss_knot[1] = g_tossb_y; g_toss_knot[2] = (s16)pose;
            u16 s3 = gfx_scb3_word(1, g_tossb_y - 16 + g_tossb_dy[k]), s4 = gfx_scb4_word(sx);
            if (g_tossb_cell_shown != g_tossb_cell[k]) {
                gfx_sprite_strips(ROOST_SPRITE, 1, 1, &gumbubble_tile_index[g_tossb_cell[k]], GUMBUBBLE_TILE_BASE, (u16)(GUMBUBBLE_PAL_SLOT << 8));
                g_tossb_cell_shown = g_tossb_cell[k];
            }
            if (!g_tossb_on) { gfx_sprite_unchained(ROOST_SPRITE, 1); g_tossb_on = 1; }
            gfx_scb_run((u16)(ADDR_SCB3 + ROOST_SPRITE), 1, &s3, 1);
            gfx_scb_run((u16)(ADDR_SCB4 + ROOST_SPRITE), 1, &s4, 1);
            return;
        }
    } else g_tossb_live = 0;   /* burst, result or no Toss Gum: the next gum appears on its wing */
    if (g_tossb_on) { obs_hide_slot(ROOST_SPRITE); g_tossb_on = 0; g_tossb_cell_shown = 0xFF; }
}

/* Gum Fling aim aids (GUM arena, aim phase only): a pointer swinging along a quarter circle around the hero with the aim angle, and FLING_ARC_DOTS dots
 * along the real throw path for the current power and angle (gumfling_path: the flight physics itself). Gum bubble art, 16 x 16 unchained sprites in the
 * shared strip range; g = the playing Game with Gum Fling in the arena aim, or 0 to park them. */
#define FLING_ARC_RADIUS 36
#define FLING_ARC_POINTER_ANIM GUM_ANIM_LEVEL4   /* round Pink Gum bubbles; the gumbubble sheet is the angry Hot Gum face and read as a head */
#define FLING_ARC_DOT_ANIM GUM_ANIM_LEVEL1
_Static_assert(FLING_ARC_COUNT <= TRIP_STRIP_COUNT, "fling aim sprites exceed the shared strip range");
static u8 g_fling_arc_on;
static void fling_arc_step(const Game *g) {
    if (g && g->gg_fling && g->mode == GAME_MODE_GUM && g->fling.phase == GF_AIM) {
        const GgFling *f = &g->fling;
        int16_t dx[FLING_ARC_DOTS], dy[FLING_ARC_DOTS];
        u16 s3[FLING_ARC_COUNT], s4[FLING_ARC_COUNT];
        int cx = (int)(g->hero[0].x >> 16), cy = (int)(g->hero[0].y >> 16);
        uint8_t a = (uint8_t)((f->deg * 182u) >> 8);   /* the angle launch_vel uses */
        if (!g_fling_arc_on) {
            for (u16 i = 0; i < FLING_ARC_COUNT; i++) {
                const GumFrame *f = &gum_frames[gum_anims[i ? FLING_ARC_DOT_ANIM : FLING_ARC_POINTER_ANIM].first_frame];
                gfx_sprite_strips((u16)(FLING_ARC_SPRITE + i), 1, 1, &gum_tile_index[f->tile_offset], GUM_TILE_BASE, (u16)((GUM_PAL_SLOT + f->palette) << 8));
                gfx_sprite_unchained((u16)(FLING_ARC_SPRITE + i), 1);
            }
            g_fling_arc_on = 1;
        }
        gumfling_path(f->power, f->deg, dx, dy, FLING_ARC_DOTS);
        for (int i = 0; i < FLING_ARC_COUNT; i++) {
            int wx = i ? cx + dx[i - 1] : cx + (FLING_ARC_RADIUS * flier_cos(a) >> 15);
            int wy = i ? cy - dy[i - 1] : cy - (FLING_ARC_RADIUS * flier_sin(a) >> 15);
            int sx = wx - 8;   /* the hero and the field live in screen space (cam 0) */
            s3[i] = camera_visible(sx, 16) && wy > -8 && wy < 232 ? gfx_scb3_word(1, wy - 8) : 0;
            s4[i] = gfx_scb4_word(sx);
        }
        gfx_scb_run((u16)(ADDR_SCB3 + FLING_ARC_SPRITE), 1, s3, FLING_ARC_COUNT);
        gfx_scb_run((u16)(ADDR_SCB4 + FLING_ARC_SPRITE), 1, s4, FLING_ARC_COUNT);
        return;
    }
    if (g_fling_arc_on) { for (u16 i = 0; i < FLING_ARC_COUNT; i++) obs_hide_slot((u16)(FLING_ARC_SPRITE + i)); g_fling_arc_on = 0; }
}

/* BIOS_USER_MODE: 1 attract, 2 game in progress (coins then only add credits). */
static volatile u8 g_start_pending;
static volatile u8 g_join_p2; /* P2 Start accepted in play (player_start); game_loop joins P2 */
static u8 read_input(void);
volatile u8 g_coin_calls; /* coins the BIOS reported (vector 0x134) and game_loop has not yet played a blip for; also read by MAME tests */

/* COIN_SOUND (vector 0x134, ngdevkit.ld): runs in the BIOS vblank handler, so it only counts. */
void coin_sound(void) { g_coin_calls++; }

/*
 * PLAYER_START (vector 0x128), called by the BIOS from its vblank SYSTEM_IO when a player
 * presses start with credits. The BIOS would also call it when the title compulsion timer
 * runs out, but game_loop writes 0x30 to BIOS_COMPULSION_S (0x10FDDA) every attract frame,
 * so that timer never runs out and the BIOS never forces a start (CREDIT-HOLD). ngdevkit's
 * wrapper_player_start calls this symbol when it is defined (ngdevkit.ld) and otherwise
 * clears BIOS_START_FLAG, which refuses every start. The BIOS deducts the credit only if
 * BIOS_USER_MODE is 2 when this returns, so accepting means: leave the start flag set,
 * set mode 2, and let game_loop start the game on the next frame.
 *
 * Bug fixed here: the game used to start from bios_statchange itself and never accepted
 * PLAYER_START. The credit was never taken, so after a game (high score SYSTEM_RETURN) the
 * BIOS still saw a credit, called USER 3 (title), forced PLAYER_START at the timeout (before
 * CREDIT-HOLD held that timer), got a refusal, and UniBIOS took over (DEMO_END, palette cleared) and called USER 3 again
 * with the timer already expired. That repeated about every 12 frames, so video_init never
 * finished: a blinking screen with only the sky. Guarded by make test-reach (boot 1 keeps
 * running past the title timeout after the save).
 */
void player_start(void) {
    /* P2 Start in arcade play joins by parachute (game_join_p2 in game_loop). Leaving bit 1 set lets the BIOS take the credit;
     * P1 Start keeps its refusal below. Refused moments (game_can_join_p2) clear the flag: the credit stays. */
    if (bios_user_mode == 2 && g_flow.state == FLOW_PLAYING && (bios_start_flag & 2)) {
        if (game_can_join_p2(&g_flow.game) && !g_join_p2) { bios_start_flag = 2; g_join_p2 = 1; }
        else bios_start_flag = 0;
        return;
    }
    /* Accept only where flow_step starts a game on start (title, table, demo), so a taken
     * credit always becomes a game; refuse during play, game over and name entry. */
    u8 st = g_flow.state;
    if (bios_user_mode == 2 || !(bios_start_flag & 1) || st > FLOW_ATTRACT_DEMO ||
        (st == FLOW_ATTRACT_TITLE && (read_input() & FLOW_RESET_COMBO) == FLOW_RESET_COMBO)) {
        bios_start_flag = 0; /* refused: the BIOS keeps the credit */
        return;
    }
    bios_user_mode = 2;
    g_start_pending = 1;
}

/* Off screen marker per human flier (design D1): a '<' or '>' on the fix layer at the screen edge, at the flier's
 * row. The fix layer is free at the edges (the HUD sits in columns 2..), costs no sprite slot and the fix shadow
 * drops unchanged cells. One cell a human; erased when the flier shows again or the match ends. P1 white, P2 gold (sun yellow). */
static void edge_marker(const Game *g, int cam_px) {
    for (int h = 0; h < HUMANS; h++) {
        int dir = 0, row = 0;
        if (g) {
            const Flier *fl = &g->hero[h];
            int w = SOOT_COLUMNS * 16;
            int sx = camera_screen_x((int)(fl->x >> 16) - FLIER_HALF_W - SOOT_BOX_DX, cam_px, w);
            if (h < g->players && fl->state != FLIER_GONE) dir = camera_edge_marker(sx, w);
            row = (int)(fl->y >> 19);
            if (row < 8) row = 8;
            if (row > 24) row = 24;
        }
        u8 col = dir < 0 ? 0 : 39;
        if (g_edge_col[h] != 0xFF && (dir == 0 || col != g_edge_col[h] || row != g_edge_row[h])) {
            gfx_text(g_edge_col[h], g_edge_row[h], PAL_TEXT, " ");
            g_edge_col[h] = 0xFF;
        }
        if (dir != 0 && g_edge_col[h] == 0xFF) {
            gfx_text(col, (u8)row, h ? PAL_HIGH : PAL_TEXT, dir < 0 ? "<" : ">");
            g_edge_col[h] = col; g_edge_row[h] = (u8)row;
        }
    }
}

/* The world (hero, pool, strips, islands, gum) draws in play and in the attract demo: the demo is the same game under the overlay. */
/* Background hold (owner rule "no visible pop-in"): a mood change rewrites the 110 plane columns over about 14 frames with the
 * planes hidden. At play or demo entry the world stays hidden and the game waits until the new mood is complete, so the first
 * frame the player sees has the whole background. g_bg_late counts frames that show the world over an incomplete background. */
#define BG_HOLD_FRAMES 2 /* entry frame plus the first game step, which picks the match mood (game.c match_start) */
static u8 g_bg_hold = BG_HOLD_FRAMES;
volatile u16 g_bg_late; /* test sentinel (tests/mame/vblank_check.lua) */
volatile u8 g_bg_held;
static u8 g_bg_paused; /* this frame the entry hold skipped flow_step: the frame has room for the start work below */
/* Also waits for the hazard strip tiles (hazard_preload, about 66 lines a bank): the reveal frame then only places the strip. */
/* Gum Trip the same way: once the course is built (game steps run the build while held), the game waits for the strip columns and
 * island tiles (trip_strip_step ready 0, island_trip_preload), so the reveal frame only places and shows them. */
/* Stadium stands: Big Blow, Burst Race and Gum Fling (stadium_hw.c); never the intro cards or the other events. */
static u8 stadium_on(const Game *g) {
    return g->mode == GAME_MODE_GUM && !g->gg_gather && !g->gg_pop && !g->gg_poop && !g->gg_dash && !seated(g);
}
static u8 cap99(uint32_t v) { return v > 99u ? 99u : (u8)v; }
static u8 g_trip_islands_loaded;
/* The Gum Fling grass field also hosts Toss Gum: one gate for both. The field reads the Fling state only for the flight scroll and landing puff; Toss Gum passes an idle one. */
static u8 ground_field(const Game *g) { return g && (g->gg_fling || g->gg_toss || g->gg_tug); }
static u8 pop_field(const Game *g) { return g && g->gg_pop; }
static u8 poop_field(const Game *g) { return g && g->gg_poop; }   /* Poop the Man draws no water floor and no islands */
static const GgFling g_idle_fling;   /* all zero: wind-up phase, no scroll */
static u8 bg_pending(void) {
    u8 world = g_flow.state == FLOW_PLAYING || g_flow.state == FLOW_ATTRACT_DEMO;
    u8 trip = world && g_flow.game.mode == GAME_MODE_TRIP;
    return g_bg_mood_busy || g_bg_mood != g_flow.game.mood || (world && !trip && !ground_field(&g_flow.game) && !hazard_preloaded())
        || (world && ground_field(&g_flow.game) && !fling_field_loaded())
        || (world && poop_field(&g_flow.game) && !poop_walkway_loaded())
        || (world && stadium_on(&g_flow.game) && !stadium_hw_loaded())
        || (trip && game_trip_ready(&g_flow.game) && !(trip_strip_loaded() && g_trip_islands_loaded));
}
/* Gum Trip entry: the course build steps run held (world hidden); the reveal waits for the course. */
static u8 trip_building(void) {
    return (g_flow.state == FLOW_PLAYING || g_flow.state == FLOW_ATTRACT_DEMO) && g_flow.game.mode == GAME_MODE_TRIP && !game_trip_ready(&g_flow.game);
}
static u8 world_state(const FlowView *v) { return (v->state == FLOW_PLAYING || v->state == FLOW_ATTRACT_DEMO) && v->game; }
static u8 world_shown(const FlowView *v) { return world_state(v) && !g_bg_hold; }
/* Storm rain (src/core/rain.c): fix layer drops in every storm-mood world, Pop Drop and the Gum Fling field excepted. The rain palette is its own fix
 * slot (RAIN_PAL_SLOT); the burst colour is written while a lightning flash lasts. */
static Rain g_rain;
static u8 g_rain_pal = 2; /* 0 normal, 1 burst, 2 not written yet */
static s32 g_rain_cam;
u16 g_rain_lines = 64; /* rain_step cost in raster lines, measured each storm frame (rain_frame); 64 until the first measurement */
static void rain_pal_put(u8 burst) {
    const u16 *p = burst ? rain_burst_palette : rain_palette;
    for (u8 i = 0; i < 5; i++) gfx_pal((u16)(RAIN_PAL_SLOT * 16 + 1 + i), p[i]);
    g_rain_pal = burst;
}
static void rain_frame(const FlowView *v) {
    const Game *g = v->game;
    u8 on = world_shown(v) && g && g_bg_mood == GAME_MOOD_STORM && !g_bg_mood_busy && !ground_field(g) && !pop_field(g);
    u8 trip = g && g->mode == GAME_MODE_TRIP;
    s32 d = g_cam_unwrapped - g_rain_cam;
    g_rain_cam = g_cam_unwrapped;
    if (on && g_rain_pal != rain_burst_active(&g_rain)) rain_pal_put(rain_burst_active(&g_rain));
    /* rain_step itself must end before VQ_FIX_LINE_END: a storm frame that reached it late ran it into vblank and skipped the flush
     * (make test-scroll, 75 of 99 skipped steps had the PC in rain_step; thoughts/spot/2026-11-22-rain-fix.md). Lines left (one fix
     * cell a line) at or under rain_step's own measured cost: rain holds still this frame. */
    u16 l0 = VQ_RASTER_LINE(*REG_LSPCMODE);
    if (on && g_rain.was_active && vq_fix_line_budget(l0) <= g_rain_lines) { bg_flash(rain_flash_index(&g_rain)); return; }
    rain_step(&g_rain, &g_gfx_q, on, trip ? RAIN_MODE_TRIP : stadium_on(g) ? RAIN_MODE_STADIUM : RAIN_MODE_ARENA, trip && d > 0 && d < 16 ? (s16)d : 0);
    u16 l1 = VQ_RASTER_LINE(*REG_LSPCMODE);
    if (on && l0 >= 0x110u && l1 > l0) { /* cost: worst recent step, decays a line a frame so a light stretch frees the gate again */
        u16 c = (u16)(l1 - l0);
        g_rain_lines = c > g_rain_lines ? c : (u16)(g_rain_lines - (g_rain_lines > c));
    }
    bg_flash(rain_flash_index(&g_rain));
}

static void put_number(char *out, u32 v, int width);
/* GET SET / GO! (gg_countdown.h): the glyph frames of the word, centred, in the arcade stage element slots (no Gum Games event draws those).
 * word = GGCD_WORD_*; GGCD_WORD_NONE parks them. Tiles are rewritten only when the word changes. */
#define COUNTDOWN_Y 72 /* top of the words, screen px */
#define COUNTDOWN_POP_STEP_FRAMES 3 /* frames per pop-in step (draft anim_A2_go: 50 ms) */
static u8 g_cd_word, g_cd_cols, g_cd_step = 0xff;
static u8 g_cd_rows[ARC_ELEM_COUNT];
static int g_cd_x[ARC_ELEM_COUNT];
/* Pop-in of the draft (draw_countdown_a2.py): sprite shrink in sixteenths and a y offset, both words; the last step holds. */
static void countdown_place(u8 step) {
    static const u8 shrink[] = {4, 8, 12, 16, 16, 16, 16, 16};
    static const int8_t dy[] = {0, 0, 0, 0, -4, -2, 1, 0};
    u8 s = shrink[step];
    u16 s2[ARC_ELEM_COUNT], s3[ARC_ELEM_COUNT], s4[ARC_ELEM_COUNT];
    for (u8 c = 0; c < g_cd_cols; c++) {
        int hpx = g_cd_rows[c] * 16;
        s2[c] = (u16)(((s - 1) << 8) | (s * 16 - 1));
        s3[c] = gfx_scb3_word(g_cd_rows[c], COUNTDOWN_Y + (hpx - hpx * s / 16) / 2 + dy[step]);
        s4[c] = gfx_scb4_word(160 + (g_cd_x[c] - 160) * s / 16);
    }
    gfx_scb_run((u16)(ADDR_SCB2 + ARC_ELEM_SPRITE), 1, s2, g_cd_cols);
    gfx_scb_run((u16)(ADDR_SCB3 + ARC_ELEM_SPRITE), 1, s3, g_cd_cols);
    gfx_scb_run((u16)(ADDR_SCB4 + ARC_ELEM_SPRITE), 1, s4, g_cd_cols);
}
static void countdown_step(u8 word, u16 t) {
    static const u16 gx[] = COUNTDOWN_TABLE_GETSET_X, ox[] = COUNTDOWN_TABLE_GO_X;
    static const u16 gw[] = COUNTDOWN_TABLE_GETSET_W, ow[] = COUNTDOWN_TABLE_GO_W;
    if (word != g_cd_word) {
        if (word) {
            u8 anim = word == GGCD_WORD_GO ? COUNTDOWN_ANIM_GO : COUNTDOWN_ANIM_GETSET;
            const u16 *xs = word == GGCD_WORD_GO ? ox : gx, *ws = word == GGCD_WORD_GO ? ow : gw;
            u8 n = countdown_anims[anim].frame_count, pal = word == GGCD_WORD_GO ? COUNTDOWN_HOT_PAL_SLOT : COUNTDOWN_PAL_SLOT;
            int left = (320 - (xs[n - 1] + ws[n - 1])) / 2, col = 0;
            for (u8 k = 0; k < n; k++) {
                const CountdownFrame *f = &countdown_frames[countdown_anims[anim].first_frame + k];
                for (u8 c = 0; c < f->tiles_w; c++, col++) {
                    gfx_sprite_strips((u16)(ARC_ELEM_SPRITE + col), 1, f->tiles_h, &countdown_tile_index[f->tile_offset + c * f->tiles_h], COUNTDOWN_TILE_BASE, (u16)(pal << 8));
                    g_cd_rows[col] = f->tiles_h;
                    g_cd_x[col] = left + xs[k] + c * 16;
                }
            }
            g_cd_cols = (u8)col;
            gfx_sprite_unchained(ARC_ELEM_SPRITE, g_cd_cols); /* every glyph column has its own x */
            for (int c = col; c < ARC_ELEM_COUNT; c++) obs_hide_slot((u16)(ARC_ELEM_SPRITE + c));
        } else {
            for (int c = 0; c < ARC_ELEM_COUNT; c++) obs_hide_slot((u16)(ARC_ELEM_SPRITE + c));
        }
        g_cd_word = word;
        g_cd_step = 0xff;
    }
    if (word) {
        u16 tw = word == GGCD_WORD_GO ? t - GGCD_SET_FRAMES - 1 : t - 1;
        u8 step = tw / COUNTDOWN_POP_STEP_FRAMES > 7 ? 7 : (u8)(tw / COUNTDOWN_POP_STEP_FRAMES);
        if (step != g_cd_step) { countdown_place(step); g_cd_step = step; }
    }
}

/* Big Blow on the fix layer: the power bar (changed cells only) and one status line, written when the attempt state changes. */
static void draw_big_blow(const GgBlow *b) {
    u8 n = b->phase == GG_BLOW_INTRO ? 0 : (u8)(b->size / (GG_BLOW_MAX / METER_STEPS));
    if (g_meter_n[0] == METER_NONE) meter_plaque(METER_COL, METER_ROW - 2, flingmeter_label_power);
    meter_tube(METER_ROW, 0, n);
    meter_flash(g_meter_n[0] == METER_STEPS);
    u32 key = (u32)b->phase | (u32)b->seq.tickets[0] << 4 | (u32)b->last_size << 8 | (u32)b->burst << 16 | (u32)b->last_qualified << 17;
    if (key == g_blow_key) return;
    g_blow_key = key;
    char line[BLOW_TEXT_W + 1];
    char nb[10];
    const char *msg = b->phase == GG_BLOW_INTRO ? "BIG BLOW   MASH A AND B" : b->phase == GG_BLOW_PLAY ? "BLOW  DO NOT BURST IT" :
                      b->phase == GG_BLOW_BURST ? "BURST   NO POINTS" : b->last_qualified ? "QUALIFIED" : "NOT QUALIFIED";
    u8 i = 0;
    while (i < BLOW_TEXT_W && msg[i]) { line[i] = msg[i]; i++; }
    if (b->phase == GG_BLOW_RESULT) {
        put_number(nb, b->last_size, 3);
        line[i++] = ' '; line[i++] = ' '; line[i++] = 'S'; line[i++] = 'I'; line[i++] = 'Z'; line[i++] = 'E'; line[i++] = ' ';
        for (u8 k = 0; nb[k] && i < BLOW_TEXT_W; k++) line[i++] = nb[k];
    }
    while (i < BLOW_TEXT_W) line[i++] = ' ';
    line[BLOW_TEXT_W] = 0;
    text((u8)((40 - BLOW_TEXT_W) / 2), BLOW_TEXT_ROW + 2, PAL_TEXT, line);
    {
        const char *tk = "TICKETS ";
        char tl[BLOW_TEXT_W + 1];
        u8 j = 0;
        while (tk[j]) { tl[j] = tk[j]; j++; }
        tl[j++] = (char)('0' + b->seq.tickets[0]);
        while (j < BLOW_TEXT_W) tl[j++] = ' ';
        tl[BLOW_TEXT_W] = 0;
        text((u8)((40 - BLOW_TEXT_W) / 2), BLOW_TEXT_ROW + 4, PAL_TEXT, tl);
    }
}

/* Burst Race on the fix layer: one power tube per side (P1 on METER_ROW, the rival two rows above) and a status line. */
static void draw_burst_race(const GgRace *r) {
    for (u8 q = 0; q < 2; q++) meter_tube((u8)(METER_ROW - 2 * q), q, r->phase == GG_RACE_INTRO ? 0 : (u8)(r->size[q] / (GG_BLOW_MAX / METER_STEPS)));
    meter_flash(g_meter_n[0] == METER_STEPS || g_meter_n[1] == METER_STEPS);
    u32 key = (u32)r->phase | (u32)r->winner << 4 | (u32)r->players << 5;
    if (key == g_blow_key) return;
    g_blow_key = key;
    const char *msg = r->phase == GG_RACE_INTRO ? "BURST RACE   MASH A AND B     " : r->phase == GG_RACE_PLAY ? "BURST YOUR BUBBLE FIRST       " :
                      r->winner == 0 ? "YOU BURST FIRST  YOU WIN    " : r->players == 2 ? "PLAYER 2 BURST FIRST         " : "THE COMPUTER BURST FIRST     ";
    text((u8)((40 - BLOW_TEXT_W) / 2), BLOW_TEXT_ROW + 2, PAL_TEXT, msg);
}


/* Tug Gum strand (tools/make_tug_sheet.py): hand-pixeled 16x16 pieces in the field marker slots (Tug Gum loads no markers), behind the birds.
 * Slots 0..16 left to right: end, 7 run pieces, knot, the 7 run pieces mirrored, end. Slot 17 is the right half of the snap.
 * The strand moves with the knot; the birds stay on their seats. */
#define TUG_STRAND_SPRITE FLFIELD_MARKER_SPRITE
#define TUG_STRAND_COUNT 18
#define TUG_STRAND_TOP 186
_Static_assert(TUG_STRAND_SPRITE + TUG_STRAND_COUNT <= ISLAND_SPRITE + ISLAND_COUNT, "the strand overruns the island slots");
volatile s16 g_tug_knot_x;   /* test probe (tests/mame/party_tug_check.lua): knot centre as drawn, 0 = no strand */
static void tug_strand_step(const Game *g) {
    static const u8 run[3][7] = {   /* end towards knot: slack, taut, stretched to a hair */
        { TUGPOSE_PIECE_THICK, TUGPOSE_PIECE_THICK, TUGPOSE_PIECE_THICK, TUGPOSE_PIECE_THICK, TUGPOSE_PIECE_THICK, TUGPOSE_PIECE_TAPER, TUGPOSE_PIECE_THIN },
        { TUGPOSE_PIECE_THICK, TUGPOSE_PIECE_THICK, TUGPOSE_PIECE_THIN, TUGPOSE_PIECE_THIN, TUGPOSE_PIECE_THIN, TUGPOSE_PIECE_THIN, TUGPOSE_PIECE_HAIR },
        { TUGPOSE_PIECE_THICK, TUGPOSE_PIECE_THIN, TUGPOSE_PIECE_THIN, TUGPOSE_PIECE_HAIR, TUGPOSE_PIECE_HAIR, TUGPOSE_PIECE_HAIR, TUGPOSE_PIECE_HAIR },
    };
    static u8 up, key = 0xFF;
    static s16 at;
    u16 s3[TUG_STRAND_COUNT], s4[TUG_STRAND_COUNT];
    if (!g || !g->gg_tug) {
        if (up) { for (u8 i = 0; i < TUG_STRAND_COUNT; i++) s3[i] = 0; gfx_scb_run((u16)(ADDR_SCB3 + TUG_STRAND_SPRITE), 1, s3, TUG_STRAND_COUNT); }
        up = 0; key = 0xFF; g_tug_knot_x = 0;
        return;
    }
    const GgTug *t = &g->tug;
    int q = t->knot < 0 ? -t->knot : t->knot;
    /* snap: 1 and 2 = the two burst frames over the knot, 3 = two loose ends */
    u8 snap = t->phase == GTG_PLAY ? 0 : t->phase == GTG_SNAP && t->t < 8 ? 1 : t->phase == GTG_SNAP && t->t < 16 ? 2 : 3;
    u8 mode = snap == 3 ? 0 : snap || q >= 96 ? 2 : 1;
    u8 storm = g->mood == GAME_MOOD_STORM;   /* thicker thin pieces: the strand was faint on the storm field */
    u8 k = (u8)(mode | snap << 2 | storm << 4);
    s16 dx = (s16)(t->knot / 4);
    if (!up) gfx_sprite_unchained(TUG_STRAND_SPRITE, TUG_STRAND_COUNT);
    if (up && k == key && dx == at) return;
    for (u8 i = 0; i < TUG_STRAND_COUNT; i++) {
        u8 m = i > 8 ? (u8)(16 - i) : i;   /* mirrored place: 0 end, 1..7 run, 8 knot */
        u8 piece = m == 0 ? TUGPOSE_PIECE_END : m == 8 ? TUGPOSE_PIECE_KNOT : run[mode][m - 1];
        u8 flip = i > 8, show = i < 17;
        int x = 24 + 16 * i;
        if (storm && piece >= TUGPOSE_PIECE_TAPER && piece <= TUGPOSE_PIECE_HAIR) piece = (u8)(piece + TUGPOSE_PIECE_TAPER_STORM - TUGPOSE_PIECE_TAPER);
        if (snap == 3) {   /* loose ends on places 6 and 10, nothing between */
            if (m == 6) piece = TUGPOSE_PIECE_SNAP2;
            if (m > 6) show = 0;
        } else if (snap) {   /* burst halves at 144 and 160; places 7 and 9 step aside under their same-piece neighbours */
            if (i == 7) x = 128;
            if (i == 9) x = 176;
            if (i == 8 || i == 17) { piece = (u8)(TUGPOSE_PIECE_SNAP0 + snap - 1); x = i == 8 ? 144 : 160; flip = i == 17; show = 1; }
        }
        if ((!up || k != key) && show) {
            const TugposeFrame *f = &tugpose_frames[tugpose_anims[TUGPOSE_ANIM_STRAND].first_frame + piece];
            gfx_sprite_strips((u16)(TUG_STRAND_SPRITE + i), 1, 1, &tugpose_tile_index[f->tile_offset], TUGPOSE_TILE_BASE, (u16)((TUGPOSE_PAL_SLOT + 4) << 8 | (flip ? SOOT_FLIP : 0)));
        }
        s3[i] = show ? gfx_scb3_word(1, TUG_STRAND_TOP) : 0;
        s4[i] = gfx_scb4_word(x + dx);
    }
    up = 1; key = k; at = dx; g_tug_knot_x = (s16)(160 + dx);
    gfx_scb_run((u16)(ADDR_SCB3 + TUG_STRAND_SPRITE), 1, s3, TUG_STRAND_COUNT);
    gfx_scb_run((u16)(ADDR_SCB4 + TUG_STRAND_SPRITE), 1, s4, TUG_STRAND_COUNT);
}
_Static_assert(TUGPOSE_PIECE_HAIR - TUGPOSE_PIECE_TAPER == TUGPOSE_PIECE_HAIR_STORM - TUGPOSE_PIECE_TAPER_STORM && TUGPOSE_PIECE_SNAP2 == TUGPOSE_PIECE_SNAP0 + 2, "strand piece order");
/* Tug Gum on the fix layer: rounds won per team and a status line. */
static void draw_tug(const Game *g) {
    const GgTug *t = &g->tug;
    u32 key = 0x40000000u | (u32)t->phase | (u32)t->wins[0] << 3 | (u32)t->wins[1] << 5 | (u32)t->humans << 7;
    char won[] = "ROUNDS WON   LEFT 0   RIGHT 0 ";
    if (key == g_blow_key) return;
    g_blow_key = key;
    won[18] = (char)('0' + t->wins[0]); won[28] = (char)('0' + t->wins[1]);
    const char *msg = t->phase == GTG_PLAY ? "MASH A TO PULL   D LETS GO    " : t->phase == GTG_SNAP ? "SNAP!                         " :
                      t->wins[0] > t->wins[1] ? "PLAYER 1 WINS                 " : t->humans == 2 ? "PLAYER 2 WINS                 " : "THE COMPUTER WINS             ";
    text((u8)((40 - BLOW_TEXT_W) / 2), BLOW_TEXT_ROW + 4, PAL_TEXT, msg);   /* rows 5..7 are the HUD */
    text((u8)((40 - BLOW_TEXT_W) / 2), BLOW_TEXT_ROW + 5, PAL_TEXT, won);
}
/* Toss Gum on the fix layer: A / B / C tags over the carrier's three targets (tile above each bird) and a status line. */
static u8 g_toss_tag[GT_SEATS][2];   /* tile column and row of the tag shown for a seat, column 0 = none; reset with the fix layer */
static void draw_toss(const Game *g) {
    const GgToss *t = &g->toss;
    u8 tag[GT_SEATS][4] = { { 0 } };
    u32 key = (u32)t->phase | (u32)t->carrier << 3 | (u32)t->alive << 5 | (u32)t->humans << 9 | (u32)t->winner << 10;
    if (key == g_blow_key) return;
    g_blow_key = key;
    for (u8 s = 0; s < GT_SEATS; s++) {
        if (g_toss_tag[s][0]) text(g_toss_tag[s][0], g_toss_tag[s][1], PAL_TEXT, "     ");
        g_toss_tag[s][0] = 0;
    }
    if (t->phase == GT_HOLD) {
        for (u8 k = 0; k < 3; k++) {
            u8 s = gg_toss_target(t->carrier, t->alive, k);
            if (s < GT_SEATS) { u8 n = 0; while (tag[s][n]) n++; tag[s][n] = (u8)('A' + k); }
        }
        for (u8 s = 0; s < GT_SEATS; s++) {
            const Flier *f = game_toss_flier(g, s);
            if (!tag[s][0] || !f) continue;
            char plate_txt[6] = { ' ', 0 };   /* the key letters on the same backing plate as the other prompts (gfx_text_plated) */
            u8 n = 0;
            while (tag[s][n]) { plate_txt[1 + n] = (char)tag[s][n]; n++; }
            plate_txt[1 + n] = ' ';
            g_toss_tag[s][0] = (u8)((f->x >> 16) / 8 - 1 - (n - 1) / 2); g_toss_tag[s][1] = (u8)((f->y >> 16) / 8 - 3);
            gfx_text_plated(g_toss_tag[s][0], g_toss_tag[s][1], PAL_HIGH, plate_txt);
        }
    }
    const char *msg = t->phase == GT_HOLD ? "TOSS THE GUM ON   A  B  C      " : t->phase == GT_FLIGHT ? "                              " :
                      t->phase == GT_BURST ? "BURST!                        " : t->winner == 0 ? "PLAYER 1 WINS                 " :
                      t->winner == 2 && t->humans == 2 ? "PLAYER 2 WINS                 " : "THE COMPUTER WINS              ";
    text((u8)((40 - BLOW_TEXT_W) / 2), BLOW_TEXT_ROW + 4, PAL_TEXT, msg);   /* rows 5..7 are the HUD */
}

/* Gum Fling on the fix layer: the power tube and the angle dial (meter block above), a status line, and in the flight view a mark flag that scrolls in with the course.
 * Distances show in metres (GF_PX_PER_M). */
static int8_t g_fling_flag = -1;   /* fix column of the mark flag on screen, -1 = none; reset with the fix layer */
#define FLING_FLAG_ROW 8
static u8 fling_put(char *line, u8 i, const char *p) { while (*p && i < BLOW_TEXT_W) line[i++] = *p++; return i; }
static u8 fling_put_m(char *line, u8 i, u32 px) {
    char nb[10];
    put_number(nb, px / GF_PX_PER_M, 4);
    for (u8 k = 0; nb[k] && i < BLOW_TEXT_W; k++) if (nb[k] != ' ') line[i++] = nb[k];
    return fling_put(line, i, " M");
}
static void draw_fling(const Game *g) {
    const GgFling *f = &g->fling;
    if (g_meter_n[0] == METER_NONE) {
        meter_plaque(METER_COL, METER_ROW - 2, flingmeter_label_power);
        meter_plaque(DIAL_COL - 1, DIAL_ROW - 2, flingmeter_label_angle);
    }
    meter_tube(METER_ROW, 0, (u8)(f->power * METER_STEPS / GF_POWER_MAX));
    meter_dial((u8)f->deg);
    meter_flash(g_meter_n[0] == METER_STEPS);
    /* mark flag: the hero sits at its screen x at launch, so the mark is GF_MARK_PX - flown pixels ahead of it */
    int8_t col = -1;
    if (col != g_fling_flag) {
        if (g_fling_flag >= 0) { text((u8)g_fling_flag, FLING_FLAG_ROW - 1, PAL_TEXT, "     "); text((u8)g_fling_flag, FLING_FLAG_ROW, PAL_TEXT, " "); }
        if (col >= 0) {
            char m[8]; u8 i = fling_put_m(m, 0, GF_MARK_PX); m[i] = 0;
            text((u8)col, FLING_FLAG_ROW - 1, FIXFONT_PAL_LIME, m);
            text((u8)col, FLING_FLAG_ROW, FIXFONT_PAL_LIME, "V");
        }
        g_fling_flag = col;
    }
    u8 sec = (u8)((f->clock + 59) / 60);
    u32 shown = f->phase == GF_LANDED ? f->dist : f->phase == GF_FLIGHT ? f->x >> 16 : f->seq.best[f->seq.turn];
    u32 key = (u32)f->phase | (u32)sec << 3 | (u32)f->seq.tickets[0] << 7 | (u32)f->seq.tickets[1] << 9 | (u32)f->foul << 11 |
              (u32)f->seq.turn << 12 | (u32)f->seq.players << 13 | (shown / GF_PX_PER_M) << 15;
    if (key == g_blow_key) return;
    g_blow_key = key;
    char line[BLOW_TEXT_W + 1];
    u8 i = 0, two = f->seq.players == 2;
    if (f->phase == GF_RESULT || f->phase == GF_END) {
        if (two) {
            u8 w = gumfling_winner(f);
            i = fling_put(line, i, w == 2 ? "A TIE  " : w ? "PLAYER 2 WINS  " : "PLAYER 1 WINS  ");
            i = fling_put_m(line, i, f->seq.best[w == 1]);
            i = fling_put(line, i, " TO ");
            i = fling_put_m(line, i, f->seq.best[w != 1]);
        } else {
            i = fling_put(line, i, f->seq.qualified[0] ? "PASSED  BEST " : "FAILED  BEST ");
            i = fling_put_m(line, i, f->seq.best[0]);
            i = fling_put(line, i, "  MARK ");
            i = fling_put_m(line, i, GF_MARK_PX);
        }
    } else if (f->phase == GF_LANDED && f->foul) {
        i = fling_put(line, i, "FOUL");
    } else if (f->phase == GF_LANDED || f->phase == GF_FLIGHT) {
        if (two) i = fling_put(line, i, f->thrower ? "PLAYER 2  " : "PLAYER 1  ");
        i = fling_put(line, i, "DISTANCE ");
        i = fling_put_m(line, i, shown);
    } else {
        u8 t = f->seq.turn;
        if (two) i = fling_put(line, i, t ? "PLAYER 2  " : "PLAYER 1  ");
        i = fling_put(line, i, "THROW ");
        line[i++] = (char)('0' + (GF_ATTEMPTS - f->seq.tickets[t] + 1));
        i = fling_put(line, i, " OF 3  TIME ");
        line[i++] = (char)('0' + sec % 10);
        if (!two) { i = fling_put(line, i, "  BEST "); i = fling_put_m(line, i, f->seq.best[0]); }
    }
    while (i < BLOW_TEXT_W) line[i++] = ' ';
    line[BLOW_TEXT_W] = 0;
    text((u8)((40 - BLOW_TEXT_W) / 2), BLOW_TEXT_ROW + 2, PAL_TEXT, line);
    if (!two) { /* the mark under the status line, solo only */
        i = fling_put(line, 0, "MARK ");
        i = fling_put_m(line, i, GF_MARK_PX);
        while (i < 12) line[i++] = ' ';
        line[i] = 0;
        text((u8)((40 - 12) / 2), BLOW_TEXT_ROW + 3, PAL_HIGH, line);
    }
    {   /* control hint under the HUD rows */
        const char *h = f->phase == GF_WINDUP ? "MASH A AND B" : f->phase == GF_AIM ? (f->t < GF_AIM_HOLD_FRAMES ? "" : "PRESS A") : f->phase == GF_FLIGHT ? "MASH A AND B TO FLAP" : "";
        i = fling_put(line, 0, h);
        while (i < BLOW_TEXT_W) line[i++] = ' ';
        line[BLOW_TEXT_W] = 0;
        text((u8)((40 - BLOW_TEXT_W) / 2), BLOW_TEXT_ROW + 4, PAL_HIGH, line);
    }
}

/* Flap Dash on the fix layer: one status line (lap, seconds, qualifying mark), rewritten when the lap or the second changes. */
static void draw_flap_dash(const GgDash *d) {
    u32 secs = d->frames / 60u;
    u32 key = (u32)d->laps | (u32)d->done << 4 | (u32)d->laps2 << 5 | (u32)d->winner << 9 | secs << 12;
    if (key == g_blow_key) return;
    g_blow_key = key;
    char line[BLOW_TEXT_W + 1], nb[10];
    u8 i = 0;
    if (d->two) {   /* 2P: both lap counters, then who won */
        const char *q = d->done ? (d->winner == 1 ? "PLAYER 1 WINS  TIME " : "PLAYER 2 WINS  TIME ") : "P1 LAP ";
        while (q[i]) { line[i] = q[i]; i++; }
        if (!d->done) { line[i++] = (char)('1' + d->laps); line[i++] = ' '; line[i++] = ' '; line[i++] = 'P'; line[i++] = '2'; line[i++] = ' '; line[i++] = 'L'; line[i++] = 'A'; line[i++] = 'P'; line[i++] = ' '; line[i++] = (char)('1' + d->laps2); line[i++] = ' '; line[i++] = ' '; line[i++] = 'T'; line[i++] = 'I'; line[i++] = 'M'; line[i++] = 'E'; line[i++] = ' '; }
        put_number(nb, secs, 3);
        for (u8 k = 0; nb[k] && i < BLOW_TEXT_W; k++) if (nb[k] != ' ') line[i++] = nb[k];
        while (i < BLOW_TEXT_W) line[i++] = ' ';
        line[BLOW_TEXT_W] = 0;
        text((u8)((40 - BLOW_TEXT_W) / 2), BLOW_TEXT_ROW + 2, PAL_TEXT, line);
        return;
    }
    const char *p = d->done ? (d->frames <= gumdash_mark(0) ? "FINISHED  QUALIFIED  TIME " : "FINISHED  NOT QUALIFIED  TIME ") : "LAP ";
    while (p[i]) { line[i] = p[i]; i++; }
    if (!d->done) { line[i++] = (char)('1' + d->laps); line[i++] = ' '; line[i++] = 'O'; line[i++] = 'F'; line[i++] = ' '; line[i++] = (char)('0' + GD_LAPS); line[i++] = ' '; line[i++] = ' '; line[i++] = 'T'; line[i++] = 'I'; line[i++] = 'M'; line[i++] = 'E'; line[i++] = ' '; }
    put_number(nb, secs, 3);
    for (u8 k = 0; nb[k] && i < BLOW_TEXT_W; k++) if (nb[k] != ' ') line[i++] = nb[k];
    if (!d->done) { line[i++] = ' '; line[i++] = ' '; line[i++] = 'M'; line[i++] = 'A'; line[i++] = 'R'; line[i++] = 'K'; line[i++] = ' '; put_number(nb, gumdash_mark(0) / 60u, 3); for (u8 k = 0; nb[k] && i < BLOW_TEXT_W; k++) if (nb[k] != ' ') line[i++] = nb[k]; }
    while (i < BLOW_TEXT_W) line[i++] = ' ';
    line[BLOW_TEXT_W] = 0;
    text((u8)((40 - BLOW_TEXT_W) / 2), BLOW_TEXT_ROW + 2, PAL_TEXT, line);
}

/* Pop Drop on the fix layer: depth and gums; rewritten when either changes. */
static u8 s_hits[2], s_hit_t[2]; /* view-only: last seen b->hits, and the 16-tick burst after a hit (pop_show_bird); the life pips flash on it */
#define PD_PIP_COL0 1   /* player 1 pips: columns 1..3 left of the DEPTH line (cols 5..34), player 2: columns 36..38 */
#define PD_PIP_COL1 36
static u16 g_pd_pips = 0xFFFF; /* what the pips show: per bird hits (2 bits) and flash blink (2 bits); redrawn only on change */

/* Life pips on the fix layer: PD_HITS_MAX hearts a bird, one goes out (white blink, then blank) per hit; a shield soak is no hit. */
static void draw_pd_pips(const GgPop *p) {
    u8 n = p->seq.players > 1 ? 2 : 1;
    u16 st = n > 1 ? 0x8000 : 0;   /* P2 joining in the countdown must redraw the pips too */
    for (u8 i = 0; i < n; i++) st |= (u16)((p->b[i].hits & 3) | (s_hit_t[i] ? 4 + ((s_hit_t[i] >> 2) & 1) : 0) << 2) << (i * 8);
    if (st == g_pd_pips) return;
    g_pd_pips = st;
    for (u8 i = 0; i < n; i++) {
        u8 hits = p->b[i].hits;
        for (u8 k = 0; k < PD_HITS_MAX; k++) {
            u8 col = (u8)((i ? PD_PIP_COL1 : PD_PIP_COL0) + k);
            if (k < PD_HITS_MAX - hits) gfx_fix_tile(col, BLOW_TEXT_ROW + 2, FIXFONT_PAL_PINK, FIXFONT_ICON_HEART);
            else if (k == PD_HITS_MAX - hits && s_hit_t[i] && ((s_hit_t[i] >> 2) & 1)) gfx_fix_tile(col, BLOW_TEXT_ROW + 2, PAL_TEXT, FIXFONT_ICON_HEART);
            else gfx_fix_tile(col, BLOW_TEXT_ROW + 2, 0, FIXFONT_BLANK);
        }
    }
}

static void draw_pop_drop(const GgPop *p) {
    if (g_blow_key == 0xFFFFFFFFu) g_pd_pips = 0xFFFF; /* the fix layer was cleared */
    draw_pd_pips(p);
    u32 key = (u32)p->depth | (u32)p->b[0].gums << 14 | (u32)p->phase << 24 | 1u << 28 | 1u << 29;
    if (key == g_blow_key) return;
    g_blow_key = key;
    char line[BLOW_TEXT_W + 1], nb[10];
    u8 i = 0;
    const char *s = "DEPTH ";
    while (s[i]) { line[i] = s[i]; i++; }
    put_number(nb, p->depth, 5);
    for (u8 k = 0; nb[k] && i < BLOW_TEXT_W; k++) if (nb[k] != ' ') line[i++] = nb[k];
    s = "  GUMS ";
    for (u8 k = 0; s[k] && i < BLOW_TEXT_W; k++) line[i++] = s[k];
    put_number(nb, p->b[0].gums, 3);
    for (u8 k = 0; nb[k] && i < BLOW_TEXT_W; k++) if (nb[k] != ' ') line[i++] = nb[k];
    while (i < BLOW_TEXT_W) line[i++] = ' ';
    line[BLOW_TEXT_W] = 0;
    text((u8)((40 - BLOW_TEXT_W) / 2), BLOW_TEXT_ROW + 2, PAL_TEXT, line);
}

/* Pop Drop sprites: birds, platforms, gum candy and shields in the free shared slots. Each frame redraws the live pieces and hides only the
 * slots that showed last frame and not this one: hiding every slot first queued an SCB3 = 0 per slot ahead of its redraw, and when the
 * vblank flush ran out of budget (GFX_FLUSH_BUDGET_US) between the two, the platform stayed hidden on screen (owner report 2026-11-19).
 * Player 2 (2P simultaneous fall) has its own bird, shield and rag slots after player 1's. */
#define PD_SPRITE 323
#define PD_BIRD_SLOT PD_SPRITE
#define PD_PLAT_SLOT (PD_SPRITE + 2)                 /* 4 platforms x 5 pieces */
#define PD_SHIELD_SLOT (PD_PLAT_SLOT + PD_PLATS * 5) /* 4 columns: the pop frames are 64 px wide */
#define PD_RAG_SLOT (PD_SHIELD_SLOT + 4)             /* 1 column: the burst gum skin, on top of the bird */
#define PD_BIRD2_SLOT (PD_RAG_SLOT + 1)              /* player 2: bird, shield, rag */
#define PD_SHIELD2_SLOT (PD_BIRD2_SLOT + 2)
#define PD_RAG2_SLOT (PD_SHIELD2_SLOT + 4)
#define PD_PUFF_SLOT (PD_RAG2_SLOT + 1)              /* bump feather puff, 3 columns a bird (48 px) */
#define PD_PUFF2_SLOT (PD_PUFF_SLOT + 3)
#define PD_SPRITE_END (PD_PUFF2_SLOT + 3)
_Static_assert(PD_SPRITE_END <= 367, "Pop Drop slots overlap the Trip pickup slots");
/* The trail gums (2 columns each) take the arena island slots, as the Gum Fling field does: island_step is off in Pop Drop and
 * island_relayout reloads their tiles on leaving. They draw under the platforms and the birds. */
#define PD_GUM_SLOT ISLAND_SPRITE
/* Pool finish (batch 2) in the object pool range, which Pop Drop does not use: a higher slot draws in front. Order back to front: background
 * gags, crowd fans with their cards, flop birds, pool (deck, edge, surface, water), ladder, splashes. */
#define PD_BACK POOL_SPRITE_BASE
#define PD_GAG_SLOT PD_BACK                     /* 2 fallers x 5 columns (bathtub: bird 2 + tub 3) */
#define PD_FAN_SLOT (PD_GAG_SLOT + 10)          /* 2 birds x 3 judges x 3 columns (fan 2 + card 1) */
#define PD_FLOP_SLOT (PD_FAN_SLOT + 18)         /* 2 birds x 2 columns */
#define PD_POOLS_SLOT (PD_FLOP_SLOT + 4)        /* the full width: 20 columns of 14 tiles (deck 2, edge 2, water 12, edge 2, deck 2) */
#define PD_LADDER_SLOT (PD_POOLS_SLOT + 20)
#define PD_SPL_SLOT (PD_LADDER_SLOT + 1)        /* 2 birds x 6 columns */
#define PD_BACK_N (PD_SPL_SLOT + 12 - PD_BACK)
_Static_assert(PD_BACK + PD_BACK_N <= POOL_SPRITE_BASE + POOL_SPRITE_COUNT, "Pop Drop pool slots overflow the object pool range");
#define PD_POOL_ROWS 14
_Static_assert(PD_GUMS * 2 <= ISLAND_COUNT, "Pop Drop trail gums overrun the island slots");
#define PD_SLOTS (PD_SPRITE_END - PD_SPRITE + PD_GUMS * 2 + PD_BACK_N)
static u8 g_pd_on;
static u8 g_pd_shown[PD_SLOTS], g_pd_new[PD_SLOTS]; /* pd_idx(slot): drawn last frame / this frame */
static const void *g_pd_key_f[PD_SLOTS]; static u16 g_pd_key_a[PD_SLOTS]; /* tiles last queued per head slot: frame + attr; strips are re-queued only on change */
#define PD_N1 (PD_SPRITE_END - PD_SPRITE)
#define PD_N2 (PD_N1 + PD_GUMS * 2)
static u8 pd_idx(u16 slot) { return (u8)(slot >= PD_SPRITE ? slot - PD_SPRITE : slot >= PD_BACK ? PD_N2 + slot - PD_BACK : PD_N1 + slot - PD_GUM_SLOT); }
static u16 pd_slot(u8 k) { return (u16)(k < PD_N1 ? PD_SPRITE + k : k < PD_N2 ? PD_GUM_SLOT + k - PD_N1 : PD_BACK + k - PD_N2); }

static const PopdropFrame *pd_frame(u8 anim, u16 n) {
    const PopdropAnim *a = &popdrop_anims[anim];
    return &popdrop_frames[a->first_frame + (a->frame_count ? n % a->frame_count : 0)];
}

/* One popdrop frame at world x (left) and screen top in palette slot pal; flip mirrors it. */
static void pd_piece(u16 slot, const PopdropFrame *f, int wx, int top, int flip, u16 pal) {
    int sx = camera_screen_x(wx, g_cam_px, f->tiles_w * 16);
    if (!camera_visible(sx, f->tiles_w * 16)) return;
    const u16 *t = &popdrop_tile_index[f->tile_offset];
    for (u8 c = 0; c < f->tiles_w; c++)
        gfx_sprite_strips((u16)(slot + c), 1, f->tiles_h, t + (flip ? f->tiles_w - 1 - c : c) * f->tiles_h, POPDROP_TILE_BASE,
                          (u16)((pal << 8) | (flip ? 1 : 0)));
    gfx_sprite_place(slot, f->tiles_w, f->tiles_h, sx, top);
    for (u8 c = 0; c < f->tiles_w; c++) g_pd_new[pd_idx(slot) + c] = 1;
}

static void pop_hide(void) {
    pool_hide_all(); /* the pool range cache must forget what the pool finish drew */
    for (u8 k = 0; k < PD_SLOTS; k++) { obs_hide_slot(pd_slot(k)); g_pd_shown[k] = 0; }
}

static void pop_show_pieces(const Game *g);

static void pop_show(const Game *g) {
    if (!g_pd_on) pop_hide(); /* entry: the shared slots may hold another view's sprites */
    g_pd_on = 1;
    for (u8 k = 0; k < PD_SLOTS; k++) g_pd_new[k] = 0;
    pop_show_pieces(g);
    for (u8 k = 0; k < PD_SLOTS; k++) {
        if (g_pd_shown[k] && !g_pd_new[k]) obs_hide_slot(pd_slot(k));
        g_pd_shown[k] = g_pd_new[k];
    }
}

/* One bird with its shield or pop and its rag. A ghost (crashed in a 2P fall that goes on) is the fall pose in the pale palette, no rag. */
static void pop_show_bird(const Game *g, u8 i, u16 bird_slot, u16 shield_slot, u16 rag_slot, u16 puff_slot, u16 pal) {
    const GgPop *p = &g->pop;
    const PdBird *b = &p->b[i];
    u8 ghost = b->crash && b->land < 0;
    u8 lvl = b->hits > 2 ? 2 : b->hits;
    u8 lean = (b->prev_in & (IN_LEFT | IN_RIGHT)) != 0;
    /* Pose order: crash, stun, brake hop, shield (hangs under its bubble), half bald (second hit taken, one more crashes), lean, fall. */
    u8 anim = ghost ? POPDROP_ANIM_GHOST : b->crash ? POPDROP_ANIM_CRASH : b->stun ? POPDROP_ANIM_BONK : b->hop < 0 ? POPDROP_ANIM_HOP
            : b->shield ? POPDROP_ANIM_HANG : b->hits >= 2 ? POPDROP_ANIM_BALD : lean ? (u8)(POPDROP_ANIM_LEAN0 + lvl) : (u8)(POPDROP_ANIM_FALL0 + lvl);
    u16 n = (u16)(g->frame >> 3);
    if (anim == POPDROP_ANIM_HOP) n = b->hop <= -9 ? 2 : b->hop <= -4 ? 3 : 1;   /* pump, wings level, wings high as it sinks */
    else if (anim == POPDROP_ANIM_BALD) n = (u16)(g->frame >> 4);
    else if (anim == POPDROP_ANIM_GHOST) n = (u16)(g->frame >> 4);
    int bx = (int)(g->hero[i].x >> 16) - 16, top = PD_BIRD_Y + b->hop - 16;
    if (b->crash && !ghost) {   /* the crash pose lies on top of the island it hit and rides off with it (art feet = frame bottom) */
        const PdPlat *on = &p->plat[b->land];
        if (!on->live) return;
        top = on->y - pd_frame(POPDROP_ANIM_CRASH, 0)->tiles_h * 16;
    }
    pd_piece(bird_slot, pd_frame(anim, n), bx, top, b->flip, ghost ? POPDROP_PAL_SLOT + 3 : pal);   /* palette 3 = the spirit ghost palette (assets/popdrop) */
    if (ghost) return;
    /* Bubble parachute (draft 2026-11-20 fun, take A): the 32 x 48 bubble-and-strand cell sits 8 px right of the bird box and 22 px above its top;
     * the 48 x 48 pop frames are centred on that bubble (box x, 34 px up); pop_t runs 1..24, six frames of four. */
    if (b->shield) pd_piece(shield_slot, pd_frame(POPDROP_ANIM_SHIELD, 0), bx + 8, top - 22, 0, POPDROP_PAL_SLOT + 2);
    else if (b->pop_t) pd_piece(shield_slot, pd_frame(POPDROP_ANIM_POP, (u16)((b->pop_t - 1) >> 2)), bx, top - 34, 0, POPDROP_PAL_SLOT + 2);
    /* Bump feather puff (hook in gg_popdrop push_apart): the six burst frames over bump_t 1..16, centred on the bird. */
    /* Island hit puff: view-only, a rising hits counter restarts the same 16-tick burst (a bump keeps the slot while it runs). */
    if (b->hits > s_hits[i]) s_hit_t[i] = 16;
    else if (s_hit_t[i]) s_hit_t[i]--;
    s_hits[i] = b->hits;
    u8 puff_t = b->bump_t ? b->bump_t : s_hit_t[i];
    if (puff_t) pd_piece(puff_slot, pd_frame(POPDROP_ANIM_PUFF, (u16)((puff_t - 1) * 6 / 16)), bx - 8, top - 8, 0, pal);
    /* The burst gum skin (draft 2026-11-18 freefall): four flutter frames on the upper beak, 11 px into the 24 px art (pad 4) and
     * 12 px above it; the limp frame lies past the splat's right edge. Mirrored with the bird; hidden inside an intact shield. */
    if (b->crash)
        pd_piece(rag_slot, pd_frame(POPDROP_ANIM_RAG, 4), b->flip ? bx - 15 : bx + 31, top, b->flip, POPDROP_PAL_SLOT);
    else if (!b->shield)
        pd_piece(rag_slot, pd_frame(POPDROP_ANIM_RAG, (u16)((g->frame >> 2) & 3)), b->flip ? bx + 1 : bx + 15, top - 12, b->flip, POPDROP_PAL_SLOT);
}

/* Pool finish. Screen-space pool across the full width: deck 32 px, edge 32 px, water 192 px, edge, deck. pool_y = deck top; surface art at
 * pool_y + 3, water from pool_y + 11, waterline pool_y + 6 (draft draw_batch2.py). Each column is one 14 tile strip (surface then water). */
static void pd_scr(u16 slot, const PopdropFrame *f, int sx, int top, int flip, u16 pal) { pd_piece(slot, f, sx + g_cam_px, top, flip, pal); }

static void pop_show_pool(const Game *g) {
    int y = g->pop.pool_y;
    static u16 col[PD_POOL_ROWS];
    const PopdropFrame *surf = pd_frame(POPDROP_ANIM_SURF, (u16)(g->frame >> 3));
    const PopdropFrame *w0 = pd_frame(POPDROP_ANIM_WATER, 0), *w1 = pd_frame(POPDROP_ANIM_WATER, 1);
    const PopdropFrame *e0 = pd_frame(POPDROP_ANIM_EDGE, 0), *e1 = pd_frame(POPDROP_ANIM_EDGE, 1);
    u16 pal = POPDROP_PAL_SLOT + 4;
    for (u8 c = 0; c < 20; c++) {
        u16 slot = (u16)(PD_POOLS_SLOT + c);
        int water = c >= 4 && c < 16, flip = c >= 16;
        u8 tc = water ? (u8)(c & 1) : (u8)(c == 3 || c == 16);   /* edge cell: tile column 0 is the deck tile, 1 the lip (the right edge is the flipped cell) */
        col[0] = popdrop_tile_index[(water ? surf : e0)->tile_offset + tc];
        for (u8 r = 1; r < PD_POOL_ROWS; r++) col[r] = popdrop_tile_index[(water ? (r > 1 ? w1 : w0) : e1)->tile_offset + tc];
        gfx_sprite_strips(slot, 1, PD_POOL_ROWS, col, POPDROP_TILE_BASE, (u16)((pal << 8) | (flip ? 1 : 0)));
        gfx_sprite_place(slot, 1, PD_POOL_ROWS, c * 16, water ? y - 5 : y);
        g_pd_new[pd_idx(slot)] = 1;
    }
    pd_scr(PD_LADDER_SLOT, pd_frame(POPDROP_ANIM_LADDER, 0), 69, y - 7, 0, pal);
}

/* A bird that flopped: its pose half sunk (it sits in a slot behind the water), the splash by size, the judges' fans and cards. */
static void pop_show_landed(const Game *g, u8 i, u16 bird_pal) {
    const GgPop *p = &g->pop;
    const PdBird *b = &p->b[i];
    int cx = (int)(g->hero[i].x >> 16), y = p->pool_y;
    static const u8 spl_cx[3] = { 16, 32, 48 }, spl_wl[3] = { 27, 42, 72 };
    pd_piece((u16)(PD_FLOP_SLOT + i * 2), pd_frame(POPDROP_ANIM_FLOP, b->pose), cx - 16, y + 6 - 20, b->flip, bird_pal);
    if (b->splash_f < PD_SPLASH_LEN(b->size) - 1)
        pd_piece((u16)(PD_SPL_SLOT + i * 6), pd_frame((u8)(POPDROP_ANIM_SPLASH_S + b->size), b->splash_f), cx - spl_cx[b->size], y + 6 - spl_wl[b->size], 0, POPDROP_PAL_SLOT + 4);
    u8 cards = p->phase == PD_RESULT || b->splash_f >= PD_SPLASH_LEN(b->size) - 1;
    for (u8 j = 0; j < PD_JUDGES; j++) {
        static const u8 fan_x[PD_JUDGES] = { 0, 24, 12 };
        int right = i == 1, fx = right ? 288 - fan_x[j] : fan_x[j], top = y - 32;
        u16 slot = (u16)(PD_FAN_SLOT + (i * PD_JUDGES + j) * 3);
        pd_scr(slot, pd_frame(POPDROP_ANIM_FAN, (u16)((g->frame >> 4) + j)), fx, top, right, SOOT_P2_PAL_SLOT);
        if (cards && b->card[j]) pd_scr((u16)(slot + 2), pd_frame(POPDROP_ANIM_CARD, (u16)(b->card[j] - 1)), right ? fx + 18 : fx - 2, top - 24, right, POPDROP_PAL_SLOT + 5);
    }
}

/* Background gag fallers: the tub with its bird behind it, the tumbling armchair, the snail on its umbrella (centre x, y). */
static void pop_show_gags(const Game *g) {
    static const u8 dy[4] = { 0, 1, 1, 0 };
    for (u8 k = 0; k < PD_FALLERS; k++) {
        const PdFaller *fl = &g->pop.fall[k];
        if (!fl->live) continue;
        u16 slot = (u16)(PD_GAG_SLOT + k * 5), n = (u16)(g->frame >> 3), pal = POPDROP_PAL_SLOT + 5;
        int x = fl->x, y = fl->y;
        if (fl->kind == PD_FALLER_BATH) {
            u8 m = (u8)(n & 3);
            pd_piece(slot, pd_frame(POPDROP_ANIM_TUBBIRD, m == 1 || m == 2), x - 24 + 6, y - 24 - 4 + dy[m], 0, POPDROP_PAL_SLOT);
            pd_piece((u16)(slot + 2), pd_frame(POPDROP_ANIM_TUB, m), x - 24, y - 24, 0, POPDROP_PAL_SLOT + 4);
        } else if (fl->kind == PD_FALLER_ARMCHAIR) pd_piece(slot, pd_frame(POPDROP_ANIM_CHAIR, n), x - 16, y - 16, 0, pal);
        else pd_piece(slot, pd_frame(POPDROP_ANIM_SNAIL, n), x - 24, y - 24, 0, pal);
    }
}

static void pop_show_pieces(const Game *g) {
    const GgPop *p = &g->pop;
    for (u8 k = 0; k < PD_PLATS; k++) {
        const PdPlat *pl = &p->plat[k];
        if (!pl->live) continue;
        u16 slot = (u16)(PD_PLAT_SLOT + k * 5);
        u8 n = (u8)(pl->mids + 2);
        for (u8 j = 0; j < n; j++) {
            const PopdropFrame *f = pd_frame(POPDROP_ANIM_PLAT, (u16)(pl->kind * 2 + (j && j < n - 1 ? 1 : 0)));
            pd_piece((u16)(slot + j), f, pl->x + j * 16, pl->y, j == n - 1, POPDROP_PAL_SLOT + 1);
        }
    }
    for (u8 k = 0; k < PD_GUMS; k++) {
        const PdGum *gm = &p->gum[k];
        if (gm->live != 1) continue;
        /* Phase per gum in the tick timing, not only in the frame shown: with (frame >> 2) + k every gum stepped on the same frame, up to
         * 15 gums x 2 strips (about 1080 us) in one flush, which with both 2P birds hit GFX_FLUSH_BUDGET_US (make test-gum-pop-drop-2p).
         * 5k is k mod 4 in the tick, so a quarter of the gums step per frame, and still about 1.25 k frames apart in the loop. */
        int fr = (int)(((g->frame + (u32)k * 5u) >> 2) & (TRIPPICKUP_PICKUP_IDLE_FRAMES - 1));
        const TrippickupFrame *f = &trippickup_frames[trippickup_anims[TRIPPICKUP_ANIM_PICKUP_IDLE].first_frame + fr];
        int sx = camera_screen_x(gm->x - 16, g_cam_px, 32);
        if (!camera_visible(sx, 32)) continue;
        u16 sl = (u16)(PD_GUM_SLOT + k * 2);
        gfx_sprite_strips(sl, 2, 2, &trippickup_tile_index[f->tile_offset], TRIPPICKUP_TILE_BASE, (u16)(TRIPPICKUP_PAL_SLOT << 8));
        gfx_sprite_place(sl, 2, 2, sx, gm->y - 16);
        g_pd_new[pd_idx(sl)] = 1; g_pd_new[pd_idx(sl) + 1] = 1;
    }
    pop_show_gags(g);
    if (p->pool_y < SCREEN_H + 8) pop_show_pool(g);
    if (p->b[0].landed) pop_show_landed(g, 0, POPDROP_PAL_SLOT);
    if (p->seq.players > 1 && p->b[1].landed) pop_show_landed(g, 1, SOOT_P2_PAL_SLOT);
    if (p->phase != PD_FALL && p->phase != PD_CRASH) return;
    pop_show_bird(g, 0, PD_BIRD_SLOT, PD_SHIELD_SLOT, PD_RAG_SLOT, PD_PUFF_SLOT, POPDROP_PAL_SLOT);
    if (p->seq.players > 1) pop_show_bird(g, 1, PD_BIRD2_SLOT, PD_SHIELD2_SLOT, PD_RAG2_SLOT, PD_PUFF2_SLOT, SOOT_P2_PAL_SLOT);   /* fall0 = the Sootling player palette: P2 reuses its P2 swap */
}

/* Poop the Man (gg_poop.h): screen-space view, no camera. Birds use the Pop Drop fall frames in the Pop Drop bird slots; walkers, umbrellas, poops,
 * shoes and the berry (assets/poop) sit in the pool range slots, which Pop Drop's hide bookkeeping (g_pd_new/g_pd_shown) already tracks. */
#define PM_W_SLOT PD_BACK                    /* 7 walkers x 2 columns */
#define PM_U_SLOT (PM_W_SLOT + PM_WALKERS * 2)   /* 7 umbrellas x 3 (the open canopy is 36 wide) */
#define PM_P_SLOT (PM_U_SLOT + PM_WALKERS * 3)   /* 6 poops */
#define PM_S_SLOT (PM_P_SLOT + PM_POOPS)         /* 3 shoes */
#define PM_H_SLOT (PM_S_SLOT + PM_SHOES)                /* 7 head splats x 1 column */
_Static_assert(PM_H_SLOT + PM_WALKERS <= PD_BACK + PD_BACK_N, "Poop the Man slots overflow the Pop Drop hide range");

/* One poop frame; (ox, oy) = top left of its sheet cell (cw wide), the opaque box sits pad_left / pad_top inside it. */
static void pm_piece(u16 slot, const PoopFrame *f, int ox, int oy, int cw, int flip, u16 pal) {
    int x = flip ? ox + cw + f->pad_left - f->tiles_w * 16 : ox - f->pad_left;   /* pad_left = art inset inside the tiles */
    if (!camera_visible(x, f->tiles_w * 16)) return;
    const u16 *t = &poop_tile_index[f->tile_offset];
    u16 attr = (u16)((pal << 8) | (flip ? 1 : 0));
    u8 hi = pd_idx(slot);
    if (!g_pd_shown[hi] || g_pd_key_f[hi] != f || g_pd_key_a[hi] != attr) {
        for (u8 c = 0; c < f->tiles_w; c++)
            gfx_sprite_strips((u16)(slot + c), 1, f->tiles_h, t + (flip ? f->tiles_w - 1 - c : c) * f->tiles_h, POOP_TILE_BASE, attr);
        g_pd_key_f[hi] = f; g_pd_key_a[hi] = attr;
    }
    gfx_sprite_place(slot, f->tiles_w, f->tiles_h, x, oy + f->pad_top);
    for (u8 c = 0; c < f->tiles_w; c++) g_pd_new[pd_idx(slot) + c] = 1;
}
static const PoopFrame *pm_frame(u8 anim, u16 n) {
    const PoopAnim *a = &poop_anims[anim];
    return &poop_frames[a->first_frame + n % a->frame_count];
}

static void poop_show_bird(const GgPoop *p, const Game *g, u8 i, u16 slot, u16 pal) {
    const PmBird *b = &p->b[i];
    u8 hurt = b->stun || b->dead;   /* dead: the stun pose, falling off screen */
    u16 n = (u16)(g->frame >> 3);
    u8 anim = hurt ? POPDROP_ANIM_BONK : b->flap_t && b->flap_t < 12 ? POPDROP_ANIM_HOP : POPDROP_ANIM_FALL0;   /* flap: the Pop Drop hop frames */
    if (anim == POPDROP_ANIM_HOP) n = b->flap_t <= 3 ? 2 : b->flap_t <= 7 ? 3 : 1;   /* pump, wings level, wings high */
    const PopdropFrame *f = pd_frame(anim, n);
    if ((b->stun || (b->inv && !b->dead)) && (g->frame & 2)) return;   /* stunned or invulnerable: blink */
    if (b->y > 232) return;
    int sx = b->x - f->tiles_w * 8, top = b->y - f->tiles_h * 8;
    if (!camera_visible(sx, f->tiles_w * 16)) return;
    const u16 *t = &popdrop_tile_index[f->tile_offset];
    u16 attr = (u16)((pal << 8) | (b->flip ? 1 : 0));
    u8 hi = pd_idx(slot);
    if (!g_pd_shown[hi] || g_pd_key_f[hi] != f || g_pd_key_a[hi] != attr) {
        for (u8 c = 0; c < f->tiles_w; c++)
            gfx_sprite_strips((u16)(slot + c), 1, f->tiles_h, t + (b->flip ? f->tiles_w - 1 - c : c) * f->tiles_h, POPDROP_TILE_BASE, attr);
        g_pd_key_f[hi] = f; g_pd_key_a[hi] = attr;
    }
    gfx_sprite_place(slot, f->tiles_w, f->tiles_h, sx, top);
    for (u8 c = 0; c < f->tiles_w; c++) g_pd_new[pd_idx(slot) + c] = 1;
}

static void poop_show_pieces(const Game *g) {
    const GgPoop *p = &g->poop;
    for (u8 k = 0; k < PM_WALKERS; k++) {
        const PmWalker *w = &p->w[k];
        if (!w->live) continue;
        u8 nw = w->kind == PM_KID ? 4 : 6, first = 0, n = 0, anim = (u8)(w->kind * 2);   /* PM_HAT..PM_KID = POOP_ANIM_HAT, BALD, WOMAN, KID */
        if (w->st == PM_WALK) { first = w->umb ? nw : 0; n = (u8)((w->t >> 3) % nw); }
        else if (w->st == PM_HIT) { first = (u8)(2 * nw); n = (u8)(w->t * 3u / PM_HIT_FRAMES); if (n > 2) n = 2; }
        else if (w->st == PM_FIST) { first = (u8)(2 * nw + 3); n = (u8)((w->t >> 3) & 1); }
        else { first = (u8)(2 * nw + 5); n = (u8)(w->t < 20 ? 0 : w->t < 28 ? 1 : 2); }
        const PoopAnim *a = &poop_anims[anim];
        const PoopFrame *f = &poop_frames[a->first_frame + first + n];
        int cx = w->x8 >> 3, flip = w->dx8 - PM_SCROLL * 8 < 0;   /* face the way it moves on screen: the backdrop does not scroll, so every walker drifts left */
        int feet = pm_lane_feet(w->lane);
        pm_piece((u16)(PM_W_SLOT + k * 2), f, cx - 16, feet - 48, 32, flip, (u16)(POOP_PAL_SLOT + f->palette));
        if (w->st != PM_WALK) {   /* head splat (draft rig: head x, top row, hit bob) lies on the head from the hit until the walker walks again */
            static const u8 hx[4] = { 4, 5, 5, 5 }, top[4] = { 0, 8, 6, 18 };
            const PoopFrame *s = pm_frame(POOP_ANIM_SPLAT_HEAD, w->st == PM_HIT ? n : 2);
            int bob = w->st == PM_HIT ? 2 - n : w->st == PM_FIST ? n : 0, off = hx[w->kind] + 1;
            pm_piece((u16)(PM_H_SLOT + k), s, flip ? cx - 16 + 32 - off - 16 : cx - 16 + off, feet - 48 + top[w->kind] + bob - 4, 16, flip, (u16)(POOP_PAL_SLOT + s->palette));
        }
        if (w->umb && w->st == PM_WALK) {
            const PoopFrame *u = pm_frame((u8)(anim + 1), 2);
            pm_piece((u16)(PM_U_SLOT + k * 3), u, flip ? cx - 20 : cx - 16, feet - 64, 36, flip, (u16)(POOP_PAL_SLOT + u->palette));
        }
    }
    for (u8 k = 0; k < PM_POOPS; k++) {
        const PmPoop *o = &p->poop[k];
        if (!o->live) continue;
        const PoopFrame *f = o->st == PM_POOP_BOUNCE ? pm_frame(POOP_ANIM_BOUNCE, (u16)(o->t >> 3)) : o->st == PM_POOP_SPLAT ? pm_frame(POOP_ANIM_SPLAT_PAVE, (u16)(o->t >> 2 > 2 ? 2 : o->t >> 2)) : pm_frame(POOP_ANIM_POOP, (u16)(g->frame >> 2));
        pm_piece((u16)(PM_P_SLOT + k), f, (int)(o->x16 >> 4) - 8, o->st == PM_POOP_SPLAT ? PM_PAVE_Y - 8 : (int)(o->y16 >> 4) - 8, 16, 0, (u16)(POOP_PAL_SLOT + f->palette));
    }
    for (u8 k = 0; k < PM_SHOES; k++) {
        const PmShoe *s = &p->shoe[k];
        if (!s->live) continue;
        const PoopFrame *f = pm_frame(POOP_ANIM_SHOE, (u16)(g->frame >> 2));
        pm_piece((u16)(PM_S_SLOT + k), f, s->x - 8, s->y - 8, 16, 0, (u16)(POOP_PAL_SLOT + f->palette));
    }
    if (p->phase != PM_PLAY) return;
    poop_show_bird(p, g, 0, PD_BIRD_SLOT, POPDROP_PAL_SLOT);
    if (p->seq.players > 1) poop_show_bird(p, g, 1, PD_BIRD2_SLOT, SOOT_P2_PAL_SLOT);
}

static void poop_show(const Game *g) {
    if (!g_pd_on) pop_hide();
    g_pd_on = 1;
    for (u8 k = 0; k < PD_SLOTS; k++) g_pd_new[k] = 0;
    poop_show_pieces(g);
    for (u8 k = 0; k < PD_SLOTS; k++) {
        if (g_pd_shown[k] && !g_pd_new[k]) obs_hide_slot(pd_slot(k));
        g_pd_shown[k] = g_pd_new[k];
    }
}

/* Poop the Man on the fix layer: per bird score and seconds left. */
static void draw_poop_man(const Game *g) {
    const GgPoop *p = &g->poop;
    u16 left = (u16)((p->timer < PM_CLOCK ? PM_CLOCK - p->timer : 0) / 60u);
    u32 key = left | (p->b[0].score & 0x3FFFu) << 16 | (u32)p->phase << 30 | 1u << 29;
    if (p->seq.players > 1) key ^= (p->b[1].score & 0xFFu) << 24;
    if (key == g_blow_key) return;
    g_blow_key = key;
    for (u8 i = 0; i < p->seq.players && i < 2; i++) {
        char line[BLOW_TEXT_W + 1], nb[10];
        u8 n = 0;
        const char *s = i ? "P2 " : "P1 ";
        while (s[n]) { line[n] = s[n]; n++; }
        put_number(nb, p->b[i].score, 6);
        for (u8 k = 0; nb[k] && n < BLOW_TEXT_W; k++) if (nb[k] != ' ') line[n++] = nb[k];
        if (i == 0) {
            s = "  TIME ";
            for (u8 k = 0; s[k] && n < BLOW_TEXT_W; k++) line[n++] = s[k];
            put_number(nb, left, 3);
            for (u8 k = 0; nb[k] && n < BLOW_TEXT_W; k++) if (nb[k] != ' ') line[n++] = nb[k];
        }
        while (n < BLOW_TEXT_W) line[n++] = ' ';
        line[BLOW_TEXT_W] = 0;
        text((u8)((40 - BLOW_TEXT_W) / 2), (u8)(BLOW_TEXT_ROW + 2 + i), PAL_TEXT, line);
    }
}

/* Bubble Gather on the fix layer: caught of 20 and seconds left; hidden while the result screen covers the fix layer. */
static void draw_gather(const Game *g) {
    u32 left = (GG_GATHER_CLOCK - g->gather_clock + 59u) / 60u;
    u32 key = (u32)g->bonus_caught[0] | left << 8 | 1u << 20;
    if (g->res.active || key == g_blow_key) return;
    g_blow_key = key;
    char line[BLOW_TEXT_W + 1], nb[10];
    u8 i = 0;
    const char *p = "BUBBLES ";
    while (p[i]) { line[i] = p[i]; i++; }
    put_number(nb, (u32)g->bonus_caught[0], 2);
    for (u8 k = 0; nb[k] && i < BLOW_TEXT_W; k++) if (nb[k] != ' ') line[i++] = nb[k];
    p = " OF 20  TIME ";
    for (u8 k = 0; p[k]; k++) line[i++] = p[k];
    put_number(nb, left, 2);
    for (u8 k = 0; nb[k] && i < BLOW_TEXT_W; k++) if (nb[k] != ' ') line[i++] = nb[k];
    while (i < BLOW_TEXT_W) line[i++] = ' ';
    line[BLOW_TEXT_W] = 0;
    text((u8)((40 - BLOW_TEXT_W) / 2), BLOW_TEXT_ROW + 2, PAL_TEXT, line);
}

static void hero_and_mode(const FlowView *v) {
    if (world_shown(v)) {
        bios_user_mode = (v->state == FLOW_PLAYING || g_start_pending) ? 2 : 1; /* the demo is attract: mode 1 (see below) */
        g_cam_px = (u16)game_camera_px(v->game);
        g_cam_unwrapped = camera_unwrapped_px(&v->game->camera);
        edge_marker(v->game, game_flier_cam_px(v->game));
        if (v->card) {   /* the rules card shows the world and its own example only: no bird or pool sprite under it (owner 2026-11-22, make test-gum-fling F4) */
            hero_hide();
            dead_release_all();
            if (g_pool.live) pool_free_all();
            pool_show();
            return;
        }
        if (v->game->gg_poop) { hero_hide(); poop_show(v->game); }
        else if (v->game->gg_pop) { hero_hide(); pop_show(v->game); }  /* no hero_show here: it queued the hero and hero_hide cleared it the same frame */
        else {
            hero_show(v->game, game_flier_cam_px(v->game));
            if (g_pd_on) { pop_hide(); g_pd_on = 0; island_relayout(); }   /* the trail gums wrote the island tiles */
        }
        if (v->game->mode == GAME_MODE_TRIP) pool_sync_trip(v->game, game_trip_ready(v->game));
        pool_sync_cpus(v->game);
        if (v->game->mode == GAME_MODE_ARCADE || v->game->mode == GAME_MODE_ARENA || v->game->gg_race || v->game->gg_dash || v->game->gg_gather || seated(v->game)) pool_sync_p2(v->game);
        if (v->game->mode == GAME_MODE_TRIP) pool_sync_rivals(v->game);
        human_leak_sync(v->game);
        if (g_pool_stress) pool_stress();
        pool_show();
    } else {
        /* BIOS_USER_MODE 2 = game in progress: play, game over, name entry and the save
         * reminder all belong to the game; 1 only once attract begins. Bug fixed here: mode 1
         * was set on entering GAME_OVER, so with a credit left UniBIOS treated the game as in
         * attract, saw the refused start and stopped calling the VBlank callback; game_loop
         * waited for vblank forever (frozen last frame, a coin woke it). An accepted start
         * keeps mode 2 until flow_step sees it. Guarded by make test-unibios (two coins). */
        if (v->state > FLOW_ATTRACT_DEMO || g_start_pending) bios_user_mode = 2; /* the reminder is still the game: a credit left in mode 1 froze the loop; its save return ignores the mode */
        else bios_user_mode = 1;
        g_cam_px = 0;
        g_cam_unwrapped = 0;
        g_edge_col[0] = g_edge_col[1] = 0xFF; /* draw() clears the fix layer with the state change */
        flier_anim_init(&g_hero_anim[0]);
        flier_anim_init(&g_hero_anim[1]);
        hero_hide();
        dead_release_all();
        if (g_pool.live) pool_free_all();
        pool_show(); /* hides the freed runs once */
    }
}

#ifdef GUMBIRDS_DEBUG_HEADER
static const char *const STATE_NAME[] = {
    "TITLE", "HIGH SCORES", "DEMO", "PLAYING", "GAME OVER", "NAME ENTRY", "SAVE REMINDER"
};
#endif

/* BIOS joypad: UP=1 DOWN=2 LEFT=4 RIGHT=8 A=0x10 B=0x20 C=0x40 D=0x80.
 * Core: A..D = 0x01..0x08, UP=0x10, DOWN=0x20, LEFT=0x40, RIGHT=0x80. */
static u8 pad_to_core(u8 cur) { return (u8)(((cur >> 4) & 0x0F) | ((cur & 0x0F) << 4)); }
static u8 read_input(void) { return pad_to_core(bios_p1current); }

/* Decimal, right aligned in `width` columns, space padded. */
/* Digits by subtracting powers of ten: draw() runs it every frame, and a 32-bit `/` or `%` is a libgcc call
 * (__udivsi3, hundreds of cycles) per digit on the 68000. More digits than `width` keep the low ones. */
static const u32 POW10[10] = { 1000000000u, 100000000u, 10000000u, 1000000u, 100000u, 10000u, 1000u, 100u, 10u, 1u };
static void put_number(char *out, u32 v, int width) {
    char d[10];
    int lead = 9; /* index of the first significant digit; a zero still shows one '0' */
    for (int k = 0; k < 10; k++) {
        char c = '0';
        while (v >= POW10[k]) { v -= POW10[k]; c++; }
        d[k] = c;
        if (c != '0' && lead == 9 && k < 9) lead = k;
    }
    for (int i = width - 1, k = 9; i >= 0; i--, k--) out[i] = (k >= lead) ? d[k] : ' ';
    out[width] = 0;
}

static void text(u8 x, u8 y, u8 pal, const char *s) {
    gfx_text(x, y, pal, s);
}

static void draw_number(u8 x, u8 y, u8 pal, u32 v, int width) {
    char buf[12];
    put_number(buf, v, width);
    text(x, y, pal, buf);
}

/* Caption rows are padded to the same width so the longer one is fully overwritten when the mode changes. */
static void draw_table(const HiscoreTable *t, u8 mode, int highlight, u8 y0) {
    char line[HISCORE_NAME_LEN + 1];
    text(12, (u8)(y0 - 2), PAL_TEXT, mode == GAME_MODE_TRIP ? "GUM TRIP SCORES" : mode == GAME_MODE_ARCADE ? "ARCADE SCORES  " : mode == GAME_MODE_PARTY ? "PARTY SCORES   " : mode == GAME_MODE_GUM ? "GUM GAMES SCORES" : "ARENA SCORES   ");
    g_table_mode_draws[mode == GAME_MODE_TRIP ? 1 : 0]++;
    for (int i = 0; i < HISCORE_ENTRIES; i++) {
        u8 pal = (i == highlight) ? PAL_HIGH : PAL_TEXT;
        char rank[4];
        put_number(rank, (u32)(i + 1), 2);
        rank[2] = '.';
        rank[3] = 0;
        text(10, (u8)(y0 + i), pal, rank);
        for (int c = 0; c < HISCORE_NAME_LEN; c++) line[c] = t->name[i][c];
        line[HISCORE_NAME_LEN] = 0;
        text(14, (u8)(y0 + i), pal, line);
        draw_number(24, (u8)(y0 + i), pal, t->score[i], 8);
    }
}

/* Last state draw() cleared the fix layer for; -1 forces a clear (video_init sets it). */
static int g_draw_state = -1;
/* Gum Trip gum meter on HUD row 6 (replaces the Balloons row): fill step last drawn, 255 = nothing drawn since the last clear.
 * g_meter_draws counts the frames in which the cells were sent (tests/mame/trip_check.lua reads it). */
#define METER_NONE 255
#define METER_ROW 6
#define METER_COL 2
static u8 g_meter_step = METER_NONE;
volatile u16 g_meter_draws;
static u8 g_distress = 0;
/* Gum Trip distress: the player's cheeks go red in 3 stages as the gum runs out (extra palettes 1..3); stage 0 restores the player palette. */
static void set_distress(u8 stage) {
    if (stage == g_distress) return;
    g_distress = stage;
    for (int i = 0; i < 16; i++)
        gfx_pal(SOOT_PAL_SLOT * 16 + i, stage ? sootling_extra_palettes[stage][i] : sootling_palettes[0][i]);
}
static void draw_gum_meter(u16 gum) {
    u8 step = (u8)trip_view_meter_step((int)gum);
    set_distress((u8)trip_view_distress(step));
    if (step == g_meter_step) return;
    g_meter_step = step;
    for (u8 c = 0; c < TRIPMETER_CELLS; c++) gfx_fix_tile((u8)(METER_COL + c), METER_ROW, PAL_TEXT, tripmeter_cell[step][c]);
    g_meter_draws++;
}
/* Arcade HUD per side (0 = player 1 left, 1 = player 2 right mirror), separate caches so one side's change never resends the other.
 * kind 0 = blank, 1 = PRESS P2 START, 2 = score block; 0xFF = not sent since the last clear. */
#define HUD_KIND_NONE 0xFF
#define HUD_KIND_BLANK 0
#define HUD_KIND_PRESS 1
#define HUD_KIND_STATS 2
#define HUD_KIND_INSERT 3 /* "INSERT COIN   " and "PRESS P2 START" share row 5 cols 24..37, both 14 wide so one fully overwrites the other */
static struct { u32 score; u8 kind, balloons, lives; } g_hud[2] = { { 0, HUD_KIND_NONE, 0, 0 }, { 0, HUD_KIND_NONE, 0, 0 } };

/* One side of the score block. P1: label then number from column 2. P2 mirrors it about the screen centre (column c -> 39 - c):
 * number then label, so the right edge of both blocks sits at the same distance from its screen edge. */
static void hud_side_stats(u8 side, u32 score, u8 balloons, u8 lives, u8 show_lives, u8 show_balloons) {
    char nb[10];
    put_number(nb, score, 8);
    if (side == 0) {
        text(2, 5, PAL_TEXT, "SCORE");
        text(8, 5, PAL_TEXT, nb);
        if (show_balloons) { text(2, 6, PAL_TEXT, "Balloons"); draw_number(11, 6, PAL_TEXT, balloons, 1); }
        if (show_lives) { text(2, 7, PAL_TEXT, "Lives"); draw_number(8, 7, PAL_TEXT, lives, 1); }
    } else {
        text(24, 5, PAL_TEXT, nb);
        text(33, 5, PAL_TEXT, "SCORE");
        if (show_balloons) { draw_number(28, 6, PAL_TEXT, balloons, 1); text(30, 6, PAL_TEXT, "Balloons"); }
        if (show_lives) { draw_number(31, 7, PAL_TEXT, lives, 1); text(33, 7, PAL_TEXT, "Lives"); }
    }
}

/* Writes one side when its value changed (the fix layer shadow drops equal cells, but the number formatting is not free). */
static void hud_side(u8 side, u8 kind, u32 score, u8 balloons, u8 lives, u8 show_lives, u8 show_balloons) {
    if (g_hud[side].kind == kind && (kind != HUD_KIND_STATS || (g_hud[side].score == score && g_hud[side].balloons == balloons && g_hud[side].lives == lives))) return;
    if (kind == HUD_KIND_STATS) {
        if (g_hud[side].kind == HUD_KIND_PRESS || g_hud[side].kind == HUD_KIND_INSERT) text(24, 5, PAL_TEXT, "              ");
        hud_side_stats(side, score, balloons, lives, show_lives, show_balloons);
    } else {
        /* only the P2 side ever blanks or prompts: its 14 columns 24..37 on rows 5..7 */
        text(24, 5, PAL_TEXT, kind == HUD_KIND_PRESS ? "PRESS P2 START" : kind == HUD_KIND_INSERT ? "INSERT COIN   " : "              ");
        if (g_hud[side].kind == HUD_KIND_STATS) { text(24, 6, PAL_TEXT, "              "); text(24, 7, PAL_TEXT, "              "); }
    }
    g_hud[side].kind = kind; g_hud[side].score = score; g_hud[side].balloons = balloons; g_hud[side].lives = lives;
}

/* Title screen (art: assets/font/draw_hud_title_final.py title_final(), art row r = fix row r + 2). Everything is drawn
 * once after the fix layer clear and again only when its value changes; draw() resets the cache on a state change. */
#define HUD_STAGE_ROW 5      /* arcade "STAGE n" / BONUS, centred between the score block (columns 2..15) and the right edge */
/* Blank line wide enough to erase any round-start banner line (the party goal lines are PARTY_GOAL_W wide). */
#define BANNER_BLANK "                                    "
#define TITLE_HI_ROW 3
#define TITLE_PLATE_ROW 22
#define TITLE_GG_GOAL_ROW 21  /* Gum Games picker: goal of the event under the cursor */
#define TITLE_SELECT_ROW 23   /* rows 23 to 27: the mode select, drawn only while it is open */
#define TITLE_PLAYERS_ROW 28   /* the players line; the PARTY and Gum Games goal line takes its row while the list is open on those rows */
#define SUB_ROWS 7            /* lines of the PARTY submenu window, rows 23..29 */
#define TITLE_GOAL_ROW 28    /* goal line, cols 2..37, under the last list row (27); credits row 29 */
#define TITLE_CREDIT_ROW 29
#define TITLE_BLINK_ON 3      /* the plate line shows for 3 of every 5 logo animation steps */
#define BIOS_COMPULSION_S ((volatile u8 *)0x10fdda) /* BIOS_COMPULSION_TIMER, BCD seconds; 0x10fddb counts its frames */
#define BIOS_CREDIT_BCD ((volatile u8 *)0x10fe00) /* BCD, 1 = one credit; measured by tests/mame/logo_check.lua under UniBIOS 4.0 (nullbios never counts) */
enum { TL_UNKNOWN = 0xFF, TL_HIDDEN = 0, TL_PRESS, TL_INSERT };
static struct { u8 init, line, select, credits, players_cr, cplate; u32 hi; u8 mode; } g_title = { 0, TL_UNKNOWN, 0xFF, 0xFF, 0xFF, 0, 0xFFFFFFFFu, 0xFF };
volatile u16 g_title_press_draws; /* test sentinel: frames "PRESS START" was (re)sent */

static void title_reset(void) { g_title.init = 0; g_title.line = TL_UNKNOWN; g_title.select = 0xFF; g_title.credits = 0xFF; g_title.players_cr = 0xFF; g_title.cplate = 0; g_title.hi = 0xFFFFFFFFu; g_title.mode = 0xFF; }

static void plate(u8 x0, u8 x1, u8 row) {
    gfx_fix_tile((u8)(x0 - 1), row, PAL_TEXT, FIXFONT_PLATE_CAP_LEFT);
    for (u8 c = x0; c <= x1; c++) gfx_fix_tile(c, row, PAL_TEXT, FIXFONT_PLATE_FILL);
    gfx_fix_tile((u8)(x1 + 1), row, PAL_TEXT, FIXFONT_PLATE_CAP_RIGHT);
}

static u8 credits_now(void) {
    u8 b = *BIOS_CREDIT_BCD;
    u8 n = (u8)((b >> 4) * 10 + (b & 15));
    return n > 99 ? 99 : n;
}

/* The CREDITS plate (title, play, game over): drawn once after title_reset, text resent only when the count moves. Returns the count. */
static u8 draw_credits(void) {
    if (!g_title.cplate) { g_title.cplate = 1; g_title.credits = 0xFF; plate(28, 36, TITLE_CREDIT_ROW); }
    u8 cr = credits_now();
    if (cr != g_title.credits) {
        g_title.credits = cr;
        char buf[3];
        put_number(buf, cr, 2);
        gfx_text_backed(28, TITLE_CREDIT_ROW, PAL_TEXT, "CREDITS ");
        gfx_text_backed(36, TITLE_CREDIT_ROW, PAL_TEXT, buf + 1);
        if (cr > 9) gfx_text_backed(35, TITLE_CREDIT_ROW, PAL_TEXT, buf);
    }
    return cr;
}

/* A takes a banked credit the way Start does: the BIOS only deducts on a Start press, so for A the game does the BCD
 * subtraction itself. Returns 1 when a credit was taken. */
static u8 take_credit(void) {
    u8 b = *BIOS_CREDIT_BCD;
    if (!b) return 0;
    *BIOS_CREDIT_BCD = (u8)((b & 15) ? b - 1 : b - 7);
    return 1;
}

/* The two title Sootlings (art: player left, computer right and mirrored), in the sprites after the logo. They step with the
 * logo animation; tiles and positions are sent only when the step changes. */
static u16 g_title_soot_step = 0xFFFF;
static void title_soot_reset(void) { g_title_soot_step = 0xFFFF; }
static void title_soot_step(int active) {
    if (!active) {
        if (g_title_soot_step != 0xFFFF) for (u8 i = 0; i < TITLE_SOOT_COUNT; i++) gfx_word((u16)(ADDR_SCB3 + TITLE_SOOT_SPRITE + i), 0);
        g_title_soot_step = 0xFFFF;
        return;
    }
    u16 t = logo_ticks();
    if (t == g_title_soot_step) return;
    g_title_soot_step = t;
    static const s8 BOB[8] = { 0, 1, 2, 1, 0, -1, -2, -1 };
    for (u8 who = 0; who < 2; who++) {
        const SootlingAnim *an = &sootling_anims[who];
        u8 k = (u8)((t + who * 3) % 8);
        const SootlingFrame *f = &sootling_frames[soot_frame(who, (u8)(k % an->frame_count))];
        u16 slot = (u16)(TITLE_SOOT_SPRITE + who * SOOT_COLUMNS);
        u16 attr = (u16)(((SOOT_PAL_SLOT + f->palette) << 8) | (who ? SOOT_FLIP : 0));
        soot_strips(slot, f, &sootling_tile_index[f->tile_offset], who, attr);
        gfx_sprite_place(slot, SOOT_COLUMNS, f->tiles_h, who ? 250 : 14, (who ? 118 : 112) + BOB[k]);
    }
}

/* Centred backed line on a title row (the row is blanked to the open sky first). */
static void title_line(u8 row, u8 pal, const char *str) {
    u8 n = 0;
    while (str[n]) n++;
    text(2, row, PAL_TEXT, BANNER_BLANK);
    gfx_text_backed((u8)((VQ_FIX_COLS - n) / 2), row, pal, str);
}

/* One list line: cursor at col 15, name at col 17 padded over the previous line's text. */
static void sub_line(u8 row, u8 on, const char *name) {
    char buf[16];
    u8 i = 0;
    while (name[i] && i < 15) { buf[i] = name[i]; i++; }
    while (i < 15) buf[i++] = ' ';
    buf[15] = 0;
    text(2, row, PAL_TEXT, BANNER_BLANK);
    gfx_text_backed(15, row, PAL_HIGH, on ? ">" : " ");
    gfx_text_backed(17, row, on ? PAL_HIGH : PAL_TEXT, buf);
}

static void draw_mode_select(u8 open, u8 mode, u8 sel, u8 sub) {
    u8 key = open ? (u8)(1 + mode + (sub ? 8 + sel * 8 : 0)) : 0; /* the submenu cursor is part of the key: the view redraws when it moves */
    if (key == g_title.select) return;
    g_title.select = key;
    g_title.players_cr = 0xFF; /* the goal line shares the players row: redraw it after any change */
    { /* PARTY submenu: the goal of the entry under the cursor (a party rule's goal line, or the rules card goal of a gum game) above the list */
        const GgCard *gc = (open && sub) ? flow_menu_card(sel) : 0;
        const char *pg = (open && sub) ? flow_menu_goal(sel) : 0;
        if (gc) title_line(TITLE_GG_GOAL_ROW, PAL_TEXT, gc->goal); else if (pg) title_line(TITLE_GG_GOAL_ROW, PAL_TEXT, pg); else text(2, TITLE_GG_GOAL_ROW, PAL_TEXT, BANNER_BLANK);
    }
    if (!open) { text(15, TITLE_SELECT_ROW, PAL_TEXT, "          "); text(15, TITLE_SELECT_ROW + 1, PAL_TEXT, "          "); text(15, TITLE_SELECT_ROW + 2, PAL_TEXT, "          "); text(15, TITLE_SELECT_ROW + 3, PAL_TEXT, "                          "); text(15, TITLE_SELECT_ROW + 4, PAL_TEXT, "          "); text(2, TITLE_GOAL_ROW, PAL_TEXT, "                                    "); return; }
    if (sub) { /* PARTY_MENU_COUNT entries in a window of SUB_ROWS lines on rows 23..29 that scrolls to keep the cursor in view */
        u8 top = sel < SUB_ROWS / 2 ? 0 : sel + SUB_ROWS / 2 >= PARTY_MENU_COUNT ? PARTY_MENU_COUNT - SUB_ROWS : sel - SUB_ROWS / 2;
        for (u8 i = 0; i < SUB_ROWS; i++) sub_line((u8)(TITLE_SELECT_ROW + i), (u8)(top + i) == sel, flow_menu_name((u8)(top + i)));
        return;
    }
    static const char *const names[4] = { "ARENA", "GUM TRIP", "ARCADE", "PARTY" };
    static const u8 order[4] = { GAME_MODE_ARENA, GAME_MODE_TRIP, GAME_MODE_ARCADE, GAME_MODE_PARTY };
    for (u8 i = 0; i < 4; i++) sub_line((u8)(TITLE_SELECT_ROW + i), order[i] == mode, names[i]);
    text(2, TITLE_SELECT_ROW + 4, PAL_TEXT, BANNER_BLANK);
    if (mode == GAME_MODE_PARTY) title_line(TITLE_GOAL_ROW, PAL_TEXT, "A TO CHOOSE AN EVENT");
    else text(2, TITLE_GOAL_ROW, PAL_TEXT, BANNER_BLANK);
}

static void draw_title(const FlowView *v) {
    if (!g_title.init) {
        g_title.init = 1;
        gfx_text_backed(11, TITLE_HI_ROW, PAL_HIGH, "HIGH SCORE");
    }
    u32 hi = v->table->score[0];
    if (hi > 999999) hi = 999999;
    if (hi != g_title.hi) {
        g_title.hi = hi;
        char buf[8];
        put_number(buf, hi, 6);
        gfx_text_backed(22, TITLE_HI_ROW, PAL_TEXT, buf);
    }
    u8 cr = draw_credits();
    if (cr != g_title.players_cr && !(v->select_open && (v->mode == GAME_MODE_PARTY || v->mode == GAME_MODE_GUM))) {
        g_title.players_cr = cr;
        plate(13, 26, TITLE_PLAYERS_ROW); /* the goal line may have erased it */
        /* Two players need two credits: offer 2 only when they are banked. */
        gfx_text_backed(13, TITLE_PLAYERS_ROW, PAL_TEXT, cr >= 2 ? "1 OR 2 PLAYERS" : "1 PLAYER      ");
    }
    u8 line = (logo_ticks() % 5) < TITLE_BLINK_ON ? ((cr > 0 || v->select_open) ? TL_PRESS : TL_INSERT) : TL_HIDDEN;
    if (line != g_title.line) {
        g_title.line = line;
        if (line == TL_HIDDEN) {
            text(13, TITLE_PLATE_ROW, PAL_TEXT, "             "); /* a space is the empty fix tile: caps and fill both clear */
        } else {
            plate(14, 24, TITLE_PLATE_ROW);
            gfx_text_backed(14, TITLE_PLATE_ROW, PAL_HIGH, line == TL_PRESS ? "PRESS START" : "INSERT COIN");
            if (line == TL_PRESS) g_title_press_draws++;
        }
    }
    draw_mode_select(v->select_open, v->mode, v->sub_i, v->sub_open);
}

/* Attract how-to-play overlay (fix layer, bottom left: cols 1..13, rows 21..26; the title's reserved cells are rows 3, 22-25 from col 11 on, row 29, so only
 * col 13 of row 22 is shared and the demo state never draws the title). Leaving the demo state clears the whole fix layer (draw), so nothing needs erasing. */
#define OV_COL_MIN 1
#define OV_COL_MAX 13
#define OV_ROW_MIN 21
#define OV_ROW_MAX 26
_Static_assert(ATTRACT_CAP1_ROW >= OV_ROW_MIN && ATTRACT_START_ROW + 2 - 1 <= OV_ROW_MAX && ATTRACT_BUTTON_ROW + 3 - 1 <= OV_ROW_MAX, "overlay rows leave 21..26");
_Static_assert(ATTRACT_CAP1_COL >= OV_COL_MIN && ATTRACT_START_COL + 2 - 1 <= OV_COL_MAX && ATTRACT_BUTTON_COL + 3 - 1 <= OV_COL_MAX, "overlay cols leave 1..13");
_Static_assert(ATTRACT_FIX_BASE >= FIXFONT_SROM_TILES && ATTRACT_FIX_BASE + ATTRACT_ICON_TILES <= 0x1000, "overlay icon tiles overlap the font or leave the 12-bit fix code range");
static u8 g_ov_stage;  /* 0: captions, 1: Start icon, 2: running */
static u8 g_ov_key = AO_NONE;
/* Parts of the first key still to draw (2: lever and button, 1: button): on demo frame 3 the key, the island ring and the pickups
 * together ran logic past vblank (thoughts/spot/reports/demo-start.md), so the first key comes one part per frame. */
static u8 g_ov_part;
static void ov_frame(u8 col, u8 row, u8 frame);

static u8 ov_key_state(u8 key) { return key == AO_FLAP ? 0 : 1; }
static void ov_key_lever(u8 key) {
    u8 lever = attract_states[ov_key_state(key)].lever;
    if (key == AO_STEER_LEFT) lever = ATTRACT_FRAME_STICK_LEFT;
    ov_frame(ATTRACT_LEVER_COL, ATTRACT_LEVER_ROW, lever);
}
static void ov_key_button(u8 key) { ov_frame(ATTRACT_BUTTON_COL, ATTRACT_BUTTON_ROW, attract_states[ov_key_state(key)].a); }

static void ov_frame(u8 col, u8 row, u8 frame) {
    const attract_frame_t *fr = &attract_frames[frame];
    for (u8 r = 0; r < fr->rows; r++)
        for (u8 c = 0; c < fr->cols; c++) {
            int8_t t = fr->tiles[r * fr->cols + c];
            if (t == ATTRACT_ICON_BLANK) gfx_fix_tile((u8)(col + c), (u8)(row + r), 0, FIXFONT_BLANK);
            else gfx_fix_tile((u8)(col + c), (u8)(row + r), ATTRACT_PAL_SLOT, (u16)(ATTRACT_FIX_BASE + t));
        }
}

/* One item per frame while the demo starts (captions, Start icon), then the action word, lever and A icon, redrawn only when the key changes. */
static void draw_overlay(const FlowView *v) {
    if (g_ov_stage == 0) {
        const char *const *cap = attract_captions[v->game->mode];
        text(ATTRACT_CAP1_COL, ATTRACT_CAP1_ROW, PAL_TEXT, cap[0]);
        text(ATTRACT_CAP2_COL, ATTRACT_CAP2_ROW, PAL_TEXT, cap[1]);
        g_ov_stage = 1;
    } else if (g_ov_stage == 1) {
        ov_frame(ATTRACT_START_COL, ATTRACT_START_ROW, attract_states[0].start);
        g_ov_stage = 2;
    } else if (g_ov_part) {
        if (g_ov_part == 2) ov_key_lever(g_ov_key); else ov_key_button(g_ov_key);
        g_ov_part--;
    } else if (v->ov_key != AO_NONE && v->ov_key != g_ov_key) {
        const u8 first = g_ov_key == AO_NONE;
        g_ov_key = v->ov_key;
        text(ATTRACT_ACTION_COL, ATTRACT_ACTION_ROW, FIXFONT_PAL_GOLD, ov_key_state(g_ov_key) == 0 ? "FLAP " : "STEER");
        if (first) { g_ov_part = 2; return; }
        ov_key_lever(g_ov_key);
        ov_key_button(g_ov_key);
    }
}

/* Writes the result screen cells that differ from what was sent: the first frames fill all cells, then one dirty region per frame. */
_Static_assert(RES_SPRITE_END <= SPRITE_SLOT_END, "result sprites leave the fixed slot ranges");
static void draw_result_fx(const Result *r);
static void podium_step(const Result *r);
static void podium_clear_actors(void);

/* Fix rows 0-1 sit above the visible top (raster line 16): art row r goes to fix row r + 2, as on the title screen. */
#define RES_FIX_ROW0 2

static void draw_result(const Game *g) {
    Result *r = &g_flow.game.res; /* the dirty bits are drawing bookkeeping the core only sets */
    u8 col, row, n = 0, bit;
    if (!g_res_up) {
        g_res_up = 1;
        g_res_col = g_res_row = 0;
        g_res_filled = 0;
        g_res_pend = 0;
        for (u16 i = 0; i < RESV_W * RESV_H; i++) g_res_shadow[i] = 0xFFFF;
        g_resfx_stage = 0;
        g_resfx_crank = 0xFF;
        for (u8 i = 0; i < RES_SLOTS; i++) g_resfx_bub[i] = 0xFF;
        for (u8 i = 0; i < 5; i++) g_resfx_wheel[i] = 0xFF;
        if (r->podium) podium_clear_actors();
    }
    /* The effects wait for the fill: both at once fill the VRAM queue and gfx_drain stalls the frame past vblank. */
    if (g_res_filled == RESV_W * RESV_H) {
        if (r->podium) { podium_step(r); r->podium = 2; }   /* 2: the podium scene is up, the MAME gate reads this (tests/mame/gum_poop_check.lua) */
        else draw_result_fx(r);
    }
    g_res_pend |= r->dirty;
    r->dirty = 0;
    if (g_res_filled < RESV_W * RESV_H) {
        while (n < RES_FILL_PER_FRAME && g_res_row < RESV_H) {
            u16 c = result_cell(&g->res, g_res_col, g_res_row);
            g_res_shadow[g_res_filled++] = c;
            gfx_fix_tile(g_res_col, (u8)(g_res_row + RES_FIX_ROW0), (u8)(c >> 12), (u16)(c & 0xFFF));
            n++;
            if (++g_res_col == RESV_W) { g_res_col = 0; g_res_row++; }
        }
        return;
    }
    for (bit = 1; bit <= RES_DIRTY_TICKET; bit = (u8)(bit << 1)) {
        u8 r0, r1, c0, c1;
        if (!(g_res_pend & bit)) continue;
        g_res_pend &= (u8)~bit;
        result_region(bit, &r0, &r1, &c0, &c1);
        for (row = r0; row <= r1; row++) {
            for (col = c0; col <= c1; col++) {
                u16 c = result_cell(&g->res, col, row);
                u16 *sh = &g_res_shadow[row * RESV_W + col];
                if (c == *sh) continue;
                *sh = c;
                gfx_fix_tile(col, (u8)(row + RES_FIX_ROW0), (u8)(c >> 12), (u16)(c & 0xFFF));
            }
        }
        break;
    }
}

static void resfx_load_palettes(void) {
    for (u8 p = 0; p < RESFX_PALETTE_COUNT; p++)
        for (u8 i = 0; i < 16; i++) gfx_pal((u16)((RESFX_PAL_SLOT + p) * 16 + i), resfx_palettes[p][i]);
}

static void resfx_frame(u16 slot, u8 anim, u8 k) {
    const ResfxFrame *f = &resfx_frames[resfx_anims[anim].first_frame + k];
    gfx_sprite_strips(slot, f->tiles_w, f->tiles_h, &resfx_tile_index[f->tile_offset], RESFX_TILE_BASE, (u16)((RESFX_PAL_SLOT + f->palette) << 8));
}

static void resfx_hide(void) {
    /* one run, not one word op per sprite (about 34 raster lines on the stage entry after the bonus, reports/stage-spike.md) */
    static const u16 k_zero[RES_SPRITE_END - RES_GLASS_SPRITE];
    gfx_scb_run((u16)(ADDR_SCB3 + RES_GLASS_SPRITE), 1, k_zero, (u8)(RES_SPRITE_END - RES_GLASS_SPRITE));
}

/* Event result podium (owner pick B 2026-11-23): the sprites over the transparent fix text of result_view.c podium_cell.
 * Two blocks on the turf (the winner's is two tiles tall, a tie makes both tall), a bird on each, a crown over the winner,
 * the scores as 16 x 24 digits. Positions are the draft's (thoughts/shared/drafts/2026-11-23-event-result). The slots are
 * the gum machine's (resfx_hide parks them); on a line at most 6 block + 4 bird + 12 digit columns. */
#define POD_BLOCK_SPRITE RES_GLASS_SPRITE
#define POD_BIRD_SPRITE (POD_BLOCK_SPRITE + 6)
#define POD_CROWN_SPRITE (POD_BIRD_SPRITE + 2 * SOOT_COLUMNS)
#define POD_DIGIT_SPRITE (POD_CROWN_SPRITE + 1)
_Static_assert(POD_DIGIT_SPRITE + 2 * RESV_POD_DIGITS <= RES_SPRITE_END, "the podium sprites must fit the result slots");
#define POD_FLOOR_Y 200
#define POD_DIGIT_Y 180
static u8 g_pod_up, g_pod_k;
static u32 g_pod_score[2];
static u16 g_pod_blk[2][2][2]; /* [team][left, middle][top, bottom] tile: static, the queue keeps the pointers */

static void podium_block(u8 side, u8 tall) {
    u8 rows = tall ? 2 : 1;
    for (u8 c = 0; c < 3; c++) {
        u16 slot = (u16)(POD_BLOCK_SPRITE + side * 3 + c);
        gfx_sprite_strips(slot, 1, rows, g_pod_blk[side][c == 1], PODIUM_TILE_BASE, (u16)(((PODIUM_PAL_SLOT + side) << 8) | (c == 2 ? SOOT_FLIP : 0))); /* right column: the left one mirrored */
        gfx_sprite_place(slot, 1, rows, (side ? 160 : 112) + c * 16, POD_FLOOR_Y - rows * 16);
    }
}

/* Player 1 looks right, the other bird is the same clip mirrored. Returns the y of the top of the art. */
static int podium_bird(const Result *r, u8 side, u8 tall, u8 clip, int bob) {
    u8 anim = side && r->cpu ? SOOTLING_ANIM_CPU : SOOTLING_ANIM_PLAYER;
    const SootlingFrame *f = &sootling_frames[soot_frame(anim, (u8)(clip % sootling_anims[anim].frame_count))];
    u16 slot = (u16)(POD_BIRD_SPRITE + side * SOOT_COLUMNS);
    int top = POD_FLOOR_Y - (tall ? 32 : 16) + 1 - f->tiles_h * 16 + bob;
    soot_strips(slot, f, &sootling_tile_index[f->tile_offset], side, (u16)(((side && !r->cpu ? SOOT_P2_PAL_SLOT : SOOT_PAL_SLOT + f->palette) << 8) | (side ? SOOT_FLIP : 0)));
    gfx_sprite_place(slot, SOOT_COLUMNS, f->tiles_h, (side ? 184 : 136) - SOOT_COLUMNS * 8, top);
    return top + f->pad_top;
}

static void podium_digits(u8 side, u32 v, u8 gold, u8 shown) {
    const PodiumAnim *an = &podium_anims[gold ? PODIUM_ANIM_DIGIT_GOLD : PODIUM_ANIM_DIGIT_BLUE];
    u8 n = shown ? resv_digits(v) : 0;
    for (u8 i = 0; i < RESV_POD_DIGITS; i++) {
        u16 slot = (u16)(POD_DIGIT_SPRITE + side * RESV_POD_DIGITS + i);
        if (i >= n) { gfx_word((u16)(ADDR_SCB3 + slot), 0); continue; }
        const PodiumFrame *f = &podium_frames[an->first_frame + resv_digit(v, n, i)];
        gfx_sprite_strips(slot, 1, f->tiles_h, &podium_tile_index[f->tile_offset], PODIUM_TILE_BASE, (u16)((PODIUM_PAL_SLOT + f->palette) << 8));
        gfx_sprite_place(slot, 1, f->tiles_h, (side ? RESV_POD_CX2 : RESV_POD_CX1) - n * 8 + i * 16 - f->pad_left, POD_DIGIT_Y - f->pad_top);
    }
}

/* The actors of the event leave: the podium text is transparent, the frozen world behind it stays as the backdrop. */
static void podium_clear_actors(void) {
    hero_hide();
    dead_release_all();
    pool_hide_all();
    gfx_word(ADDR_SCB3 + GUM_SPRITE, 0); gfx_word(ADDR_SCB3 + GUM_P2_SPRITE, 0);
    tug_strand_step(0); toss_bubble_step(0); fling_arc_step(0);
    resfx_hide();
    g_pod_up = 0;
}

static void podium_step(const Result *r) {
    static const s8 BOB[8] = { 0, 1, 2, 1, 0, -1, -2, -1 }; /* the title birds' bob */
    u8 two = (u8)(r->two || r->cpu), tie = r->winner == RES_WIN_TIE, k = (u8)((r->t >> 3) & 7);
    const PodiumFrame *cf = &podium_frames[podium_anims[PODIUM_ANIM_CROWN].first_frame];
    if (!g_pod_up) {
        g_pod_up = 1; g_pod_k = 0xFF; g_pod_score[0] = g_pod_score[1] = 0xFFFFFFFFu;
        for (u8 t = 0; t < 2; t++)
            for (u8 i = 0; i < 4; i++) /* sheet order: top left, top middle, bottom left, bottom middle */
                g_pod_blk[t][i & 1][i >> 1] = podium_tile_index[podium_frames[podium_anims[PODIUM_ANIM_BLOCK0 + t].first_frame + i].tile_offset];
        for (u8 s = 0; s <= two; s++) podium_block(s, tie || r->winner == s);
        if (!tie) gfx_sprite_strips(POD_CROWN_SPRITE, 1, cf->tiles_h, &podium_tile_index[cf->tile_offset], PODIUM_TILE_BASE, (u16)((PODIUM_PAL_SLOT + cf->palette) << 8));
    }
    if (k != g_pod_k) { /* the winner bobs through its clip, the loser stands still */
        g_pod_k = k;
        for (u8 s = 0; s <= two; s++) {
            u8 win = !tie && r->winner == s;
            int top = podium_bird(r, s, tie || win, win ? k : 0, win ? BOB[k] : 0);
            if (win) gfx_sprite_place(POD_CROWN_SPRITE, 1, cf->tiles_h, (s ? 184 : 136) - 8 - cf->pad_left, top - 15 - cf->pad_top);
        }
    }
    for (u8 s = 0; s <= two; s++) {
        u32 v = s ? r->score2 : r->score_shown;
        if (v == g_pod_score[s]) continue;
        g_pod_score[s] = v;
        podium_digits(s, v, tie || r->winner == s, !(s && r->cpu && !v)); /* a computer score the event does not store shows no digits (game_end_event) */
    }
}

/* The moving parts of the result screen: cage glass, falling bubbles, counter wheels, crank, ticket, and the sky colours.
 * The sprites are set up over four frames (the bonus stage parks these slots first), then only words that change are sent. */
static void draw_result_fx(const Result *r) {
    int x, y;
    u8 i, ph = (u8)(r->t & 7);
    if (r->t < 3) return;
    switch (g_resfx_stage) {
    case 0:
        resfx_hide();
        resfx_frame(RES_GLASS_SPRITE, RESFX_ANIM_GLASS, 0);
        gfx_sprite_place(RES_GLASS_SPRITE, 6, 5, RESULT_CAGE_X, RESULT_CAGE_Y);
        g_resfx_stage++;
        return;
    case 1:
        gfx_sprite_unchained(RES_BUBBLE_SPRITE, RES_SLOTS);
        gfx_sprite_unchained(RES_WHEEL_SPRITE, 5);
        for (i = 0; i < 5; i++) gfx_word((u16)(ADDR_SCB4 + RES_WHEEL_SPRITE + i), gfx_scb4_word(RESULT_WHEEL_X + 16 * i));
        g_resfx_stage++;
        return;
    case 2:
        resfx_frame(RES_TICKET_SPRITE, RESFX_ANIM_TICKET, 0);
        g_resfx_stage++;
        return;
    case 3:
        gfx_sprite_place(RES_TICKET_SPRITE, 12, 5, RESULT_TICKET_X, RESULT_TICKET_Y - RESULT_TICKET_H);
        gfx_sprite_place(RES_CRANK_SPRITE, 2, 2, RESULT_CRANK_X, RESULT_CRANK_Y);
        g_resfx_stage++;
        break;
    default:
        break;
    }
    for (i = 0; i < r->caught; i++) {
        u16 slot = (u16)(RES_BUBBLE_SPRITE + i);
        u8 fr = res_bubble(r, i, &x, &y);
        if (!fr) { gfx_word((u16)(ADDR_SCB3 + slot), 0); continue; }
        if (g_resfx_bub[i] != fr) { g_resfx_bub[i] = fr; resfx_frame(slot, RESFX_ANIM_BUBBLE, (u8)(fr - 1)); }
        gfx_word((u16)(ADDR_SCB3 + slot), gfx_scb3_word(1, RESULT_CAGE_Y + y - 8));
        gfx_word((u16)(ADDR_SCB4 + slot), gfx_scb4_word(RESULT_CAGE_X + x - 8));
    }
    for (i = 0; i < 5; i++) { /* wheel frame k shows digit k over k + 1: the position scrolls it up through the window */
        u8 v = r->wheel[i], fr = (u8)(v >> 4);
        if (g_resfx_wheel[i] != fr) { g_resfx_wheel[i] = fr; resfx_frame((u16)(RES_WHEEL_SPRITE + i), RESFX_ANIM_WHEEL, fr); }
        gfx_word((u16)(ADDR_SCB3 + RES_WHEEL_SPRITE + i), gfx_scb3_word(2, RESULT_WHEEL_Y - (v & 15)));
    }
    if (g_resfx_crank != r->crank) { g_resfx_crank = r->crank; resfx_frame(RES_CRANK_SPRITE, RESFX_ANIM_CRANK, r->crank); }
    gfx_word((u16)(ADDR_SCB3 + RES_TICKET_SPRITE), gfx_scb3_word(5, RESULT_TICKET_Y - RESULT_TICKET_H + r->ticket_out));
    /* Living sky: the stripe colours (entries 1..12 of the three sky palettes) move one place every 8 frames, one palette a
     * frame (12 palette words); the star colours (13..15) change places every 16 frames. */
    if (ph < 3) {
        u16 base = (u16)((FIXFONT_PAL_RES_SKY0 + ph) * 16);
        u8 k = g_resfx_sky;
        if (!ph) { if (++g_resfx_sky == 12) g_resfx_sky = 0; k = g_resfx_sky; }
        for (i = 0; i < 12; i++) {
            gfx_pal((u16)(base + 1 + i), fixfont_palettes[FIXFONT_PAL_RES_SKY0 + ph][1 + k]);
            if (++k == 12) k = 0;
        }
    } else if ((r->t & 15) == 4) {
        if (++g_resfx_star == 3) g_resfx_star = 0;
        for (i = 0; i < 9; i++) {
            u8 p = (u8)(i >= 6 ? 2 : i >= 3 ? 1 : 0), e = (u8)(i - 3 * p), k = (u8)(e + g_resfx_star);
            if (k >= 3) k = (u8)(k - 3);
            gfx_pal((u16)((FIXFONT_PAL_RES_SKY0 + p) * 16 + 13 + e), fixfont_palettes[FIXFONT_PAL_RES_SKY0 + p][13 + k]);
        }
    }
}

static void draw(const FlowView *v) {
    char buf[3];
    u8 res_over = 0;
    /* The header only changes with the state: send it after the clear. The fix shadow (vq_fix_put) keeps it, and a
     * hardware reset of the fix layer goes through video_init, which forces this branch (g_draw_state = -1). */
    if (g_res_up && !(v->state == FLOW_PLAYING && v->game && v->game->res.active)) {
        g_res_up = 0;
        res_over = 1;
        resfx_hide();
        g_draw_state = -1; /* the result screen is over: clear the fix layer, the HUD comes back */
    }
    if (g_hl_up && v->highlight < 0) {
        g_hl_up = 0;
        g_draw_state = -1; /* the title's highlighted table is gone (the mode list opened): clear its rows */
    }
    static u8 g_toss_up;   /* a restart into or out of Toss Gum inside FLOW_PLAYING (the P2 join) needs the fix layer cleared like a state change */
    u8 toss_now = v->game && seated(v->game);
    if (toss_now != g_toss_up) { g_toss_up = toss_now; g_draw_state = -1; }
    if ((int)v->state != g_draw_state) {
        if (res_over) gfx_cls_busy(); else gfx_cls();
        title_reset();
        g_draw_state = (int)v->state;
        g_hud[0].kind = g_hud[1].kind = HUD_KIND_NONE;
        g_ov_stage = 0; g_ov_key = AO_NONE; g_ov_part = 0;
        g_rs_drawn = RS_NONE; g_rs_num = 0; g_banner_up = 0; g_howto_up = 0; g_card_up = 0; g_mode_key = 0xFF; g_blow_key = 0xFFFFFFFFu; meter_reset(); g_fling_flag = -1; g_cont_key[0] = g_cont_key[1] = 0xFF; g_stage_key = 0xFF; g_over_up = 0;
        g_meter_step = METER_NONE;
        set_distress(0);
#ifdef GUMBIRDS_DEBUG_HEADER /* gmake DEBUG_HEADER=1; the normal build leaves the top rows to the HUD */
        text(2, 2, PAL_TEXT, "GUMBIRDS");
        text(2, 3, PAL_TEXT, STATE_NAME[v->state]);
        /* pad so a shorter name overwrites a longer one */
        text(2 + (u8)0, 4, PAL_TEXT, "              ");
#endif
    }
    switch (v->state) {
    case FLOW_ATTRACT_TITLE:
        draw_title(v);
        break;
    case FLOW_ATTRACT_TABLE:
        draw_table(v->table, v->table_mode, v->highlight, 12); /* caption row 10, entries 12..21: centered in visible rows 2..29 */
        break;
    case FLOW_ATTRACT_DEMO:
    case FLOW_PLAYING:
    case FLOW_GAME_OVER:
        if (v->state == FLOW_PLAYING && v->game && v->game->res.active) {
            draw_result(v->game);
            break;
        }
        if (v->state != FLOW_ATTRACT_DEMO) draw_credits();
        /* Per-frame HUD: resend a side only when its values moved (or first frame of the state with a game). */
        if (v->game) {
            const Game *g = v->game;
            u8 arc = game_lives_mode(g) && g->party_rule != PARTY_ROOST && v->state != FLOW_ATTRACT_DEMO; /* Roost Rule: no lives, so no counter */
            u8 p2hud = (g->mode == GAME_MODE_ARCADE || g->mode == GAME_MODE_ARENA || seated(g)) && v->state != FLOW_ATTRACT_DEMO; /* the P2 side: PRESS / INSERT / stats */
            u8 b0 = (u8)g->hero[0].balloons;
            u8 l0 = (u8)g->lives[0].lives;
            /* P1: the old block (score, balloons; no balloons row in Gum Trip), plus lives in the arcade */
            if (!seated(g) && (g_hud[0].kind != HUD_KIND_STATS || g->score != g_hud[0].score || b0 != g_hud[0].balloons || l0 != g_hud[0].lives)) {
                hud_side_stats(0, g->score, b0, l0, arc, g->mode != GAME_MODE_TRIP && g->mode != GAME_MODE_GUM);
                g_hud[0].kind = HUD_KIND_STATS; g_hud[0].score = g->score; g_hud[0].balloons = b0; g_hud[0].lives = l0;
            }
            if (p2hud) {
                u8 in = g->players == 2;
                u8 cr = g->credits;
                u8 out = (!in || g->lives[1].state == ARC_LIFE_ENDED); /* never joined, or out of lives and continues */
                if (seated(g)) hud_side(1, game_can_join_p2(g) && v->state == FLOW_PLAYING ? (cr > 0 ? HUD_KIND_PRESS : HUD_KIND_INSERT) : HUD_KIND_BLANK, 0, 0, 0, 0, 0);   /* Toss Gum: no score block, only the join prompt before the first burst */
                else if (out && v->state == FLOW_PLAYING) hud_side(1, cr > 0 ? HUD_KIND_PRESS : HUD_KIND_INSERT, 0, 0, 0, 0, 0);
                else if (in) hud_side(1, HUD_KIND_STATS, g->lives[1].score, (u8)g->hero[1].balloons, (u8)g->lives[1].lives, g->party_rule != PARTY_ROOST, 1);
                else hud_side(1, HUD_KIND_BLANK, 0, 0, 0, 0, 0);
            }
        }
        if (v->game && v->game->mode == GAME_MODE_TRIP && !v->game->gg_fling) draw_gum_meter(v->game->trip.gum);
        else set_distress(0);
        if (v->state == FLOW_ATTRACT_DEMO && v->game) draw_overlay(v);
        if (v->state == FLOW_PLAYING && v->game && (v->game->mode == GAME_MODE_GUM || v->game->gg_fling) && !v->card) { if (v->game->gg_tug) draw_tug(v->game); else if (v->game->gg_toss) draw_toss(v->game); else if (v->game->gg_fling) draw_fling(v->game); else if (v->game->gg_gather) draw_gather(v->game); else if (v->game->gg_poop) draw_poop_man(v->game); else if (v->game->gg_pop) draw_pop_drop(&v->game->pop); else if (v->game->gg_dash) draw_flap_dash(&v->game->dash); else if (v->game->gg_race) draw_burst_race(&v->game->race); else draw_big_blow(&v->game->blow); }
        if (v->state == FLOW_PLAYING && v->game) draw_prompts(v->game, (v->game->mode == GAME_MODE_GUM || v->game->gg_fling) && !v->card && !v->howto);
        else prompt_reset();
        {
            /* mode name in the bottom-left corner while playing, written when the mode or rule changes only */
            u8 key = (v->state == FLOW_PLAYING && v->game) ? (v->game->party_rule != PARTY_NONE ? (u8)(8 + v->game->party_rule) : (u8)(1 + v->game->mode)) : 0;
            if (key != g_mode_key) {
                char lb[MODE_LABEL_W + 1];
                const char *name = !key ? "" : key >= 8 ? game_party_name(v->game->party_rule) : v->game->mode == GAME_MODE_TRIP ? "GUM TRIP" : v->game->mode == GAME_MODE_GUM ? "GUM GAMES" : v->game->mode == GAME_MODE_ARCADE ? "ARCADE" : "ARENA";
                u8 i = 0;
                g_mode_key = key;
                while (i < MODE_LABEL_W && name[i]) { lb[i] = name[i]; i++; }
                while (i < MODE_LABEL_W) lb[i++] = ' ';
                lb[MODE_LABEL_W] = 0;
                text(MODE_LABEL_COL, MODE_LABEL_ROW, PAL_TEXT, lb);
            }
        }
        {
            /* PARTY how-to: rule name, three lines and the skip prompt, written when the screen changes only */
            u8 up = (v->state == FLOW_PLAYING && v->game && v->howto) ? 1 : 0;
            if (up != g_howto_up) {
                u8 i;
                u8 rule = v->game->party_rule;
                g_howto_up = up;
                gfx_center_text(HOWTO_ROW, PAL_TEXT, up ? game_party_name(rule) : BANNER_BLANK);
                for (i = 0; i < 3; i++) gfx_center_text((u8)(HOWTO_ROW + 1 + i), PAL_TEXT, up ? game_party_howto(rule, i) : BANNER_BLANK);
                gfx_center_text(HOWTO_ROW + 5, PAL_TEXT, up ? "PRESS A OR START TO SKIP" : BANNER_BLANK);
            }
        }
        {
            /* Gum Games rules card, layout A (card_draw); the Fling bars and status text wait under it and come back when it goes */
            const GgCard *c = (v->state == FLOW_PLAYING) ? v->card : 0;
            card_palette(c != 0);
            if (c != g_card_up) {
                g_card_up = c;
                g_card_k = CARD_NONE;
                if (c) {
                    gfx_commit_all(); /* the picker clear reaches the screen before the card draws over it */
                    gfx_drain();
                    card_draw(c);
                } else { card_clear(); g_blow_key = 0xFFFFFFFFu; meter_reset(); g_fling_flag = -1; g_mode_key = 0xFF; g_hud[0].kind = g_hud[1].kind = HUD_KIND_NONE; }
            }
            if (c) card_animate(c, card_frame(v->card_t));
        }
        {
            /* ROUND nn then GO! (arena game only: the demo and Gum Trip report RS_NONE); fix font, no panel; cleared when the phase ends */
            u8 rs = (v->state == FLOW_PLAYING && v->game) ? (u8)game_round_start_phase(v->game) : (u8)RS_NONE;
            int rn = rs == RS_ROUND ? game_round_number(v->game) : 0;
            if (rs != g_rs_drawn || rn != g_rs_num) {
                const char *l0 = rs == RS_ROUND ? game_round_start_text(v->game, 0) : 0;
                if (rs == RS_ROUND && l0) {
                    const char *l1 = game_round_start_text(v->game, 1);
                    gfx_center_blank(11, 3, sizeof BANNER_BLANK - 1, PAL_TEXT);
                    if (v->game->party_rule != PARTY_NONE) { /* party: ROUND nn above the rule or twist name and its goal line */
                        char rb[10] = "ROUND ";
                        rb[6] = (char)('0' + (rn / 10) % 10); rb[7] = (char)('0' + rn % 10); rb[8] = 0;
                        if (rb[6] == '0') { rb[6] = rb[7]; rb[7] = 0; }
                        gfx_center_text(11, PAL_TEXT, rb);
                    }
                    gfx_center_text(12, PAL_TEXT, l0);
                    gfx_center_text(13, PAL_TEXT, l1);
                } else if (rs == RS_ROUND) {
                    char rb[10] = "ROUND ";
                    if (v->game->mode == GAME_MODE_ARCADE) { rb[0] = 'S'; rb[1] = 'T'; rb[2] = 'A'; rb[3] = 'G'; rb[4] = 'E'; }
                    rb[6] = (char)('0' + (rn / 10) % 10); rb[7] = (char)('0' + rn % 10); rb[8] = 0;
                    if (rb[6] == '0') { rb[6] = rb[7]; rb[7] = 0; }
                    gfx_center_text(13, PAL_TEXT, "           ");
                    gfx_center_text(13, PAL_TEXT, rb);
                } else if (rs == RS_GO) {
                    gfx_center_blank(11, 3, sizeof BANNER_BLANK - 1, PAL_TEXT);
                    gfx_center_text(13, PAL_TEXT, "GO!");
                } else {
                    gfx_center_blank(11, 3, sizeof BANNER_BLANK - 1, PAL_TEXT);
                }
                g_rs_drawn = rs; g_rs_num = rn;
            }
        }
        {
            /* Arcade HUD: STAGE n top centre, BONUS in a bonus stage; written when the value changes, not per frame */
            const Game *g = v->game;
            u8 key = 0;
            if ((v->state == FLOW_PLAYING || v->state == FLOW_GAME_OVER) && g && g->mode == GAME_MODE_ARCADE)
                key = g->arc.state == ARC_BONUS ? 254 : (u8)g->arc.stage;
            if (key != g_stage_key) {
                char sb[9] = "BONUS   ";
                if (key && key != 254) {
                    sb[0] = 'S'; sb[1] = 'T'; sb[2] = 'A'; sb[3] = 'G'; sb[4] = 'E'; sb[5] = ' ';
                    sb[6] = (char)('0' + (key / 10) % 10); sb[7] = (char)('0' + key % 10);
                    if (sb[6] == '0') { sb[6] = sb[7]; sb[7] = ' '; }
                } else if (!key) {
                    for (u8 i = 0; i < 8; i++) sb[i] = ' ';
                }
                if (key || g_stage_key != 0xFF) gfx_center_text(HUD_STAGE_ROW, PAL_TEXT, sb);
                g_stage_key = key;
            }
        }
        {
            /* GAME OVER: big text mid screen while the flow holds the state (GAMEOVER_FRAMES, A or Start skips) */
            u8 on = v->state == FLOW_GAME_OVER;
            if (on != g_over_up) {
                if (on) gfx_text_backed(15, 14, PAL_HIGH, "GAME OVER"); /* the tall font has digits only, so plain backed letters; the state change that ends it clears the fix layer */
                g_over_up = on;
            }
        }
        {
            /* Arcade continue plate (game_step_arena freezes the world when no one plays): on the side of the player whose lives ended
             * (P1 left, P2 right, under the HUD); the words, then the seconds left. Redrawn once a second, per side. */
            for (u8 h = 0; h < HUMANS; h++) {
                const ArcLives *l = v->game ? &v->game->lives[h] : 0;
                u8 key = (v->state == FLOW_PLAYING && l && game_lives_mode(v->game) && l->state == ARC_LIFE_CONTINUE)
                             ? (u8)(1 + arc_continue_seconds(l) + (v->game->credits ? 0x80 : 0)) : 0;
                u8 x0 = h ? 24 : 3, row;
                if (key == g_cont_key[h]) continue;
                if (key) {
                    u8 sec = (u8)((key & 0x7F) - 1);
                    char sb[13] = "TIME LEFT   ";
                    for (row = 9; row <= 12; row++) plate(x0, (u8)(x0 + 11), row);
                    text(x0, 9, PAL_HIGH, "CONTINUE");
                    text(x0, 10, PAL_TEXT, (key & 0x80) ? "PRESS START" : "INSERT COIN");
                    if (sec > 10) { sb[10] = '1'; sb[11] = '0'; } else sb[10] = (char)('0' + sec);
                    text(x0, 11, PAL_TEXT, sb);
                } else if (g_cont_key[h] != 0xFF) {
                    for (row = 9; row <= 12; row++) text((u8)(x0 - 1), row, PAL_TEXT, "              ");
                }
                g_cont_key[h] = key;
            }
        }
        {
            /* Round clear banner over the match end hold: playing only (the demo shows none); blanked when the hold ends */
            int on = v->state == FLOW_PLAYING && v->game && v->game->round_end == RE_HOLD;
            if (on || g_banner_up) {
                BannerCtx bc;
                u8 col, row;
                u16 blank;
                u8 rows, rows_left = BANNER_ROWS_PER_FRAME;
                int f;
                int fr = MATCH_END_FRAMES - (int)v->game->round_timer;
                bc.winner = (uint8_t)game_banner_winner(v->game); bc.round = (uint16_t)game_round_number(v->game); bc.last = (uint8_t)game_banner_flags(v->game);
                blank = banner_cell(0, &bc, BANNER_W, 0); /* outside the panel: what an undrawn cell is */
                if (fr < 0) fr = 0;
                if (fr > 119) fr = 119;
                if (!g_banner_up || fr < g_banner_last) {
                    rows = 0xFF; /* going up (or time went back): every row */
                } else {
                    rows = 0; /* frames can be skipped: all rows that can change since the last draw */
                    for (f = g_banner_last + 1; f <= fr; f++) rows |= banner_dirty_rows((uint16_t)f);
                }
                if (!g_banner_up) {
                    for (row = 0; row < BANNER_W * BANNER_H; row++) g_banner_shadow[row] = blank;
                }
                g_banner_last = fr;
                if (!g_banner_up) g_banner_pending = 0;
                g_banner_pending |= rows;
                rows = 0;
                if (!on) {
                    g_banner_pending = 0; /* the panel goes in one pass: a per-cell loop over all rows cost about 200 raster lines */
                    g_banner_cells += gfx_fix_clear_shadowed(BANNER_COL, BANNER_ROW, BANNER_W, BANNER_H, g_banner_shadow, blank);
                    /* the bonus stage starts on the frame the banner goes: this blank ran after the round-start text and wiped it */
                    if (g_rs_drawn != RS_NONE) g_rs_drawn = 0xFF;                } else {
                    for (row = 0; row < BANNER_H && rows_left; row++) {
                        if (g_banner_pending & (1 << row)) { rows |= (u8)(1 << row); g_banner_pending &= (u8)~(1 << row); rows_left--; }
                    }
                }
                for (row = 0; row < BANNER_H; row++) {
                    if (!(rows & (1 << row))) continue;
                    for (col = 0; col < BANNER_W; col++) {
                        u16 c = on ? banner_cell((uint16_t)fr, &bc, (uint8_t)(BANNER_COL + col), (uint8_t)(BANNER_ROW + row)) : blank; /* banner_cell takes screen cells */
                        u16 *sh = &g_banner_shadow[row * BANNER_W + col];
                        if (c == *sh) continue;
                        *sh = c;
                        gfx_fix_tile((u8)(BANNER_COL + col), (u8)(BANNER_ROW + row), (u8)(c >> 12), (u16)(c & 0xFFF));
                        g_banner_cells++;
                    }
                }
                g_banner_calls++;
                g_banner_up = on;
            }
        }
        break;
    case FLOW_NAME_ENTRY:
        text(2, 5, PAL_TEXT, "SCORE");
        draw_number(8, 5, PAL_TEXT, v->score, 8);
        if (v->players == 2) text(18, 5, PAL_TEXT, v->entry_h ? "PLAYER 2" : "PLAYER 1");
        if (v->entry) {
            char name[NAME_LEN + 1];
            for (int i = 0; i < NAME_LEN; i++) {
                char c = (i < v->entry->pos) ? v->entry->name[i]
                                              : nameentry_symbol_char(v->entry->sym[i]);
                name[i] = c ? c : '_';
            }
            name[NAME_LEN] = 0;
            text(16, 13, PAL_HIGH, name);
            buf[0] = '^'; buf[1] = 0;
            text((u8)(16 + v->entry->pos), 14, PAL_TEXT, buf);
            /* idle countdown: the entry saves itself at 0 (NAME_TIMEOUT_FRAMES) */
            text(28, 5, PAL_TEXT, "TIME");
            g_name_seconds_shown = nameentry_seconds_left(v->entry);
            draw_number(33, 5, PAL_TEXT, g_name_seconds_shown, 2);
        }
        break;
    case FLOW_SAVE_REMINDER:
        text(2, 5, PAL_TEXT, "SCORE");
        draw_number(8, 5, PAL_TEXT, v->score, 8);
        gfx_center_text(13, PAL_TEXT, "OPEN THE MENU TO SAVE");
        break;
    }
    if (v->state != FLOW_ATTRACT_TABLE && v->highlight >= 0) {
        g_hl_up = 1;
        draw_table(v->table, v->table_mode, v->highlight, 16);
    }
}

/*
 * BIOS USER commands: one boot init, then resume.
 *
 * The BIOS jumps to the cartridge USER vector for every command in BIOS_USER_REQUEST
 * (0 init backup RAM, 1 eye-catcher, 2 game/demo, 3 title). It does so again after boot,
 * e.g. command 3 when a coin is inserted during attract. ngdevkit's crt0 dispatches the
 * command through rom_mvs_startup_init / rom_eye_catcher / rom_game / rom_title, and its
 * defaults for 2 and 3 (rom_game_default, rom_title_default) re-run the C runtime init
 * (clear .bss, copy .data) and call main() each time. That wipes every RAM variable
 * (g_flow, g_frame_counter) mid session.
 *
 * Gumbirds overrides rom_game and rom_title (link-time hooks in ngdevkit.ld): the first
 * entry after power-on goes through the ngdevkit default (C runtime init, then main), every
 * later entry re-enables interrupts and resumes game_loop() with RAM intact. The flow
 * state machine owns attract/title/play, so commands 2 and 3 need no separate screens.
 * Command 0 keeps the ngdevkit default: flow_init already loads defaults when the
 * backup RAM image is missing or invalid. Command 1 never comes (header mode,
 * rom_eye_catcher_mode 2: the cart's own header code, not the BIOS, draws the eye-catcher).
 *
 * g_boot_magic lives in .bss, so the C runtime init clears it and main() sets it after
 * init. A reset must not leave it set (relies on the BIOS work RAM test/clear at boot;
 * unverified on hardware, see thoughts/shared/research/2026-11-09_p0-toolchain.md).
 */
#define BOOT_MAGIC 0x424F4F54u /* 'BOOT' */
static volatile u32 g_boot_magic;

/* ngdevkit crt0 defaults: C runtime init, _init, then main / main_mvs_title. */
extern void rom_game_default(void);
extern void rom_title_default(void);
void rom_game(void);
void rom_title(void);

static void game_loop(void);
static u8 g_coin_blipped;

/*
 * Video state the game owns: fix layer, palettes, hero sprite. A real BIOS (SNK MVS BIOS,
 * UniBIOS) clears palette RAM before it re-enters the cartridge, e.g. USER command 3 on a
 * coin during attract; nullbios does not. So this runs on the first boot and on every
 * resume, or the screen stays black after a coin while the game runs on.
 * Guarded by tests/mame/unibios_check.lua (make test-unibios).
 */
/* Whole-screen palette fade (sprites, fix, backdrop): the same bg_fade_color scaling the mood fade uses, applied to the used palettes of palette RAM.
 * It runs in the main thread outside the vblank queue (palette RAM takes CPU writes any time), so it costs no VBlank budget. The full-colour
 * copy is taken from palette RAM itself; a fade in must start with the queue drained so RAM holds the final colours.
 * Each step is computed into s_pal_next during the frame and block-copied right after gfx_wait_vblank returns: a pass computed in place
 * outlasted vblank and the beam showed half-updated palettes (colour tearing). The bank select moves CPU access and display together, so a
 * hidden-bank double buffer is not possible; the copy loop is the shortest write that exists. Only palettes (16 word blocks) that hold a
 * non-zero word are faded and copied: the used ones are slots 0..75 plus slot 255, so a "highest non-zero index" range would cover all 4096. */
#define SCREEN_FADE_WORDS 4096u
#define SCREEN_FADE_BLOCKS 128u /* most palettes one fade handles (76 used; later ones are left untouched), s_pal_next is 4 KB */
static u16 s_pal_full[SCREEN_FADE_BLOCKS * 16]; /* the saved words of the faded palettes only, in s_pal_blk order (RAM: a whole-bank copy cost 4 KB of stack room) */
static u16 s_pal_next[SCREEN_FADE_BLOCKS * 16];
static u8 s_pal_blk[SCREEN_FADE_BLOCKS];
static u16 s_pal_nb;
/* Save the non-zero palettes of the bank (at most SCREEN_FADE_BLOCKS, later ones are left untouched) for a fade. */
static void screen_fade_save(void) {
    const volatile u16 *bank = (const volatile u16 *)MMAP_PALBANK1;
    s_pal_nb = 0;
    for (u16 b = 0; b < SCREEN_FADE_WORDS / 16 && s_pal_nb < SCREEN_FADE_BLOCKS; b++) {
        u16 *out = &s_pal_full[s_pal_nb * 16];
        u16 any = 0;
        for (u8 j = 0; j < 16; j++) any |= out[j] = bank[b * 16 + j];
        if (any) s_pal_blk[s_pal_nb++] = (u8)b;
    }
}
static u8 s_pal_slot[SCREEN_FADE_WORDS / 16]; /* palette block -> index in s_pal_full, 0xFF: not shadowed (video_init only) */
/* gfx_pal hook while video_init builds the palettes: a written block gets a compact slot (seeded from palette RAM so unwritten words keep their
 * BIOS value), later blocks past SCREEN_FADE_BLOCKS are left untouched like in screen_fade_save. */
static void pal_shadow_set(u16 idx, u16 val) {
    const u16 b = idx >> 4;
    u8 k = s_pal_slot[b];
    if (k == 0xFF) {
        if (s_pal_nb >= SCREEN_FADE_BLOCKS) return;
        k = (u8)s_pal_nb++;
        s_pal_slot[b] = k;
        s_pal_blk[k] = (u8)b;
        for (u8 j = 0; j < 16; j++) s_pal_full[k * 16 + j] = ((volatile u16 *)MMAP_PALBANK1)[b * 16 + j];
    }
    s_pal_full[k * 16 + (idx & 15)] = val;
}
/* A pass scales the 4 bit channels through a 16 entry table built per step (no hardware 32 bit multiply: bg_fade_color per word, three software
 * multiplies, took ~15 frames a pass). The dark-bit LSBs are dropped while fading. The last step (level BG_FADE_MAX) writes the saved words
 * back, exact, and level 0 is black. Unused slots stay 0. */
_Static_assert(BG_FADE_MAX % 4 == 0, "screen_fade steps 4 levels");
static void screen_fade(u8 from, u8 to) {
    gfx_drain();
    if (to < from) screen_fade_save();
    const u16 nb = s_pal_nb;
    for (;;) {
        u16 lr[16], lg[16], lb[16]; /* channel value scaled by the level, already shifted into place */
        for (u8 v = 0; v < 16; v++) { u16 x = (u16)(v * from >> 4); lr[v] = (u16)(x << 8); lg[v] = (u16)(x << 4); lb[v] = x; }
        if (!from) { u32 *z = (u32 *)s_pal_next; for (u16 i = 0; i < nb * 8u; i++) z[i] = 0; } /* level 0 is black: no per-word pass, one frame sooner */
        else for (u16 k = 0; k < nb; k++) {
            const u16 *in = &s_pal_full[k * 16];
            u16 *out = &s_pal_next[k * 16];
            if (from >= BG_FADE_MAX) { for (u8 j = 0; j < 16; j++) out[j] = in[j]; continue; }
            for (u8 j = 0; j < 16; j++) {
                u16 c = in[j];
                out[j] = c ? (u16)((c & 0x8000) | lr[(c >> 8) & 15] | lg[(c >> 4) & 15] | lb[c & 15]) : 0;
            }
        }
        gfx_wait_vblank();
        {
            const u16 *src = s_pal_next;
            for (u16 k = 0; k < nb; k++) {
                u32 dst = (u32)MMAP_PALBANK1 + (u32)s_pal_blk[k] * 32;
                __asm__ volatile ("movem.l (%0)+,%%d0-%%d7\n\tmovem.l %%d0-%%d7,(%1)"
                                  : "+a"(src) : "a"(dst) : "d0", "d1", "d2", "d3", "d4", "d5", "d6", "d7", "memory");
            }
        }
        if (from == to) return;
        /* A pass costs ~2 frames, all of them with the frame counter frozen (unibios_check STALL_LIMIT): a fade takes 4 levels a pass
         * (BG_FADE_MAX is a multiple of 4). */
        from = from < to ? (u8)(from + 4) : (u8)(from - 4);
    }
}

static void video_init(void) {
    gfx_init();
    /* Palettes are built in the fade source and only reach palette RAM through the fade-up: queued, they cost ~24 vblanks of
     * the coin entry (20 us a word) and the screen is black until the fade anyway. */
    for (u16 b = 0; b < SCREEN_FADE_WORDS / 16; b++) s_pal_slot[b] = 0xFF;
    s_pal_nb = 0;
    g_pal_shadow = pal_shadow_set;
    bg_backdrop_dark(1);
    /* Commit the fix clear FIRST, while palette 0 is still the BIOS zero: the budgeted queue flushes in order, so a clear
     * committed last left the BIOS tile 0x20 fill visible about 30 frames after a coin (tests/mame/unibios_check.lua, COIN1). */
    gfx_cls_init();
    /* Fix layer palettes 0..FIX_PAL_COUNT-1 (generated with the font). */
    for (u8 s = 0; s < FIX_PAL_COUNT; s++)
        for (u8 i = 0; i < 16; i++) gfx_pal((u16)(s * 16 + i), fixfont_palettes[s][i]);
    soot_load_palettes();
    for (u8 p = 0; p < CHUTE_PALETTE_COUNT; p++)
        for (u8 i = 0; i < 16; i++) gfx_pal((u16)((CHUTE_PAL_SLOT + p) * 16 + i), chute_palettes[p][i]);
    for (u8 i = 0; i < 16; i++) gfx_pal((u16)(CHUTE_P2_PAL_SLOT * 16 + i), chute_extra_palettes[0][i]);
    for (u8 i = 0; i < 16; i++) gfx_pal((u16)(GUMBUBBLE_PAL_SLOT * 16 + i), gumbubble_palettes[0][i]);
    for (u8 i = 0; i < 16; i++) gfx_pal((u16)(RULECARD_PAL_SLOT * 16 + i), rulecard_palettes[0][i]);
    for (u8 p = 0; p < PODIUM_PALETTE_COUNT; p++)
        for (u8 i = 0; i < 16; i++) gfx_pal((u16)((PODIUM_PAL_SLOT + p) * 16 + i), podium_palettes[p][i]);
    for (u8 i = 0; i < 16; i++) { gfx_pal((u16)(COUNTDOWN_PAL_SLOT * 16 + i), countdown_palettes[0][i]); gfx_pal((u16)(COUNTDOWN_HOT_PAL_SLOT * 16 + i), countdown_extra_palettes[COUNTDOWN_EXTRA_PAL_HOT][i]); }
    obs_load_palettes();
    island_load_palettes();
    trip_strip_load_palettes();
    trip_pickup_load_palettes();
    for (u8 p = 0; p < POPDROP_PALETTE_COUNT; p++)
        for (u8 i = 0; i < 16; i++) gfx_pal((u16)((POPDROP_PAL_SLOT + p) * 16 + i), popdrop_palettes[p][i]);
    for (u8 p = 0; p < POOP_PALETTE_COUNT; p++)
        for (u8 i = 0; i < 16; i++) gfx_pal((u16)((POOP_PAL_SLOT + p) * 16 + i), poop_palettes[p][i]);
    for (u8 p = 0; p < POOP_EXTRA_PALETTE_COUNT; p++)
        for (u8 i = 0; i < 16; i++) gfx_pal((u16)((POOP_PAL_SLOT + POOP_PALETTE_COUNT + p) * 16 + i), poop_extra_palettes[p][i]);
    for (u8 p = 0; p < POPDROPSKY_PALETTE_COUNT; p++)
        for (u8 i = 0; i < 16; i++) gfx_pal((u16)((POPDROPSKY_PAL_SLOT + p) * 16 + i), popdropsky_palettes[p][i]);
    gum_load_palettes();
    splash_load_palettes();
    resfx_load_palettes();
    logo_load_palettes();
    logo_reset();
    title_soot_reset();
    for (u8 i = 0; i < TRIPHAZ_PALETTE_COUNT; i++)
        for (u8 c = 0; c < 16; c++) gfx_pal((u16)((TRIPHAZ_PAL_SLOT + i) * 16 + c), triphaz_palettes[i][c]);
    for (u8 i = 0; i < ARCADE_PALETTE_COUNT; i++)
        for (u8 c = 0; c < 16; c++) gfx_pal((u16)((ARCADE_PAL_SLOT + i) * 16 + c), arcade_palettes[i][c]);
    for (u8 c = 0; c < 16; c++) gfx_pal((u16)(ATTRACT_PAL_SLOT * 16 + c), attract_icon_palette[c]);
    rain_init(&g_rain, RAIN_PAL_SLOT);
    rain_pal_put(0);
    for (u8 c = 0; c < 16; c++) gfx_pal((u16)(PROMPT_PAL_SLOT * 16 + c), inputprompt_palette[c]);
    bg_load_palettes();
    gfx_word(ADDR_SCB3 + SPRITE_RESERVED, 0); /* sprite 0 is never visible (src/sprite_slots.h): nothing else writes this slot */
    bg_init();
    bg_set_mood(g_flow.game.mood, 1); /* the screen is black here anyway: swap to the wanted mood at once, not a visible fade out and in after the BIOS return */
    /* GAMEOVER-BLUE-2: finish the plane swap here, while the screen is still black. Left to bg_update it took ~14 frames after the fade-up, and the
     * lit backdrop showed alone (flat blue, fix text on top) until the strips landed. */
    for (u8 guard = 0; g_bg_mood_busy && guard < 200; guard++) { bg_update(0); gfx_commit_all(); gfx_drain(); }
    hazard_init();
    trip_strip_init();
    hero_hide();
    dead_release_all();
    pool_hide_all(); /* the hardware state is unknown; live objects redraw next frame */
    arcade_elems_forget();
    g_draw_state = -1;
    gfx_commit_all();
    gfx_drain(); /* init is outside the per-frame budget: it blocks, one flush per vblank, until everything is written */
    g_pal_shadow = 0; /* the compact fade source already holds every palette: screen_fade(0, ..) needs no save */
    screen_fade(0, BG_FADE_MAX); /* the BIOS return leaves the palette black: fade up, no cut */
    bg_backdrop_dark(0); /* only now: nothing is drawn during the fade-up, so a lit backdrop alone would show as a blue screen; it comes with the first frame */
}

static void resume_game_loop(void) {
    /* Same hardware prologue as the crt0 defaults, minus the C runtime init. */
    __asm__ volatile ("move.w #0x2700,%%sr" ::: "memory");
    /* IRQACK is an LSPC register and every LSPC write lands inside vblank. The BIOS enters here (USER, e.g. command 3
     * on a coin during attract) at a time it picks, often right at the end of its 40 line vblank handler, so the ack
     * used to race vblank end (tests/mame/vblank_check.lua: second coin, write 0.3 lines after vblank end). Interrupts
     * are masked, so poll the raster line; the wait is under one frame, once per resume. */
    while (!VQ_RASTER_IN_VBLANK(*REG_LSPCMODE)) *REG_WATCHDOGW = 0;
    *(volatile u16 *)REG_IRQACK = 7;
    *REG_WATCHDOGW = 0;
    __asm__ volatile ("move.w #0x2000,%%sr" ::: "memory");
    *REG_CRTFIX = 1;
    /* video_init blocks for many vblanks (budgeted flush), and game_loop only sends sounds after it: play the coin blip now so it
     * is not 40+ frames late. g_coin_blipped tells game_loop the pending coin already has its blip (tests/mame/sound_check.lua). */
    if (g_coin_calls) { sound_play_sfx(SND_SFX_COIN); sound_tick(); g_coin_blipped = 1; }
    video_init();
    game_loop();
}

void rom_game(void) {
    if (g_boot_magic == BOOT_MAGIC) { resume_game_loop(); return; }
    rom_game_default();
}

void rom_title(void) {
    if (g_boot_magic == BOOT_MAGIC) { resume_game_loop(); return; }
    rom_title_default();
}

int main(void) {
    pool_reset();
    video_init();
    sound_init();
    flow_init(&g_flow, g_hiscore_image, SCORE_IMAGE_SIZE);
    g_boot_magic = BOOT_MAGIC;
    game_loop();
    return 0;
}

/*
 * Backup RAM protocol. The BIOS, not the game, copies the work RAM block named in the cart
 * header (0x10E pointer, 0x112 length; ngdevkit: .bss.bram) into battery backed RAM at
 * 0xD00000, and it does so only when USER returns to it through SYSTEM_RETURN (nullbios
 * biosstart.S soft_reset: jsr USER, then save_game_data_to_bram; the SNK MVS BIOS and
 * UniBIOS save at the same point, which is why real games end each demo cycle with
 * SYSTEM_RETURN). MAME's saveram and the MiSTer Neo Geo core's save file are that RAM.
 * game_loop never returned, so a new hiscore table never left work RAM and was lost at
 * power off. Now, after each image write, the loop returns as soon as the game is in
 * attract (BIOS_USER_MODE 1): main/resume_game_loop return, ngdevkit's wrapper_user jumps
 * to SYSTEM_RETURN, the BIOS saves and calls USER again, and rom_game/rom_title resume
 * the loop with RAM intact (same path as a coin re-entry). Guarded by make test-reach.
 *
 * Every game end also returns (g_game_ended), as MVS games end a play with SYSTEM_RETURN, on the first attract frame
 * right after flow_step, while BIOS_USER_MODE is still 2. Bug fixed here: without it the BIOS compulsion timer (0x10FDDA) was never reloaded and read 0, so with
 * a credit left UniBIOS forced PLAYER_START on the first attract frame after game over: a new game with no Start press
 * (arcade continue countdown run out, two coins). Guarded by make test-arcade-contout.
 */
static u8 g_bram_unsaved, g_game_ended;

/* Every return from game_loop reaches the BIOS through SYSTEM_RETURN, and the BIOS writes IRQACK (an LSPC register) about 19
 * lines later, before it calls USER again. A return from a park that woke late in vblank put that ack 5.6 lines past vblank end
 * (tests/mame/vblank_check.lua, game end at frame 1769). Return only in the first 16 vblank lines (0x1F0..0x1FF, 24+ lines
 * left), interrupts masked so the wait cannot be preempted; the screen is already faded to black, so at most one black frame. */
static void bios_return_sync(void) {
    __asm__ volatile ("move.w #0x2700,%%sr" ::: "memory");
    while (VQ_RASTER_LINE(*REG_LSPCMODE) < 0x1F0u) *REG_WATCHDOGW = 0;
}

static void game_loop(void) {
    FlowView view;
    for (;;) {
        /* A credit is taken by the BIOS (player_start) on a Start press, or here for A: both reach flow_step as start,
         * and flow_step turns a taken credit into a game at once. A coin jumps to the title first. */
        static u8 s_a_prev;
        u8 in = read_input();
        u8 a_edge = (u8)((in & IN_A) && !s_a_prev);
        s_a_prev = (u8)((in & IN_A) != 0);
        u8 start = g_start_pending;
        g_start_pending = 0;
        __asm__ volatile ("move.w #0x2700,%%sr" ::: "memory"); /* coin_sound counts in the vblank handler: keep read and decrement whole */
        u8 coined = coin_drain((uint8_t *)&g_coin_calls);
        __asm__ volatile ("move.w #0x2000,%%sr" ::: "memory");
        if (coined && !start) flow_coin(&g_flow);
        if (a_edge && !start && g_flow.state <= FLOW_ATTRACT_DEMO && bios_user_mode == 1 && (in & FLOW_RESET_COMBO) != FLOW_RESET_COMBO && !flow_a_opens_submenu(&g_flow) && take_credit()) start = 1;
        g_flow.game.input2 = pad_to_core(bios_p2current);
        while (g_flow.game.credits_spent) { take_credit(); g_flow.game.credits_spent--; } /* a continue costs a credit (BIOS refuses Start in play) */
        g_flow.game.credits = credits_now();
        if (g_join_p2) { g_join_p2 = 0; flow_join_p2(&g_flow, g_frame_counter); }
        g_flow.game.start_in[1] = (u8)((g_flow.state == FLOW_PLAYING || g_flow.state == FLOW_NAME_ENTRY) && (bios_statchange & 2)); /* P2 continue, P2 name letter */
        g_flow.game.start_in[0] = (u8)(g_flow.state == FLOW_PLAYING && (bios_statchange & 1)); /* arcade continue: Start continues, A only counts down */
        /* Start also ends the result screen and the GAME OVER text, and confirms a name entry letter like A (player_start refuses Start there) */
        if ((bios_statchange & 1) && ((g_flow.state == FLOW_PLAYING && g_flow.game.res.active) || g_flow.state == FLOW_GAME_OVER || g_flow.state == FLOW_NAME_ENTRY)) in |= IN_A;
        g_flow.credit_hold = (u8)(credits_now() > 0); /* owner rule "never force start": credits hold the PRESS START title */
        /* The title fades its next mood while it runs (about 100 frames after a Gum Trip run): only a Start, which would enter the world, waits. */
        g_bg_paused = g_bg_hold && bg_pending() && (g_flow.state != FLOW_ATTRACT_TITLE || start);
        /* The game waits while the entry background loads. A taken credit waits with it: bug fixed here, a Start accepted on
         * the title during the mood rewrite after a Gum Trip run was dropped here (credit gone, no game). make test-black-screen. */
        if (!g_bg_paused) flow_step(&g_flow, in, start, g_frame_counter);
        else if (start) g_start_pending = 1;
        /* Never force start: keep the BIOS compulsion timer (BCD seconds) from running out in attract, so the BIOS never calls
         * PLAYER_START without a Start press and never takes a credit on its own. Bug fixed here: with a credit and no press,
         * UniBIOS forced a game after 30 s. Guarded by make test-unibios (d) and test-arcade-contout (A7). */
        if (g_flow.state <= FLOW_ATTRACT_DEMO) *BIOS_COMPULSION_S = 0x30;
        {
            /* hazard kind per round: a new game starts at round 0; a new round (not during the banner HOLD) swaps the strip */
            static int s_round = 0;
            static u8 s_was_playing = 0;
            u8 playing = (g_flow.state == FLOW_PLAYING || g_flow.state == FLOW_ATTRACT_DEMO) && (g_flow.game.mode == GAME_MODE_ARENA || g_flow.game.mode == GAME_MODE_ARCADE); /* a new arcade stage swaps the strip like a new round */
            int rnd = game_round_number(&g_flow.game);
            if (playing && !s_was_playing) { hazard_game_restart(world_hazard(&g_flow.game)); s_round = rnd; }
            else if (playing && rnd != s_round && g_flow.game.round_end != RE_HOLD) { hazard_round_restart(world_hazard(&g_flow.game)); s_round = rnd; }
            s_was_playing = playing;
        }
        { /* arena layout per round: game.c match_start selected it; the island sprites follow in the same frame (the ROUND banner freeze) */
            static int s_layout = 0, s_look = 0;
            if (stage_layout_index() != s_layout || stage_look() != s_look) { s_layout = stage_layout_index(); s_look = stage_look(); island_relayout(); }
        }
        game_set_hazard(&g_flow.game, hazard_kind_now()); /* after flow_step: a new play resets the game; same kind the strip starts with this frame */
        if (g_flow.dirty) {
            score_serialise(&g_flow.tables, g_hiscore_image, SCORE_IMAGE_SIZE);
            g_hiscore_saves++;
            g_flow.dirty = 0;
            g_bram_unsaved = 1;
        }
        if (g_flow.ended) { g_flow.ended = 0; g_game_ended = 1; }   /* GAME OVER, or a minigame's result screen left straight to the title */
        if (g_game_ended && g_flow.state <= FLOW_ATTRACT_DEMO) {
            g_game_ended = 0;
            screen_fade(BG_FADE_MAX, 0); /* fade down, not a hard cut to the BIOS black */
            bios_return_sync();
            return; /* still user mode 2: SYSTEM_RETURN before any vblank sees mode 1 with a stale compulsion timer (see above) */
        }
        flow_view(&g_flow, &view);
        g_round_end_s[0] = g_flow.game.round_end; g_round_end_s[1] = g_flow.game.round_timer;
        g_round_end_s[2] = g_flow.game.round_start; g_round_end_s[3] = game_flier_visible(&g_flow.game);
        if (coined && !g_coin_blipped) sound_play_sfx(SND_SFX_COIN);
        if (coined) g_coin_blipped = 0;
        if (view.game && view.state == FLOW_PLAYING && g_flow.game.cd_ev) { /* GET SET tick, higher beep on GO! (existing samples: continue_tick, round_go) */
            sound_play_sfx((g_flow.game.cd_ev & GGCD_EV_GO) ? SND_SFX_ROUND_GO : SND_SFX_CONTINUE_TICK);
            g_flow.game.cd_ev = 0;
        }
        if (view.game && view.state == FLOW_PLAYING && g_flow.game.gg_poop) { /* Poop the Man: Fling samples; bounce = bump, berry = pickup, shoe hit = foul */
            const GgPoop *pm = &g_flow.game.poop;
            if (pm->b[0].drop_t == 1 || pm->b[1].drop_t == 1) sound_play_sfx(SND_SFX_FLING_THROW);
            if (pm->last_hit_pts_ev) sound_play_sfx(SND_SFX_FLING_LAND);
            if (pm->sfx & PM_SFX_BOUNCE) sound_play_sfx(SND_SFX_BUMP);
            if (pm->sfx & PM_SFX_FLAP) sound_play_sfx(SND_SFX_FLAP_A);
            if (pm->sfx & PM_SFX_DEAD) sound_play_sfx(SND_SFX_FLING_FOUL);
            g_flow.game.poop.sfx = 0;
            if (pm->b[0].stun == PM_STUN || pm->b[1].stun == PM_STUN) sound_play_sfx(SND_SFX_FLING_FOUL);
        }
        if (view.game && view.state == FLOW_PLAYING && g_flow.game.gg_toss && g_flow.game.toss.sfx) { /* Toss Gum sounds (Fling samples) */
            u8 te = g_flow.game.toss.sfx;
            g_flow.game.toss.sfx = 0;
            if (te & GT_SFX_TOSS) sound_play_sfx(SND_SFX_FLING_THROW);
            if (te & GT_SFX_BURST) sound_play_sfx(SND_SFX_FLING_FOUL);
            if (te & GT_SFX_WIN) sound_play_sfx(SND_SFX_FLING_WIN);
        }
        if (view.game && view.state == FLOW_PLAYING && g_flow.game.gg_tug && g_flow.game.tug.sfx) { /* Tug Gum sounds (Fling samples) */
            u8 te = g_flow.game.tug.sfx;
            g_flow.game.tug.sfx = 0;
            if (te & GTG_SFX_PULL) sound_play_sfx(SND_SFX_FLING_RUNUP_1);
            if (te & GTG_SFX_LETGO) sound_play_sfx(SND_SFX_FLING_THROW);
            if (te & GTG_SFX_SNAP) sound_play_sfx(SND_SFX_FLING_WIN);   /* the snap ends a won round: the foul buzzer read as an error (owner 2026-11-21) */
            if (te & GTG_SFX_WIN) sound_play_sfx(SND_SFX_FLING_WIN);
        }
        if (view.game && view.state == FLOW_PLAYING && g_flow.game.gg_fling && g_flow.game.fling.sfx) { /* Gum Fling sounds */
            u8 fe = g_flow.game.fling.sfx;
            g_flow.game.fling.sfx = 0;
            if (fe & GF_SFX_TICK) sound_play_sfx((u8)(SND_SFX_FLING_RUNUP_1 + g_flow.game.fling.power * 4u / (GF_POWER_MAX + 1u))); /* run-up tick rises with power */
            if (fe & GF_SFX_THROW) sound_play_sfx(SND_SFX_FLING_THROW);
            if (fe & GF_SFX_LAND) sound_play_sfx(SND_SFX_FLING_LAND);
            if (fe & GF_SFX_FOUL) sound_play_sfx(SND_SFX_FLING_FOUL);
            if (fe & GF_SFX_WIN) sound_play_sfx(SND_SFX_FLING_WIN);
            if (fe & GF_SFX_LOSE) sound_play_sfx(SND_SFX_FLING_LOSE);
        }
        if (view.game && view.state == FLOW_PLAYING && g_flow.game.res.events) { /* result screen sounds */
            u8 re = g_flow.game.res.events;
            g_flow.game.res.events = 0;
            if (re & RES_EV_VANISH) sound_play_pop();
            if (re & RES_EV_TICK) sound_play_sfx(SND_SFX_TALLY_TICK);
            if (re & RES_EV_JINGLE) sound_play_sfx(SND_SFX_PERFECT);
            if (re & RES_EV_BONUS) sound_play_sfx(SND_SFX_TALLY_BONUS);
        }
        sound_frame(&view);
        sound_tick();
        /* First of the frame's sprite words: the title logo and Sootlings share slots 323.. with every mode's strips, and a hide queued after a
         * mode entry's tile and stadium ops reached the hardware 8 frames late (Gum Fling rules card, slot 324 under it; tests/mame/gum_fling_check.lua F4). */
        /* Only the hides go first: the show runs after the world steps below, as a step there writes 0 to slot 323 once on the title's
         * first frames and would land over a show queued before it (test-logo L1). */
        if (view.state != FLOW_ATTRACT_TITLE || bg_dark()) { logo_step(0); title_soot_step(0); }
        draw(&view);
        /* The result screen's fix scene covers the world: its steps wait, so the fill frames keep their budget. */
        if (view.state == FLOW_PLAYING && view.game && view.game->res.active) {
            /* Bonus result screen (it covers the world): hide the strip and load the next stage's strip tiles once the fill is done,
             * so the stage entry frame's hazard start only places it (two banks there cost about 113 lines, reports/stage-spike.md). */
            if (g_res_filled == RESV_W * RESV_H && view.game->mode == GAME_MODE_ARCADE) { /* only the arcade has a next stage: arc.stage is not a minigame's stage */
                hazard_step(0, g_cam_px);
                hazard_game_restart(world_get(world_of_stage(arc_next_stage(view.game->arc.stage)))->hazard);
                hazard_preload();
            }
            /* Podium over the stadium: the stands keep cheering behind the transparent text (once the fill is done, it has the frame budget). */
            if (g_res_filled == RESV_W * RESV_H && view.game->res.podium && stadium_on(view.game))
                stadium_hw_step(1, 1, view.game->mood, view.game->gg_fling, view.game->gg_fling && view.game->fling.phase >= GF_FLIGHT ? (int)(view.game->fling.x >> 16) : 0);
            goto world_done;
        }
        hero_and_mode(&view);
        {
            u8 world = world_shown(&view);
            u8 trip = world && view.game->mode == GAME_MODE_TRIP;
            u8 trip_game = (world || view.state == FLOW_GAME_OVER) && view.game && view.game->mode == GAME_MODE_TRIP;
            hazard_step((world || view.state == FLOW_GAME_OVER) && !trip_game && !ground_field(view.game) && !pop_field(view.game) && !poop_field(view.game), g_cam_px); /* the hazard strip is the arena's floor; Gum Trip has its own, Pop Drop shows only its platforms */
            if (g_bg_paused && world_state(&view) && view.game->mode != GAME_MODE_TRIP && !ground_field(view.game)) hazard_preload(); /* the reveal frame then only places it */
            /* arcade only: elements kill, so they must be seen (worst scanline with them is checked in tests/host/test_sprite_budget.c) */
            /* Bonus first: on the frame it ends it parks slot 323, which the stage elements share and draw right after. */
            arcade_bonus_step(world && ((view.game->mode == GAME_MODE_ARCADE && view.game->arc.state == ARC_BONUS) || (view.game->mode == GAME_MODE_GUM && view.game->gg_gather)) && !view.game->res.active ? view.game : 0);
            arcade_elems_step(world && view.game->mode == GAME_MODE_ARCADE && view.game->arc.state != ARC_BONUS ? view.game : 0); /* the bonus shows no stage elements: hidden once on entry */
            u8 stadium = world_state(&view) && stadium_on(view.game);
            island_step(world && !trip && !stadium && !ground_field(view.game) && !pop_field(view.game) && !poop_field(view.game), g_cam_px); /* arena islands are not drawn in Gum Trip, on the stadium events, on the Gum Fling / Toss Gum field or in Pop Drop */
            fling_field_step(ground_field(view.game) ? seated(view.game) ? &g_idle_fling : &view.game->fling : 0, view.game ? view.game->mood : 0, world_state(&view), world, !(view.game && seated(view.game)), view.game && view.game->gg_tug); /* after island_step: it takes the island slots */
            poop_walkway_step(poop_field(view.game) ? &view.game->poop : 0, view.game ? view.game->mood : 0, world_state(&view), world); /* after island_step: it takes the island slots */
            {   /* stadium stands: scores, result and wave edges from the event state */
                static u8 s_fin;
                const Game *sg = view.game;
                if (stadium) {
                    u8 p1 = 0, p2 = 0, res = 0;
                    int win = -1;
                    if (sg->gg_fling) {
                        p1 = cap99(sg->fling.seq.points[0]); p2 = cap99(sg->fling.seq.points[1]);
                        res = sg->fling.phase >= GF_RESULT;
                        win = gumfling_winner(&sg->fling); if (win > 1) win = -1;
                    } else if (sg->gg_race) {
                        p1 = cap99(sg->race.size[0] / 4u); p2 = cap99(sg->race.size[1] / 4u);
                        res = sg->race.phase >= GG_RACE_RESULT; win = sg->race.winner;
                    } else {
                        p1 = cap99(sg->blow.seq.best[0]); p2 = cap99(sg->blow.seq.best[1]);
                        if (sg->blow.size > (sg->blow.seq.turn ? p2 : p1)) { if (sg->blow.seq.turn) p2 = cap99(sg->blow.size); else p1 = cap99(sg->blow.size); }
                        res = sg->blow.phase >= GG_BLOW_RESULT; win = sg->blow.seq.players < 2 ? -1 : (p1 > p2 ? 0 : p2 > p1 ? 1 : -1);
                    }
                    stadium_hw_scores(p1, p2);
                    if (res && !s_fin) { stadium_hw_finish(win); if (sg->gg_race || sg->gg_fling || sg->blow.seq.players < 2) stadium_hw_wave(); }
                    s_fin = res;
                } else s_fin = 0;
                stadium_hw_step(stadium, world, sg ? sg->mood : 0, stadium && sg->gg_fling, stadium && sg->gg_fling && sg->fling.phase >= GF_FLIGHT ? (int)(sg->fling.x >> 16) : 0);
                bg_stadium_planes((u8)stadium);
            }
            /* the course (islands, kill strips, pickups) stays through Game Over like the planes and the hazard anim: all leave at the title */
            island_trip_step(trip_game ? &view.game->trip_gen : 0, trip_game ? view.game->trip.px : 0, trip_game && game_trip_ready(view.game));
            {   /* entry hold: the strip queues its columns hidden (ready 0) and the islands load their tiles hidden. Not on the entry
                 * frame (trip_hold 0, no build step yet): start_game and the title teardown already fill it. */
                u8 trip_held = g_bg_hold && world_state(&view) && view.game->mode == GAME_MODE_TRIP && view.game->trip_hold;
                g_trip_islands_loaded = trip_held && game_trip_ready(view.game) && island_trip_preload(&view.game->trip_gen);
                trip_strip_step((trip_game || trip_held) ? &view.game->trip_gen : 0, (trip_game || trip_held) ? view.game->trip.px : 0, trip_game && game_trip_ready(view.game));
            }
            trip_pickup_step(trip_game ? &view.game->trip_gen : 0, trip_game ? view.game->trip.px : 0, trip_game ? view.game->trip.steps : 0, trip_game && game_trip_ready(view.game));
            /* Arena: the bubble is full size until the last balloon bursts (level 0 starts the pop); Gum Trip: its gum meter. */
            u8 arena = world && (view.game->mode == GAME_MODE_ARENA || view.game->mode == GAME_MODE_ARCADE);
            u8 race = world && view.game->gg_race;
            u8 blow = world && is_big_blow(view.game);
            gum_step(0, arena || race || blow || (trip && game_trip_ready(view.game)), trip ? view.game->trip.gum : (race ? race_gum(view.game, 0) : blow ? blow_gum(view.game) : arena ? (uint16_t)(human_bubble_level(view.game, 0) * (GUM_MAX / GUM_VIEW_LEVELS)) : GUM_MAX), (trip || arena || race || blow) ? view.game->frame : 0, g_gum_pose[0].drawn, g_gum_pose[0].frame, g_gum_pose[0].flip, g_gum_pose[0].cx, g_gum_pose[0].top, world && human_leaks(view.game, 0));
            roost_marker_step(arena && view.state == FLOW_PLAYING ? view.game : 0);
            card_scene_step(view.state == FLOW_PLAYING && view.card, view.card_t);
            { u8 on = view.state == FLOW_PLAYING && view.game; countdown_step(on ? ggcd_word(view.game->cd_t) : GGCD_WORD_NONE, on ? view.game->cd_t : 0); }
            tug_strand_step(world && view.state == FLOW_PLAYING && !view.card ? view.game : 0);
            toss_bubble_step(view.state == FLOW_PLAYING ? view.game : 0);   /* Toss Gum is GAME_MODE_GUM, not arena: the function checks gg_toss itself */
            fling_arc_step(world && view.state == FLOW_PLAYING && !view.card ? view.game : 0);
            { u8 g1 = race || (arena && view.game->players == 2); /* inactive: gum_step ignores every other argument, so they are not computed */
                gum_step(1, g1, !g1 ? 0 : race ? race_gum(view.game, 1) : (uint16_t)(human_bubble_level(view.game, 1) * (GUM_MAX / GUM_VIEW_LEVELS)), view.game->frame, g_gum_pose[1].drawn, g_gum_pose[1].frame, g_gum_pose[1].flip, g_gum_pose[1].cx, g_gum_pose[1].top, g1 && world && human_leaks(view.game, 1)); }
            {   /* the splash starts from the same crossing that plays the splosh sound; it keeps running through Game Over */
                const SoundEvents *se = sound_events();
                const Game *sg = view.game;   /* Gum Trip: its own floor death starts the gum splat (the splosh edge needs a water or lava kind) */
                splash_update(splash_enabled((world || view.state == FLOW_GAME_OVER) && sg, trip_game),
                              trip_game ? sg->trip_splat : se->n_splosh > 0, trip_game ? SPLASH_KIND_GUM : sg ? sg->hazard_kind : 0,
                              trip_game ? sg->hero[0].x >> 16 : se->splosh_x, trip_game ? sg->trip_splat_y : 0,
                              trip_game ? game_flier_cam_px(sg) : g_cam_px); /* the trip flier lives in screen space (owner 2026-11-17: splat far from the death) */
            }
            logo_step(view.state == FLOW_ATTRACT_TITLE && !bg_dark()); /* the logo has no palette fade: it leaves while a mood change holds the planes black and returns with the fade-in */
            title_soot_step(view.state == FLOW_ATTRACT_TITLE);
            hazard_trip_anim(trip_game);
            /* Gum Trip drops the far and near background planes; arena and title show them. Dropped already in the entry hold (world
             * hidden): on the reveal frame it ran with the course start and wrapped past vblank. */
            bg_trip_planes(trip_game || (g_bg_hold && world_state(&view) && view.game->mode == GAME_MODE_TRIP && view.game->trip_hold));
        }
        /* game.c picks the mood per match and per attract loop; no-op when unchanged. In the entry hold (world hidden) the mood cuts in
         * at once and the game waits for it, so the first frame of play shows the whole background. Everywhere else (title, an arena
         * round, a demo rematch, an arcade world change) it fades: the planes dim to black, swap in the dark, brighten, and the game runs on. */
        bg_set_mood(g_flow.game.mood, (u8)(world_state(&view) && g_bg_hold));
        bg_pop_sky((u8)((world_state(&view) || view.state == FLOW_GAME_OVER) && pop_field(view.game)), view.game ? view.game->pop.dist : 0); /* Pop Drop: summer sky instead of the arena planes (1P, 2P, demo) */
        rain_frame(&view);
        bg_update(g_cam_unwrapped); /* the planes loop on the unwrapped camera (arena and Gum Trip alike) */
        g_bg_held = (u8)(world_state(&view) && g_bg_hold); /* test sentinel: this frame kept the world hidden */
        if (world_shown(&view) && bg_bare()) g_bg_late++; /* the world over the flat lit backdrop: a cut swap in play */
        if (!world_state(&view)) g_bg_hold = BG_HOLD_FRAMES;
        else if (g_bg_hold && !bg_pending() && !trip_building()) g_bg_hold = g_flow.game.mode == GAME_MODE_TRIP ? 0 : g_bg_hold - 1; /* a built course: its steps picked the mood */
    world_done:
        gfx_commit();
        g_frame_counter++;
        gfx_wait_vblank(); /* the vblank callback flushes the queue: the only VRAM and palette writes of the frame */
        if (g_bram_unsaved && (bios_user_mode == 1 || g_flow.state == FLOW_SAVE_REMINDER)) {
            g_bram_unsaved = 0;
            screen_fade(BG_FADE_MAX, 0);
            bios_return_sync();
            return; /* to the BIOS: SYSTEM_RETURN, backup RAM save, USER again (see above) */
        }
    }
}
