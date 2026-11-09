/*
 * main.c - Neo Geo glue for Roofline: vblank loop, joypad, backup RAM, fix-layer drawing.
 * All game logic lives in src/core (host tested). Nothing here decides gameplay.
 */
#include <ngdevkit/neogeo.h>
#include <ngdevkit/ng-fix.h>
#include <ngdevkit/ng-video.h>
#include <ngdevkit/bios-ram.h>
#include "core/flow.h"
#include "core/obstacle_view.h"
#include "core/obj_pool.h"
#include "core/laser_view.h"
#include "core/hero_view.h"
#include "gfx.h"
#include "sprite_slots.h"
#include "vram_layout.h"
#include "bg.h"
#include "sound.h"

/* Palette 0 = white text, palette 1 = yellow (highlight). Entry 0 of a palette is transparent; the backdrop is the last palette RAM entry (bg.c). */
#define PAL_TEXT 0
#define PAL_HIGH 1

/* Hiscore image in battery backed RAM (.bss.bram at 0x100000). */
u8 _backup_ram g_hiscore_image[HISCORE_IMAGE_SIZE];

/* RAM sentinel for the headless test: counts main loop frames. Address in the ELF map. */
volatile u32 g_frame_counter;

/* RAM sentinel for the headless reachability test (make test-reach): counts backup RAM image writes. */
volatile u32 g_hiscore_saves;

static Flow g_flow;

/*
 * Hero sprite. Tile bases and palette slots come from vram_layout.h, sprite slots from
 * sprite_slots.h (the hero draws in front of the city background and the obstacles). A hero frame is 3 tile columns = 3 hardware sprites: the first has
 * position and height, the other two are sticky (SCB3 bit 6) and follow it 16 px apart.
 * Register sequence copied from ngdevkit-examples 03-sprite-animation/main.c:54-84.
 * Y register = 496 - screen top (wraps at 512), X register = screen x.
 */
#define HERO_COLUMNS 3
#define HERO_BOX_DX 11 /* box left = HERO_X - (hit box inset 4 + art pad_left 7) */
#define HERO_RUN_TICKS 4 /* game frames per run frame */

/* Test sentinels (tests/mame/hit_check.lua): hero animation and frame index last written to the sprite registers, 0xFFFF while hidden. */
volatile u16 g_hero_shown_frame;
volatile u16 g_hero_shown_anim;

static void hero_load_palettes(void) {
    for (int p = 0; p < HERO_PALETTE_COUNT; p++)
        for (int i = 0; i < 16; i++)
            gfx_pal((HERO_PAL_SLOT + p) * 16 + i, hero_palettes[p][i]);
}

static void hero_hide(void) {
    gfx_word(ADDR_SCB3 + HERO_SPRITE, 0); /* height 0 hides the sprite and the sticky ones after it */
    g_hero_shown_frame = 0xFFFF;
    g_hero_shown_anim = 0xFFFF;
}

static u8 hero_pick_frame(const Game *g, HeroLook look) {
    u8 anim;
    if (look == HV_LOOK_HIT) anim = HERO_ANIM_HIT;
    else {
        LaserPose pose = laser_view_pose(g);
        int recoil = pose == LV_POSE_RECOIL, shoot = pose == LV_POSE_SHOOT;
        if (g->hero_h > 0) anim = recoil ? HERO_ANIM_JUMP_RECOIL : HERO_ANIM_JUMP;
        else if (g->ducking) anim = recoil ? HERO_ANIM_DUCK_RECOIL : HERO_ANIM_DUCK;
        else anim = recoil ? HERO_ANIM_RUN_RECOIL : shoot ? HERO_ANIM_RUN_SHOOT : HERO_ANIM_RUN;
    }
    g_hero_shown_anim = anim;
    const HeroAnim *a = &hero_anims[anim];
    return (u8)(a->first_frame + (g->frame / HERO_RUN_TICKS) % a->frame_count);
}

static void hero_show(const Game *g) {
    int visible;
    HeroLook look = hero_view_look(g, &visible);
    if (!visible) { hero_hide(); return; }
    u8 frame = hero_pick_frame(g, look);
    g_hero_shown_frame = frame;
    const HeroFrame *f = &hero_frames[frame];
    int hx, hy, hw, hh;
    game_hero_box(g, &hx, &hy, &hw, &hh);
    int top = hy + hh - f->tiles_h * 16; /* feet = bottom of the hit box */
    int left = hx - HERO_BOX_DX;
    u16 attr = (u16)((HERO_PAL_SLOT + f->palette) << 8);
    gfx_sprite_block(HERO_SPRITE, HERO_COLUMNS, f->tiles_h, &hero_tile_index[f->tile_offset], HERO_TILE_BASE, attr, left, top);
}

