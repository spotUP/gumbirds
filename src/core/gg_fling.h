#ifndef GG_FLING_H
#define GG_FLING_H
#include <stdint.h>
#include "flier.h"
#include "gumgames.h"

/* Gum Games event Gum Fling (pure logic): mash A and B until the run-up clock ends (power freezes), then the angle needle swings
 * back and forth between GF_DEG_MIN and GF_DEG_MAX; press A to stop it and launch (or it launches by itself after GF_AIM_TIMEOUT_FRAMES).
 * Ballistic flight, no flapping. Distance in pixels is read at touch-down; three attempts, best counts. */
#define GF_ATTEMPTS 3u
#define GF_WINDUP_FRAMES 360u           /* run-up clock per attempt */
#define GF_POWER_MAX 32u                /* counted A / B presses that fill the power bar */
#define GF_POWER_DRAIN_FRAMES 36u       /* the power falls one step per this many frames, so slow mashing cannot top out */
#define GF_AIM_SWEEP_FRAMES 45u         /* needle sweep GF_DEG_MIN -> GF_DEG_MAX; back is the same again */
#define GF_AIM_TIMEOUT_FRAMES 180u      /* no press in the aim: throw at the current angle */
#define GF_AIM_HOLD_FRAMES 30u          /* aim start: needle still and buttons ignored, so the hand can stop mashing before A */
#define GF_DEG_MIN 15u
#define GF_DEG_MAX 75u
#define GF_FLAP_PRESS 12u               /* flap charge added per A / B press in flight */
#define GF_FLAP_DRAIN 1u                /* flap charge lost per frame, so only frantic mashing builds it */
#define GF_FLAP_MAX 60u
#define GF_FLAP_THRESH 30u              /* no lift at or below this charge */
#define GF_FLAP_CAP_MIN_PX 40          /* flap lift ceiling: the launch apex, at least this high (a 15 degree apex is ~13 px) */
#define GF_FLAP_LIFT 90                 /* 16.16 vy gained per frame per charge step above the threshold (tuned with GF_FLAP_PRESS 12: 5 presses/s +0, 15/s about +25..30 percent distance) */
/* Speed (owner 2026-11-20: "slow motion"): every launch speed is k = 1.5 times the old one and gravity k^2 (old 1350 -> 3038),
 * so the paths are the same curves flown in 1/1.5 of the time: same range (v^2/g), best-angle full-power flight about 137 frames, about 205 before.
 * The old vx cap of 2 px per frame was copied from CAM_MAX_STEP_PX, but the fling scroll is camera_scroll (no easing, no cap) and the
 * turf strips load from f->x, so nothing limits it; 3 = 2 * k keeps the capped flat throws the same shape too. */
#define GF_V0_BASE 98304                /* launch speed with no run-up, 16.16 px per frame (1.5 px) */
#define GF_V0_PER_PRESS 6144            /* 3/32 px per frame per counted press: full power = 4.5 px per frame */
#define GF_MAX_VX FL_PX(3)              /* horizontal cap, 2 px * k */
#define GF_GRAVITY 3038                 /* 16.16 px per frame squared (1350 * 1.5^2 = 3037.5) */
/* Power drain (owner 2026-11-20: "too easy to get max power"): the run-up loses 1 counted press every GF_POWER_DRAIN_FRAMES frames
 * (60 / 36 = 1.67 presses per second), whether or not the player presses, so only mashing holds the bar up. Net fill over the
 * 360 frame run-up, presses per second -> bar: 5 -> 20 of 32 (62 percent, never full); 6 -> 26 (81); 7 -> 32 after 6.0 s (just);
 * 8 -> full after 5.0 s; 10 -> full after 3.9 s; 12 -> 3.1 s. Hands that cannot sustain 8 presses per second do not fill the bar. */
#define GF_POWER_DRAIN_FRAMES 36u
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
    uint8_t drain_t;                   /* frames since the last power drain tick */
    uint8_t thrower;                   /* player of the current / last attempt (0 = P1) */
    uint8_t more;                      /* gg_seq_attempt result of the last attempt: someone has a throw left */
    uint8_t sfx;                       /* GF_SFX_* bits */
    uint16_t clock, t, flap;
    int32_t h_cap;                     /* 16.16 flap ceiling: launch apex, at least GF_FLAP_CAP_MIN_PX */
    GgMash mash;
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
/* Needle angle in degrees GF_DEG_MIN..GF_DEG_MAX after t aim frames (triangle wave). */
uint8_t gumfling_deg(uint16_t t);
/* One frame in the arena (WINDUP = mash, AIM = swinging needle) or on the landing / result screen. Returns a GF_EV_* (LAUNCH: switch to the course). */
int gumfling_step(GgFling *f, uint8_t in);
/* One flight frame (in: A / B presses charge the flap). Returns GF_EV_LANDED on the touch-down frame. */
int gumfling_fly(GgFling *f, uint8_t in);
/* Preview of a throw with run-up power and aim angle in degrees: n points (dx, dy) in pixels from the launch point, dy up
 * positive, spread evenly in time over the whole flight, using the same launch and flight frame as the real throw. Returns the flight frames. */
int gumfling_path(uint8_t power, uint8_t deg, int16_t *dx, int16_t *dy, int n);
/* Scroll step of the last flight frame in 16.16 px. */
int32_t gumfling_scroll(const GgFling *f);
#endif
