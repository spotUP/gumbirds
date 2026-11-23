#include "cpu_opponent.h"
#include "game.h"
#include "arena.h"
#include "nameentry.h"   /* IN_LEFT, IN_RIGHT */

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

uint8_t cpu_popdrop(Cpu *c, const GgPop *p, const Flier *bird)
{
    int i, ty = 0x7FFF, tx = 0, dir = 0;
    uint8_t in = 0;
    if (p->phase != PD_FALL || p->b[1].crash) return 0;
    for (i = 0; i < PD_GUMS; i++)   /* the gum trail threads every row's gap: follow the nearest point not yet clear of the bird's box */
        if (p->gum[i].live && p->gum[i].y > PD_BIRD_Y - PD_BIRD_HALF_H - PD_PLAT_H && p->gum[i].y < ty) { ty = p->gum[i].y; tx = p->gum[i].bx; }
    if (ty != 0x7FFF) {   /* aim for a speed in proportion to the distance, so the stick lets go in time and the bird does not overshoot the gap */
        int32_t want = arena_dx(tx, (int)(bird->x >> 16)) * (65536 / CPU_POP_EASE);
        if (want > PD_STEER) want = PD_STEER; else if (want < -PD_STEER) want = -PD_STEER;
        dir = bird->vx < want - PD_STEER_ACC / 2 ? 1 : bird->vx > want + PD_STEER_ACC / 2 ? -1 : 0;
    }
    if (dir != c->flip) { c->flip = (uint8_t)dir; c->t = 0; }   /* a new heading is a new cue: the reaction delay restarts */
    if (c->t < 0xFFFFu) c->t++;
    if (dir && cpu_act(c, 1)) in = dir > 0 ? IN_RIGHT : IN_LEFT;   /* a fumbled frame lets go of the stick */
    return in;
}

uint8_t cpu_input(Game *g)
{
    if (g->gg_dash) return cpu_flapdash(&g->opp, &g->hero[1]);
    if (g->gg_race) return cpu_burstrace(&g->opp, &g->race);
    if (g->gg_pop) return cpu_popdrop(&g->opp, &g->pop, &g->hero[1]);
    return 0;   /* next game: one case here */
}
