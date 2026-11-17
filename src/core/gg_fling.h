#ifndef GG_FLING_H
#define GG_FLING_H
#include <stdint.h>
#include "flier.h"
#include "gumgames.h"

/* Gum Games event Gum Fling (pure logic): mash A/B for run-up power, hold C to sweep the angle needle (0..90 degrees),
 * release to launch. Ballistic flight, no flapping. Distance in pixels is read at touch-down; three attempts, best counts.
 * A launch below GF_DEG_MIN or above GF_DEG_MAX degrees, or no launch before the run-up clock ends, is a foul (zero). */
#define GF_ATTEMPTS 3u
#define GF_WINDUP_FRAMES 360u           /* run-up clock per attempt */
#define GF_POWER_MAX 32u                /* counted A/B presses that fill the power bar */
#define GF_AIM_CAP 128u                 /* frames of C held for the needle to reach 90 degrees */
#define GF_DEG_MIN 15u
#define GF_DEG_MAX 75u
#define GF_V0_BASE FL_PX(1)             /* launch speed with no run-up, 16.16 px per frame */
#define GF_V0_PER_PRESS 4096            /* 1/16 px per frame per counted press: full power = 3 px per frame */
#define GF_MAX_VX FL_PX(2)              /* CAM_MAX_STEP_PX: above this the view cannot keep up with the scroll */
#define GF_GRAVITY 2000                 /* 16.16 px per frame squared */
#define GF_MARK_PX 150u                 /* qualifying distance */
#define GF_SHOW_FRAMES 90u              /* touch-down held on screen before the next attempt */
#define GF_FOUL_FRAMES 60u

enum { GF_WINDUP, GF_AIM, GF_FLIGHT, GF_LANDED, GF_END };
enum { GF_EV_NONE, GF_EV_LAUNCH, GF_EV_LANDED, GF_EV_NEXT };

typedef struct {
    uint8_t phase, prev_in, power, deg, foul;
    uint16_t clock, t;
    GgMash mash;
    GgHold hold;
    GgSeq seq;
    int32_t vx, vy;                    /* 16.16 px per frame, vy up is positive */
    int32_t h;                         /* 16.16 height above the ground */
    uint32_t x;                        /* 16.16 px flown */
    uint32_t dist;                     /* px read at touch-down, 0 for a foul */
    int32_t ground_y;                  /* 16.16 screen y of the hero's centre at touch-down; set by the course step, 0 = not yet */
} GgFling;

void gumfling_init(GgFling *f);
/* Needle angle in degrees for an aim charge (frames of C held). */
uint8_t gumfling_deg(uint16_t charge);
/* One frame in the arena (WINDUP, AIM) or on the landing screen. Returns a GF_EV_* (LAUNCH: switch to the course). */
int gumfling_step(GgFling *f, uint8_t in);
/* One flight frame. Returns GF_EV_LANDED on the touch-down frame. */
int gumfling_fly(GgFling *f);
/* Scroll step of the last flight frame in 16.16 px. */
int32_t gumfling_scroll(const GgFling *f);
#endif
