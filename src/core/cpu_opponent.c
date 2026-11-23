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
    c->level = level; c->t = 0; c->since = 0xFF; c->flip = 0; c->aim = 0;
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

uint8_t cpu_gumfling(Cpu *c, const GgFling *f)
{
    const CpuLevel *l = cpu_level(c->level);
    uint8_t in = 0;
    if (f->seq.turn != 1) return 0;
    if (f->phase == GF_AIM) {   /* c->flip is the sloppy-throw roll here, rolled once on the first live aim frame */
        if (f->t == GF_AIM_HOLD_FRAMES) c->flip = (int)rng_range(&c->rng, 100u) < l->miss_pct;
        return f->t >= GF_AIM_HOLD_FRAMES + l->delay && (c->flip || f->deg >= CPU_FLING_DEG) ? IN_A : 0;
    }
    if (f->phase != GF_WINDUP && f->phase != GF_FLIGHT) return 0;   /* mash the run-up, then the flap charge */
    if (c->t < 0xFFFFu) c->t++;   /* the reaction timer runs while the hands work */
    if (c->since < 0xFF) c->since++;
    if (c->since >= l->period) {
        if (cpu_act(c, 1)) { in = c->flip ? IN_A : IN_B; c->flip ^= 1; }
        c->since = 0;
    }
    return in;
}

uint8_t cpu_popdrop(Cpu *c, const GgPop *p, const Flier *bird)
{
    const CpuLevel *l = cpu_level(c->level);
    int i, tg = 0, ty = 0x7FFF, tx = 0, dir = 0;
    uint8_t in = 0;
    if (p->phase != PD_FALL || p->b[1].crash) return 0;
    for (i = 0; i < PD_GUMS; i++)   /* the gum trail threads every row's gap: follow the nearest point not yet clear of the bird's box */
        if (p->gum[i].live && p->gum[i].y > PD_BIRD_Y - PD_BIRD_HALF_H - PD_PLAT_H && p->gum[i].y < ty) { ty = p->gum[i].y; tx = p->gum[i].bx; tg = i; }
    if (ty != 0x7FFF) {
        if (c->since != tg) { c->since = (uint8_t)tg; c->aim = (int8_t)((int)rng_range(&c->rng, 2u * l->miss_pct + 1u) - l->miss_pct); }   /* a new gap: misjudge it once by up to miss_pct px either way */
        tx += c->aim;   /* aim for a speed in proportion to the distance, so the stick lets go in time and the bird does not overshoot the gap */
        int32_t want = arena_dx(tx, (int)(bird->x >> 16)) * (65536 / CPU_POP_EASE);
        if (want > PD_STEER) want = PD_STEER; else if (want < -PD_STEER) want = -PD_STEER;
        dir = bird->vx < want - PD_STEER_ACC / 2 ? 1 : bird->vx > want + PD_STEER_ACC / 2 ? -1 : 0;
    }
    if ((uint8_t)dir != c->flip) { c->flip = (uint8_t)dir; c->t = 0; }   /* a new heading is a new cue: the reaction delay restarts */
    if (c->t < 0xFFFFu) c->t++;
    if (dir && cpu_act(c, 1)) in = dir > 0 ? IN_RIGHT : IN_LEFT;   /* a fumbled frame lets go of the stick */
    return in;
}

uint8_t cpu_poopman(Cpu *c, const GgPoop *p)
{
    const CpuLevel *l = cpu_level(c->level);
    const PmBird *b = &p->b[1];
    const PmWalker *w;
    int i, best = -1, bd = 0x7FFF, d, t, dx, tol;
    uint8_t in = 0;
    if (p->phase != PM_PLAY || b->dead || b->stun) return 0;
    if (b->y > CPU_POOP_HOVER_Y && !(b->prev_in & IN_A)) in |= IN_A;   /* hold the street height: flap on the press edge */
    for (i = 0; i < PM_WALKERS; i++) {   /* the nearest walker that can still be hit (no umbrella up) */
        d = (p->w[i].x8 >> 3) - b->x; if (d < 0) d = -d;
        if (p->w[i].live && p->w[i].st == PM_WALK && !p->w[i].umb && d < bd) { bd = d; best = i; }
    }
    if (best < 0) { c->t = 0; c->since = 0xFF; return in; }
    if (c->since != best) { c->since = (uint8_t)best; c->t = 0; c->flip = (uint8_t)((int)rng_range(&c->rng, 100u) < l->miss_pct); }   /* a new target: roll its aim error once */
    if (c->t < 0xFFFFu) c->t++;
    if (c->t < l->delay) return in;   /* it takes `delay` frames to settle on a walker */
    w = &p->w[best];
    d = pm_lane_feet(w->lane) - CPU_POOP_HEAD_H - (b->y + 8);   /* the poop falls d px: y = t(t+1)/8 */
    for (t = 1; t < 40 && t * (t + 1) < 8 * d; t++) {}
    dx = (w->x8 >> 3) + (w->dx8 - PM_SCROLL * 8) * t / 8 - b->x + (c->flip ? CPU_POOP_AIM_ERR : 0);   /* where the walker will be when the poop arrives */
    tol = 3;
    if (dx > tol) in |= IN_RIGHT; else if (dx < -tol) in |= IN_LEFT;
    else if (!b->drop_cd && !(b->prev_in & IN_B)) in |= IN_B;
    return in;
}

uint8_t cpu_input(Game *g)
{
    if (g->gg_poop) return cpu_poopman(&g->opp, &g->poop);
    if (g->gg_gather) return cpu_bubblegather(&g->opp, &g->hero[1], &g->bonus);
    if (g->gg_dash) return cpu_flapdash(&g->opp, &g->hero[1]);
    if (g->gg_race) return cpu_burstrace(&g->opp, &g->race);
    if (g->gg_fling) return cpu_gumfling(&g->opp, &g->fling);
    if (g->blow.seq.players == 2) return cpu_bigblow(&g->opp, &g->blow);
    if (g->gg_pop) return cpu_popdrop(&g->opp, &g->pop, &g->hero[1]);
    return 0;   /* next game: one case here */
}
