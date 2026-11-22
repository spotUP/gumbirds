#ifndef GG_POOP_H
#define GG_POOP_H
#include <stdint.h>
#include "gumgames.h"
#include "rng.h"

/* Gum Games event Poop the Man (pure logic, owner plan 2026-11-20). Scrolling city street: the birds fly free over it (stick left/right steers at
 * PM_BIRD_VX, no stick holds x, the arena flier's top air speed; gravity pulls them down and A (press edge) is a flap, like every other mode; stick up/down does
 * nothing), B drops one poop that keeps the bird's forward speed (lead the target); no ammo, only a PM_DROP_CD frame cooldown per bird.
 * A bird that touches a walker body (full cell box, any state) or the pavement dies: streak ends, score kept, it falls off screen, respawns at
 * mid-height after PM_DEAD_FRAMES with PM_INV_FRAMES of invulnerability (blink). Input is ignored while dead. Walkers cross the street both ways
 * below; a poop that reaches a head box scores PM_BASE * type factor (hat x2, bald x3) * combo (streak, cap x4). Pavement miss = 0 and ends the streak.
 * An umbrella (some walkers open one when a bird is above; storm: all) bounces the poop: no score, streak ends. A hit walker is angry: it shakes a
 * fist (harmless) or throws a shoe up at the bird; a shoe that reaches a bird stuns it PM_STUN frames and ends its streak. 60 s, 1 or 2 birds on the same screen, highest score wins. Record = best score of either player (higher is better).
 * p->phase is the event phase for the prompt helper: PM_PLAY (rules card and countdown run before, in game.c), PM_RESULT, PM_DONE. */
#define PM_W 320
#define PM_CLOCK 3600u               /* 60 s */
#define PM_RESULT_FRAMES 1u          /* the event result screen holds the totals; a frozen arena here read as a stall (owner 2026-11-22) */
#define PM_BASE 100u
#define PM_COMBO_CAP 4u
#define PM_STUN 45u
#define PM_SCROLL 2                  /* street scroll, px per frame (walkers and berries move with it) */
#define PM_FEET_Y 176                /* the city roof line the backdrop draws as ground (GROUND = 176 in assets/city/draw_city.py); walker feet bottom row is PM_FEET_Y - 1 */
#define PM_PAVE_Y (PM_FEET_Y + 4)                   /* a poop lower than this hit the pavement */
#define PM_BIRD_Y_MIN 24
#define PM_DROP_CD 12u               /* frames between two drops of one bird */
#define PM_DEAD_FRAMES 90u
#define PM_INV_FRAMES 60u
#define PM_BODY_HALF_W 8             /* walker body half width for the bird touch (bird half width PM_BIRD_HALF_W is added) */
#define PM_BIRD_VX 27                /* 1/16 px per frame sideways while Left / Right is held (FLIER_TOP_AIR_SPEED 1.667 px); no stick = no drift */
#define PM_GRAVITY 1                 /* 1/16 px per frame per frame (flier.c gravity 3413/65536 px scaled to 1/16 px, rounded) */
#define PM_FLAP_VY 14                /* A press sets vy to this much upward (1/16 px per frame) */
#define PM_FLAP_CD 9u                /* FLIER_FLAP_COOLDOWN */
#define PM_FALL_MAX 40               /* 2.5 px per frame */
#define PM_RISE_MAX 24
#define PM_SPAWN_Y 64
#define PM_HEAD_H 12                 /* head box height below the walker's top */
#define PM_HEAD_HALF_W 8
#define PM_UMB_Y 12                  /* an open umbrella covers the PM_UMB_H px above the head box */
#define PM_UMB_H 8
#define PM_UMB_HALF_W 16
#define PM_UMB_RANGE 40              /* a bird within this many px sideways of an umbrella walker, above it, opens it */
#define PM_POOPS 6
#define PM_WALKERS 7
#define PM_SHOES 3
#define PM_BIRD_HALF_W 12
#define PM_BIRD_HALF_H 10
#define PM_HIT_FRAMES 30u            /* splat on the head, then the walker is angry */
#define PM_ANGRY_FRAMES 70u
#define PM_SPAWN_EVERY 40u
enum { PM_PLAY, PM_RESULT, PM_DONE };
enum { PM_HAT, PM_BALD, PM_WOMAN, PM_KID };
enum { PM_WALK, PM_HIT, PM_FIST, PM_THROW };   /* walker states (art: walk, hit, fist, throw) */
enum { PM_POOP_FALL, PM_POOP_BOUNCE, PM_POOP_SPLAT };   /* SPLAT: lies on the pavement PM_SPLAT_FRAMES, scrolling with the street */
#define PM_SPLAT_FRAMES 30u
#define PM_SFX_BOUNCE 1u             /* GgPoop.sfx bits raised by gm_step for the view (throw, head hit and shoe hit are read from the bird / last_hit fields) */
#define PM_SFX_FLAP 2u               /* a bird flapped */
#define PM_SFX_DEAD 4u               /* a bird died */

typedef struct { int16_t x8, dx8; uint8_t kind, st, live, umb_prone, umb, owner; uint16_t t; } PmWalker;   /* x8 = centre in 1/8 px; dx8 = own speed relative to the street, 1/8 px per frame */
typedef struct { int32_t x16, y16; int16_t vx16, vy16; uint8_t live, st, t, owner; } PmPoop;     /* centre and velocity in 1/16 px (per frame) */
typedef struct { int16_t x, y; int8_t vx, vy; uint8_t live; } PmShoe;   /* px per frame */
typedef struct {
    int16_t x, y;                    /* centre, px */
    int16_t xf, yf;                  /* 1/16 px remainders */
    int16_t vy16;                    /* 1/16 px per frame, down positive */
    uint8_t flip, streak, stun, prev_in, drop_t, drop_cd, flap_cd, flap_t, dead, inv;   /* drop_t / flap_t: frames since the last drop / flap (view), 0 = none; dead, inv: frames left */
    uint32_t score;
} PmBird;

typedef struct {
    GgSeq seq;
    Rng rng;
    uint8_t phase, done;
    uint8_t storm;                   /* 1 = every walker carries an umbrella */
    PmBird b[2];
    PmWalker w[PM_WALKERS];
    PmPoop poop[PM_POOPS];
    PmShoe shoe[PM_SHOES];
    uint16_t timer;                  /* frames played */
    uint16_t end_t;
    uint16_t scroll;                 /* street scroll distance, px, wraps at 65536 (view reads it mod the ring width) */
    uint8_t last_hit_b, last_hit_pts_ev; /* view hooks: bird of the last head hit, 1 on the frame it scored */
    uint32_t last_pts;
    uint8_t sfx;                     /* PM_SFX_* raised this frame, cleared by the caller */
    uint8_t splat_n, sfx_n;          /* running counts (wrap) of splats started and bounce events: test hooks */
} GgPoop;

void gm_init(GgPoop *p, uint32_t seed, uint8_t storm);
void gm_add_p2(GgPoop *p);
/* One frame. Returns 1 on the frame the event ends (points then in p->seq.points[]). */
int gm_step(GgPoop *p, uint8_t in1, uint8_t in2);
/* Score factor of a walker kind: hat 2, bald 3, others 1. Streak factor: 1..PM_COMBO_CAP. */
uint8_t gm_kind_mult(uint8_t kind);
#endif
