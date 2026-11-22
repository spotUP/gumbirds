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
/* Flap Dash: flap when the computer's bird sits below GD_CPU_TARGET_Y, after `delay` frames of seeing it low, at most one press per `period` frames, each press fumbled with miss_pct. */
#define CPU_DASH_TARGET_Y FL_PX(110)
uint8_t cpu_flapdash(Cpu *c, const Flier *bird);
/* Burst Race: pump A/B alternately, one press per `period` frames once the heat is on, after `delay` frames of reaction, each press fumbled with miss_pct. */
uint8_t cpu_burstrace(Cpu *c, const GgRace *r);
#endif
