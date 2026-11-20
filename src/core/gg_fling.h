#ifndef GG_FLING_H
#define GG_FLING_H
#include <stdint.h>
#include "flier.h"
#include "gumgames.h"

/* Gum Games event Gum Fling (pure logic), mash A for run-up power, press B to end the run-up and start the
 * angle needle, keep B held to sweep it (0..90 degrees), release B to launch. Ballistic flight, no flapping. Distance in pixels is read at touch-down; three attempts, best counts.
 * A launch below GF_DEG_MIN or above GF_DEG_MAX degrees, or no launch before the run-up clock ends, is a foul (zero). */
#define GF_ATTEMPTS 3u
#define GF_WINDUP_FRAMES 360u           /* run-up clock per attempt */
#define GF_POWER_MAX 32u                /* counted A presses that fill the power bar */
#define GF_AIM_CAP 128u                 /* frames of B held for the needle to reach 90 degrees */
#define GF_DEG_MIN 15u
#define GF_DEG_MAX 75u
#define GF_V0_BASE FL_PX(1)             /* launch speed with no run-up, 16.16 px per frame */
#define GF_V0_PER_PRESS 4096            /* 1/16 px per frame per counted press: full power = 3 px per frame */
#define GF_MAX_VX FL_PX(2)              /* CAM_MAX_STEP_PX: above this the view cannot keep up with the scroll */
#define GF_GRAVITY 1350                 /* 16.16 px per frame squared */
#define GF_MARK_PX 270u                 /* qualifying distance */
#define GF_SHOW_FRAMES 90u              /* touch-down held on screen before the next attempt */
#define GF_FOUL_FRAMES 60u
#define GF_RESULT_FRAMES 180u           /* winner / pass-fail line held before the event ends */
#define GF_PX_PER_M 3u                  /* on-screen distance unit: pixels per metre (mark 270 px = 90 M) */

/* Sound requests raised by the step (main.c plays them and clears the byte). */
#define GF_SFX_TICK 0x01u               /* run-up clock: one per second */
#define GF_SFX_THROW 0x02u
#define GF_SFX_LAND 0x04u
#define GF_SFX_FOUL 0x08u
#define GF_SFX_WIN 0x10u
#define GF_SFX_LOSE 0x20u

enum { GF_WINDUP, GF_AIM, GF_FLIGHT, GF_LANDED, GF_RESULT, GF_END };
enum { GF_EV_NONE, GF_EV_LAUNCH, GF_EV_LANDED, GF_EV_NEXT };

typedef struct {
    uint8_t phase, prev_in, power, deg, foul;
    uint8_t thrower;                   /* player of the current / last attempt (0 = P1) */
    uint8_t more;                      /* gg_seq_attempt result of the last attempt: someone has a throw left */
    uint8_t sfx;                       /* GF_SFX_* bits */
    uint16_t clock, t;
    GgHold hold;
    GgSeq seq;
    int32_t vx, vy;                    /* 16.16 px per frame, vy up is positive */
    int32_t h;                         /* 16.16 height above the ground */
    uint32_t x;                        /* 16.16 px flown */
    uint32_t dist;                     /* px read at touch-down, 0 for a foul */
    int32_t ground_y;                  /* 16.16 screen y of the hero's centre at touch-down; set by the course step, 0 = not yet */
} GgFling;

void gumfling_init(GgFling *f);
/* P2 joins before the first throw: three throws, turns alternate. */
void gumfling_add_p2(GgFling *f);
/* Winner of a finished 2P event: 0 or 1, 2 = tie. */
uint8_t gumfling_winner(const GgFling *f);
/* Needle angle in degrees for an aim charge (frames of B held). */
uint8_t gumfling_deg(uint16_t charge);
/* One frame in the arena (WINDUP, AIM) or on the landing / result screen. Returns a GF_EV_* (LAUNCH: switch to the course). */
int gumfling_step(GgFling *f, uint8_t in);
/* One flight frame. Returns GF_EV_LANDED on the touch-down frame. */
int gumfling_fly(GgFling *f);
/* Preview of a throw with run-up power and aim charge (frames of B held): n points (dx, dy) in pixels from the launch point, dy up
 * positive, spread evenly in time over the whole flight, using the same launch and flight frame as the real throw. Returns the flight frames. */
int gumfling_path(uint8_t power, uint16_t charge, int16_t *dx, int16_t *dy, int n);
/* Scroll step of the last flight frame in 16.16 px. */
int32_t gumfling_scroll(const GgFling *f);
#endif
