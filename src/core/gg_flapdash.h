#ifndef GG_FLAPDASH_H
#define GG_FLAPDASH_H
#include <stdint.h>
#include "flier.h"
#include "gumgames.h"

/* Gum Games event Flap Dash (pure logic): mash A/B to flap the hero around the 384 px arena ring for GD_LAPS laps.
 * Record = frames from the first frame to the finish (lower is better). */
#define GD_LAPS 3u
#define GD_MAX_VX FL_PX(2)             /* CAM_MAX_STEP_PX: above this the bird outruns the camera */
#define GD_FLOOR_Y FL_PX(190)          /* surface under the hero's feet */
#define GD_MARK_FRAMES 1500u           /* qualifying time on the first medley loop (25 s; the cap alone needs about 580) */
#define GD_RESULT_FRAMES 150u          /* result screen after the finish, then the event is over (one run, no retry) */
#define GD_MARK_MIN 700u               /* floor of the tightened mark: the top air speed alone needs about 690 */

/* 2P (owner 2026-11-23): same course, both birds on one screen, first to GD_LAPS laps wins. Contact slows both a little, no push. */
#define GD_P2_GAP 20                   /* 2P: P2 starts this many px behind P1 so the birds do not overlap at the line */
#define GD_BUMP_DX 10                  /* contact box: |dx| below this and ... */
#define GD_BUMP_DY 14                  /* ... |dy| below this (px) */
#define GD_BUMP_SHIFT 3                /* each contact frame both birds lose vx >> 3 (12.5%) */

typedef struct {
    GgMash mash;
    uint8_t prev_in, laps, done, end_t;   /* end_t: frames shown on the result after the finish */
    uint32_t frames;
    int32_t lap_dist;                  /* 16.16 px travelled in the current lap, 0..ARENA_W16 */
    GgMash mash2;                      /* P2 lane (read only while two) */
    uint8_t prev_in2, laps2, two;      /* two = 1 once P2 joined */
    uint8_t winner;                    /* 0 none yet, 1 = P1, 2 = P2 (two only) */
    uint8_t p2_is_cpu;                 /* set by whoever feeds input2 from the computer: its time never becomes a human record */
    int32_t lap_dist2;
} GgDash;

/* Place the hero at the start line and clear the run. */
void gumdash_init(GgDash *d, Flier *hero);
/* One frame. dir is forced to +1, every new A or B press is the flap. Returns 1 on the frame the last lap completes (and keeps returning 0 after). */
int gumdash_step(GgDash *d, Flier *hero, uint8_t in);
/* P2 joins before the first step: hero2 starts GD_P2_GAP px behind hero on the same line. */
void gumdash_add_p2(GgDash *d, const Flier *hero, Flier *hero2);
/* One frame with P2: in = P1, in2 = P2 (from g->input2). Without P2 it is gumdash_step. Returns 1 on the frame the race is decided. */
int gumdash_step2(GgDash *d, Flier hero[2], uint8_t in, uint8_t in2);
/* Qualifying time in frames on medley loop `loop` (0 = first): 5% tighter each loop. */
uint32_t gumdash_mark(uint32_t loop);
#endif
