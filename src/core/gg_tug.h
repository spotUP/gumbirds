#ifndef GG_TUG_H
#define GG_TUG_H
#include <stdint.h>
#include "rng.h"

/* TUG-GUM (PARTY, pure logic): two teams of two pull a gum strand with a knot in the middle.
 * Seats: 0 = P1, 1 = P1 partner, 2 = P2 or the computer rival, 3 = its partner. Partners add no force (looks only).
 * Knot is in quarter pixels from the middle; negative = towards team 0 (left). The team that drags the knot over
 * its own win line (+/- GTG_WIN_Q) takes the round; the strand snaps and the losing team is slapped. Best of 3.
 * A / B / C: any new press is one pull. D: let go, you slide back; a rival who pulled within GTG_LETGO_WINDOW frames
 * stumbles and their pulls count for nothing for GTG_STUMBLE_FRAMES. */
#define GTG_SEATS 4u
#define GTG_WIN_Q 128              /* 32 px in quarter pixels */
#define GTG_PULL_Q 6               /* one pull moves the knot 1.5 px */
#define GTG_LETGO_Q 12             /* letting go gives the rival 3 px */
#define GTG_LETGO_WINDOW 15u       /* about 0.25 s */
#define GTG_STUMBLE_FRAMES 36u     /* about 0.6 s */
#define GTG_SLIDE_FRAMES 14u
#define GTG_PRESS_POSE_FRAMES 8u
#define GTG_CPU_GAP_MIN 8u         /* the computer rival presses every GAP_MIN + random(GAP_SPAN) frames */
#define GTG_CPU_GAP_SPAN 6u
#define GTG_SNAP_FRAMES 90u
#define GTG_RESULT_FRAMES 180u
#define GTG_ROUNDS_TO_WIN 2

enum { GTG_PLAY, GTG_SNAP, GTG_RESULT, GTG_END };
enum { GTG_POSE_IDLE, GTG_POSE_PULL0, GTG_POSE_PULL1, GTG_POSE_PULL2, GTG_POSE_STRAIN, GTG_POSE_SLIDE,
       GTG_POSE_STUMBLE, GTG_POSE_SLAPPED, GTG_POSE_CHEER0, GTG_POSE_CHEER1, GTG_POSE_COUNT };

#define GTG_SFX_PULL 1u
#define GTG_SFX_LETGO 2u
#define GTG_SFX_SNAP 4u
#define GTG_SFX_WIN 8u

typedef struct {
    Rng rng;
    uint8_t phase;
    uint8_t humans;                  /* 1 or 2 */
    uint8_t prev[2];                 /* last frame's inputs */
    uint8_t wins[2];
    uint8_t round_winner;
    uint8_t sfx;                     /* GTG_SFX_* raised this frame, cleared by the caller */
    uint8_t press_n[2], press_pose[2], slide[2], stumble[2], since_pull[2];
    uint8_t cpu_gap;
    int16_t knot;
    uint16_t t;
} GgTug;

void gg_tug_start(GgTug *t, uint32_t seed, uint8_t humans);
void gg_tug_step(GgTug *t, uint8_t in1, uint8_t in2);
int gg_tug_pose(const GgTug *t, uint8_t seat);

#endif
