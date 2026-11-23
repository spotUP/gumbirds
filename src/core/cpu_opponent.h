#ifndef CPU_OPPONENT_H
#define CPU_OPPONENT_H
#include <stdint.h>
#include "rng.h"

/* CPU opponent for the Gum Games (pure logic): in a 1-player game the computer plays P2 through Game.input2 with the rules of 2-player.
 * Each game adds ONE function `uint8_t cpu_<game>(Cpu *c, ...)` returning a P2 input byte, plus one case in cpu_input (cpu_opponent.c).
 * The difficulty is one table (cpu_levels in cpu_opponent.c): reaction delay, error rate and action rate by level. */
enum { CPU_OFF, CPU_EASY, CPU_NORMAL, CPU_HARD, CPU_LEVELS };

typedef struct {
    uint8_t delay;       /* frames the computer takes to react to a cue (the GO of a countdown, a new target) */
    uint8_t miss_pct;    /* percent of intended actions it fumbles (0..100) */
    uint8_t period;      /* frames between intended actions of a mash game (lower = faster hands) */
} CpuLevel;

typedef struct {
    uint8_t level;       /* CPU_* */
    uint16_t t;          /* frames the current cue has held (the reaction timer) */
    uint8_t since;       /* frames since the last action (the hands) */
    uint8_t flip;        /* alternates A and B in mash games */
    Rng rng;
} Cpu;

/* Row of the table for a level (CPU_OFF reads as Easy so no caller indexes out of range). */
const CpuLevel *cpu_level(uint8_t level);
/* Start the computer at `level`; the seed drives every error roll, so a run replays. */
void cpu_init(Cpu *c, uint8_t level, uint32_t seed);
/* 1 when an intended action goes through this frame: false for the first `delay` frames of the cue and on a miss roll. Call once per intended action. */
int cpu_act(Cpu *c, int want);

#include "flier.h"
#include "gumgames.h"
#include "arcade.h"
/* Flap Dash: flap when the computer's bird sits below GD_CPU_TARGET_Y, after `delay` frames of seeing it low, at most one press per `period` frames, each press fumbled with miss_pct. */
#define CPU_DASH_TARGET_Y FL_PX(110)
uint8_t cpu_flapdash(Cpu *c, const Flier *bird);
/* Burst Race: pump A/B alternately, one press per `period` frames once the heat is on, after `delay` frames of reaction, each press fumbled with miss_pct. */
uint8_t cpu_burstrace(Cpu *c, const GgRace *r);
#include "gumgames.h"
/* Big Blow: on its own turn it pumps (alternating A and B, one press per `period` frames, each fumbled with miss_pct, after `delay` frames) until the bubble reaches CPU_BLOW_TARGET, then lets it leak and tops it up. */
#define CPU_BLOW_TARGET 54u   /* above the qualifying size 48, below the burst at GG_BLOW_MAX */
uint8_t cpu_bigblow(Cpu *c, const GgBlow *b);
/* Bubble Gather: fly at the nearest live bubble (steer by the seam-wrapped dx, flap while the bird is below it), after `delay` frames of seeing it, at most one flap per `period` frames, each flap fumbled with miss_pct. */
uint8_t cpu_bubblegather(Cpu *c, const Flier *bird, const ArcBonus *b);
/* Pop Drop: steer toward the nearest gum-trail point the platforms have not yet passed (the trail runs through every row's gap); a new heading waits `delay` frames, each steering frame is fumbled with miss_pct. */
#define CPU_POP_EASE 8   /* the wanted speed is the distance to the gap over this many frames */
#include "gg_popdrop.h"
uint8_t cpu_popdrop(Cpu *c, const GgPop *p, const Flier *bird);
#include "gg_fling.h"
/* Gum Fling: on its turn it mashes the run-up and the flight flap like Burst Race (one press per `period`, fumbled with miss_pct), then stops the needle `delay` frames into the aim at CPU_FLING_DEG; a miss_pct roll makes the throw sloppy (needle stopped at once, a flat low throw). */
#define CPU_FLING_DEG 45u
uint8_t cpu_gumfling(Cpu *c, const GgFling *f);
#endif
