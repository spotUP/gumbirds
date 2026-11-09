/*
 * game.h - hardware independent game state and per-frame step for Roofline.
 * Portable C99. Fixed point only. No malloc, no globals. The Neo Geo main loop calls
 * game_reset(seed) at start press and game_step(&g, input) once per frame, then draws from
 * the public state.
 *
 * Coordinates: screen origin top-left, 320x224. The floor line is at y = GROUND_Y. Obstacle x
 * is the left edge in 8.8 fixed point; y, w, h are whole pixels. The hero hit box left edge is
 * the constant HERO_X.
 */
#ifndef ROOFLINE_GAME_H
#define ROOFLINE_GAME_H

#include <stdint.h>
#include <stddef.h>
#include "tuning.h"
#include "rng.h"

/* Input bits, active when set. Buttons A..D map to the Neo Geo A, B, C, D buttons. */
#define IN_A 0x01u /* fire laser (held) */
#define IN_B 0x02u /* jump (press) */
#define IN_C 0x04u /* duck (held) */
#define IN_D 0x08u /* unused */

typedef enum {
    OB_VENT = 0, /* floor vent, jump only, laser passes through */
    OB_CABLE,    /* high cable, duck only, laser passes through */
    OB_DRONE,    /* flying enemy at head height, shootable */
    OB_BOT       /* rooftop bot on the floor, shootable (or jump it) */
} ObstacleType;

typedef struct {
    int32_t x;    /* left edge, 8.8 */
    int16_t y;    /* top edge, pixels */
    int16_t w, h; /* pixels */
    uint8_t type; /* ObstacleType */
    uint8_t active;
    uint8_t near; /* came within NEAR_MISS_PX of the hero without touching */
    uint8_t tainted; /* hit or overlapped during invulnerability: no near-miss award */
} Obstacle;

typedef struct {
    int32_t x;    /* left edge, 8.8 */
    int16_t y;    /* top edge, pixels */
    uint8_t active;
} Bolt;

typedef struct {
    Rng rng;
    uint32_t frame;      /* frames since reset */
    uint32_t distance;   /* 8.8 pixels travelled */
    uint32_t score;      /* total score: distance points + bonuses */
    uint32_t bonus;      /* kill and near-miss points */
    int32_t speed;       /* scroll speed, 8.8 px per frame (derived, kept for drawing) */
    uint32_t spawn_acc;  /* 8.8 pixels since the last spawn */
    uint16_t next_gap;   /* pixels until the next spawn */

    int32_t hero_h;      /* height of the feet above the floor, 8.8 */
    int32_t hero_vy;     /* vertical speed, 8.8, positive is up */
    uint8_t ducking;
    uint8_t lives;
    uint8_t over;        /* 1 after the last life is lost */
    uint16_t invuln;     /* frames of invulnerability left */

    uint16_t heat;       /* 0..HEAT_MAX, drawn as the HUD bar */
    uint16_t lockout;    /* frames of dark light left; 0 means the laser works */
    uint16_t fire_cd;    /* frames until the next shot is allowed */
    uint8_t chain;       /* kills in the current chain minus one (0 for the first) */
    uint16_t chain_timer;/* frames left to extend the chain; 0 means no chain running */
    uint8_t prev_in;     /* previous input, for edge detection */

    Obstacle obs[MAX_OBSTACLES];
    Bolt bolts[MAX_BOLTS];

    /* Counters for tests and the HUD. */
    uint32_t kills, shots, overheats, hits, near_misses, spawned;

    /* Last kill, for the hit flash (src/core/laser_view.c): centre of the enemy, game frame. */
    int16_t kill_x, kill_y;
    uint32_t kill_frame;
} Game;

void game_reset(Game *g, uint32_t seed);
void game_step(Game *g, uint8_t input);

/* Current hero hit box (x, y top, w, h) for drawing and tests. */
void game_hero_box(const Game *g, int *x, int *y, int *w, int *h);
/* Score multiplier a kill would get right now (1..CHAIN_MAX). */
uint32_t game_multiplier(const Game *g);

#endif
