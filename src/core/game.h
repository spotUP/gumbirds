/*
 * game.h - hardware independent game state and per-frame step for Gumbirds.
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
#include "result.h"

#define HUMANS 2 /* human fighter slots: fighter index 0..HUMANS-1 are humans, computer fliers follow from HUMANS */

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

/* Background moods. GAME_MOOD_COUNT counts the moods game_next_mood rotates (moon, dusk, storm); src/bg.c draws all BG_MOOD_COUNT. */
enum { GAME_MOOD_MOON, GAME_MOOD_DUSK, GAME_MOOD_STORM, GAME_MOOD_COUNT, BG_MOOD_COUNT = GAME_MOOD_COUNT };

/* Play mode, chosen on the title (flow.h Flow.mode) and set by game_set_mode after game_reset. */
typedef enum {
    GAME_MODE_ARENA = 0,
    GAME_MODE_TRIP,
    GAME_MODE_ARCADE,
    GAME_MODE_PARTY /* title row and score table index only: game_set_mode plays it as arena, party_rule carries the rule */
} GameMode;

/* PARTY rules (Left/Right on the PARTY title row). PARTY_NONE = not a party game. Order = on-screen cycle order. */
enum { PARTY_NONE = 0, PARTY_ROUND, PARTY_ROOST, PARTY_HOT, PARTY_ROULETTE, PARTY_RULE_COUNT };
/* Rule of the Round twists, one per round (Game.twist). TWIST_NONE outside that rule. */
enum { TWIST_NONE = 0, TWIST_ONE_GUM, TWIST_CROWDED, TWIST_SLOW, TWIST_QUICK, TWIST_MIRROR, TWIST_WINDY, TWIST_COUNT };
/* Widest rule goal line in fix-layer columns (PARTY_GOAL_W); the title pads shorter lines to it. */
#define PARTY_GOAL_W 36
/* Rule name and goal line (the one table; owner-approved wording), twist name; "" for an unknown value. */
const char *game_party_name(uint8_t rule);
const char *game_party_goal(uint8_t rule);
const char *game_twist_name(uint8_t twist);

/* Round end (arena, real game): HOLD shows the banner for MATCH_END_FRAMES, PAN slides the camera back to the spawn with
 * the flier hidden, then the next round starts. Zero is RE_NONE so game_reset needs no init. */
enum RoundEnd { RE_NONE = 0, RE_HOLD, RE_PAN };
/* Round start: ROUND nn, then GO!, with fliers, hazards and input frozen. Zero is RS_NONE. */
enum RoundStart { RS_NONE = 0, RS_ROUND, RS_GO };

/* Roost Rule (PARTY_ROOST): one island is the roost; a fighter standing alone on it earns a tick every ROOST_TICK_FRAMES. */
#define ROOST_TICK_FRAMES 30
#define ROOST_TARGET_TICKS 20
#define ROOST_ROUND_FRAMES 2700
#define ROOST_FIGHTERS (HUMANS + STAGE_SPAWN_COUNT)
typedef struct {
    uint8_t idx;       /* stage platform index of the roost */
    uint8_t last;      /* roost of the previous round (0xFF = none): the next pick differs */
    uint8_t paying;    /* 1 only while a tick is being scored: every other score path is shut in this rule */
    uint16_t timer;    /* frames left in the round */
    uint16_t acc;      /* frames the current sole stander has stood */
    uint8_t sole;      /* fighter index standing alone (0xFF = nobody or shared) */
    uint8_t ticks[ROOST_FIGHTERS]; /* ticks per fighter this round (humans first, then computer fliers) */
    Flier mark;        /* AI target: rests where a standing flier's centre rests; not a fighter */
} Roost;

