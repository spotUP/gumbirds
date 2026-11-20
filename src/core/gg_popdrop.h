#ifndef GG_POPDROP_H
#define GG_POPDROP_H
#include <stdint.h>
#include "flier.h"
#include "gumgames.h"
#include "rng.h"

/* Gum Games event Pop Drop (pure logic), the free-fall design: the bird falls without end and the fall speeds up. Platforms (rock island, steel girder,
 * wooden plank) rush up from below, gum candy drifts up between them. The stick steers left / right. A platform hit = bounce, a stun of PD_STUN frames and
 * one caught gum lost; the third hit is the crash. Every PD_SHIELD_EVERY gums blow a shield bubble that soaks one hit. Score = depth in metres + gums.
 * One attempt per player. With P2 both birds fall at once through the same scroll and platforms (owner pick 2026-11-20): birds push
 * each other apart (no damage), a crashed bird floats on as a ghost (no collision) until both crashed; each bird's score goes to
 * its GgSeq slot. The record is the best score (higher is better, 0 = none).
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
#define PD_RESULT_FRAMES 150u
#define PD_PLATS 4
#define PD_GUMS 3
#define PD_SPAWN_Y 240                /* a platform enters below the 224 px screen */
#define PD_PLAT_H 16
#define PD_QUALIFY 200u               /* score that counts as qualified */
#define PD_STAGE_SCORE 50u            /* score per gg_points stage */
#define PD_BOUNCE_START (-14)         /* bird display offset right after a hit; it settles back in a few frames */
#define PD_HOP_PX 12                  /* brake hop: the bird (and its hit box) jumps this many px up, then sinks back 1 px per frame */
#define PD_BRAKE_FRAMES 10u           /* brake hop: the fall runs at half speed this many frames (the stored speed is not touched) */
#define PD_FLAP_MAX 3u                /* brake hop: flaps stored */
#define PD_FLAP_REFILL 20u            /* brake hop: frames until one flap is stored again (full refill 60 frames) */
#define PD_HOP_PX_2P 20               /* 2P brake hop: only that bird lifts, the shared scroll is not slowed */
#define PD_P2_GAP 48                  /* 2P: start gap between the birds, px */
#define PD_PUSH_KICK 65536            /* bird-bird bump: each bird leaves at least 1 px per frame (16.16) */
enum { PD_FALL, PD_CRASH, PD_RESULT };
enum { PD_ROCK, PD_GIRDER, PD_PLANK };

typedef struct { int16_t x, y; uint8_t kind, mids, live, hit; } PdPlat;   /* hit: bit k set once bird k hit it */   /* x = left edge in arena px, y = top in screen px */
typedef struct { int16_t x, y; uint8_t live; } PdGum;                      /* centre */

typedef struct {                      /* one bird; 1P uses b[0] */
    uint8_t hits, stun, shield, flip, prev_in;   /* flip: bird faces left (1) or right (0); prev_in: last input (A edge, view lean) */
    uint8_t crash;                    /* 1 = crashed (2P: floats on as a ghost, no collision) */
    uint8_t pop_t;                    /* frames since the shield burst, 0 = none (view) */
    uint8_t catch_t;                  /* frames since the last gum was caught, 0 = none (view) */
    uint8_t bump_t;                   /* frames since a bird-bird bump, 0 = none (view hook: squawk + feather puff) */
    uint8_t shield_count;             /* gums toward the next shield, 0 .. PD_SHIELD_EVERY - 1 */
    uint8_t flaps, flap_t;            /* brake hop: flaps stored, frames toward the next refill */
    int8_t hop;                       /* bird offset of the brake hop, px, 0 .. -PD_HOP_PX (moves the hit box too) */
    int8_t bounce;                    /* display offset of the bird, px (view only) */
    uint16_t gums;                    /* gums caught and kept */
    uint16_t score;                   /* depth + gums, frozen at the crash */
} PdBird;

typedef struct {
    GgSeq seq;                        /* players 1 or 2; one ticket each; points[] and best[] carry the result */
    Rng rng;
    PdPlat plat[PD_PLATS];
    PdGum gum[PD_GUMS];
    PdBird b[2];
    uint8_t phase, done, end_t;
    uint8_t brake_t;                  /* 1P brake hop: frames of slow fall left */
    uint16_t timer;
    uint32_t dist;                    /* scroll distance, 1/16 px */
    uint16_t depth;                   /* metres: dist / 128 */
    uint16_t spd;
    uint16_t last_score;              /* best score of the attempt just ended */
} GgPop;

/* Clear the event for one player and start the first fall. seed feeds the platform layout. */
void gp_init(GgPop *p, Flier *hero, uint32_t seed);
/* P2 joins before the first fall moves: hero2 is P2's bird, both fall at once. */
void gp_add_p2(GgPop *p, Flier *hero, Flier *hero2);
/* One frame; hero[0] / in1 = P1, hero[1] / in2 = P2 (read only with P2). Returns 1 on the frame the event ends (points then in p->seq.points). */
int gp_step(GgPop *p, Flier *hero, uint8_t in1, uint8_t in2);
#endif
