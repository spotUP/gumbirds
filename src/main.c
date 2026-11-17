/*
 * main.c - Neo Geo glue for Gumbirds: vblank loop, joypad, backup RAM, fix-layer drawing.
 * All game logic lives in src/core (host tested). Nothing here decides gameplay.
 */
#include <ngdevkit/neogeo.h>
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
#include "gen/gumbubble_tables.h"
#include "gen/gumleak_tables.h"
#include "gfx.h"
#include "sprite_slots.h"
#include "vram_layout.h"
#include "bg.h"
#include "hazard.h"
#include "island.h"
#include "trip_strip.h"
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
static const FlierClips k_clips = {
    k_clip_first, k_clip_count, k_clip_loop, k_frame_ticks,
    SOOTLING_CLIP_FLAP, SOOTLING_CLIP_FLY, SOOTLING_CLIP_SETTLE, SOOTLING_CLIP_IDLE, SOOTLING_CLIP_PUMP,
    SOOTLING_CLIP_INFLATE, SOOTLING_CLIP_FALL, SOOTLING_CLIP_POP2, SOOTLING_CLIP_POP1,
    SOOTLING_CLIP_WALK, SOOTLING_CLIP_LAND, SOOTLING_CLIP_BREATHE
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
static u8 g_howto_up; /* PARTY how-to overlay (fix rows HOWTO_ROW..) is on screen */
#define HOWTO_ROW 22
#define MODE_LABEL_ROW 29 /* last visible fix row, left safe column: the credits plate sits at columns 28..37 */
#define BLOW_BAR_CELLS 16
#define BLOW_BAR_COL 12
#define BLOW_BAR_ROW 26
#define BLOW_TEXT_ROW 5
#define BLOW_TEXT_W 30
#define MODE_LABEL_COL 2
#define MODE_LABEL_W 17   /* longest name: RULE OF THE ROUND */
static u32 g_blow_key = 0xFFFFFFFFu; /* Big Blow text on screen (phase, tickets, last attempt); reset with the fix layer */
static GgBar g_blow_bar = { BLOW_BAR_CELLS, 0 };
static u8 g_blow_bar_up;
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
    /* Protected blink: the animation above keeps stepping, only the sprites go dark (a protected flier is never FALLING). */
    if (!flier_view_visible(fl, g->frame)) { hero_hide(); g_soot_player_tile = (u16)(SOOT_TILE_BASE + tiles[0]); g_blink_hidden++; return; }   /* hero_hide clears the tile sentinel; the clip under test keeps it */
    g_blink_shown++;
    int left = sx;
    u16 attr = (u16)(((SOOT_PAL_SLOT + f->palette) << 8) | (flip ? SOOT_FLIP : 0));
    u16 slot = HERO_SPRITE;
    if (g->mode != GAME_MODE_TRIP && flier_body_front(fl)) {
        int d = dead_claim(DEAD_OWNER_HERO(0));
        if (d >= 0) { hero_hide(); slot = (u16)(DEAD_BODY_SPRITE + d * DEAD_BODY_COLUMNS); }
    } else dead_release(DEAD_OWNER_HERO(0));
    g_gum_pose[0].drawn = 1; g_gum_pose[0].frame = shown; g_gum_pose[0].flip = (u8)flip; g_gum_pose[0].cx = left + SOOT_COLUMNS * 8; g_gum_pose[0].top = top;
    soot_strips(slot, f, tiles, flip, attr);
    gfx_sprite_place(slot, SOOT_COLUMNS, f->tiles_h, left, top);
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
_Static_assert(GUM_P2_SPRITE + GUM_COUNT <= ROOST_SPRITE && ROOST_SPRITE + ROOST_COUNT <= ISLAND_SPRITE, "roost marker sprites overlap the gum bubbles or the islands");
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
static void gum_obj_sync(u8 *slot, int want, const Game *g, const PoolObj *body, int leaking, u8 level) {
    u8 k = *slot;
    if (!want) { if (k != POOL_NONE) { obj_pool_free(&g_pool, k); *slot = POOL_NONE; } return; }
    if (k == POOL_NONE) {
        k = obj_pool_alloc(&g_pool, 0, 0, 0, 0, 0);
        if (k == POOL_NONE) return;
        *slot = k;
    }
    PoolObj *p = &g_pool.obj[k];
    p->flags = (u8)(p->flags | POOL_F_HERO);
    p->flags = (u8)((p->flags & ~(POOL_F_FLIP | POOL_F_BLINK | POOL_F_SCREEN)) | (body->flags & (POOL_F_FLIP | POOL_F_BLINK | POOL_F_SCREEN)));
    p->type = (u8)(0xC0 | gum_view_frame(GUM_STATE_WOBBLE, (uint32_t)gum_view_wobble_clock(g->frame, leaking)));
    p->anim = body->type; p->anim_tick = level;   /* anim_tick: bubble level 1..16 (pool_show_gum / pool_show_leak) */
    p->x = body->x; p->y = body->y;
}

_Static_assert(GUM_WOBBLE_FRAMES == 2 * GUM_LEAK_TICK, "double-speed wobble steps once per leak frame");

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
        gum_obj_sync(gslot, 1, g, body, 1, level);
        k = *slot;
    }
    PoolObj *p = &g_pool.obj[k];
    p->flags = (u8)((p->flags | POOL_F_HERO) & ~(POOL_F_FLIP | POOL_F_BLINK | POOL_F_SCREEN));
    p->flags = (u8)(p->flags | (body->flags & (POOL_F_FLIP | POOL_F_BLINK | POOL_F_SCREEN)));
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
        if (!visible) dead_release(DEAD_OWNER_CPU(i));
        if (!visible || cpu_show_front(g, i)) {
            if (k != POOL_NONE) { obj_pool_free(&g_pool, k); g_cpu_obj[i] = POOL_NONE; }
            chute_obj_sync(g, i, 0, 0, c, feet);
            gum_obj_sync(&g_gum_obj[i], 0, g, 0, 0, 0);
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
        p->type = flier_anim_step(&g_cpu_anim[i], c, &k_clips, &flip); /* sheet frame; the player palette offset is added in pool_show_hero */
        if (arc_pump_in_window(&g->pump[i]) && c->state == FLIER_ALIVE) p->type = flier_pump_frame(&k_clips, arc_pump_progress(&g->pump[i])); /* sitting rival: pump frame */
        if (flip) p->flags |= POOL_F_FLIP; else p->flags &= (u8)~POOL_F_FLIP;
        p->x = c->x;
        p->y = feet;
        if (flier_view_visible(c, g->frame)) p->flags &= (u8)~POOL_F_BLINK; else p->flags |= POOL_F_BLINK;
        chute_obj_sync(g, i, c->state == FLIER_PARACHUTE, flip, c, feet);
        u8 lvl = pump_level(&g->pump[i], c->state == FLIER_ALIVE);
        gum_obj_sync(&g_gum_obj[i], 1, g, p, gum_view_leaks_balloons(c->balloons), lvl);
        leak_obj_sync(&g_leak_obj[i], &g_gum_obj[i], gum_view_leaks_balloons(c->balloons), g, p, lvl);
    }
}

