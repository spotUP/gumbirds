#include "cpu_opponent.h"
#include "game.h"

static const CpuLevel cpu_levels[CPU_LEVELS] = {
    /* delay, miss_pct, period */
    { 3, 25, 5 },   /* Off row, never used: reads as Easy */
    { 3, 25, 5 },   /* Easy */
    { 2, 12, 4 },   /* Normal */
    { 1, 3,  4 },   /* Hard */
};

const CpuLevel *cpu_level(uint8_t level) { return &cpu_levels[level > CPU_HARD || level == CPU_OFF ? CPU_EASY : level]; }

void cpu_init(Cpu *c, uint8_t level, uint32_t seed)
{
    c->level = level; c->t = 0; c->since = 0xFF; c->flip = 0;
    rng_seed(&c->rng, seed);
}

int cpu_act(Cpu *c, int want)
{
    const CpuLevel *l = cpu_level(c->level);
    if (!want || c->t < l->delay) return 0;
    return (int)rng_range(&c->rng, 100u) >= l->miss_pct;
}

uint8_t cpu_flapdash(Cpu *c, const Flier *bird)
{
    const CpuLevel *l = cpu_level(c->level);
    int low = bird->y > CPU_DASH_TARGET_Y;
    uint8_t in = 0;
    if (low) { if (c->t < 0xFFFFu) c->t++; } else c->t = 0;
    if (c->since < 0xFF) c->since++;
    if (cpu_act(c, low && c->since >= l->period)) { in = c->flip ? IN_A : IN_B; c->flip ^= 1; }
    if (low && c->since >= l->period) c->since = 0;   /* a fumbled press still costs the hands their beat */
    return in;
}

uint8_t cpu_burstrace(Cpu *c, const GgRace *r)
{
    const CpuLevel *l = cpu_level(c->level);
    uint8_t in = 0;
    if (r->phase != GG_RACE_PLAY) return 0;
    if (c->t < 0xFFFFu) c->t++;   /* the cue is the GO */
    if (c->since < 0xFF) c->since++;
    if (c->since >= l->period) {
        if (cpu_act(c, 1)) { in = c->flip ? IN_A : IN_B; c->flip ^= 1; }
        c->since = 0;   /* a fumbled press still costs the hands their beat */
    }
    return in;
}

uint8_t cpu_bigblow(Cpu *c, const GgBlow *b)
{
    const CpuLevel *l = cpu_level(c->level);
    int my_turn = b->seq.turn == 1 && b->phase == GG_BLOW_PLAY;
    int want = my_turn && b->size < CPU_BLOW_TARGET;
    uint8_t in = 0;
    if (my_turn) { if (c->t < 0xFFFFu) c->t++; } else { c->t = 0; c->since = 0xFF; }
    if (c->since < 0xFF) c->since++;
    if (cpu_act(c, want && c->since >= l->period)) { in = c->flip ? IN_A : IN_B; c->flip ^= 1; }
    if (want && c->since >= l->period) c->since = 0;
    return in;
}

uint8_t cpu_input(Game *g)
{
    if (g->gg_dash) return cpu_flapdash(&g->opp, &g->hero[1]);
    if (g->gg_race) return cpu_burstrace(&g->opp, &g->race);
    if (g->blow.seq.players == 2) return cpu_bigblow(&g->opp, &g->blow);
    return 0;   /* next game: one case here */
}
