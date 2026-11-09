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
#include "core/laser_view.h"
#include "core/hero_view.h"
#include "gfx.h"
#include "sprite_slots.h"
#include "vram_layout.h"
#include "bg.h"

/* Palette 0 = white text, palette 1 = yellow (highlight). Entry 0 of a palette is transparent; the backdrop is the last palette RAM entry (bg.c). */
#define PAL_TEXT 0
#define PAL_HIGH 1

/* Hiscore image in battery backed RAM (.bss.bram at 0x100000). */
u8 _backup_ram g_hiscore_image[HISCORE_IMAGE_SIZE];

/* RAM sentinel for the headless test: counts main loop frames. Address in the ELF map. */
volatile u32 g_frame_counter;

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
 * follow the hero palettes, sprite slots start at OBSTACLE_SPRITE_BASE (sprite_slots.h). Each obstacle in the game pool
 * owns OBS_MAX_COLUMNS consecutive hardware sprites, so slot = index, never reused for another
 * object. Same register sequence as the hero; the animation index of an obstacle is its type.
 */
#define OBS_SPRITE OBSTACLE_SPRITE_BASE
_Static_assert(BG_SPRITE_END <= OBSTACLE_SPRITE_BASE, "background sprites overlap obstacles");
_Static_assert(OBSTACLE_SPRITE_BASE + OBSTACLE_SPRITE_COUNT <= HERO_SPRITE, "obstacle sprites overlap hero");
_Static_assert(HERO_COLUMNS <= HERO_SPRITE_COUNT && HERO_SPRITE + HERO_SPRITE_COUNT <= 381, "hero sprite range");
_Static_assert(MAX_OBSTACLES * OBS_MAX_COLUMNS <= OBSTACLE_SPRITE_COUNT, "obstacle sprite slots");
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

static void obs_hide(int i) {
    for (int c = 0; c < OBS_MAX_COLUMNS; c++) obs_hide_slot(OBS_SPRITE + i * OBS_MAX_COLUMNS + c);
}

static void obs_hide_all(void) {
    for (int i = 0; i < MAX_OBSTACLES; i++) obs_hide(i);
}

static void obs_show(const Game *g, int i) {
    const Obstacle *o = &g->obs[i];
    int x = o->x >> 8;
    if (!o->active || x >= SCREEN_W || o->type > OB_BOT) { obs_hide(i); return; }
    const ObsAnim *a = &obs_anims[o->type];
    const ObsFrame *f = &obs_frames[a->first_frame +
        obstacle_view_frame(o->type, g->frame, a->frame_count)];
    int slot = OBS_SPRITE + i * OBS_MAX_COLUMNS;
    int top = o->y + o->h - f->tiles_h * 16; /* art bottom = hit box bottom */
    int left = x - f->pad_left;
    u16 attr = (u16)((OBS_PAL_SLOT + f->palette) << 8);
    gfx_sprite_block(slot, f->tiles_w, f->tiles_h, &obs_tile_index[f->tile_offset], OBS_TILE_BASE, attr, left, top);
    for (int c = f->tiles_w; c < OBS_MAX_COLUMNS; c++) obs_hide_slot(slot + c);
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

static void laser_hide_all(void) {
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
    for (int p = 0; p < LV_BAR_PAIRS; p++) {
        int slot = LASER_BAR_SPRITE + p;
        if (!laser_view_bar_visible(g)) { obs_hide_slot(slot); continue; }
        const HeatFrame *f = &heat_frames[heat_anims[HEAT_ANIM_BAR].first_frame + laser_view_bar_frame(g, p)];
        laser_put(slot, 1, f->tiles_h, HEAT_BAR_X + p * 16 - f->pad_left, HEAT_BAR_Y - f->pad_top,
                  (u16)((HEAT_PAL_SLOT + f->palette) << 8), &heat_tile_index[f->tile_offset], HEAT_TILE_BASE);
    }
}

/* BIOS_USER_MODE: 1 attract, 2 game in progress (coins then only add credits). */
static void hero_and_mode(const FlowView *v) {
    if (v->state == FLOW_PLAYING && v->game) {
        bios_user_mode = 2;
        hero_show(v->game);
        for (int i = 0; i < MAX_OBSTACLES; i++) obs_show(v->game, i);
        laser_show(v->game);
    } else {
        bios_user_mode = 1;
        hero_hide();
        obs_hide_all();
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
static void put_number(char *out, u32 v, int width) {
    int i;
    for (i = width - 1; i >= 0; i--) {
        out[i] = (char)('0' + v % 10);
        v /= 10;
        if (v == 0) { while (--i >= 0) out[i] = ' '; break; }
    }
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

static void draw(const FlowView *v) {
    char buf[3];
    if ((int)v->state != g_draw_state) {
        gfx_cls();
        g_draw_state = (int)v->state;
    }
    text(2, 2, PAL_TEXT, "ROOFLINE");
    text(2, 3, PAL_TEXT, STATE_NAME[v->state]);
    /* pad so a shorter name overwrites a longer one */
    text(2 + (u8)0, 4, PAL_TEXT, "              ");
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
        if (v->game) {
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

static void game_loop(void) __attribute__((noreturn));

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
    obs_hide_all();
    laser_hide_all();
    g_draw_state = -1;
    gfx_commit();
    gfx_drain(); /* init is outside the per-frame budget: it blocks, one flush per vblank, until everything is written */
}

static void resume_game_loop(void) __attribute__((noreturn));
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
    if (g_boot_magic == BOOT_MAGIC) resume_game_loop();
    rom_game_default();
}

void rom_title(void) {
    if (g_boot_magic == BOOT_MAGIC) resume_game_loop();
    rom_title_default();
}

int main(void) {
    video_init();
    flow_init(&g_flow, g_hiscore_image, HISCORE_IMAGE_SIZE);
    g_boot_magic = BOOT_MAGIC;
    game_loop();
}

static void game_loop(void) {
    FlowView view;
    for (;;) {
        u8 start = (bios_statchange & CNT_START1) ? 1 : 0;
        flow_step(&g_flow, read_input(), start, g_frame_counter);
        if (g_flow.dirty) {
            hiscore_serialise(&g_flow.table, g_hiscore_image, HISCORE_IMAGE_SIZE);
            g_flow.dirty = 0;
        }
        flow_view(&g_flow, &view);
        draw(&view);
        hero_and_mode(&view);
        bg_update(view.game ? view.game->distance : 0, g_frame_counter);
        gfx_commit();
        g_frame_counter++;
        gfx_wait_vblank(); /* the vblank callback flushes the queue: the only VRAM and palette writes of the frame */
    }
}
