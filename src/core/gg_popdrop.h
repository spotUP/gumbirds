#ifndef GG_POPDROP_H
#define GG_POPDROP_H
#include <stdint.h>
#include "flier.h"
#include "gumgames.h"
#include "rng.h"

/* Gum Games event Pop Drop (pure logic), the free-fall design: the bird falls without end and the fall speeds up. Platforms (rock island, steel girder,
 * wooden plank) rush up from below, gum candy drifts up between them. The stick steers left / right. A platform hit = bounce, a stun of PD_STUN frames and
 * one caught gum lost; the third hit is the crash. A trail of gums (owner pick 2026-11-20) threads each row's open gap: platforms never sit on it,
 * so a bird that follows it at full speed never hits. Every PD_SHIELD_EVERY gums blow a shield bubble that soaks one hit. Score = depth in metres + gums.
 * One attempt per player. With P2 both birds fall at once through the same scroll and platforms (owner pick 2026-11-20): birds push
 * each other apart (no damage), a crashed bird floats on as a ghost (no collision) until both crashed; each bird's score goes to
 * its GgSeq slot. The record is the best score (higher is better, 0 = none).
 * Pool finish (owner pick 2026-11-20, batch 2): at depth PD_POOL_DEPTH a pool surface (p->pool_y, screen px) rises to the bird; platforms stop
 * spawning PD_POOL_CLEAR px short of it. Every bird still alive when its feet touch the surface flops: pose (the last of the pose
 * buttons pressed during the fall: IN_B = cannonball, IN_C = face-first, IN_D = belly; none = belly; IN_A stays the brake hop) and
 * impact speed (p->spd: small / medium / big splash) give three judge cards 1..10 (no rng) and flop points = sum of cards * PD_FLOP_MULT,
 * added to depth + gums. A crashed bird (2P ghost) never flops. Odd fallers (bathtub bird, armchair, umbrella snail) are background
 * gags in p->fall[] (type, x, y), no collision, drawn later by the view; they use their own rng so the platform layout is unchanged.
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
#define PD_SHIELD_EVERY 5u            /* 1 trail gum per gap: a shield about every 5 gaps followed */
#define PD_CRASH_FRAMES 90u
#define PD_RESULT_FRAMES 150u
#define PD_PLATS 4
#define PD_GUMS 20                    /* trail gums live at once: 256 px of live y / 14.4 px spacing = 18 at most */
#define PD_TRAIL_GUMS 1               /* gums per gap: one, at the new row's gap point (owner pick 2026-11-20: way too many gums) */
#define PD_TRAIL_SHIFT_MAX 48         /* trail sideways move per gap, px (also capped at 1 px per frame of fall, 40 % of PD_STEER) */
#define PD_AIM_OVERLAP 4              /* aimed row: px the platform edge reaches into a bird's hit box (owner pick 2026-11-20: aim about half the rows) */
#define PD_TRAIL_CLEAR 16             /* px between the trail and a platform's hit box edge, room for the follower's lag */
#define PD_SPAWN_Y 240                /* a platform enters below the 224 px screen */
#define PD_PLAT_H 16
#define PD_QUALIFY (PD_POOL_DEPTH + PD_FLOP_MAX / 2u)   /* qualified = reach the pool AND land a decent flop (half the max) or collect gums */
#define PD_STAGE_SCORE 50u            /* score per gg_points stage */
#define PD_BOUNCE_START (-14)         /* bird display offset right after a hit; it settles back in a few frames */
#define PD_HOP_PX 12                  /* brake hop: the bird (and its hit box) jumps this many px up, then sinks back 1 px per frame */
#define PD_BRAKE_FRAMES 10u           /* brake hop: the fall runs at half speed this many frames (the stored speed is not touched) */
#define PD_FLAP_MAX 3u                /* brake hop: flaps stored */
#define PD_FLAP_REFILL 20u            /* brake hop: frames until one flap is stored again (full refill 60 frames) */
#define PD_HOP_PX_2P 20               /* 2P brake hop: only that bird lifts, the shared scroll is not slowed */
#define PD_P2_GAP 48                  /* 2P: start gap between the birds, px */
#define PD_PUSH_KICK 65536            /* bird-bird bump: each bird leaves at least 1 px per frame (16.16) */
#define PD_POOL_DEPTH 900u            /* metres to the pool (about 45 s at the speed ramp; owner 2026-11-20) */
#define PD_POOL_CLEAR 32              /* px of free fall between the last platform's bottom and the pool surface */
#define PD_POOL_FRAMES 180u           /* flop, splash and cards on screen before the result */
#define PD_SPLASH_TICKS 3u            /* game frames per splash frame */
#define PD_SPLASH_LEN(size) ((size) == 0 ? 16u : (size) == 1 ? 20u : 23u)   /* frames of the small / medium / big splash drafts */
#define PD_SIZE_MEDIUM 56u            /* impact speed (1/16 px per frame) from which the splash is medium: with 3 hits worth 24 speed the 1P range is about 40..74 */
#define PD_SIZE_BIG 70u
/* Impact speed per bird: 1P the scroll already lost PD_SPEED_HIT_LOSS per hit; 2P the scroll is shared, so each bird loses it from its own hits.
 * Table at full speed 112: 0 hits 112 big, 1 hit 88 big, 2 hits 64 medium; at start speed 40 every hit count is small. */
