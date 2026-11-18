#ifndef GG_POPDROP_H
#define GG_POPDROP_H
#include <stdint.h>
#include "flier.h"
#include "gumgames.h"
#include "rng.h"

/* Gum Games event Pop Drop (pure logic), the free-fall design: the bird falls without end and the fall speeds up. Platforms (rock island, steel girder,
 * wooden plank) rush up from below, gum candy drifts up between them. The stick steers left / right. A platform hit = bounce, a stun of PD_STUN frames and
 * one caught gum lost; the third hit is the crash. Every PD_SHIELD_EVERY gums blow a shield bubble that soaks one hit. Score = depth in metres + gums.
 * One attempt per player; with P2 the turns alternate (GgSeq, as Gum Fling). The record is the best score (higher is better, 0 = none).
 * The bird stays at screen row PD_BIRD_Y; the world scrolls past, so hero y never moves (hero x steers, with the arena wrap). */
#define PD_BIRD_X FL_PX(192)
#define PD_BIRD_Y 72                  /* bird centre, screen px */
#define PD_BIRD_HALF_W 10             /* hit box half width / half height, px */
#define PD_BIRD_HALF_H 14
#define PD_SPEED_START 40             /* scroll speed in 1/16 px per frame (2.5 px) */
#define PD_SPEED_MAX 112              /* 7 px per frame */
#define PD_SPEED_RAMP 20u             /* +1 speed unit every this many frames */
#define PD_SPEED_HIT_LOSS 24          /* a hit takes this much speed off (never below the start speed) */
#define PD_STEER 163840               /* steering speed cap: 2.5 px per frame, 16.16 */
#define PD_STEER_ACC 16384            /* 0.25 px per frame per frame */
#define PD_STUN 30u                   /* 0.5 s without steering after a hit */
#define PD_HITS_MAX 3u                /* the third hit is the crash */
#define PD_SHIELD_EVERY 10u
#define PD_CRASH_FRAMES 90u
#define PD_PAUSE_FRAMES 60u
#define PD_RESULT_FRAMES 150u
#define PD_PLATS 4
#define PD_GUMS 3
#define PD_SPAWN_Y 240                /* a platform enters below the 224 px screen */
#define PD_PLAT_H 16
#define PD_QUALIFY 200u               /* score that counts as qualified */
#define PD_STAGE_SCORE 50u            /* score per gg_points stage */
#define PD_BOUNCE_START (-14)         /* bird display offset right after a hit; it settles back in a few frames */
enum { PD_FALL, PD_CRASH, PD_PAUSE, PD_RESULT };
enum { PD_ROCK, PD_GIRDER, PD_PLANK };

typedef struct { int16_t x, y; uint8_t kind, mids, live, hit; } PdPlat;   /* x = left edge in arena px, y = top in screen px */
typedef struct { int16_t x, y; uint8_t live; } PdGum;                      /* centre */

typedef struct {
    GgSeq seq;                        /* players 1 or 2; one ticket each; points[] and best[] carry the result */
    Rng rng;
    PdPlat plat[PD_PLATS];
    PdGum gum[PD_GUMS];
    uint8_t phase, hits, stun, shield, done, end_t, flip, prev_in;   /* flip: bird faces left (1) or right (0) */
    uint8_t pop_t;                    /* frames since the shield burst, 0 = none (view) */
    uint8_t catch_t;                  /* frames since the last gum was caught, 0 = none (view) */
    uint8_t shield_count;             /* gums toward the next shield, 0 .. PD_SHIELD_EVERY - 1 */
    int8_t bounce;                    /* display offset of the bird, px (view only) */
    uint16_t gums;                    /* gums caught and kept */
    uint16_t timer;
    uint32_t dist;                    /* scroll distance, 1/16 px */
    uint16_t depth;                   /* metres: dist / 128 */
    uint16_t score;                   /* depth + gums */
    uint16_t spd;
    uint16_t last_score;              /* score of the attempt just ended */
} GgPop;

/* Clear the event for one player and start the first fall. seed feeds the platform layout. */
void gp_init(GgPop *p, Flier *hero, uint32_t seed);
/* P2 joins before the first fall is over: two turns. */
void gp_add_p2(GgPop *p);
/* One frame. Returns 1 on the frame the last attempt ends (points are then in p->seq.points). */
int gp_step(GgPop *p, Flier *hero, uint8_t in);
#endif
