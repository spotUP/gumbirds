/*
 * game.h - hardware independent game state and per-frame step for Bubblegum Brawl.
 * Portable C99. Fixed point only. No malloc, no globals. The flow calls game_reset(seed) at start
 * press and game_step_arena(&g, input) once per frame, then the main loop draws from the public state.
 *
 * Coordinates: screen origin top-left, 320x224 (arena 384x180 wrapping, arena.h; the screen shows it through the camera, camera.h).
 */
#ifndef BRAWL_GAME_H
#define BRAWL_GAME_H

#include <stdint.h>
#include <stddef.h>
#include "camera.h"
#include "tuning.h"
#include "rng.h"
#include "flier.h"
#include "ai.h"
#include "stage.h"
#include "trip.h"
#include "trip_gen.h"
#include "trip_hit.h"
#include "trip_rival.h"
#include "arcade.h"
#include "arc_elements.h"

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

/* Play mode, chosen on the title (flow.h Flow.mode) and set by game_set_mode after game_reset. */
typedef enum {
    GAME_MODE_ARENA = 0,
    GAME_MODE_TRIP,
    GAME_MODE_ARCADE
} GameMode;

/* Round end (arena, real game): HOLD shows the banner for MATCH_END_FRAMES, PAN slides the camera back to the spawn with
 * the flier hidden, then the next round starts. Zero is RE_NONE so game_reset needs no init. */
enum RoundEnd { RE_NONE = 0, RE_HOLD, RE_PAN };
/* Round start: ROUND nn, then GO!, with fliers, hazards and input frozen. Zero is RS_NONE. */
enum RoundStart { RS_NONE = 0, RS_ROUND, RS_GO };

typedef struct {
    Rng rng;
    uint32_t frame;      /* frames since reset */
    uint32_t distance;   /* 8.8 pixels travelled */
    uint32_t score;      /* total score: stomps, drowned and defeated computer fliers, match bonuses */
    uint8_t mode;        /* GameMode; ARENA after game_reset */
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
    uint8_t rounds;      /* 1 = real arena game: round end hold/pan and round start freeze run. flow start_game sets it; the demo and direct game_step_arena callers keep 0 (immediate rematch, no freeze) */
    uint8_t round_end;   /* RoundEnd */
    uint16_t round_timer;/* frames left in RE_HOLD */
    uint8_t round_start; /* RoundStart */
    uint16_t round_start_timer; /* frames spent in the current round start phase */
    uint8_t hazard_kind; /* hazard.h kind drawn in this play (game_set_hazard); selects every flier's kill line */
    uint32_t bounces;    /* body-contact reflects (test sentinel) */
    Trip trip;           /* Gum Trip state, live in GAME_MODE_TRIP (game_step_trip) */
    TripGen trip_gen;    /* Gum Trip course (chunk ring), seeded by game_set_mode, advanced by game_step_trip */
    TripRivals trip_rivals; /* Gum Trip rivals (trip_rival.h), seeded by game_set_mode, stepped by game_step_trip */
    uint8_t trip_events; /* TRIP_EV_* bits of the last game_step_trip frame (0 when none); sound and view read it */
    uint8_t trip_rival_events; /* TRIP_RIV_EV_* bits of the last game_step_trip frame (0 when none); sound and view read it */
    uint8_t trip_hold;   /* hold steps taken at run start while the first screen chunks are built (one per game_step_trip), sentinel */
    ArcRun arc;          /* Arcade run (stage table, arcade.h), live in GAME_MODE_ARCADE; the arena step runs it */
    uint8_t cont_a;      /* A was held on the previous arena step (press edge for the arcade continue) */
    ArcLives lives;      /* Arcade lives: a flier death loses one, none left ends the run (continue screen: game_step_arena) */
    ArcPump pump[STAGE_SPAWN_COUNT]; /* per computer flier: blow-up window that decides its stomp score */
    ArcElements elems;   /* Arcade stage elements of the current stage (arc_elements.h), built by match_start, stepped in play only */
    ArcBonus bonus;      /* Arcade bonus stage, live while arc.state == ARC_BONUS after the banner hold */
    Camera camera;       /* follows the living human fliers, stepped every game_step_arena; view reads game_camera_px */
} Game;

void game_reset(Game *g, uint32_t seed);
/* Sets the hazard kind and the kill line of the player and every computer flier. The one entry for the kind: call it after
 * game_reset (which clears it to spikes) and whenever the drawn kind changes; rematches keep it. */
void game_set_hazard(Game *g, uint8_t kind);
/* Arena step (used by the flow in play and demo): A flaps, left/right steer (nameentry.h bits). The run ends when the
 * flier is DROWNED or GONE. Score is survival time (distance advances SPEED_BASE per frame while alive). */
void game_step_arena(Game *g, uint8_t input);
/* Selects the mode right after game_reset. TRIP: Gum Trip start (flier mid-screen, two balloons, no wrap, gum at GUM_START);
 * ARENA keeps the arena spawn. */
void game_set_mode(Game *g, uint8_t mode);
/* The one per-frame entry the flow calls in play: dispatches on g->mode to game_step_arena or game_step_trip. */
void game_step(Game *g, uint8_t input);
/* Gum Trip step: A flaps, left/right steer. Order per frame: trip_hit_floor_y, flier_step (no wrap, island floor),
 * trip_step (scroll carry, clamp, gum), tripgen_advance (trip px), trip_collide (pickups, hazards, strips; bits in
 * trip_events); then distance, score and over are taken from the trip. */
void game_step_trip(Game *g, uint8_t input);
/* 1 once the course chunks cover the screen at the current trip distance. While 0, game_step_trip only builds one chunk
 * and returns (a hold of 2 steps at run start): no flier, scroll, collision or view read of chunks happens. */
int game_trip_ready(const Game *g);
/* Camera x in whole screen pixels, 0..383 (wrapped): screen x = world x - this (wrapped, see arena.h). */
int game_camera_px(const Game *g);
/* Camera x the player flier is placed with: game_camera_px in the arena (world x), 0 in Gum Trip (flier x is a screen x). */
int game_flier_cam_px(const Game *g);

/* 0 while the flier is hidden by the round end camera slide (RE_PAN of a real game), else 1. */
int game_flier_visible(const Game *g);
/* Round start phase (RoundStart) and the round number to show (matches_won + 1). */
int game_round_start_phase(const Game *g);
int game_round_number(const Game *g);
/* Text of the round-start phase when it is not "STAGE nn": line 0 and 1 of the bonus stage announcement, else 0. */
const char *game_round_start_text(const Game *g, int line);
/* BANNER_* flags for the round banner: 0 in the arena, BANNER_STAGE in arcade, BANNER_BONUS while the arcade bonus stage runs. */
int game_banner_flags(const Game *g);
/* 1 while the hazard strip animation must hold: a round start phase or a round end hold/pan. Arena only. */
int game_hazards_frozen(const Game *g);

#endif