typedef struct {
    Rng rng;
    uint32_t frame;      /* frames since reset */
    uint32_t distance;   /* 8.8 pixels travelled */
    uint32_t score;      /* total score: stomps, drowned and defeated computer fliers, match bonuses */
    uint8_t mode;        /* GameMode; ARENA after game_reset (PARTY runs as ARENA) */
    uint8_t party_rule;  /* PARTY_NONE unless a PARTY game; set by flow after game_set_mode */
    uint8_t twist;       /* TWIST_* of the current round (PARTY_ROUND only); match_start draws it, never the same twice in a row */
    uint8_t mood;        /* background mood (GAME_MOOD_*) the screen shows; game_reset keeps it, game_next_mood changes it */
    uint8_t over;        /* 1 when the player flier is DROWNED or GONE */
    uint8_t players;     /* 1 or 2 humans in play (game_reset sets 1) */
    uint8_t input2;      /* player 2 input byte (main.c sets it like start_in); unused while players == 1 */
    uint8_t credits;     /* credits banked (main.c sets it from the BIOS each frame); the arcade continue needs one */
    uint8_t round_winner;/* Arena two-player round end: BannerWinner (P1, P2 or computer) for the round clear banner */
    uint8_t out_mask;    /* Arena two-player: bit h set once human h's death cost a life; cleared when it respawns (next round) */
    uint8_t last_popper; /* human index that last popped or defeated a computer flier: the stage-clear banner winner */

    /* Arena slice: the flier replaces the runner hero in play. flier_steps counts flier_step calls (test sentinel). */
    Flier hero[HUMANS];  /* the humans: hero[0] is player 1; hero[1] stays GONE while players == 1 */
    uint32_t flier_steps;
    uint32_t flaps[HUMANS];      /* flap press edges while the flier lives (sound event source) */

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
    uint8_t trip_splat;  /* 1 on the one frame the player dies at the floor (bottom rock or kill line), or a roof-killed body falls through the floor line; trip_splat_y is the feet line, the gum splat lands there */
    int16_t trip_splat_y;
    uint8_t trip_roof_fall; /* 1 from a roof death until the falling body reaches the floor line (its trip_splat frame) */
    uint8_t trip_hold;   /* hold steps taken at run start while the first screen chunks are built (one per game_step_trip), sentinel */
    ArcRun arc;          /* Arcade run (stage table, arcade.h), live in GAME_MODE_ARCADE; the arena step runs it */
    uint8_t cont_a[HUMANS];      /* A was held on the previous arena step (press edge for the arcade continue) */
    uint8_t start_in[HUMANS];    /* Start button changed to pressed this frame (main.c sets it from the BIOS); the arcade continue reads its edge */
    uint8_t cont_start[HUMANS];  /* start_in on the previous arena step */
    uint8_t credits_spent;       /* continues taken since main.c last paid them; main.c deducts one BIOS credit per count and clears it */
    ArcLives lives[HUMANS];      /* Arcade lives: a flier death loses one, none left ends the run (continue screen: game_step_arena) */
    ArcPump pump[STAGE_SPAWN_COUNT]; /* per computer flier: blow-up window that decides its stomp score */
    ArcElements elems;   /* Arcade stage elements of the current stage (arc_elements.h), built by match_start, stepped in play only */
    uint8_t bonus_caught[HUMANS]; /* bubbles each human popped in this bonus stage (bonus.caught is the team total) */
    ArcBonus bonus;      /* Arcade bonus stage, live while arc.state == ARC_BONUS after the banner hold */
    Result res;          /* Result screen after the bonus stage (result.h): active while it shows; arc.state stays ARC_BONUS */
    Roost roost;         /* Roost Rule state (party_rule == PARTY_ROOST), reset by match_start */
    Camera camera;       /* follows the living human fliers, stepped every game_step_arena; view reads game_camera_px */
} Game;

void game_reset(Game *g, uint32_t seed);
/* Next background mood: never the current one. Every match start calls it (arena match or round, arcade stage); the attract title
 * calls it when the demo did not (flow.c). With two moods it alternates; with more it draws the step from g->rng, so a fixed seed
 * fixes the order (two moods take no random value, so the match sequence of a seed is unchanged). */
void game_next_mood(Game *g);
/* Sets the hazard kind and the kill line of the player and every computer flier. The one entry for the kind: call it after
 * game_reset (which clears it to spikes) and whenever the drawn kind changes; rematches keep it. */
void game_set_hazard(Game *g, uint8_t kind);
/* Arcade: player 2 joins now (players = 2, fresh lives, spawn beside player 1). The drop-in parachute and the credit are later phases. */
void game_start_p2(Game *g);
int game_can_join_p2(const Game *g);
/* Lives, continues and per-human scores run: the arcade, and an Arena match with two humans (versus). */
int game_lives_mode(const Game *g);
/* Round clear banner winner (BannerWinner): the Arena versus winner, else the last popper. */
int game_banner_winner(const Game *g);
/* Real join (P2 Start mid play): parachute drop-in at the camera centre; 0 = refused. */
int game_join_p2(Game *g);
/* Arena step (used by the flow in play and demo): A flaps, left/right steer (nameentry.h bits). The run ends when the
 * flier is DROWNED or GONE. Score is survival time (distance advances SPEED_BASE per frame while alive). */
void game_step_arena(Game *g, uint8_t input);
/* Selects the mode right after game_reset. TRIP: Gum Trip start (flier mid-screen, two balloons, no wrap, gum at GUM_START);
 * ARENA keeps the arena spawn. */
void game_set_mode(Game *g, uint8_t mode);
/* The one per-frame entry the flow calls in play: dispatches on g->mode to game_step_arena or game_step_trip. */
void game_step(Game *g, uint8_t input);
/* Attract demo: builds a pending arena or arcade match (match_start: stage, elements, rivals) without stepping it and returns 1;
 * else 0. The demo has no ROUND banner freeze to carry that frame, so the flow steps the game from the next frame. */
int game_begin(Game *g);
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
/* Text of the round-start phase when it is not "ROUND nn": line 0 and 1 of the bonus stage announcement, or of a PARTY game
 * (rule or twist name, then goal line; the view draws ROUND nn above it), else 0. */
const char *game_round_start_text(const Game *g, int line);
/* How-to overlay line 0..2 of a PARTY rule (PARTY_*), shown before round 1; "" for an unknown rule or line. */
const char *game_party_howto(uint8_t rule, int line);
/* Roost Rule: the roost platform's world rectangle (left x, top y, width) for the marker; returns 0 when the rule is not running. */
int game_roost_rect(const Game *g, int *x, int *top, int *w);
/* BANNER_* flags for the round banner: 0 in the arena, BANNER_STAGE in arcade, BANNER_BONUS while the arcade bonus stage runs. */
int game_banner_flags(const Game *g);
/* 1 while the hazard strip animation must hold: a round start phase or a round end hold/pan. Arena only. */
int game_hazards_frozen(const Game *g);

#endif
