/*
 * game.h - hardware independent game state and per-frame step for Bubblegum Brawl.
 * Portable C99. Fixed point only. No malloc, no globals. The flow calls game_reset(seed) at start
 * press and game_step_arena(&g, input) once per frame, then the main loop draws from the public state.
 *
 * Coordinates: screen origin top-left, 320x224 (flier world 320x180, src/core/stage.h).
 */
#ifndef BRAWL_GAME_H
#define BRAWL_GAME_H

#include <stdint.h>
#include <stddef.h>
#include "tuning.h"
#include "rng.h"
#include "flier.h"
#include "ai.h"
#include "stage.h"

/* Input bits, active when set. Buttons A..D map to the Neo Geo A, B, C, D buttons. */
#define IN_A 0x01u /* flap (press); name entry: accept */
#define IN_B 0x02u /* name entry: back; unused in play */
#define IN_C 0x04u /* unused in play */
#define IN_D 0x08u /* unused in play */

/* Object pool animation index = row of the obstacle sheet (assets/obstacles). The sheet art draws the arena
 * platforms (OB_VENT) and the pool stress test (main.c). */
typedef enum {
    OB_VENT = 0,
    OB_CABLE,
    OB_DRONE,
    OB_BOT
} ObstacleType;

typedef struct {
    Rng rng;
    uint32_t frame;      /* frames since reset */
    uint32_t distance;   /* 8.8 pixels travelled */
    uint32_t score;      /* total score: stomps, drowned and defeated computer fliers, match bonuses */
    uint8_t over;        /* 1 when the player flier is DROWNED or GONE */

    /* Arena slice: the flier replaces the runner hero in play. flier_steps counts flier_step calls (test sentinel). */
    Flier flier;
    uint32_t flier_steps;
    uint32_t flaps;      /* flap press edges while the flier lives (sound event source) */

    /* Computer fliers (src/core/ai.c). cpu[i] is live while state < FLIER_DROWNED; slots at or above cpu_count stay GONE.
     * Sentinels for tests: stomps, matches_won, cpu_alive, and the per-AI think counters. */
    Flier cpu[STAGE_SPAWN_COUNT];
    Ai ai[STAGE_SPAWN_COUNT];
    uint8_t cpu_count;   /* fliers of the current match */
    uint8_t cpu_alive;   /* of those, not yet drowned or gone */
    uint32_t stomps;     /* balloons popped by stomps, any flier */
    uint32_t matches_won;
    uint32_t bounces;    /* body-contact reflects (test sentinel) */
} Game;

void game_reset(Game *g, uint32_t seed);
/* Arena step (used by the flow in play and demo): A flaps, left/right steer (nameentry.h bits). The run ends when the
 * flier is DROWNED or GONE. Score is survival time (distance advances SPEED_BASE per frame while alive). */
void game_step_arena(Game *g, uint8_t input);

#endif