/*
 * Obstacle sprites. Tiles follow the hero tiles in the C-ROM (Makefile cat order), palettes
 * follow the hero palettes. Obstacles draw through the object pool (src/core/obj_pool.h): each active
 * on-screen obstacle holds one pool object, whose sprite run (POOL_COLS hardware sprites from POOL_SPRITE_BASE,
 * sprite_slots.h) it keeps until it leaves. The game logic (src/core/game.c) still owns the obstacle
 * positions in 8.8; pool_sync_obstacles copies them each frame (pool anchor for an obstacle: x = hit box
 * left, y = hit box bottom). Same register sequence as the hero; the animation index of an object is its type.
 */
_Static_assert(BG_SPRITE_END <= POOL_SPRITE_BASE, "background sprites overlap the object pool");
_Static_assert(POOL_SPRITE_COUNT == POOL_SPRITES, "pool sprite range size");
_Static_assert(POOL_SPRITE_BASE + POOL_SPRITE_COUNT <= HERO_SPRITE, "object pool sprites overlap hero");
_Static_assert(OBS_MAX_COLUMNS <= POOL_COLS, "obstacle frame wider than a pool sprite run");
_Static_assert(MAX_OBSTACLES <= POOL_MAX, "obstacles do not fit the pool");
_Static_assert(OBS_ANIM_VENT == OB_VENT && OBS_ANIM_CABLE == OB_CABLE &&
               OBS_ANIM_DRONE == OB_DRONE && OBS_ANIM_BOT == OB_BOT, "obstacle sheet order");

static void obs_load_palettes(void) {
    for (int p = 0; p < OBS_PALETTE_COUNT; p++)
        for (int i = 0; i < 16; i++)
            gfx_pal((OBS_PAL_SLOT + p) * 16 + i, obs_palettes[p][i]);
}

/* Height 0 and not sticky hides a sprite on its own. */
static void obs_hide_slot(int slot) {
    gfx_word(ADDR_SCB3 + slot, 0);
}

static ObjPool g_pool;
static u8 g_obs_obj[MAX_OBSTACLES]; /* pool index of obstacle i, POOL_NONE when it has none */
/* Test hook: tests/mame/vblank_check.lua sets it to fill the pool with drifting objects while PLAYING (max object
 * count frame-time check). Nothing in the game sets it. */
volatile u8 g_pool_stress;
/* Sentinels for the headless test (addresses from the ELF map): frames the pool view drew at least one object, live
 * objects drawn in the last frame. */
volatile u16 g_pool_frames;
volatile u8 g_pool_live;
#define POOL_F_STRESS 0x02

/* Animation frame whose SCB1 tile strips object i's run holds, + 1 (0: unknown). Strips are not deduped by the
 * queue and cost most of the vblank budget (vq_cost), so a moving object only requeues them on a frame change. */
static u8 g_pool_drawn[POOL_MAX];
_Static_assert(OBS_FRAME_COUNT < 255, "pool frame cache holds frame index + 1 in a byte");

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

static void pool_reset(void) {
    obj_pool_init(&g_pool, POOL_SPRITE_BASE);
    for (int i = 0; i < MAX_OBSTACLES; i++) g_obs_obj[i] = POOL_NONE;
}

static void pool_free_all(void) {
    for (u8 i = 0; i < POOL_MAX; i++) obj_pool_free(&g_pool, i);
    for (int i = 0; i < MAX_OBSTACLES; i++) g_obs_obj[i] = POOL_NONE;
}

