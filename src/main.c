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
#include "core/flier.h"
#include "core/flow.h"
#include "core/obstacle_view.h"
#include "core/obj_pool.h"
#include "core/flier_view.h"
#include "gfx.h"
#include "sprite_slots.h"
#include "vram_layout.h"
#include "bg.h"
#include "hazard.h"
#include "island.h"
#include "sound.h"

/* Palette 0 = white text, palette 1 = yellow (highlight). Entry 0 of a palette is transparent; the backdrop is the last palette RAM entry (bg.c). */
#define PAL_TEXT FIXFONT_PAL_WHITE
#define PAL_HIGH FIXFONT_PAL_GOLD

/* Hiscore image in battery backed RAM (.bss.bram at 0x100000). */
u8 _backup_ram g_hiscore_image[HISCORE_IMAGE_SIZE];

/* RAM sentinel for the headless test: counts main loop frames. Address in the ELF map. */
volatile u32 g_frame_counter;

/* RAM sentinel for the headless reachability test (make test-reach): counts backup RAM image writes. */
volatile u32 g_hiscore_saves;

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
#define SOOT_COLUMNS (SOOTLING_ART_W / 16) /* a Sootling frame is 2 tile columns wide, 3 tiles high (32 x 48) */
#define SOOT_BOX_DX SOOTLING_BOX_FIRST_COL /* sprite left = flier centre x - FLIER_HALF_W - 14: the 4 px hit box is art columns 14..17 */
#define SOOT_FLIP 1     /* SCB1 attribute bit 0: horizontal flip; a mirrored frame also draws its columns in reverse order (soot_strips) */
_Static_assert(SOOTLING_FRAME_COUNT == 2 * SOOTLING_FRAMES, "sheet: SOOTLING_FRAMES frames per palette (player, computer)");
_Static_assert(SOOT_COLUMNS == SOOTLING_MAX_COLUMNS && SOOT_COLUMNS * 16 == SOOTLING_ART_W, "Sootling frames are 2 columns wide");
_Static_assert(SOOTLING_BOX_LAST_COL - SOOTLING_BOX_FIRST_COL + 1 == 2 * FLIER_HALF_W, "art hit box columns must equal the 4 px gameplay box");
_Static_assert(SOOTLING_BOX_FIRST_COL + 2 * FLIER_HALF_W + SOOTLING_BOX_FIRST_COL == SOOTLING_ART_W, "art is centred on the hit box (a mirrored frame keeps the box)");
_Static_assert(SOOTLING_ART_H == 48 && SOOTLING_FEET_ROW == SOOTLING_ART_H - 1, "frame is 48 px tall with the feet on its last row");

/* Clip table and per frame ticks come from frames.json through the build (sootling_tables.h). */
static const u8 k_clip_first[SOOTLING_CLIP_COUNT] = SOOTLING_TABLE_CLIP_FIRST;
static const u8 k_clip_count[SOOTLING_CLIP_COUNT] = SOOTLING_TABLE_CLIP_COUNT;
static const u8 k_clip_loop[SOOTLING_CLIP_COUNT] = SOOTLING_TABLE_CLIP_LOOP;
static const u8 k_frame_ticks[SOOTLING_FRAMES] = SOOTLING_TABLE_FRAME_TICKS;
static const FlierClips k_clips = {
    k_clip_first, k_clip_count, k_clip_loop, k_frame_ticks,
    SOOTLING_CLIP_FLAP2, SOOTLING_CLIP_FLAP1, SOOTLING_CLIP_POP2, SOOTLING_CLIP_POP1, SOOTLING_CLIP_INFLATE,
    SOOTLING_CLIP_FALL, SOOTLING_CLIP_IDLE
};
static FlierAnim g_hero_anim;

/* Test sentinels (tests/mame/flier_check.lua): first tile number last written to the sprite registers for the player
 * and for a computer flier (0 until drawn, player 0 again while hidden), and computer draws so far. g_soot_range holds
 * {first Sootling tile, tile count, palette slot of the player palette, then those three sentinels in that order}. */
volatile u16 g_soot_range[6] = { SOOT_TILE_BASE, SOOTLING_TILE_COUNT, SOOT_PAL_SLOT, 0, 0, 0 };
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
volatile u8 g_cam_px;
/* Fix layer cell of the off screen marker last drawn (col 0xFF: none). */
static u8 g_edge_col = 0xFF, g_edge_row;