/* Player 2: body and parachute in pool objects P2_OBJ_BODY / P2_OBJ_CHUTE, claimed once P2 has joined and kept until the
 * world is left (pool_free_all). A hidden P2 keeps the objects with POOL_F_BLINK set, so a computer flier never allocates
 * them. A bounced body draws from a dead body slot instead (owner DEAD_OWNER_HERO(1)). */
static void pool_sync_p2(const Game *g) {
    if (g->players < 2) return;
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
    b->x = fl->x; b->y = feet;
    if (flier_view_visible(fl, g->frame)) b->flags &= (u8)~POOL_F_BLINK; else b->flags |= POOL_F_BLINK;
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
            gum_obj_sync(&g_rival_gum_obj[i], 0, g, 0, 0, 0);
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
        gum_obj_sync(&g_rival_gum_obj[i], 1, g, p, gum_view_leaks_balloons(c->balloons), GUM_VIEW_LEVELS);   /* rivals do not pump */
        leak_obj_sync(&g_rival_leak_obj[i], &g_rival_gum_obj[i], gum_view_leaks_balloons(c->balloons), g, p, GUM_VIEW_LEVELS);
    }
}

/* Player bubble jet (look only): leaking = Gum Trip gum below half for player 1, one balloon left in the arena and arcade. */
static int human_leaks(const Game *g, int pl) {
    if (g->mode == GAME_MODE_TRIP) return pl == 0 && game_trip_ready(g) && gum_view_leaks_gum(g->trip.gum);
    return gum_view_leaks_balloons(g->hero[pl].balloons);
}
/* Arena / arcade bubble level of a human: full, or growing while that human pumps after a parachute landing. */
static u8 human_bubble_level(const Game *g, int pl) { return pump_level(&g->hpump[pl], g->hero[pl].state == FLIER_ALIVE); }
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
    if (p->flags & POOL_F_BLINK) { if (g_pool_drawn[i]) pool_hide_run(i); return; }
    int flip = (p->flags & POOL_F_FLIP) != 0;
    GumOffset o = gum_view_offset(p->anim, flip);
    if (!o.show) { if (g_pool_drawn[i]) pool_hide_run(i); return; }
    const SootlingFrame *bf = &sootling_frames[soot_frame(SOOTLING_ANIM_CPU, p->anim)];
    int lvl = p->anim_tick;
    const GumFrame *f = &gum_frames[gum_anims[gum_view_anim((uint8_t)lvl, GUM_STATE_WOBBLE)].first_frame + (p->type & 7)];
    int bx = camera_screen_x(obj_pool_px(p->x) - FLIER_HALF_W - SOOT_BOX_DX, (p->flags & POOL_F_SCREEN) ? 0 : g_cam_px, SOOT_COLUMNS * 16);
    int x = bx + SOOT_COLUMNS * 8 - f->tiles_w * 8 + o.dx;
    if (!camera_visible(x, f->tiles_w * 16)) { if (g_pool_drawn[i]) pool_hide_run(i); return; }
    u16 slot = obj_pool_sprite(&g_pool, i);
    u8 key = (u8)((p->type & 7) + 1 + lvl * 8);   /* level 1..16 and wobble frame 0..5 */
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
            if (b->flags & POOL_F_BLINK) goto hide;
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
        int wob = lf % GUM_WOBBLE_FRAMES;
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

