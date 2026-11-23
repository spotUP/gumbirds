#include "cpu_opponent.h"
#include "game.h"
#include "nameentry.h"

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

uint8_t cpu_bubblegather(Cpu *c, const Flier *bird, const ArcBonus *b)
{
    const CpuLevel *l = cpu_level(c->level);
    int cx = (int)(bird->x >> 16), cy = (int)(bird->y >> 16), best = 0x7FFF, tx = 0, ty = 0, found = 0, i, dx;
    uint8_t in = 0;
    if (b->over) return 0;
    for (i = 0; i < ARC_BONUS_LIVE_MAX; i++) {   /* the nearest live bubble across the seam */
        const ArcBubble *u = &b->b[i];
        int bx = u->x + ARC_BONUS_BOX / 2, by = (int)(u->y16 >> 16) + ARC_BONUS_BOX / 2;
        int d = (arena_dx(bx, cx) < 0 ? -arena_dx(bx, cx) : arena_dx(bx, cx)) + (by > cy ? by - cy : cy - by);
        if (u->live && d < best) { best = d; tx = bx; ty = by; found = 1; }
    }
    if (!found) { c->t = 0; return 0; }
    if (c->t < 0xFFFFu) c->t++;
    if (c->since < 0xFF) c->since++;
    if (c->t < l->delay) return 0;   /* it takes `delay` frames to notice a bubble */
    dx = arena_dx(tx, cx);
    if (dx > 3) in |= IN_RIGHT; else if (dx < -3) in |= IN_LEFT;
    if (cy > ty && c->since >= l->period) {
        if (cpu_act(c, 1)) in |= IN_A;
        c->since = 0;   /* a fumbled flap still costs the hands their beat */
    }
    return in;
}

uint8_t cpu_input(Game *g)
{
    if (g->gg_gather) return cpu_bubblegather(&g->opp, &g->hero[1], &g->bonus);
    if (g->gg_dash) return cpu_flapdash(&g->opp, &g->hero[1]);
    if (g->gg_race) return cpu_burstrace(&g->opp, &g->race);
    if (g->blow.seq.players == 2) return cpu_bigblow(&g->opp, &g->blow);
    return 0;   /* next game: one case here */
}