static void hero_hide(void) {
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

static void hero_show(const Game *g) {
    const Flier *fl = &g->flier;
    int feet = (int)((fl->y + flier_half_h(fl)) >> 16);
    if (fl->state == FLIER_GONE || feet > SCREEN_H) { hero_hide(); return; }
    int flip;
    const SootlingFrame *f = &sootling_frames[soot_frame(SOOTLING_ANIM_PLAYER, flier_anim_step(&g_hero_anim, fl, &k_clips, &flip))];
    const u16 *tiles = &sootling_tile_index[f->tile_offset];
    g_soot_player_tile = (u16)(SOOT_TILE_BASE + tiles[0]);
    int top = feet - f->tiles_h * 16;
    int sx = camera_screen_x((int)(fl->x >> 16) - FLIER_HALF_W - SOOT_BOX_DX, g_cam_px, SOOT_COLUMNS * 16);
    if (!camera_visible(sx, SOOT_COLUMNS * 16)) { hero_hide(); return; }
    int left = sx;
    u16 attr = (u16)(((SOOT_PAL_SLOT + f->palette) << 8) | (flip ? SOOT_FLIP : 0));
    soot_strips(HERO_SPRITE, f, tiles, flip, attr);
    gfx_sprite_place(HERO_SPRITE, SOOT_COLUMNS, f->tiles_h, left, top);
}

/*
 * Obstacle-sheet sprites. Tiles follow the logo tiles in the C-ROM (Makefile cat order), palettes follow the fix-layer
 * palettes. They draw through the object pool (src/core/obj_pool.h): each pool object holds a sprite run (POOL_COLS
 * hardware sprites from POOL_SPRITE_BASE, sprite_slots.h); the animation index of an object is its type. Live users:
 * the computer fliers (pool_sync_cpus) and the pool stress test hook. The arena platforms are the island sprites (src/island.c).
 */
_Static_assert(POOL_SPRITE_COUNT == POOL_SPRITES, "pool sprite range size");
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
        for (int i = 0; i < 16; i++)
            gfx_pal((ISLAND_PAL_SLOT + p) * 16 + i, island_palettes[p][i]);
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
_Static_assert(SOOT_COLUMNS <= POOL_COLS, "Sootling frames must fit a pool run");

/* Animation frame whose SCB1 tile strips object i's run holds, + 1 (0: unknown). Strips are not deduped by the
 * queue and cost most of the vblank budget (vq_cost), so a moving object only requeues them on a frame change. */
static u8 g_pool_drawn[POOL_MAX];
_Static_assert(OBS_FRAME_COUNT < 255 && SOOTLING_FRAME_COUNT < 127, "pool frame cache holds frame index + 1 (+ 128 mirrored) in a byte");

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

static void pool_reset(void) {
    for (int i = 0; i < STAGE_SPAWN_COUNT; i++) g_cpu_obj[i] = POOL_NONE;
    obj_pool_init(&g_pool, POOL_SPRITE_BASE);
}

static void pool_free_all(void) {
    for (int i = 0; i < STAGE_SPAWN_COUNT; i++) g_cpu_obj[i] = POOL_NONE;
    for (u8 i = 0; i < POOL_MAX; i++) obj_pool_free(&g_pool, i);
}

/* Computer fliers: one pool object each while on screen (anchor: centre x, feet y). type = sheet frame of the clip (flier_anim_step), flags POOL_F_FLIP when facing left. */
static FlierAnim g_cpu_anim[STAGE_SPAWN_COUNT];
static void pool_sync_cpus(const Game *g) {
    for (int i = 0; i < STAGE_SPAWN_COUNT; i++) {
        const Flier *c = &g->cpu[i];
        u8 k = g_cpu_obj[i];
        int feet = (int)((c->y + flier_half_h(c)) >> 16);
        if (i >= g->cpu_count || c->state >= FLIER_DROWNED || feet > SCREEN_H) {
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
        if (flip) p->flags |= POOL_F_FLIP; else p->flags &= (u8)~POOL_F_FLIP;
        p->x = c->x;
        p->y = (int32_t)(c->y + flier_half_h(c));
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
    u8 fi = soot_frame(SOOTLING_ANIM_CPU, p->type);
    const SootlingFrame *f = &sootling_frames[fi];
    int flip = (p->flags & POOL_F_FLIP) != 0;
    int x = camera_screen_x(obj_pool_px(p->x) - FLIER_HALF_W - SOOT_BOX_DX, g_cam_px, SOOT_COLUMNS * 16);
    u16 slot = obj_pool_sprite(&g_pool, i);
    if (!camera_visible(x, SOOT_COLUMNS * 16)) { pool_hide_run(i); return; }
    int top = obj_pool_px(p->y) - f->tiles_h * 16;
    const u16 *tiles = &sootling_tile_index[f->tile_offset];
    u8 key = (u8)(fi + 1 + (flip ? 128 : 0)); /* frame and mirror state the strips hold */
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

static void pool_show(void) {
    u16 scb3[POOL_MAX];
    u32 m = obj_pool_take_hidden(&g_pool);
    for (u8 i = 0; m; i++, m >>= 1) if (m & 1) pool_hide_run(i);
    PoolObj *p = g_pool.obj;
    for (u8 i = 0; i < POOL_MAX; i++, p++) {
        scb3[i] = 0;
        if (!(p->flags & POOL_F_LIVE)) continue;
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

/* BIOS_USER_MODE: 1 attract, 2 game in progress (coins then only add credits). */
static volatile u8 g_start_pending;
static u8 read_input(void);

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
static void edge_marker(const Game *g) {
    int dir = 0, row = 0;
    if (g) {
        const Flier *fl = &g->flier;
        int w = SOOT_COLUMNS * 16;
        int sx = camera_screen_x((int)(fl->x >> 16) - FLIER_HALF_W - SOOT_BOX_DX, g_cam_px, w);
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
        g_cam_px = (u8)game_camera_px(v->game);
        edge_marker(v->game);
        hero_show(v->game);
        pool_sync_cpus(v->game);
        if (g_pool_stress) pool_stress();
        pool_show();
    } else {
        /* BIOS_USER_MODE 2 = game in progress: play, game over, name entry and the save
         * reminder all belong to the game; 1 only once attract begins. Bug fixed here: mode 1
         * was set on entering GAME_OVER, so with a credit left UniBIOS treated the game as in
         * attract, saw the refused start and stopped calling the VBlank callback; game_loop
         * waited for vblank forever (frozen last frame, a coin woke it). An accepted start
         * keeps mode 2 until flow_step sees it. Guarded by make test-unibios (two coins). */
        if (v->state > FLOW_ATTRACT_DEMO || g_start_pending) bios_user_mode = 2;
        else bios_user_mode = 1;
        g_cam_px = 0;
        g_edge_col = 0xFF; /* draw() clears the fix layer with the state change */
        flier_anim_init(&g_hero_anim);
        hero_hide();
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

static void draw_table(const HiscoreTable *t, int highlight, u8 y0) {
    char line[HISCORE_NAME_LEN + 1];
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
static u32 g_hud_score;
static u32 g_hud_lives;

static void draw(const FlowView *v) {
    char buf[3];
    /* The header only changes with the state: send it after the clear. The fix shadow (vq_fix_put) keeps it, and a
     * hardware reset of the fix layer goes through video_init, which forces this branch (g_draw_state = -1). */
    if ((int)v->state != g_draw_state) {
        gfx_cls();
        g_draw_state = (int)v->state;
        g_hud_game = 0;
#ifdef GUMBIRDS_DEBUG_HEADER /* gmake DEBUG_HEADER=1; the normal build leaves the top rows to the HUD */
        text(2, 2, PAL_TEXT, "GUMBIRDS");
        text(2, 3, PAL_TEXT, STATE_NAME[v->state]);
        /* pad so a shorter name overwrites a longer one */
        text(2 + (u8)0, 4, PAL_TEXT, "              ");
#endif
    }
    switch (v->state) {
    case FLOW_ATTRACT_TITLE:
        gfx_center_text(13, PAL_TEXT, "PRESS START");
        break;
    case FLOW_ATTRACT_TABLE:
        draw_table(v->table, v->highlight, 8);
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
            text(2, 6, PAL_TEXT, "Balloons");
            draw_number(11, 6, PAL_TEXT, v->game->flier.balloons, 1);
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
        draw_table(v->table, v->highlight, 16);
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
 * backup RAM image is missing or invalid. Command 1 never comes (rom_eye_catcher_mode 0:
 * the BIOS draws the eye-catcher).
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
    gfx_cls();
    /* Fix layer palettes 0..FIX_PAL_COUNT-1 (generated with the font). */
    for (u8 s = 0; s < FIX_PAL_COUNT; s++)
        for (u8 i = 0; i < 16; i++) gfx_pal((u16)(s * 16 + i), fixfont_palettes[s][i]);
    soot_load_palettes();
    obs_load_palettes();
    island_load_palettes();
    bg_load_palettes();
    bg_init();
    hazard_init();
    hero_hide();
    pool_hide_all(); /* the hardware state is unknown; live objects redraw next frame */
    g_draw_state = -1;
    gfx_commit();
    gfx_drain(); /* init is outside the per-frame budget: it blocks, one flush per vblank, until everything is written */
}

static void resume_game_loop(void) {
    /* Same hardware prologue as the crt0 defaults, minus the C runtime init. */
    __asm__ volatile ("move.w #0x2700,%%sr" ::: "memory");
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
    flow_init(&g_flow, g_hiscore_image, HISCORE_IMAGE_SIZE);
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
        u8 start = g_start_pending; /* games start only through the BIOS PLAYER_START (credit taken) */
        g_start_pending = 0;
        flow_step(&g_flow, read_input(), start, g_frame_counter);
        if (g_flow.dirty) {
            hiscore_serialise(&g_flow.table, g_hiscore_image, HISCORE_IMAGE_SIZE);
            g_hiscore_saves++;
            g_flow.dirty = 0;
            g_bram_unsaved = 1;
        }
        flow_view(&g_flow, &view);
        sound_frame(&view);
        sound_tick();
        draw(&view);
        hero_and_mode(&view);
        hazard_step(view.state == FLOW_PLAYING || view.state == FLOW_GAME_OVER, g_cam_px);
        island_step(view.state == FLOW_PLAYING, g_cam_px);
        bg_update(g_cam_px); /* parallax planes follow the camera */
        gfx_commit();
        g_frame_counter++;
        gfx_wait_vblank(); /* the vblank callback flushes the queue: the only VRAM and palette writes of the frame */
        if (g_bram_unsaved && bios_user_mode == 1) {
            g_bram_unsaved = 0;
            return; /* to the BIOS: SYSTEM_RETURN, backup RAM save, USER again (see above) */
        }
    }
}