#define PD_JUDGES 3
#define PD_FLOP_MAX (PD_JUDGES * 10u * PD_FLOP_MULT)   /* 90 */
#define PD_FLOP_MULT 3u               /* flop points per card point: 3 judges x 10 x 3 = 90 at most, depth + gums is about 340 */
#define PD_FALLERS 2                  /* background gags live at once */
#define PD_FALLER_EVERY 180u          /* next faller after this many frames plus up to PD_FALLER_EVERY more */
enum { PD_FALL, PD_CRASH, PD_RESULT, PD_POOL };   /* PD_POOL appended so the existing numbers stay */
enum { PD_POSE_BELLY, PD_POSE_CANNON, PD_POSE_FACE };
enum { PD_SPLASH_SMALL, PD_SPLASH_MEDIUM, PD_SPLASH_BIG };
enum { PD_FALLER_BATH, PD_FALLER_ARMCHAIR, PD_FALLER_SNAIL };
enum { PD_ROCK, PD_GIRDER, PD_PLANK };

typedef struct { int16_t x, y; uint8_t kind, mids, live, hit; } PdPlat;   /* hit: bit k set once bird k hit it */   /* x = left edge in arena px, y = top in screen px */
typedef struct { int16_t x, y; uint8_t kind, live; int8_t dx; } PdFaller;   /* gag, centre; dx = sideways drift: 1 px every 4 frames */
typedef struct { int16_t x, y; uint8_t live; } PdGum;                      /* centre; trail gums, see spawn() */

typedef struct {                      /* one bird; 1P uses b[0] */
    uint8_t hits, stun, shield, flip, prev_in;   /* flip: bird faces left (1) or right (0); prev_in: last input (A edge, view lean) */
    uint8_t crash;                    /* 1 = crashed (2P: floats on as a ghost, no collision) */
    int8_t land;                      /* platform index of the final crash hit (the crash pose lies on it), -1 = none (a 2P ghost) */
    uint8_t pop_t;                    /* frames since the shield burst, 0 = none (view) */
    uint8_t catch_t;                  /* frames since the last gum was caught, 0 = none (view) */
    uint8_t bump_t;                   /* frames since a bird-bird bump, 0 = none (view hook: squawk + feather puff) */
    uint8_t shield_count;             /* gums toward the next shield, 0 .. PD_SHIELD_EVERY - 1 */
    uint8_t flaps, flap_t;            /* brake hop: flaps stored, frames toward the next refill */
    int8_t hop;                       /* bird offset of the brake hop, px, 0 .. -PD_HOP_PX (moves the hit box too) */
    int8_t bounce;                    /* display offset of the bird, px (view only) */
    uint16_t gums;                    /* gums caught and kept */
    uint16_t score;                   /* depth + gums (+ flop points), frozen at the crash / the pool */
    uint8_t pose_pick;                /* latched pose button: PD_POSE_* */
    uint8_t landed;                   /* 1 = flopped into the pool: pose, size, card[], flop, splash_f are valid (view) */
    uint8_t pose, size;               /* the flop: PD_POSE_*, PD_SPLASH_* */
    uint8_t card[PD_JUDGES];          /* score cards 1..10 held up by the crowd birds */
    uint8_t splash_t, splash_f;       /* frames since impact (stops at the end of the splash); splash frame 0 .. PD_SPLASH_LEN(size) - 1 */
    uint16_t flop;                    /* flop points */
} PdBird;

typedef struct {
    GgSeq seq;                        /* players 1 or 2; one ticket each; points[] and best[] carry the result */
    Rng rng;
    PdPlat plat[PD_PLATS];
    PdGum gum[PD_GUMS];
    PdBird b[2];
    PdFaller fall[PD_FALLERS];
    Rng frng;                         /* faller schedule only */
    uint16_t fall_next;               /* timer value of the next faller */
    int16_t pool_y;                   /* pool surface, screen px (below 224 = off screen); after impact it keeps rising a few px as the birds sink */
    uint8_t phase, done, end_t;
    uint8_t brake_t;                  /* 1P brake hop: frames of slow fall left */
    uint16_t timer;
    uint32_t dist;                    /* scroll distance, 1/16 px */
    uint16_t depth;                   /* metres: dist / 128 */
    uint16_t spd;
    uint16_t last_score;              /* best score of the attempt just ended */
    int16_t trail_x;                  /* gap point of the newest row, arena px: the gum trail runs from here to the next row's */
} GgPop;

/* Clear the event for one player and start the first fall. seed feeds the platform layout. */
void gp_init(GgPop *p, Flier *hero, uint32_t seed);
/* P2 joins before the first fall moves: hero2 is P2's bird, both fall at once. */
void gp_add_p2(GgPop *p, Flier *hero, Flier *hero2);
/* One frame; hero[0] / in1 = P1, hero[1] / in2 = P2 (read only with P2). Returns 1 on the frame the event ends (points then in p->seq.points). */
int gp_step(GgPop *p, Flier *hero, uint8_t in1, uint8_t in2);
#endif
