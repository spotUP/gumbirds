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

/* AI_HOLD (PARTY Roost Rule): with Ai.hold set, ai_step skips the thinks and flies to the target (the roost mark), then stands on it.
 * It flaps only while far from the target in x, or below it in the air, and never while standing on the island. */
typedef enum { AI_FILL = 0, AI_FLEE, AI_CHASE, AI_HOLD } AiState;
#define AI_HOLD_NEAR_PX 24    /* x distance under which the holder drops onto the island instead of cruising */
#define AI_HOLD_STEER_MIN 3   /* x dead zone: it stops steering when this close to the mark */
#define AI_HOLD_CRUISE_PX 24  /* far: flap while the mark is less than this far below (the holder cruises above it) */
#define AI_HOLD_LAND_PX 2     /* near, airborne: flap only when more than this below the mark */
#define AI_HOLD_LIFT_PX 4     /* standing: jump when the mark is higher than this */

typedef struct {
    uint8_t state;    /* AiState */
    uint16_t timer;   /* frames until the next think */
    int8_t dir;       /* held between thinks */
    uint32_t thinks;  /* think count (test sentinel) */
    int8_t think_cut;/* frames shaved off every think period by the rank; negative = slower than the arena value (party Slow Thinkers) */
    int8_t out_dir;   /* steering the last think produced; game.c repeats it on the frames the rival does not think (stagger) */
    uint8_t hold;     /* 1 = AI_HOLD: fly to the target and stand on it (set by game.c for the Roost Rule holder) */
    uint8_t flee;     /* 1 = every think flees the target at any range (Hot Gum: rivals of the carrier; set by game.c) */
} Ai;

/* rank 1 is the arena AI; higher arcade ranks (arcade.h) think sooner. */
void ai_init(Ai *a, Rng *r, int rank);
/* Nearest live rival (state ALIVE or PARACHUTE) among the humans and the computer fliers, by squared distance. NULL
 * when none. self is excluded by pointer. */
const Flier *ai_nearest(const Flier *self, const Flier *humans, int human_count, const Flier *cpus, int cpu_count);
/* The pure decision: state for a flier and its target (no side effects). */
AiState ai_decide(const Flier *self, const Flier *target);
/* One frame: counts the timer down; on zero thinks (state, dir) and re-arms with jitter. target may be
 * NULL (idle). Fills *out for flier_step. */
void ai_step(Ai *a, Rng *r, const Flier *self, const Flier *target, FlierInput *out);
/* The per-frame flap test: dir.y (Q15, y down, negated when fleeing) of the direction (dx, dy) < AI_FLAP_MAX. */
int ai_flap_wanted(AiState s, int32_t dx, int32_t dy);
/* Steering direction (-1, 0, 1) at a think: same answer as the sign test on dir.x of flier_angle, without the angle search. */
int ai_steer_dir(AiState s, int32_t dx, int32_t dy);

#endif