static void pool_show_hero(PoolObj *p, u8 i, u16 *scb3) {
    if ((p->type & 0xE0) == 0xE0) { pool_show_leak(p, i, scb3); return; }
    if ((p->type & 0xC0) == 0xC0) { pool_show_gum(p, i, scb3); return; }
    if (p->type & 0x80) { pool_show_chute(p, i, scb3); return; }
    if (p->flags & POOL_F_BLINK) { g_blink_pool[0]++; if (g_pool_drawn[i]) pool_hide_run(i); return; } /* the animation kept stepping in the sync; the hide costs queue words once */
    g_blink_pool[1]++;
    int p2 = i == P2_OBJ_BODY;
    u8 fi = soot_frame(p2 ? SOOTLING_ANIM_PLAYER : SOOTLING_ANIM_CPU, p->type);
    const SootlingFrame *f = &sootling_frames[fi];
    int flip = (p->flags & POOL_F_FLIP) != 0;
    int x = camera_screen_x(obj_pool_px(p->x) - FLIER_HALF_W - SOOT_BOX_DX, (p->flags & POOL_F_SCREEN) ? 0 : g_cam_px, SOOT_COLUMNS * 16);
    u16 slot = obj_pool_sprite(&g_pool, i);
    if (!camera_visible(x, SOOT_COLUMNS * 16)) { pool_hide_run(i); return; }
    int top = obj_pool_px(p->y) - f->tiles_h * 16;
    if (p2) { g_gum_pose[1].drawn = 1; g_gum_pose[1].frame = p->type; g_gum_pose[1].flip = (u8)flip; g_gum_pose[1].cx = x + SOOT_COLUMNS * 8; g_gum_pose[1].top = top; }
    const u16 *tiles = &sootling_tile_index[f->tile_offset];
    u8 key = (u8)(p->type + 1 + (flip ? 128 : 0)); /* frame and mirror state the strips hold; the computer palette only, so the clip frame is unique */
    if (g_pool_drawn[i] != key) {
        soot_strips(slot, f, tiles, flip, (u16)(((p2 ? SOOT_P2_PAL_SLOT : SOOT_PAL_SLOT + f->palette) << 8) | (flip ? SOOT_FLIP : 0)));
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
static u8 g_arc_used = ARC_ELEM_COUNT; /* columns used last frame (top of the range); the ones below are already hidden */
_Static_assert(ARCADE_FRAME_COUNT < 255, "arc frame cache holds frame index + 1 in a byte");

static void arcade_elems_forget(void) {
    for (u8 c = 0; c < ARC_ELEM_COUNT; c++) g_arc_drawn[c] = 0;
    g_arc_used = ARC_ELEM_COUNT;
    g_arc_dirty = 1;
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
    for (int i = 0; i < n; i++) {
        const ArcSprite *b = &blocks[i];
        u8 fi = (u8)(arcade_anims[k_arc_anim[b->piece]].first_frame + k_arc_first[b->piece] + b->frame);
        const ArcadeFrame *f = &arcade_frames[fi];
        int w = f->tiles_w * 16, sx = camera_screen_x(b->x - f->pad_left, g_cam_px, w);
        if (used + f->tiles_w > ARC_ELEM_COUNT || !camera_visible(sx, w)) continue;
        int s = ARC_ELEM_COUNT - used - f->tiles_w;
        u16 slot = (u16)(ARC_ELEM_SPRITE + s);
        if (g_arc_drawn[s] != (u8)(fi + 1)) {
            gfx_sprite_strips(slot, f->tiles_w, f->tiles_h, &arcade_tile_index[f->tile_offset], ARCADE_TILE_BASE, (u16)((ARCADE_PAL_SLOT + f->palette) << 8));
            gfx_sprite_chain(slot, f->tiles_w);
            g_arc_drawn[s] = (u8)(fi + 1);
            for (int c = 1; c < f->tiles_w; c++) g_arc_drawn[s + c] = 0;
        }
        gfx_word((u16)(ADDR_SCB3 + slot), gfx_scb3_word(f->tiles_h, b->y - f->pad_top));
        gfx_word((u16)(ADDR_SCB4 + slot), gfx_scb4_word(sx));
        used += f->tiles_w;
    }
    for (int i = ARC_ELEM_COUNT - g_arc_used; i < ARC_ELEM_COUNT - used; i++) { obs_hide_slot(ARC_ELEM_SPRITE + i); g_arc_drawn[i] = 0; }
    g_arc_used = (u8)used;
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

/* Hot Gum bubble (PARTY): the angry bubble B over the carrier's head, one 16x16 sprite in the Roost marker slot (the rules never run together).
 * g = the playing Game, or 0 to park it. The 12-step sequence in gumbubble_tables.h loops; the fuse speeds the wobble up as it runs low. */
static const u8 g_hotb_cell[GUMBUBBLE_SEQ_COUNT] = GUMBUBBLE_TABLE_SEQ_CELL;
static const s8 g_hotb_dx[GUMBUBBLE_SEQ_COUNT] = GUMBUBBLE_TABLE_SEQ_DX;
static const s8 g_hotb_dy[GUMBUBBLE_SEQ_COUNT] = GUMBUBBLE_TABLE_SEQ_DY;
static const u8 g_hotb_ticks[GUMBUBBLE_SEQ_COUNT] = GUMBUBBLE_TABLE_SEQ_TICKS;
static u8 g_hotb_on;
static u8 g_hotb_cell_shown = 0xFF;
static void hot_bubble_step(const Game *g) {
    const Flier *c = g ? game_hot_carrier(g) : 0;
    if (c) {
        int t = (int)(g->frame % GUMBUBBLE_LOOP_TICKS), k = 0, sx;
        while (k < GUMBUBBLE_SEQ_COUNT - 1 && t >= g_hotb_ticks[k]) { t -= g_hotb_ticks[k]; k++; }
        sx = camera_screen_x((int)(c->x >> 16) - 8 + g_hotb_dx[k], g_cam_px, 16);
        if (camera_visible(sx, 16)) {
            u16 s3 = gfx_scb3_word(1, (int)(c->y >> 16) - 34 + g_hotb_dy[k]), s4 = gfx_scb4_word(sx);
            if (g_hotb_cell_shown != g_hotb_cell[k]) {
                gfx_sprite_strips(ROOST_SPRITE, 1, 1, &gumbubble_tile_index[g_hotb_cell[k]], GUMBUBBLE_TILE_BASE, (u16)(GUMBUBBLE_PAL_SLOT << 8));
                g_hotb_cell_shown = g_hotb_cell[k];
            }
            if (!g_hotb_on) { gfx_sprite_unchained(ROOST_SPRITE, 1); g_hotb_on = 1; }
            gfx_scb_run((u16)(ADDR_SCB3 + ROOST_SPRITE), 1, &s3, 1);
            gfx_scb_run((u16)(ADDR_SCB4 + ROOST_SPRITE), 1, &s4, 1);
            return;
        }
    }
    if (g_hotb_on) { obs_hide_slot(ROOST_SPRITE); g_hotb_on = 0; g_hotb_cell_shown = 0xFF; }
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
static u8 g_trip_islands_loaded;
static u8 bg_pending(void) {
    u8 world = g_flow.state == FLOW_PLAYING || g_flow.state == FLOW_ATTRACT_DEMO;
    u8 trip = world && g_flow.game.mode == GAME_MODE_TRIP;
    return g_bg_mood_busy || g_bg_mood != g_flow.game.mood || (world && !trip && !hazard_preloaded())
        || (trip && game_trip_ready(&g_flow.game) && !(trip_strip_loaded() && g_trip_islands_loaded));
}
/* Gum Trip entry: the course build steps run held (world hidden); the reveal waits for the course. */
static u8 trip_building(void) {
    return (g_flow.state == FLOW_PLAYING || g_flow.state == FLOW_ATTRACT_DEMO) && g_flow.game.mode == GAME_MODE_TRIP && !game_trip_ready(&g_flow.game);
}
static u8 world_state(const FlowView *v) { return (v->state == FLOW_PLAYING || v->state == FLOW_ATTRACT_DEMO) && v->game; }
static u8 world_shown(const FlowView *v) { return world_state(v) && !g_bg_hold; }

static void put_number(char *out, u32 v, int width);
static void text(u8 x, u8 y, u8 pal, const char *s);
/* Big Blow on the fix layer: the power bar (changed cells only) and one status line, written when the attempt state changes. */
static void draw_big_blow(const GgBlow *b) {
    uint8_t ops[BLOW_BAR_CELLS];
    if (!g_blow_bar_up) {
        char cells[BLOW_BAR_CELLS + 1];
        for (u8 i = 0; i < BLOW_BAR_CELLS; i++) cells[i] = '-';
        cells[BLOW_BAR_CELLS] = 0;
        text(BLOW_BAR_COL, BLOW_BAR_ROW, PAL_TEXT, cells);
        g_blow_bar.filled = 0;
        g_blow_bar_up = 1;
    }
    int n = gg_bar_set(&g_blow_bar, (u8)(b->phase == GG_BLOW_INTRO ? 0 : b->size / (GG_BLOW_MAX / BLOW_BAR_CELLS)), ops, BLOW_BAR_CELLS);
    for (int i = 0; i < n; i++) text((u8)(BLOW_BAR_COL + (ops[i] & 0x7F)), BLOW_BAR_ROW, PAL_HIGH, (ops[i] & 0x80) ? ">" : "-");
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

/* Burst Race on the fix layer: one power bar per side (P1 on BLOW_BAR_ROW, the rival two rows above) and a status line. */
static GgBar g_race_bar[2];
static void draw_burst_race(const GgRace *r) {
    uint8_t ops[BLOW_BAR_CELLS];
    if (!g_blow_bar_up) {
        char cells[BLOW_BAR_CELLS + 1];
        for (u8 i = 0; i < BLOW_BAR_CELLS; i++) cells[i] = '-';
        cells[BLOW_BAR_CELLS] = 0;
        for (u8 s = 0; s < 2; s++) { text(BLOW_BAR_COL, (u8)(BLOW_BAR_ROW - 2 * s), PAL_TEXT, cells); g_race_bar[s].width = BLOW_BAR_CELLS; g_race_bar[s].filled = 0; }
        g_blow_bar_up = 1;
    }
    for (u8 s = 0; s < 2; s++) {
        int n = gg_bar_set(&g_race_bar[s], (u8)(r->phase == GG_RACE_INTRO ? 0 : r->size[s] / (GG_BLOW_MAX / BLOW_BAR_CELLS)), ops, BLOW_BAR_CELLS);
        for (int i = 0; i < n; i++) text((u8)(BLOW_BAR_COL + (ops[i] & 0x7F)), (u8)(BLOW_BAR_ROW - 2 * s), PAL_HIGH, (ops[i] & 0x80) ? ">" : "-");
    }
    u32 key = (u32)r->phase | (u32)r->winner << 4 | (u32)r->players << 5;
    if (key == g_blow_key) return;
    g_blow_key = key;
    const char *msg = r->phase == GG_RACE_INTRO ? "BURST RACE   MASH A AND B     " : r->phase == GG_RACE_PLAY ? "BURST YOUR BUBBLE FIRST       " :
                      r->winner == 0 ? "YOU BURST FIRST  YOU WIN    " : r->players == 2 ? "PLAYER 2 BURST FIRST         " : "THE COMPUTER BURST FIRST     ";
    text((u8)((40 - BLOW_TEXT_W) / 2), BLOW_TEXT_ROW + 2, PAL_TEXT, msg);
}

/* Flap Dash on the fix layer: one status line (lap, seconds, qualifying mark), rewritten when the lap or the second changes. */
static void draw_flap_dash(const GgDash *d) {
    u32 secs = d->frames / 60u;
    u32 key = (u32)d->laps | (u32)d->done << 4 | secs << 8;
    if (key == g_blow_key) return;
    g_blow_key = key;
    char line[BLOW_TEXT_W + 1], nb[10];
    u8 i = 0;
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

/* Bubble Gather on the fix layer: caught of 20 and seconds left; hidden while the result screen covers the fix layer. */
static void draw_gather(const Game *g) {
    u32 left = (GG_GATHER_CLOCK - g->gather_clock + 59u) / 60u;
    u32 key = (u32)g->bonus.caught | left << 8 | 1u << 20;
    if (g->res.active || key == g_blow_key) return;
    g_blow_key = key;
    char line[BLOW_TEXT_W + 1], nb[10];
    u8 i = 0;
    const char *p = "BUBBLES ";
    while (p[i]) { line[i] = p[i]; i++; }
    put_number(nb, (u32)g->bonus.caught, 2);
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
        hero_show(v->game, game_flier_cam_px(v->game));
        if (v->game->mode == GAME_MODE_TRIP) pool_sync_trip(v->game, game_trip_ready(v->game));
        pool_sync_cpus(v->game);
        if (v->game->mode == GAME_MODE_ARCADE || v->game->mode == GAME_MODE_ARENA) pool_sync_p2(v->game);
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
#define TITLE_SELECT_ROW 23   /* rows 23 to 27: the mode select, drawn only while it is open */
#define TITLE_PLAYERS_ROW 28   /* the players line; the PARTY and Gum Games goal line takes its row while the list is open on those rows */
#define TITLE_GOAL_ROW 28     /* goal line, cols 2..37, under the last list row (27); credits row 29 */
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

static void draw_mode_select(u8 open, u8 mode, u8 rule, u8 event) {
    u8 key = open ? (u8)(1 + mode + (mode == GAME_MODE_PARTY ? rule * 8 : 0)) : 0;
    if (key == g_title.select) return;
    g_title.select = key;
    g_title.players_cr = 0xFF; /* the goal line shares the players row: redraw it after any change */
    if (!open) { text(15, TITLE_SELECT_ROW, PAL_TEXT, "          "); text(15, TITLE_SELECT_ROW + 1, PAL_TEXT, "          "); text(15, TITLE_SELECT_ROW + 2, PAL_TEXT, "          "); text(15, TITLE_SELECT_ROW + 3, PAL_TEXT, "                          "); text(15, TITLE_SELECT_ROW + 4, PAL_TEXT, "          "); text(2, TITLE_GOAL_ROW, PAL_TEXT, "                                    "); return; }
    gfx_text_backed(15, TITLE_SELECT_ROW, PAL_HIGH, mode == GAME_MODE_ARENA ? ">" : " ");
    gfx_text_backed(17, TITLE_SELECT_ROW, mode == GAME_MODE_ARENA ? PAL_HIGH : PAL_TEXT, "ARENA   ");
    gfx_text_backed(15, TITLE_SELECT_ROW + 1, PAL_HIGH, mode == GAME_MODE_TRIP ? ">" : " ");
    gfx_text_backed(17, TITLE_SELECT_ROW + 1, mode == GAME_MODE_TRIP ? PAL_HIGH : PAL_TEXT, "GUM TRIP");
    gfx_text_backed(15, TITLE_SELECT_ROW + 2, PAL_HIGH, mode == GAME_MODE_ARCADE ? ">" : " ");
    gfx_text_backed(17, TITLE_SELECT_ROW + 2, mode == GAME_MODE_ARCADE ? PAL_HIGH : PAL_TEXT, "ARCADE  ");
    /* PARTY row and goal line: centred, so the row is cleared to the open sky first (unbacked blanks), then drawn backed */
    text(2, TITLE_SELECT_ROW + 3, PAL_TEXT, BANNER_BLANK);
    text(2, TITLE_GOAL_ROW, PAL_TEXT, BANNER_BLANK);
    if (mode == GAME_MODE_PARTY) {
        const char *name = game_party_name(rule), *goal = game_party_goal(rule);
        u8 n = 0, g = 0;
        while (name[n]) n++;
        while (goal[g]) g++;
        u8 x = (u8)((VQ_FIX_COLS - 6 - n) / 2); /* "PARTY " + rule name */
        gfx_text_backed((u8)(x - 2), TITLE_SELECT_ROW + 3, PAL_HIGH, ">");
        gfx_text_backed(x, TITLE_SELECT_ROW + 3, PAL_HIGH, "PARTY ");
        gfx_text_backed((u8)(x + 6), TITLE_SELECT_ROW + 3, PAL_TEXT, name);
        gfx_text_backed((u8)((VQ_FIX_COLS - g) / 2), TITLE_GOAL_ROW, PAL_TEXT, goal);
    } else {
        gfx_text_backed(15, TITLE_SELECT_ROW + 3, PAL_HIGH, " ");
        gfx_text_backed(17, TITLE_SELECT_ROW + 3, PAL_TEXT, "PARTY");
    }
    gfx_text_backed(15, TITLE_SELECT_ROW + 4, PAL_HIGH, mode == GAME_MODE_GUM ? ">" : " ");
    gfx_text_backed(17, TITLE_SELECT_ROW + 4, mode == GAME_MODE_GUM ? PAL_HIGH : PAL_TEXT, "GUM GAMES");
    if (mode == GAME_MODE_GUM) gfx_center_text(TITLE_GOAL_ROW, PAL_TEXT, event == GG_FLAP_DASH ? "FLAP DASH  LEFT OR RIGHT TO CHANGE    " : event == GG_BUBBLE_GATHER ? "BUBBLE GATHER  LEFT OR RIGHT TO CHANGE" : event == GG_BURST_RACE ? "BURST RACE  LEFT OR RIGHT TO CHANGE   " : "BIG BLOW  LEFT OR RIGHT TO CHANGE     ");
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
    draw_mode_select(v->select_open, v->mode, v->party_rule, v->gg_event);
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
    }
    /* The effects wait for the fill: both at once fill the VRAM queue and gfx_drain stalls the frame past vblank. */
    if (g_res_filled == RESV_W * RESV_H) draw_result_fx(r);
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
    /* The header only changes with the state: send it after the clear. The fix shadow (vq_fix_put) keeps it, and a
     * hardware reset of the fix layer goes through video_init, which forces this branch (g_draw_state = -1). */
    if (g_res_up && !(v->state == FLOW_PLAYING && v->game && v->game->res.active)) {
        g_res_up = 0;
        resfx_hide();
        g_draw_state = -1; /* the result screen is over: clear the fix layer, the HUD comes back */
    }
    if (g_hl_up && v->highlight < 0) {
        g_hl_up = 0;
        g_draw_state = -1; /* the title's highlighted table is gone (the mode list opened): clear its rows */
    }
    if ((int)v->state != g_draw_state) {
        gfx_cls();
        title_reset();
        g_draw_state = (int)v->state;
        g_hud[0].kind = g_hud[1].kind = HUD_KIND_NONE;
        g_ov_stage = 0; g_ov_key = AO_NONE; g_ov_part = 0;
        g_rs_drawn = RS_NONE; g_rs_num = 0; g_banner_up = 0; g_howto_up = 0; g_mode_key = 0xFF; g_blow_key = 0xFFFFFFFFu; g_blow_bar_up = 0; g_cont_key[0] = g_cont_key[1] = 0xFF; g_stage_key = 0xFF; g_over_up = 0;
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
            u8 p2hud = (g->mode == GAME_MODE_ARCADE || g->mode == GAME_MODE_ARENA) && v->state != FLOW_ATTRACT_DEMO; /* the P2 side: PRESS / INSERT / stats */
            u8 b0 = (u8)g->hero[0].balloons;
            u8 l0 = (u8)g->lives[0].lives;
            /* P1: the old block (score, balloons; no balloons row in Gum Trip), plus lives in the arcade */
            if (g_hud[0].kind != HUD_KIND_STATS || g->score != g_hud[0].score || b0 != g_hud[0].balloons || l0 != g_hud[0].lives) {
                hud_side_stats(0, g->score, b0, l0, arc, g->mode != GAME_MODE_TRIP && g->mode != GAME_MODE_GUM);
                g_hud[0].kind = HUD_KIND_STATS; g_hud[0].score = g->score; g_hud[0].balloons = b0; g_hud[0].lives = l0;
            }
            if (p2hud) {
                u8 in = g->players == 2;
                u8 cr = g->credits;
                u8 out = (!in || g->lives[1].state == ARC_LIFE_ENDED); /* never joined, or out of lives and continues */
                if (out && v->state == FLOW_PLAYING) hud_side(1, cr > 0 ? HUD_KIND_PRESS : HUD_KIND_INSERT, 0, 0, 0, 0, 0);
                else if (in) hud_side(1, HUD_KIND_STATS, g->lives[1].score, (u8)g->hero[1].balloons, (u8)g->lives[1].lives, g->party_rule != PARTY_ROOST, 1);
                else hud_side(1, HUD_KIND_BLANK, 0, 0, 0, 0, 0);
            }
        }
        if (v->game && v->game->mode == GAME_MODE_TRIP) draw_gum_meter(v->game->trip.gum);
        else set_distress(0);
        if (v->state == FLOW_ATTRACT_DEMO && v->game) draw_overlay(v);
        if (v->state == FLOW_PLAYING && v->game && v->game->mode == GAME_MODE_GUM) { if (v->game->gg_gather) draw_gather(v->game); else if (v->game->gg_dash) draw_flap_dash(&v->game->dash); else if (v->game->gg_race) draw_burst_race(&v->game->race); else draw_big_blow(&v->game->blow); }
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
static void video_init(void) {
    gfx_init();
    /* Commit the fix clear FIRST, while palette 0 is still the BIOS zero: the budgeted queue flushes in order, so a clear
     * committed last left the BIOS tile 0x20 fill visible about 30 frames after a coin (tests/mame/unibios_check.lua, COIN1). */
    gfx_cls();
    gfx_commit_all();
    /* Fix layer palettes 0..FIX_PAL_COUNT-1 (generated with the font). */
    for (u8 s = 0; s < FIX_PAL_COUNT; s++)
        for (u8 i = 0; i < 16; i++) gfx_pal((u16)(s * 16 + i), fixfont_palettes[s][i]);
    soot_load_palettes();
    for (u8 p = 0; p < CHUTE_PALETTE_COUNT; p++)
        for (u8 i = 0; i < 16; i++) gfx_pal((u16)((CHUTE_PAL_SLOT + p) * 16 + i), chute_palettes[p][i]);
    for (u8 i = 0; i < 16; i++) gfx_pal((u16)(CHUTE_P2_PAL_SLOT * 16 + i), chute_extra_palettes[0][i]);
    for (u8 i = 0; i < 16; i++) gfx_pal((u16)(GUMBUBBLE_PAL_SLOT * 16 + i), gumbubble_palettes[0][i]);
    obs_load_palettes();
    island_load_palettes();
    trip_strip_load_palettes();
    trip_pickup_load_palettes();
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
    bg_load_palettes();
    gfx_word(ADDR_SCB3 + SPRITE_RESERVED, 0); /* sprite 0 is never visible (src/sprite_slots.h): nothing else writes this slot */
    bg_init();
    hazard_init();
    trip_strip_init();
    hero_hide();
    dead_release_all();
    pool_hide_all(); /* the hardware state is unknown; live objects redraw next frame */
    arcade_elems_forget();
    g_draw_state = -1;
    gfx_commit_all();
    gfx_drain(); /* init is outside the per-frame budget: it blocks, one flush per vblank, until everything is written */
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
        if (a_edge && !start && g_flow.state <= FLOW_ATTRACT_DEMO && bios_user_mode == 1 && (in & FLOW_RESET_COMBO) != FLOW_RESET_COMBO && take_credit()) start = 1;
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
        if (g_flow.state == FLOW_GAME_OVER) g_game_ended = 1;
        else if (g_game_ended && g_flow.state <= FLOW_ATTRACT_DEMO) {
            g_game_ended = 0;
            return; /* still user mode 2: SYSTEM_RETURN before any vblank sees mode 1 with a stale compulsion timer (see above) */
        }
        flow_view(&g_flow, &view);
        g_round_end_s[0] = g_flow.game.round_end; g_round_end_s[1] = g_flow.game.round_timer;
        g_round_end_s[2] = g_flow.game.round_start; g_round_end_s[3] = game_flier_visible(&g_flow.game);
        if (coined && !g_coin_blipped) sound_play_sfx(SND_SFX_COIN);
        if (coined) g_coin_blipped = 0;
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
        draw(&view);
        /* The result screen's fix scene covers the world: its steps wait, so the fill frames keep their budget. */
        if (view.state == FLOW_PLAYING && view.game && view.game->res.active) {
            /* Bonus result screen (it covers the world): hide the strip and load the next stage's strip tiles once the fill is done,
             * so the stage entry frame's hazard start only places it (two banks there cost about 113 lines, reports/stage-spike.md). */
            if (g_res_filled == RESV_W * RESV_H) {
                hazard_step(0, g_cam_px);
                hazard_game_restart(world_get(world_of_stage(arc_next_stage(view.game->arc.stage)))->hazard);
                hazard_preload();
            }
            goto world_done;
        }
        hero_and_mode(&view);
        {
            u8 world = world_shown(&view);
            u8 trip = world && view.game->mode == GAME_MODE_TRIP;
            u8 trip_game = (world || view.state == FLOW_GAME_OVER) && view.game && view.game->mode == GAME_MODE_TRIP;
            hazard_step((world || view.state == FLOW_GAME_OVER) && !trip_game, g_cam_px); /* the hazard strip is the arena's floor; Gum Trip has its own */
            if (g_bg_paused && world_state(&view) && view.game->mode != GAME_MODE_TRIP) hazard_preload(); /* the reveal frame then only places it */
            /* arcade only: elements kill, so they must be seen (worst scanline with them is checked in tests/host/test_sprite_budget.c) */
            /* Bonus first: on the frame it ends it parks slot 323, which the stage elements share and draw right after. */
            arcade_bonus_step(world && ((view.game->mode == GAME_MODE_ARCADE && view.game->arc.state == ARC_BONUS) || (view.game->mode == GAME_MODE_GUM && view.game->gg_gather)) && !view.game->res.active ? view.game : 0);
            arcade_elems_step(world && view.game->mode == GAME_MODE_ARCADE && view.game->arc.state != ARC_BONUS ? view.game : 0); /* the bonus shows no stage elements: hidden once on entry */
            island_step(world && !trip, g_cam_px); /* arena islands are not drawn in Gum Trip */
            /* the course (islands, kill strips, pickups) stays through Game Over like the planes and the hazard anim: all leave at the title */
            island_trip_step(trip_game ? &view.game->trip_gen : 0, trip_game ? view.game->trip.px : 0, trip_game && game_trip_ready(view.game));
            {   /* entry hold: the strip queues its columns hidden (ready 0) and the islands load their tiles hidden. Not on the entry
                 * frame (trip_hold 0, no build step yet): start_game and the title teardown already fill it. */
                u8 trip_held = g_bg_hold && world_state(&view) && view.game->mode == GAME_MODE_TRIP && view.game->trip_hold;
                g_trip_islands_loaded = trip_held && game_trip_ready(view.game) && island_trip_preload(&view.game->trip_gen);
                trip_strip_step((trip_game || trip_held) ? &view.game->trip_gen : 0, (trip_game || trip_held) ? view.game->trip.px : 0, trip_game && game_trip_ready(view.game));
            }
            trip_pickup_step(trip_game ? &view.game->trip_gen : 0, trip_game ? view.game->trip.px : 0, trip_game ? view.game->trip.steps : 0, trip_game && game_trip_ready(view.game));
            /* Arena: the bubble is always full size (no gum value, no pop); Gum Trip: its gum meter. */
            u8 arena = world && (view.game->mode == GAME_MODE_ARENA || view.game->mode == GAME_MODE_ARCADE);
            gum_step(0, arena || (trip && game_trip_ready(view.game)), trip ? view.game->trip.gum : (arena ? (uint16_t)(human_bubble_level(view.game, 0) * (GUM_MAX / GUM_VIEW_LEVELS)) : GUM_MAX), (trip || arena) ? view.game->frame : 0, g_gum_pose[0].drawn, g_gum_pose[0].frame, g_gum_pose[0].flip, g_gum_pose[0].cx, g_gum_pose[0].top, world && human_leaks(view.game, 0));
            roost_marker_step(arena && view.state == FLOW_PLAYING ? view.game : 0);
            hot_bubble_step(arena && view.state == FLOW_PLAYING ? view.game : 0);
            gum_step(1, arena && view.game->players == 2, (uint16_t)(human_bubble_level(view.game, 1) * (GUM_MAX / GUM_VIEW_LEVELS)), view.game->frame, g_gum_pose[1].drawn, g_gum_pose[1].frame, g_gum_pose[1].flip, g_gum_pose[1].cx, g_gum_pose[1].top, world && human_leaks(view.game, 1));
            {   /* the splash starts from the same crossing that plays the splosh sound; it keeps running through Game Over */
                const SoundEvents *se = sound_events();
                const Game *sg = view.game;   /* Gum Trip: its own floor death starts the gum splat (the splosh edge needs a water or lava kind) */
                splash_update(splash_enabled((world || view.state == FLOW_GAME_OVER) && sg, trip_game),
                              trip_game ? sg->trip_splat : se->n_splosh > 0, trip_game ? SPLASH_KIND_GUM : sg ? sg->hazard_kind : 0,
                              trip_game ? sg->hero[0].x >> 16 : se->splosh_x, trip_game ? sg->trip_splat_y : 0,
                              trip_game ? game_flier_cam_px(sg) : g_cam_px); /* the trip flier lives in screen space (owner 2026-11-17: splat far from the death) */
            }
            logo_step(view.state == FLOW_ATTRACT_TITLE);
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
            return; /* to the BIOS: SYSTEM_RETURN, backup RAM save, USER again (see above) */
        }
    }
}
