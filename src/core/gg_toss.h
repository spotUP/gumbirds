#ifndef GG_TOSS_H
#define GG_TOSS_H
#include <stdint.h>
#include "rng.h"

/* TOSS-GUM (PARTY, pure logic): four birds stand in an ellipse, one holds a gum with a hidden fuse and tosses it on.
 * The bird holding it when it bursts is out; the gum then goes to a random survivor with a shorter fuse; the last bird wins.
 * Seats are clockwise seen from above: 0 = P1 (left), 1 = computer 1 (back), 2 = P2 (right), 3 = computer 2 (front).
 * A / B / C toss to the left neighbour / across / the right neighbour: the living others in clockwise order o[0..n-1],
 * button k (A = 0, B = 1, C = 2) picks o[k * n / 3] (3 others: o0 o1 o2; 2: A o0, B o0, C o1; 1: all o0). */
#define GT_SEATS 4u
#define GT_FUSE_BASE 480u          /* frames of fuse in round 1 (8 s) before the random part */
#define GT_FUSE_JITTER 120u        /* up to this many extra frames, random */
#define GT_FUSE_STEP 90u           /* the fuse is this much shorter after every burst */
#define GT_FUSE_MIN 150u
#define GT_FLIGHT_FRAMES 29       /* toss arc (draft toss_arc: 29 frames); the fuse is paused in the air */
#define GT_THINK_MIN 30u           /* a computer carrier tosses after GT_THINK_MIN + random(GT_THINK_SPAN) frames */
#define GT_THINK_SPAN 60u
#define GT_BURST_FRAMES 72        /* burst animation (draft: 72 frames) */
#define GT_RESULT_FRAMES 180
#define GT_LEAD_FRAMES 60u         /* a freshly caught gum cannot be tossed on for this long (catch pose) */

enum { GT_HOLD, GT_FLIGHT, GT_BURST, GT_RESULT, GT_END };

typedef struct {
    Rng rng;
    uint8_t phase, alive;            /* alive: bit per seat */
    uint8_t humans;                  /* 1 or 2: seats 0 and 1 (P2 = seat 2) are human */
    uint8_t carrier, target, winner; /* seat; target while in flight; winner seat after the last burst */
    uint8_t prev[2];                 /* last frame's inputs of P1 and P2 */
    uint8_t round;                   /* bursts so far */
    uint8_t sfx;                     /* GT_SFX_* bits raised by a step (main.c plays and clears) */
    uint16_t fuse, think, t, lead;
} GgToss;

#define GT_SFX_TOSS 0x01u
#define GT_SFX_BURST 0x02u
#define GT_SFX_WIN 0x04u

void gg_toss_start(GgToss *t, uint32_t seed, uint8_t humans);
/* Fuse length for a round (0 = first), without the random part. */
uint16_t gg_toss_fuse(uint8_t round);
/* Seat that button k (0 = A, 1 = B, 2 = C) tosses to from `from` with the given alive mask; 0xFF when no other bird lives. */
uint8_t gg_toss_target(uint8_t from, uint8_t alive, uint8_t k);
/* Seat that human p (0 or 1) controls. */
uint8_t gg_toss_seat_of(uint8_t p);
uint8_t gg_toss_count(const GgToss *t);   /* living birds */
/* One frame; in1/in2 are the two players' input bytes. */
void gg_toss_step(GgToss *t, uint8_t in1, uint8_t in2);
#endif