static void pool_sync_obstacles(const Game *g) {
    for (int i = 0; i < MAX_OBSTACLES; i++) {
        const Obstacle *o = &g->obs[i];
        u8 k = g_obs_obj[i];
        if (!o->active || (o->x >> 8) >= SCREEN_W || o->type > OB_BOT) {
            if (k != POOL_NONE) { obj_pool_free(&g_pool, k); g_obs_obj[i] = POOL_NONE; }
            continue;
        }
        if (k == POOL_NONE) {
            k = obj_pool_alloc(&g_pool, o->type, 0, 0, 0, 0);
            if (k == POOL_NONE) continue; /* pool full: not drawn this frame */
            g_obs_obj[i] = k;
        }
        PoolObj *p = &g_pool.obj[k];
        if (p->type != o->type) { p->type = o->type; p->anim = 0; p->anim_tick = 0; }
        p->x = o->x * 256;                     /* 8.8 -> 16.16 */
        p->y = obj_pool_fp((int16_t)(o->y + o->h));
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

static void pool_show(void) {
    u16 scb3[POOL_MAX];
    u32 m = obj_pool_take_hidden(&g_pool);
    for (u8 i = 0; m; i++, m >>= 1) if (m & 1) pool_hide_run(i);
    PoolObj *p = g_pool.obj;
    for (u8 i = 0; i < POOL_MAX; i++, p++) {
        scb3[i] = 0;
        if (!(p->flags & POOL_F_LIVE)) continue;
        const ObsAnim *a = &obs_anims[p->type];
        obj_pool_anim(p, obstacle_view_ticks(p->type), a->frame_count);
        u8 fi = (u8)(a->first_frame + p->anim);
        const ObsFrame *f = &obs_frames[fi];
        int x = obj_pool_px(p->x);
        u16 slot = obj_pool_sprite(&g_pool, i);
        if (x >= SCREEN_W) { pool_hide_run(i); continue; }
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
        g_pool_scb4[i] = gfx_scb4_word(x - f->pad_left);
    }
    gfx_scb_run(ADDR_SCB3 + POOL_SPRITE_BASE, POOL_COLS, scb3, POOL_MAX);
    gfx_scb_run(ADDR_SCB4 + POOL_SPRITE_BASE, POOL_COLS, g_pool_scb4, POOL_MAX);
    g_pool_live = g_pool.live;
    if (g_pool.live) g_pool_frames++;
}

/*
 * Laser sprites (slots in sprite_slots.h, in front of the hero): one beam per live bolt, the kill
 * flash, and the heat bar. Beam and flash art are frames of the hero set (palette HERO_PAL_SLOT +
 * frame palette); the bar is the "heat" set. Positions and frames come from core/laser_view.c.
 * The heat bar is sprites because the fix layer font is fixed (no partial or coloured cells);
 * only the label HEAT is on the fix layer (draw()).
 */
#define LASER_BEAM_COLUMNS 2
#define HEAT_BAR_X 64
#define HEAT_BAR_Y 40
_Static_assert(LASER_BEAM_SPRITE >= HERO_SPRITE + HERO_SPRITE_COUNT, "laser sprites overlap hero");
_Static_assert(LASER_SPRITE_END <= 381, "laser sprite range");
_Static_assert(MAX_BOLTS * LASER_BEAM_COLUMNS <= LASER_BEAM_SLOTS, "beam sprite slots");
_Static_assert(LV_BAR_PAIRS <= LASER_BAR_SLOTS, "heat bar sprite slots");
_Static_assert(HEAT_FRAME_COUNT >= LV_BAR_CELLS, "heat bar frames");

static void heat_load_palettes(void) {
    for (int p = 0; p < HEAT_PALETTE_COUNT; p++)
        for (int i = 0; i < 16; i++)
            gfx_pal((HEAT_PAL_SLOT + p) * 16 + i, heat_palettes[p][i]);
}

/* Heat bar state last sent by laser_show: (filled cells << 1) | 1 when shown, 0 when hidden; BAR_UNKNOWN after
 * laser_hide_all (hidden sprites, so any state redraws). */
#define BAR_UNKNOWN 0xFF
static u8 g_bar_drawn = BAR_UNKNOWN;

static void laser_hide_all(void) {
    g_bar_drawn = BAR_UNKNOWN;
    for (int i = 0; i < LASER_SPRITE_END - LASER_BEAM_SPRITE; i++) obs_hide_slot(LASER_BEAM_SPRITE + i);
}

/* One frame of `cols` columns at `slot`: first column has position and height, the rest are sticky. */
static void laser_put(int slot, int cols, int rows, int left, int top, u16 attr, const u16 *tiles, int tile_base) {
    gfx_sprite_block((u16)slot, (u8)cols, (u8)rows, tiles, (u16)tile_base, attr, left, top);
}

static void laser_show(const Game *g) {
    for (int i = 0; i < MAX_BOLTS; i++) {
        int slot = LASER_BEAM_SPRITE + i * LASER_BEAM_COLUMNS, x, y;
        const HeroFrame *f = &hero_frames[hero_anims[HERO_ANIM_LASER].first_frame];
        if (laser_view_beam(g, i, &x, &y)) {
            laser_put(slot, f->tiles_w, f->tiles_h, x - f->pad_left, y - f->pad_top,
                      (u16)((HERO_PAL_SLOT + f->palette) << 8), &hero_tile_index[f->tile_offset], HERO_TILE_BASE);
            for (int c = f->tiles_w; c < LASER_BEAM_COLUMNS; c++) obs_hide_slot(slot + c);
        } else {
            for (int c = 0; c < LASER_BEAM_COLUMNS; c++) obs_hide_slot(slot + c);
        }
    }
    int cx, cy, fr;
    if (laser_view_flash(g, &cx, &cy, &fr)) {
        const HeroFrame *f = &hero_frames[hero_anims[HERO_ANIM_HIT_FLASH].first_frame + fr];
        laser_put(LASER_FLASH_SPRITE, f->tiles_w, f->tiles_h, cx - f->src_w / 2 - f->pad_left,
                  cy - f->src_h / 2 - f->pad_top, (u16)((HERO_PAL_SLOT + f->palette) << 8),
                  &hero_tile_index[f->tile_offset], HERO_TILE_BASE);
    } else {
        obs_hide_slot(LASER_FLASH_SPRITE);
        obs_hide_slot(LASER_FLASH_SPRITE + 1);
    }
    /* The bar only changes with its filled cell count or the blink phase: redraw its LV_BAR_PAIRS sprites only then. */
    u8 bar = laser_view_bar_visible(g) ? (u8)((laser_view_cells(g->heat) << 1) | 1) : 0;
    if (bar == g_bar_drawn) return;
    g_bar_drawn = bar;
    for (int p = 0; p < LV_BAR_PAIRS; p++) {
        int slot = LASER_BAR_SPRITE + p;
        if (!bar) { obs_hide_slot(slot); continue; }
        const HeatFrame *f = &heat_frames[heat_anims[HEAT_ANIM_BAR].first_frame + laser_view_bar_frame(g, p)];
        laser_put(slot, 1, f->tiles_h, HEAT_BAR_X + p * 16 - f->pad_left, HEAT_BAR_Y - f->pad_top,
                  (u16)((HEAT_PAL_SLOT + f->palette) << 8), &heat_tile_index[f->tile_offset], HEAT_TILE_BASE);
    }
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

static void hero_and_mode(const FlowView *v) {
    if (v->state == FLOW_PLAYING && v->game) {
        bios_user_mode = 2;
        hero_show(v->game);
        pool_sync_obstacles(v->game);
        if (g_pool_stress) pool_stress();
        pool_show();
        laser_show(v->game);
    } else {
        /* BIOS_USER_MODE 2 = game in progress: play, game over, name entry and the save
         * reminder all belong to the game; 1 only once attract begins. Bug fixed here: mode 1
         * was set on entering GAME_OVER, so with a credit left UniBIOS treated the game as in
         * attract, saw the refused start and stopped calling the VBlank callback; game_loop
         * waited for vblank forever (frozen last frame, a coin woke it). An accepted start
         * keeps mode 2 until flow_step sees it. Guarded by make test-unibios (two coins). */
        if (v->state > FLOW_ATTRACT_DEMO || g_start_pending) bios_user_mode = 2;
        else bios_user_mode = 1;
        hero_hide();
        if (g_pool.live) pool_free_all();
        pool_show(); /* hides the freed runs once */
        laser_hide_all();
    }
}

static const char *const STATE_NAME[] = {
    "TITLE", "HIGH SCORES", "DEMO", "PLAYING", "GAME OVER", "NAME ENTRY", "SAVE REMINDER"
};

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
        text(2, 2, PAL_TEXT, "ROOFLINE");
        text(2, 3, PAL_TEXT, STATE_NAME[v->state]);
        /* pad so a shorter name overwrites a longer one */
        text(2 + (u8)0, 4, PAL_TEXT, "              ");
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
        if (v->game && (!g_hud_game || v->game->score != g_hud_score || v->game->lives != g_hud_lives)) {
            g_hud_game = 1;
            g_hud_score = v->game->score;
            g_hud_lives = v->game->lives;
            text(2, 5, PAL_TEXT, "SCORE");
            draw_number(8, 5, PAL_TEXT, v->game->score, 8);
            text(2, 6, PAL_TEXT, "LIVES");
            draw_number(8, 6, PAL_TEXT, v->game->lives, 2);
            text(2, 7, PAL_TEXT, "HEAT");
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
 * Roofline overrides rom_game and rom_title (link-time hooks in ngdevkit.ld): the first
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
    /* Palette bank 1 for the fix layer: set both text palettes. */
    gfx_pal(0, 0x8000); gfx_pal(1, 0x0fff); gfx_pal(2, 0x0555);
    gfx_pal(16, 0x8000); gfx_pal(17, 0x0ff0); gfx_pal(18, 0x0550);
    hero_load_palettes();
    obs_load_palettes();
    heat_load_palettes();
    bg_load_palettes();
    bg_init();
    hero_hide();
    pool_hide_all(); /* the hardware state is unknown; live objects redraw next frame */
    laser_hide_all();
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
        bg_update(view.game ? view.game->distance : 0, g_frame_counter);
        gfx_commit();
        g_frame_counter++;
        gfx_wait_vblank(); /* the vblank callback flushes the queue: the only VRAM and palette writes of the frame */
        if (g_bram_unsaved && bios_user_mode == 1) {
            g_bram_unsaved = 0;
            return; /* to the BIOS: SYSTEM_RETURN, backup RAM save, USER again (see above) */
        }
    }
}
