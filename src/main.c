/*
 * main.c - Neo Geo glue for Bubblegum Brawl: vblank loop, joypad, backup RAM, fix-layer drawing.
 * All game logic lives in src/core (host tested). Nothing here decides gameplay.
 */
#include <ngdevkit/neogeo.h>
#include <ngdevkit/ng-fix.h>
#include <ngdevkit/ng-video.h>
#include <ngdevkit/bios-ram.h>
#include "core/stage.h"
#include "core/camera.h"
#include "core/bg_scroll.h"
#include "core/flier.h"
#include "core/flow.h"
#include "core/banner.h"
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
#include "gfx.h"
#include "sprite_slots.h"
#include "vram_layout.h"
#include "bg.h"
#include "hazard.h"
#include "island.h"
#include "trip_strip.h"
#include "gum.h"
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
    SOOTLING_CLIP_FLAP2, SOOTLING_CLIP_FLAP1, SOOTLING_CLIP_POP2, SOOTLING_CLIP_POP1, SOOTLING_CLIP_INFLATE,
    SOOTLING_CLIP_FALL, SOOTLING_CLIP_IDLE,
    { SOOTLING_CLIP_WALK0, SOOTLING_CLIP_WALK1, SOOTLING_CLIP_WALK2 },
    { SOOTLING_CLIP_LAND0, SOOTLING_CLIP_LAND1, SOOTLING_CLIP_LAND2 },
    { SOOTLING_CLIP_BREATHE0, SOOTLING_CLIP_BREATHE1, SOOTLING_CLIP_BREATHE2 }
};
static FlierAnim g_hero_anim;

/* Test sentinels (tests/mame/flier_check.lua): first tile number last written to the sprite registers for the player
 * and for a computer flier (0 until drawn, player 0 again while hidden), and computer draws so far. g_soot_range holds
 * {first Sootling tile, tile count, palette slot of the player palette, then those three sentinels in that order}. */
volatile u16 g_blink_hidden, g_blink_shown; /* test sentinels: hero frames hidden / drawn while the blink test runs */
volatile u16 g_blink_pool[2]; /* test sentinels: pool flier frames hidden / drawn by the protected blink */
volatile u16 g_soot_range[6] = { SOOT_TILE_BASE, SOOTLING_TILE_COUNT, SOOT_PAL_SLOT, 0, 0, 0 };
/* Test hook (tests/mame/flier_check.lua): what hero_show last chose for the player: clip, sheet frame, ticks on that frame. */
volatile u16 g_soot_view[3];
#define g_soot_player_tile g_soot_range[3]
#define g_soot_cpu_tile g_soot_range[4]
#define g_soot_cpu_draws g_soot_range[5]

