/*
 * ai.h - computer flier controller (design doc 3.1). Portable C99, fixed point, no divide, no globals.
 * Every AI_THINK_FRAMES (+- AI_THINK_JITTER) frames it picks a state and steering from the nearest rival; the flap decision runs every frame:
 *   FILL   no balloons and the rival is farther than AI_FILL_DIST: does nothing (no stored pods exist, the settled
 *          option; the reference refill action source was not available).
 *   FLEE   no balloons, or the rival is within AI_FLEE_DIST and the flier is not above it by AI_ABOVE_MARGIN.
 *   CHASE  otherwise.
 * Chase and flee steer when |dir.x| > AI_STEER_MIN steer; they press flap each frame when dir.y < AI_FLAP_MAX (Q15, y down), the cooldown is over and the button was released. Flee negates dir.
 * Distances are screen pixels (reference values halved: the arena is 384x180 and wraps; distances are the shortest across the seam, reference scale 0.5).
 */
#ifndef BRAWL_AI_H
#define BRAWL_AI_H

#include <stdint.h>
#include "tuning.h"
#include "rng.h"
#include "flier.h"

typedef enum { AI_FILL = 0, AI_FLEE, AI_CHASE } AiState;

typedef struct {
    uint8_t state;    /* AiState */
    uint16_t timer;   /* frames until the next think */
    int8_t dir;       /* held between thinks */
    uint32_t thinks;  /* think count (test sentinel) */
    uint8_t think_cut;/* frames shaved off every think period by the arcade rank */
} Ai;

/* rank 1 is the arena AI; higher arcade ranks (arcade.h) think sooner. */
void ai_init(Ai *a, Rng *r, int rank);
/* Nearest live rival (state ALIVE or PARACHUTE) among the player and the computer fliers, by squared distance. NULL
 * when none. self is excluded by pointer. */
const Flier *ai_nearest(const Flier *self, const Flier *player, const Flier *cpus, int cpu_count);
/* The pure decision: state for a flier and its target (no side effects). */
AiState ai_decide(const Flier *self, const Flier *target);
/* One frame: counts the timer down; on zero thinks (state, dir) and re-arms with jitter. target may be
 * NULL (idle). Fills *out for flier_step. */
void ai_step(Ai *a, Rng *r, const Flier *self, const Flier *target, FlierInput *out);

#endif