static void soot_load_palettes(void) {
    for (int p = 0; p < SOOTLING_PALETTE_COUNT; p++)
        for (int i = 0; i < 16; i++)
            gfx_pal((SOOT_PAL_SLOT + p) * 16 + i, sootling_palettes[p][i]);
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
static u8 g_cont_key = 0xFF; /* arcade continue panel on the fix layer: 0 none, else 1 + seconds left */
static u8 g_banner_up; /* the round clear banner is on the fix layer */
#define BANNER_ROWS_PER_FRAME 2
static u8 g_banner_pending; /* rows still to draw: the panel opens a few rows per frame to stay inside vblank */
static int g_banner_last; /* banner frame drawn last */
static u16 g_banner_shadow[BANNER_W * BANNER_H]; /* cell last sent: only changed cells cost vblank time */
static int g_rs_num;
/* Fix layer cell of the off screen marker last drawn (col 0xFF: none). */
static u8 g_edge_col = 0xFF, g_edge_row;

static struct { u8 drawn, frame, flip; int cx, top; } g_gum_pose;   /* where the player is drawn this frame: the gum bubble sits on it (src/gum.c) */
static void hero_hide(void) {
    g_gum_pose.drawn = 0;
    gfx_word(ADDR_SCB3 + HERO_SPRITE, 0); /* height 0 hides the sprite and the sticky ones after it */
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
#define DEAD_OWNER_HERO 0
#define DEAD_OWNER_CPU(i) ((u8)(1 + (i)))
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

static void hero_show(const Game *g, int cam_px) {
    const Flier *fl = &g->flier;
    int feet = (int)((fl->y + flier_half_h(fl)) >> 16);
    if (!game_flier_visible(g) || !flier_body_visible(fl) || (feet > SCREEN_H && fl->state < FLIER_FALLING)) { hero_hide(); dead_release(DEAD_OWNER_HERO); return; }
    int flip;
    u8 shown = flier_anim_step(&g_hero_anim, fl, &k_clips, &flip);
    g_soot_view[0] = g_hero_anim.clip;
    g_soot_view[1] = shown;
    g_soot_view[2] = g_hero_anim.tick;
    const SootlingFrame *f = &sootling_frames[soot_frame(SOOTLING_ANIM_PLAYER, shown)];
    const u16 *tiles = &sootling_tile_index[f->tile_offset];
    g_soot_player_tile = (u16)(SOOT_TILE_BASE + tiles[0]);
    int top = feet - f->tiles_h * 16;
    int sx = camera_screen_x((int)(fl->x >> 16) - FLIER_HALF_W - SOOT_BOX_DX, cam_px, SOOT_COLUMNS * 16);
    if (!camera_visible(sx, SOOT_COLUMNS * 16)) { hero_hide(); dead_release(DEAD_OWNER_HERO); return; }
    /* Protected blink: the animation above keeps stepping, only the sprites go dark (a protected flier is never FALLING). */
    if (!flier_view_visible(fl, g->frame)) { hero_hide(); g_soot_player_tile = (u16)(SOOT_TILE_BASE + tiles[0]); g_blink_hidden++; return; }   /* hero_hide clears the tile sentinel; the clip under test keeps it */
    g_blink_shown++;
    int left = sx;
    u16 attr = (u16)(((SOOT_PAL_SLOT + f->palette) << 8) | (flip ? SOOT_FLIP : 0));
    u16 slot = HERO_SPRITE;
    if (g->mode != GAME_MODE_TRIP && flier_body_front(fl)) {
        int d = dead_claim(DEAD_OWNER_HERO);
        if (d >= 0) { hero_hide(); slot = (u16)(DEAD_BODY_SPRITE + d * DEAD_BODY_COLUMNS); }
    } else dead_release(DEAD_OWNER_HERO);
    g_gum_pose.drawn = 1; g_gum_pose.frame = shown; g_gum_pose.flip = (u8)flip; g_gum_pose.cx = left + SOOT_COLUMNS * 8; g_gum_pose.top = top;
    soot_strips(slot, f, tiles, flip, attr);
    gfx_sprite_place(slot, SOOT_COLUMNS, f->tiles_h, left, top);
}

/*
 * Obstacle-sheet sprites. Tiles follow the logo tiles in the C-ROM (Makefile cat order), palettes follow the fix-layer
 * palettes. They draw through the object pool (src/core/obj_pool.h): each pool object holds a sprite run (POOL_COLS
 * hardware sprites from POOL_SPRITE_BASE, sprite_slots.h); the animation index of an object is its type. Live users:
 * the computer fliers (pool_sync_cpus) and the pool stress test hook. The arena platforms are the island sprites (src/island.c).
 */
_Static_assert(POOL_SPRITE_COUNT == POOL_SPRITES, "pool sprite range size");
_Static_assert(BG_SPRITE_END <= GUM_SPRITE && GUM_SPRITE + GUM_COUNT <= ISLAND_SPRITE, "gum sprites overlap the background or the islands");
_Static_assert(ISLAND_SPRITE + ISLAND_COUNT <= POOL_SPRITE_BASE, "island sprites overlap the object pool");
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

static void pool_reset(void) {
    for (int i = 0; i < STAGE_SPAWN_COUNT; i++) g_cpu_obj[i] = POOL_NONE;
    for (int i = 0; i < TRIP_RIVAL_MAX; i++) g_rival_obj[i] = POOL_NONE;
    obj_pool_init(&g_pool, POOL_SPRITE_BASE);
    g_haz_claimed = 0;
}

static void pool_free_all(void) {
    for (int i = 0; i < STAGE_SPAWN_COUNT; i++) g_cpu_obj[i] = POOL_NONE;
    for (int i = 0; i < TRIP_RIVAL_MAX; i++) g_rival_obj[i] = POOL_NONE;
    for (u8 i = 0; i < POOL_MAX; i++) obj_pool_free(&g_pool, i);
    g_haz_claimed = 0;
}

/* Computer fliers: one pool object each while on screen (anchor: centre x, feet y). type = sheet frame of the clip (flier_anim_step), flags POOL_F_FLIP when facing left. */
static FlierAnim g_cpu_anim[STAGE_SPAWN_COUNT];
/* A computer flier that bounced on spikes draws from a dead body slot (in front of the spike art) instead of a pool object. */
static int cpu_show_front(const Game *g, int i) {
    const Flier *c = &g->cpu[i];
    if (g->mode == GAME_MODE_TRIP || !flier_body_front(c)) { dead_release(DEAD_OWNER_CPU(i)); return 0; }
    int d = dead_claim(DEAD_OWNER_CPU(i));
    if (d < 0) return 0;
    int flip;
    u8 shown = flier_anim_step(&g_cpu_anim[i], c, &k_clips, &flip);
    const SootlingFrame *f = &sootling_frames[soot_frame(SOOTLING_ANIM_CPU, shown)];
    const u16 *tiles = &sootling_tile_index[f->tile_offset];
    int feet = (int)((c->y + flier_half_h(c)) >> 16);
    int sx = camera_screen_x((int)(c->x >> 16) - FLIER_HALF_W - SOOT_BOX_DX, g_cam_px, SOOT_COLUMNS * 16);
    u16 slot = (u16)(DEAD_BODY_SPRITE + d * DEAD_BODY_COLUMNS);
    if (!camera_visible(sx, SOOT_COLUMNS * 16)) { dead_release(DEAD_OWNER_CPU(i)); return 1; }
    soot_strips(slot, f, tiles, flip, (u16)(((SOOT_PAL_SLOT + f->palette) << 8) | (flip ? SOOT_FLIP : 0)));
    gfx_sprite_place(slot, SOOT_COLUMNS, f->tiles_h, sx, feet - f->tiles_h * 16);
    return 1;
}

static void pool_sync_cpus(const Game *g) {
    int slots = g->mode == GAME_MODE_ARCADE ? STAGE_SPAWN_COUNT : CPU_MAX; /* arena runs 3 slots: the extra arcade slots cost frame time in the arena worst case */
    for (int i = 0; i < slots; i++) {
        const Flier *c = &g->cpu[i];
        u8 k = g_cpu_obj[i];
        int visible = i < g->cpu_count && flier_body_visible(c) && (c->state >= FLIER_FALLING || (int)((c->y + flier_half_h(c)) >> 16) <= SCREEN_H);
        if (!visible) dead_release(DEAD_OWNER_CPU(i));
        if (!visible || cpu_show_front(g, i)) {
            if (k != POOL_NONE) { obj_pool_free(&g_pool, k); g_cpu_obj[i] = POOL_NONE; }
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
        p->y = (int32_t)(c->y + flier_half_h(c));
        if (flier_view_visible(c, g->frame)) p->flags &= (u8)~POOL_F_BLINK; else p->flags |= POOL_F_BLINK;
    }
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
static void pool_show_hero(PoolObj *p, u8 i, u16 *scb3) {
    if (p->flags & POOL_F_BLINK) { g_blink_pool[0]++; if (g_pool_drawn[i]) pool_hide_run(i); return; } /* the animation kept stepping in the sync; the hide costs queue words once */
    g_blink_pool[1]++;
    u8 fi = soot_frame(SOOTLING_ANIM_CPU, p->type);
    const SootlingFrame *f = &sootling_frames[fi];
    int flip = (p->flags & POOL_F_FLIP) != 0;
    int x = camera_screen_x(obj_pool_px(p->x) - FLIER_HALF_W - SOOT_BOX_DX, (p->flags & POOL_F_SCREEN) ? 0 : g_cam_px, SOOT_COLUMNS * 16);
    u16 slot = obj_pool_sprite(&g_pool, i);
    if (!camera_visible(x, SOOT_COLUMNS * 16)) { pool_hide_run(i); return; }
    int top = obj_pool_px(p->y) - f->tiles_h * 16;
    const u16 *tiles = &sootling_tile_index[f->tile_offset];
    u8 key = (u8)(p->type + 1 + (flip ? 128 : 0)); /* frame and mirror state the strips hold; the computer palette only, so the clip frame is unique */
    if (g_pool_drawn[i] != key) {
        soot_strips(slot, f, tiles, flip, (u16)(((SOOT_PAL_SLOT + f->palette) << 8) | (flip ? SOOT_FLIP : 0)));
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
    for (u8 i = 0; m; i++, m >>= 1) if (m & 1) pool_hide_run(i);
    PoolObj *p = g_pool.obj;
    for (u8 i = 0; i < POOL_MAX; i++, p++) {
        scb3[i] = 0;
        if (!(p->flags & POOL_F_LIVE)) continue;
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
    gfx_scb_run(ADDR_SCB3 + POOL_SPRITE_BASE, POOL_COLS, scb3, POOL_MAX);
    gfx_scb_run(ADDR_SCB4 + POOL_SPRITE_BASE, POOL_COLS, g_pool_scb4, POOL_MAX);
    g_pool_live = g_pool.live;
    if (g_pool.live) g_pool_frames++;
}

/* Arcade stage elements (src/core/arc_view.h): vent, spark, flipper, grabber, hatch, in the ARC_ELEM_SPRITE columns. Which frame and where
 * is core logic (arc_view_build); here the blocks become strips. Slots are filled front to back; the rest are hidden every frame
 * (gfx_word drops unchanged words), which also covers a mode, stage or state change and the arena. */
_Static_assert(ARCADE_VENT_ART_W == 32 && ARCADE_SPARK_ART_W == 16 && ARCADE_FLIPPER_ART_W == 40 && ARCADE_GRABBER_ART_W == 40 && ARCADE_GRABBER_ART_H == 44,
               "arcade art sizes differ from ARC_VIEW_W/H in core/arc_view.h");
_Static_assert(ARCADE_VENT_FRAMES == ARCADE_PIECE_BODY_A_COUNT && ARCADE_SPARK_FRAMES == ARCADE_PIECE_SPARK_A_COUNT && ARCADE_FLIPPER_FRAMES == ARCADE_PIECE_FLIPPER_A_COUNT &&
               ARCADE_GRABBER_FRAMES == ARC_GRAB_FRAMES && ARCADE_PIECE_HATCH_COUNT == 1, "arcade frame counts differ from arc_view");
_Static_assert(ARCADE_MAX_COLUMNS <= 3, "arcade frames are at most 3 columns (ARC_VIEW_COLS)");
static const u8 k_arc_anim[ARCV_PIECES] = { ARCADE_ANIM_STORM, ARCADE_ANIM_STORM, ARCADE_ANIM_PLAYER, ARCADE_ANIM_PLAYER, ARCADE_ANIM_STORM };
static const u8 k_arc_first[ARCV_PIECES] = { ARCADE_PIECE_BODY_A_FIRST, ARCADE_PIECE_SPARK_A_FIRST, ARCADE_PIECE_FLIPPER_A_FIRST, ARCADE_PIECE_GRABBER_A_FIRST, ARCADE_PIECE_HATCH_FIRST };
static u16 g_arc_tick;
static u8 g_arc_dirty; /* slots may hold element sprites: hide them once after the last draw, not every frame (vblank budget) */

static void arcade_elems_step(const Game *g) {
    ArcSprite blocks[ARC_VIEW_MAX];
    int n = 0, used = 0;
    if (!g && !g_arc_dirty) return;
    g_arc_dirty = g != 0;
    if (g) n = arc_view_build(&g->elems, g_arc_tick++, blocks);
    for (int i = 0; i < n; i++) {
        const ArcSprite *b = &blocks[i];
        const ArcadeFrame *f = &arcade_frames[arcade_anims[k_arc_anim[b->piece]].first_frame + k_arc_first[b->piece] + b->frame];
        int w = f->tiles_w * 16, sx = camera_screen_x(b->x - f->pad_left, g_cam_px, w);
        if (used + f->tiles_w > ARC_ELEM_COUNT || !camera_visible(sx, w)) continue;
        u16 slot = (u16)(ARC_ELEM_SPRITE + used);
        gfx_sprite_strips(slot, f->tiles_w, f->tiles_h, &arcade_tile_index[f->tile_offset], ARCADE_TILE_BASE, (u16)((ARCADE_PAL_SLOT + f->palette) << 8));
        gfx_sprite_place(slot, f->tiles_w, f->tiles_h, sx, b->y - f->pad_top);
        used += f->tiles_w;
    }
    for (int i = used; i < ARC_ELEM_COUNT; i++) obs_hide_slot(ARC_ELEM_SPRITE + i);
}

/* Bonus stage: bubbles (Gum Trip pickup art, 2 sprite columns each) in the first slots of the shared strip range, in the order of the live
 * bubbles (at most ARC_BONUS_LIVE_MAX at once, so 20 slots); then the 4 gum nozzles in front of them and their mouth puffs (2 columns each);
 * the floor strip in the island slots (the bonus layout draws no islands, island_layout.c), 2 columns per 32 px tile. Arcade art, palette ARCADE_ANIM_NOZZLE. */
#define BONUS_NOZZLE_SPRITE (ARC_BONUS_SPRITE + 2 * ARC_BONUS_LIVE_MAX)
#define BONUS_PUFF_SPRITE (BONUS_NOZZLE_SPRITE + 2 * ARC_NOZZLE_COUNT)
#define BONUS_FLOOR_TILES (ARC_BONUS_WORLD_W / 32)
_Static_assert(BONUS_PUFF_SPRITE + 2 * ARC_NOZZLE_COUNT <= ARC_BONUS_SPRITE + TRIP_STRIP_COUNT, "bonus sprites exceed the shared strip range");
_Static_assert(ARC_BONUS_COUNT >= 2 * ARC_BONUS_LIVE_MAX && 2 * BONUS_FLOOR_TILES <= ISLAND_COUNT, "bonus sprite slot counts");
_Static_assert(ARCADE_PIECE_NOZZLE0_COUNT == 1 && ARCADE_PIECE_FLOOR_COUNT == 1 && ARCADE_PIECE_PUFF_COUNT == 4, "bonus art frame counts");
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
    int idx = 0, piece, moved = 0, first = g_bonus_cam < 0;
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
    ArcSprite blocks[ARC_BONUS_BUBBLES];
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
        if (i < n) {
            const ArcSprite *b = &blocks[i];
            const TrippickupFrame *f = &trippickup_frames[trippickup_anims[TRIPPICKUP_ANIM_PICKUP_IDLE].first_frame + b->frame];
            int sx = camera_screen_x(b->x, g_cam_px, 32);
            if (camera_visible(sx, 32)) {
                const u16 *tl = &trippickup_tile_index[f->tile_offset];
                if (g_bonus_bub_tiles[i] != tl) { gfx_sprite_strips(slot, 2, 2, tl, TRIPPICKUP_TILE_BASE, (u16)(TRIPPICKUP_PAL_SLOT << 8)); g_bonus_bub_tiles[i] = tl; }
                if (!(g_bonus_bub_on & (1u << i))) { gfx_sprite_chain(slot, 2); g_bonus_bub_on |= 1u << i; } /* the chain words go out once, then 2 words a frame */
                gfx_word((u16)(ADDR_SCB3 + slot), gfx_scb3_word(2, b->y));
                gfx_word((u16)(ADDR_SCB4 + slot), gfx_scb4_word(sx));
                continue;
            }
        }
        if (g_bonus_bub_on & (1u << i)) { obs_hide_slot(slot); obs_hide_slot(slot + 1); g_bonus_bub_on &= ~(1u << i); g_bonus_bub_tiles[i] = 0; }
    }
    bonus_static_place();
    for (int k = 0; k < ARC_NOZZLE_COUNT; k++) {
        int top = arc_nozzle_top(k), x = arc_nozzle_x(k), p = g->bonus.puff[k];
        if (p) { bonus_piece((u16)(BONUS_PUFF_SPRITE + 2 * k), ARCADE_PIECE_PUFF_FIRST + ((ARC_BONUS_PUFF_FRAMES - p) >> 2), x, top - 24); g_bonus_puff_on |= (u8)(1 << k); }
        else if (g_bonus_puff_on & (1 << k)) { obs_hide_slot((u16)(BONUS_PUFF_SPRITE + 2 * k)); obs_hide_slot((u16)(BONUS_PUFF_SPRITE + 2 * k + 1)); g_bonus_puff_on &= (u8)~(1 << k); }
    }
}

/* BIOS_USER_MODE: 1 attract, 2 game in progress (coins then only add credits). */
static volatile u8 g_start_pending;
static u8 read_input(void);
volatile u8 g_coin_calls; /* coins the BIOS reported (vector 0x134) and game_loop has not yet played a blip for; also read by MAME tests */

/* COIN_SOUND (vector 0x134, ngdevkit.ld): runs in the BIOS vblank handler, so it only counts. */
void coin_sound(void) { g_coin_calls++; }

/*
 * PLAYER_START (vector 0x128), called by the BIOS from its vblank SYSTEM_IO when a player
 * presses start with credits, or when the title compulsion timer runs out. ngdevkit's
 * wrapper_player_start calls this symbol when it is defined (ngdevkit.ld) and otherwise
 * clears BIOS_START_FLAG, which refuses every start. The BIOS deducts the credit only if
 * BIOS_USER_MODE is 2 when this returns, so accepting means: leave the start flag set,
 * set mode 2, and let game_loop start the game on the next frame.
 *
 * Bug fixed here: the game used to start from bios_statchange itself and never accepted
 * PLAYER_START. The credit was never taken, so after a game (high score SYSTEM_RETURN) the
 * BIOS still saw a credit, called USER 3 (title), forced PLAYER_START at the timeout, got
 * a refusal, and UniBIOS took over (DEMO_END, palette cleared) and called USER 3 again
 * with the timer already expired. That repeated about every 12 frames, so video_init never
 * finished: a blinking screen with only the sky. Guarded by make test-reach (boot 1 keeps
 * running past the title timeout after the save).
 */
void player_start(void) {
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

/* Off screen marker for the human flier (design D1): a '<' or '>' on the fix layer at the screen edge, at the flier's
 * row. The fix layer is free at the edges (the HUD sits in columns 2..), costs no sprite slot and the fix shadow
 * drops unchanged cells. One cell at a time; erased when the flier shows again or the match ends. */
static void edge_marker(const Game *g, int cam_px) {
    int dir = 0, row = 0;
    if (g) {
        const Flier *fl = &g->flier;
        int w = SOOT_COLUMNS * 16;
        int sx = camera_screen_x((int)(fl->x >> 16) - FLIER_HALF_W - SOOT_BOX_DX, cam_px, w);
        if (fl->state != FLIER_GONE) dir = camera_edge_marker(sx, w);
        row = (int)(fl->y >> 19);
        if (row < 8) row = 8;
        if (row > 24) row = 24;
    }
    u8 col = dir < 0 ? 0 : 39;
    if (g_edge_col != 0xFF && (dir == 0 || col != g_edge_col || row != g_edge_row)) {
        gfx_text(g_edge_col, g_edge_row, PAL_TEXT, " ");
        g_edge_col = 0xFF;
    }
    if (dir != 0 && g_edge_col == 0xFF) {
        gfx_text(col, (u8)row, PAL_HIGH, dir < 0 ? "<" : ">");
        g_edge_col = col; g_edge_row = (u8)row;
    }
}

static void hero_and_mode(const FlowView *v) {
    if (v->state == FLOW_PLAYING && v->game) {
        bios_user_mode = 2;
        g_cam_px = (u16)game_camera_px(v->game);
        g_cam_unwrapped = camera_unwrapped_px(&v->game->camera);
        edge_marker(v->game, game_flier_cam_px(v->game));
        hero_show(v->game, game_flier_cam_px(v->game));
        if (v->game->mode == GAME_MODE_TRIP) pool_sync_trip(v->game, game_trip_ready(v->game));
        pool_sync_cpus(v->game);
        if (v->game->mode == GAME_MODE_TRIP) pool_sync_rivals(v->game);
        if (g_pool_stress) pool_stress();
        pool_show();
    } else {
        /* BIOS_USER_MODE 2 = game in progress: play, game over, name entry and the save
         * reminder all belong to the game; 1 only once attract begins. Bug fixed here: mode 1
         * was set on entering GAME_OVER, so with a credit left UniBIOS treated the game as in
         * attract, saw the refused start and stopped calling the VBlank callback; game_loop
         * waited for vblank forever (frozen last frame, a coin woke it). An accepted start
         * keeps mode 2 until flow_step sees it. Guarded by make test-unibios (two coins). */
        if ((v->state > FLOW_ATTRACT_DEMO && v->state != FLOW_SAVE_REMINDER) || g_start_pending) bios_user_mode = 2; /* BG2: the reminder screen allows the BIOS save */
        else bios_user_mode = 1;
        g_cam_px = 0;
        g_cam_unwrapped = 0;
        g_edge_col = 0xFF; /* draw() clears the fix layer with the state change */
        flier_anim_init(&g_hero_anim);
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
static u8 read_input(void) {
    u8 cur = bios_p1current;
    return (u8)(((cur >> 4) & 0x0F) | ((cur & 0x0F) << 4));
}

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
    text(12, (u8)(y0 - 2), PAL_TEXT, mode == GAME_MODE_TRIP ? "GUM TRIP SCORES" : mode == GAME_MODE_ARCADE ? "ARCADE SCORES  " : "ARENA SCORES   ");
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
/* Score and lives draw() last sent for the game HUD; g_hud_game 0 = not sent since the last clear. */
static u8 g_hud_game;
/* Gum Trip gum meter on HUD row 6 (replaces the Balloons row): fill step last drawn, 255 = nothing drawn since the last clear.
 * g_meter_draws counts the frames in which the cells were sent (tests/mame/trip_check.lua reads it). */
#define METER_NONE 255
#define METER_ROW 6
#define METER_COL 2
static u8 g_meter_step = METER_NONE;
volatile u16 g_meter_draws;
static void draw_gum_meter(u16 gum) {
    u8 step = (u8)trip_view_meter_step((int)gum);
    if (step == g_meter_step) return;
    g_meter_step = step;
    for (u8 c = 0; c < TRIPMETER_CELLS; c++) gfx_fix_tile((u8)(METER_COL + c), METER_ROW, PAL_TEXT, tripmeter_cell[step][c]);
    g_meter_draws++;
}
static u32 g_hud_score;
static u32 g_hud_lives;

/* Title screen (art: assets/font/draw_hud_title_final.py title_final(), art row r = fix row r + 2). Everything is drawn
 * once after the fix layer clear and again only when its value changes; draw() resets the cache on a state change. */
#define TITLE_HI_ROW 3
#define TITLE_PLATE_ROW 22
#define TITLE_SELECT_ROW 23   /* rows 23 to 25: the mode select, drawn only while it is open */
#define TITLE_PLAYERS_ROW 26
#define TITLE_CREDIT_ROW 29
#define TITLE_BLINK_ON 3      /* the plate line shows for 3 of every 5 logo animation steps */
#define BIOS_CREDIT_BCD ((volatile u8 *)0x10fe00) /* BCD, 1 = one credit; measured by tests/mame/logo_check.lua under UniBIOS 4.0 (nullbios never counts) */
enum { TL_UNKNOWN = 0xFF, TL_HIDDEN = 0, TL_PRESS, TL_INSERT };
static struct { u8 init, line, select, credits; u32 hi; u8 mode; } g_title = { 0, TL_UNKNOWN, 0xFF, 0xFF, 0xFFFFFFFFu, 0xFF };
volatile u16 g_title_press_draws; /* test sentinel: frames "PRESS START" was (re)sent */

static void title_reset(void) { g_title.init = 0; g_title.line = TL_UNKNOWN; g_title.select = 0xFF; g_title.credits = 0xFF; g_title.hi = 0xFFFFFFFFu; g_title.mode = 0xFF; }

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

static void draw_mode_select(u8 open, u8 mode) {
    u8 key = open ? (u8)(1 + mode) : 0;
    if (key == g_title.select) return;
    g_title.select = key;
    if (!open) { text(15, TITLE_SELECT_ROW, PAL_TEXT, "          "); text(15, TITLE_SELECT_ROW + 1, PAL_TEXT, "          "); text(15, TITLE_SELECT_ROW + 2, PAL_TEXT, "          "); return; }
    gfx_text_backed(15, TITLE_SELECT_ROW, PAL_HIGH, mode == GAME_MODE_ARENA ? ">" : " ");
    gfx_text_backed(17, TITLE_SELECT_ROW, mode == GAME_MODE_ARENA ? PAL_HIGH : PAL_TEXT, "ARENA   ");
    gfx_text_backed(15, TITLE_SELECT_ROW + 1, PAL_HIGH, mode == GAME_MODE_TRIP ? ">" : " ");
    gfx_text_backed(17, TITLE_SELECT_ROW + 1, mode == GAME_MODE_TRIP ? PAL_HIGH : PAL_TEXT, "GUM TRIP");
    gfx_text_backed(15, TITLE_SELECT_ROW + 2, PAL_HIGH, mode == GAME_MODE_ARCADE ? ">" : " ");
    gfx_text_backed(17, TITLE_SELECT_ROW + 2, mode == GAME_MODE_ARCADE ? PAL_HIGH : PAL_TEXT, "ARCADE  ");
}

static void draw_title(const FlowView *v) {
    if (!g_title.init) {
        g_title.init = 1;
        gfx_text_backed(11, TITLE_HI_ROW, PAL_HIGH, "HIGH SCORE");
        plate(13, 26, TITLE_PLAYERS_ROW);
        gfx_text_backed(13, TITLE_PLAYERS_ROW, PAL_TEXT, "1 OR 2 PLAYERS");
        plate(28, 36, TITLE_CREDIT_ROW);
    }
    u32 hi = v->table->score[0];
    if (hi > 999999) hi = 999999;
    if (hi != g_title.hi) {
        g_title.hi = hi;
        char buf[8];
        put_number(buf, hi, 6);
        gfx_text_backed(22, TITLE_HI_ROW, PAL_TEXT, buf);
    }
    u8 cr = credits_now();
    if (cr != g_title.credits) {
        g_title.credits = cr;
        char buf[3];
        put_number(buf, cr, 2);
        gfx_text_backed(28, TITLE_CREDIT_ROW, PAL_TEXT, "CREDITS ");
        gfx_text_backed(36, TITLE_CREDIT_ROW, PAL_TEXT, buf + 1);
        if (cr > 9) gfx_text_backed(35, TITLE_CREDIT_ROW, PAL_TEXT, buf);
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
    draw_mode_select(v->select_open, v->mode);
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
    } else if (v->ov_key != AO_NONE && v->ov_key != g_ov_key) {
        const u8 st = v->ov_key == AO_FLAP ? 0 : 1;
        u8 lever = attract_states[st].lever;
        if (v->ov_key == AO_STEER_LEFT) lever = ATTRACT_FRAME_STICK_LEFT;
        g_ov_key = v->ov_key;
        text(ATTRACT_ACTION_COL, ATTRACT_ACTION_ROW, FIXFONT_PAL_GOLD, st == 0 ? "FLAP " : "STEER");
        ov_frame(ATTRACT_LEVER_COL, ATTRACT_LEVER_ROW, lever);
        ov_frame(ATTRACT_BUTTON_COL, ATTRACT_BUTTON_ROW, attract_states[st].a);
    }
}

static void draw(const FlowView *v) {
    char buf[3];
    /* The header only changes with the state: send it after the clear. The fix shadow (vq_fix_put) keeps it, and a
     * hardware reset of the fix layer goes through video_init, which forces this branch (g_draw_state = -1). */
    if ((int)v->state != g_draw_state) {
        gfx_cls();
        title_reset();
        g_draw_state = (int)v->state;
        g_hud_game = 0;
        g_ov_stage = 0; g_ov_key = AO_NONE;
        g_rs_drawn = RS_NONE; g_rs_num = 0; g_banner_up = 0; g_cont_key = 0xFF;
        g_meter_step = METER_NONE;
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
        draw_table(v->table, v->table_mode, v->highlight, 8);
        break;
    case FLOW_ATTRACT_DEMO:
    case FLOW_PLAYING:
    case FLOW_GAME_OVER:
        /* Per-frame HUD: resend only when score or lives moved (or first frame of the state with a game). */
        if (v->game && (!g_hud_game || v->game->score != g_hud_score || v->game->flier.balloons != g_hud_lives)) {
            g_hud_game = 1;
            g_hud_score = v->game->score;
            g_hud_lives = v->game->flier.balloons;
            text(2, 5, PAL_TEXT, "SCORE");
            draw_number(8, 5, PAL_TEXT, v->game->score, 8);
            if (v->game->mode != GAME_MODE_TRIP) {
                text(2, 6, PAL_TEXT, "Balloons");
                draw_number(11, 6, PAL_TEXT, v->game->flier.balloons, 1);
            }
        }
        if (v->game && v->game->mode == GAME_MODE_TRIP) draw_gum_meter(v->game->trip.gum);
        if (v->state == FLOW_ATTRACT_DEMO && v->game) draw_overlay(v);
        {
            /* ROUND nn then GO! (arena game only: the demo and Gum Trip report RS_NONE); fix font, no panel; cleared when the phase ends */
            u8 rs = (v->state == FLOW_PLAYING && v->game) ? (u8)game_round_start_phase(v->game) : (u8)RS_NONE;
            int rn = rs == RS_ROUND ? game_round_number(v->game) : 0;
            if (rs != g_rs_drawn || rn != g_rs_num) {
                const char *l0 = rs == RS_ROUND ? game_round_start_text(v->game, 0) : 0;
                if (rs == RS_ROUND && l0) {
                    gfx_center_text(12, PAL_TEXT, "                  ");
                    gfx_center_text(13, PAL_TEXT, "                  ");
                    gfx_center_text(12, PAL_TEXT, l0);
                    gfx_center_text(13, PAL_TEXT, game_round_start_text(v->game, 1));
                } else if (rs == RS_ROUND) {
                    char rb[10] = "ROUND ";
                    if (v->game->mode == GAME_MODE_ARCADE) { rb[0] = 'S'; rb[1] = 'T'; rb[2] = 'A'; rb[3] = 'G'; rb[4] = 'E'; }
                    rb[6] = (char)('0' + (rn / 10) % 10); rb[7] = (char)('0' + rn % 10); rb[8] = 0;
                    if (rb[6] == '0') { rb[6] = rb[7]; rb[7] = 0; }
                    gfx_center_text(13, PAL_TEXT, "           ");
                    gfx_center_text(13, PAL_TEXT, rb);
                } else if (rs == RS_GO) {
                    gfx_center_text(12, PAL_TEXT, "                  ");
                    gfx_center_text(13, PAL_TEXT, "                  ");
                    gfx_center_text(13, PAL_TEXT, "GO!");
                } else {
                    gfx_center_text(13, PAL_TEXT, "           ");
                }
                g_rs_drawn = rs; g_rs_num = rn;
            }
        }
        {
            /* Arcade continue screen (game_step_arena freezes the world): a plate with the words and the seconds left; redrawn once a second */
            u8 key = (v->state == FLOW_PLAYING && v->game && v->game->mode == GAME_MODE_ARCADE && v->game->lives.state == ARC_LIFE_CONTINUE)
                         ? (u8)(1 + arc_continue_seconds(&v->game->lives)) : 0;
            if (key != g_cont_key) {
                u8 row;
                char sb[16] = "TIME LEFT   ";
                if (key) {
                    for (row = 11; row <= 14; row++) plate(13, 26, row);
                    gfx_center_text(11, PAL_HIGH, "CONTINUE");
                    gfx_center_text(12, PAL_TEXT, "PRESS BUTTON A");
                    if (key > 10) { sb[10] = '1'; sb[11] = '0'; } else sb[10] = (char)('0' + key - 1);
                    gfx_center_text(13, PAL_TEXT, sb);
                } else if (g_cont_key != 0xFF) {
                    for (row = 11; row <= 14; row++) text(12, row, PAL_TEXT, "                ");
                }
                g_cont_key = key;
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
                bc.winner = BANNER_P1; bc.round = (uint16_t)game_round_number(v->game); bc.last = (uint8_t)game_banner_flags(v->game);
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
                    rows = 0xFF; g_banner_pending = 0;
                } else {
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
    if (v->state != FLOW_ATTRACT_TABLE && v->highlight >= 0)
        draw_table(v->table, v->table_mode, v->highlight, 16);
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
 * Bubblegum Brawl overrides rom_game and rom_title (link-time hooks in ngdevkit.ld): the first
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
    obs_load_palettes();
    island_load_palettes();
    trip_strip_load_palettes();
    trip_pickup_load_palettes();
    gum_load_palettes();
    splash_load_palettes();
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
 */
static u8 g_bram_unsaved;

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
        flow_step(&g_flow, in, start, g_frame_counter);
        {
            /* hazard kind per round: a new game starts at round 0; a new round (not during the banner HOLD) swaps the strip */
            static int s_round = 0;
            static u8 s_was_playing = 0;
            u8 playing = g_flow.state == FLOW_PLAYING && (g_flow.game.mode == GAME_MODE_ARENA || g_flow.game.mode == GAME_MODE_ARCADE); /* a new arcade stage swaps the strip like a new round */
            int rnd = game_round_number(&g_flow.game);
            if (playing && !s_was_playing) { hazard_game_restart(); s_round = rnd; }
            else if (playing && rnd != s_round && g_flow.game.round_end != RE_HOLD) { hazard_round_restart(); s_round = rnd; }
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
        flow_view(&g_flow, &view);
        g_round_end_s[0] = g_flow.game.round_end; g_round_end_s[1] = g_flow.game.round_timer;
        g_round_end_s[2] = g_flow.game.round_start; g_round_end_s[3] = game_flier_visible(&g_flow.game);
        if (coined) sound_play_sfx(SND_SFX_COIN);
        sound_frame(&view);
        sound_tick();
        draw(&view);
        hero_and_mode(&view);
        {
            u8 trip = view.state == FLOW_PLAYING && view.game && view.game->mode == GAME_MODE_TRIP;
            u8 trip_game = (view.state == FLOW_PLAYING || view.state == FLOW_GAME_OVER) && view.game && view.game->mode == GAME_MODE_TRIP;
            hazard_step((view.state == FLOW_PLAYING || view.state == FLOW_GAME_OVER) && !trip_game, g_cam_px); /* the hazard strip is the arena's floor; Gum Trip has its own */
            /* arcade only: elements kill, so they must be seen (worst scanline with them is checked in tests/host/test_sprite_budget.c) */
            arcade_elems_step(view.state == FLOW_PLAYING && view.game && view.game->mode == GAME_MODE_ARCADE ? view.game : 0);
            arcade_bonus_step(view.state == FLOW_PLAYING && view.game && view.game->mode == GAME_MODE_ARCADE && view.game->arc.state == ARC_BONUS ? view.game : 0);
            island_step(view.state == FLOW_PLAYING && !trip, g_cam_px); /* arena islands are not drawn in Gum Trip */
            /* the course (islands, kill strips, pickups) stays through Game Over like the planes and the hazard anim: all leave at the title */
            island_trip_step(trip_game ? &view.game->trip_gen : 0, trip_game ? view.game->trip.px : 0, trip_game && game_trip_ready(view.game));
            trip_strip_step(trip_game ? &view.game->trip_gen : 0, trip_game ? view.game->trip.px : 0, trip_game && game_trip_ready(view.game));
            trip_pickup_step(trip_game ? &view.game->trip_gen : 0, trip_game ? view.game->trip.px : 0, trip_game ? view.game->trip.steps : 0, trip_game && game_trip_ready(view.game));
            /* Arena: the bubble is always full size (no gum value, no pop); Gum Trip: its gum meter. */
            u8 arena = view.state == FLOW_PLAYING && view.game && (view.game->mode == GAME_MODE_ARENA || view.game->mode == GAME_MODE_ARCADE);
            gum_step(arena || (trip && game_trip_ready(view.game)), trip ? view.game->trip.gum : GUM_MAX, (trip || arena) ? view.game->frame : 0, g_gum_pose.drawn, g_gum_pose.frame, g_gum_pose.flip, g_gum_pose.cx, g_gum_pose.top);
            {   /* the splash starts from the same crossing that plays the splosh sound; it keeps running through Game Over */
                const SoundEvents *se = sound_events();
                splash_update(splash_enabled((view.state == FLOW_PLAYING || view.state == FLOW_GAME_OVER) && view.game, trip_game), se->n_splosh > 0, view.game ? view.game->hazard_kind : 0, se->splosh_x, g_cam_px);
            }
            logo_step(view.state == FLOW_ATTRACT_TITLE);
            title_soot_step(view.state == FLOW_ATTRACT_TITLE);
            hazard_trip_anim(trip_game);
            bg_trip_planes(trip_game); /* Gum Trip drops the far and near background planes; arena and title show them */
        }
        bg_update(g_cam_unwrapped); /* the planes loop on the unwrapped camera (arena and Gum Trip alike) */
        gfx_commit();
        g_frame_counter++;
        gfx_wait_vblank(); /* the vblank callback flushes the queue: the only VRAM and palette writes of the frame */
        if (g_bram_unsaved && bios_user_mode == 1) {
            g_bram_unsaved = 0;
            return; /* to the BIOS: SYSTEM_RETURN, backup RAM save, USER again (see above) */
        }
    }
}
