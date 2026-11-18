#include "gg_popdrop.h"
#include "arena.h"
#include "game.h"       /* IN_* */
#include "nameentry.h"  /* IN_LEFT, IN_RIGHT */

static int plat_w(const PdPlat *q) { return 16 * (2 + q->mids); }

/* Start one fall (keeps seq and the rng). */
static void fall_begin(GgPop *p, Flier *hero)
{
    int i;
    for (i = 0; i < PD_PLATS; i++) p->plat[i].live = 0;
    for (i = 0; i < PD_GUMS; i++) p->gum[i].live = 0;
    p->phase = PD_FALL; p->hits = 0; p->stun = 0; p->shield = 0; p->shield_count = 0;
    p->pop_t = 0; p->catch_t = 0; p->bounce = 0; p->flip = 0; p->gums = 0;
    p->timer = 0; p->dist = 0; p->depth = 0; p->score = 0; p->spd = PD_SPEED_START;
    flier_init(hero, PD_BIRD_X, FL_PX(PD_BIRD_Y), 0, 0);
}

void gp_init(GgPop *p, Flier *hero, uint32_t seed)
{
    p->done = 0; p->end_t = 0; p->prev_in = 0; p->last_score = 0;
    rng_seed(&p->rng, seed);
    gg_seq_start(&p->seq, GG_POP_DROP, 1);
    p->seq.tickets[0] = 1;
    fall_begin(p, hero);
}

void gp_add_p2(GgPop *p)
{
    p->seq.players = 2;
    p->seq.tickets[1] = 1;
}

static void spawn(GgPop *p)
{
    int i, low = 0;
    for (i = 0; i < PD_PLATS; i++) if (p->plat[i].live && p->plat[i].y > low) low = p->plat[i].y;
    if (low > PD_SPAWN_Y - 72) return;           /* the lowest platform has not cleared the gap yet */
    for (i = 0; i < PD_PLATS; i++) {
        PdPlat *q = &p->plat[i];
        if (q->live) continue;
        q->kind = (uint8_t)rng_range(&p->rng, 3);
        q->mids = (uint8_t)(1 + rng_range(&p->rng, 3));
        q->x = (int16_t)rng_range(&p->rng, ARENA_W);          /* the ring wraps, so any left edge is legal */
        q->y = PD_SPAWN_Y; q->live = 1; q->hit = 0;
        break;
    }
    for (i = 0; i < PD_GUMS; i++) {                /* a gum drifts up behind the platform, at its own x */
        PdGum *g = &p->gum[i];
        if (g->live) continue;
        g->x = (int16_t)rng_range(&p->rng, ARENA_W); g->y = PD_SPAWN_Y + 44; g->live = 1;
        break;
    }
}

static void hit(GgPop *p)
{
    if (p->shield) { p->shield = 0; p->pop_t = 1; return; }
    p->hits++;
    p->stun = PD_STUN; p->bounce = PD_BOUNCE_START;
    p->spd = (uint16_t)(p->spd > PD_SPEED_START + PD_SPEED_HIT_LOSS ? p->spd - PD_SPEED_HIT_LOSS : PD_SPEED_START);
    if (p->gums) p->gums--;
    if (p->hits >= PD_HITS_MAX) { p->phase = PD_CRASH; p->timer = 0; }
}

static void attempt_end(GgPop *p, Flier *hero)
{
    uint32_t stage = p->score / PD_STAGE_SCORE;
    p->last_score = p->score;
    if (stage > 255) stage = 255;
    if (gg_seq_attempt(&p->seq, p->score, (uint8_t)stage, p->score >= PD_QUALIFY)) {
        p->phase = PD_PAUSE; p->timer = 0;
    } else {
        p->phase = PD_RESULT; p->timer = 0;
    }
    (void)hero;
}

static void fall_step(GgPop *p, Flier *hero, uint8_t in)
{
    int i, bx, step, dir = ((in & IN_RIGHT) ? 1 : 0) - ((in & IN_LEFT) ? 1 : 0);
    uint32_t before = p->dist >> 4;

    if (p->stun) { p->stun--; dir = 0; }
    if (dir) { hero->vx += dir * PD_STEER_ACC; p->flip = (uint8_t)(dir < 0); }
    else if (hero->vx > PD_STEER_ACC) hero->vx -= PD_STEER_ACC / 2;
    else if (hero->vx < -PD_STEER_ACC) hero->vx += PD_STEER_ACC / 2;
    else hero->vx = 0;
    if (hero->vx > PD_STEER) hero->vx = PD_STEER;
    if (hero->vx < -PD_STEER) hero->vx = -PD_STEER;
    hero->x = arena_wrap_x(hero->x + hero->vx);
    hero->facing = (uint8_t)!p->flip;

    p->timer++;
    if (p->spd < PD_SPEED_MAX && p->timer % PD_SPEED_RAMP == 0) p->spd++;
    p->dist += p->spd;
    step = (int)((p->dist >> 4) - before);
    p->depth = (uint16_t)(p->dist >> 7);
    if (p->bounce < 0) p->bounce++;
    if (p->pop_t && ++p->pop_t > 24) p->pop_t = 0;
    if (p->catch_t && ++p->catch_t > 16) p->catch_t = 0;

    bx = hero->x >> 16;
    for (i = 0; i < PD_PLATS; i++) {
        PdPlat *q = &p->plat[i];
        int w, half;
        if (!q->live) continue;
        q->y = (int16_t)(q->y - step);
        if (q->y < -PD_PLAT_H) { q->live = 0; continue; }
        w = plat_w(q); half = w / 2;
        if (!q->hit && !p->stun && p->phase == PD_FALL && q->y < PD_BIRD_Y + PD_BIRD_HALF_H && q->y + PD_PLAT_H > PD_BIRD_Y - PD_BIRD_HALF_H) {
            int d = arena_dx(bx, q->x + half);
            if (d < 0) d = -d;
            if (d < half + PD_BIRD_HALF_W) { q->hit = 1; hit(p); }
        }
    }
    for (i = 0; i < PD_GUMS; i++) {
        PdGum *g = &p->gum[i];
        int d;
        if (!g->live) continue;
        g->y = (int16_t)(g->y - step);
        if (g->y < -16) { g->live = 0; continue; }
        d = arena_dx(bx, g->x); if (d < 0) d = -d;
        if (p->phase == PD_FALL && d < PD_BIRD_HALF_W + 8 && g->y > PD_BIRD_Y - PD_BIRD_HALF_H - 8 && g->y < PD_BIRD_Y + PD_BIRD_HALF_H + 8) {
            g->live = 0; p->gums++; p->catch_t = 1;
            if (++p->shield_count >= PD_SHIELD_EVERY) { p->shield_count = 0; p->shield = 1; }
        }
    }
    if (p->phase == PD_FALL) spawn(p);
    p->score = (uint16_t)(p->depth + p->gums);
}

int gp_step(GgPop *p, Flier *hero, uint8_t in)
{
    p->prev_in = in;
    switch (p->phase) {
    case PD_FALL:
        fall_step(p, hero, in);
        break;
    case PD_CRASH:
        if (++p->timer >= PD_CRASH_FRAMES) attempt_end(p, hero);
        break;
    case PD_PAUSE:
        if (++p->timer >= PD_PAUSE_FRAMES) fall_begin(p, hero);
        break;
    case PD_RESULT:
        p->end_t++;
        if (++p->timer >= PD_RESULT_FRAMES && !p->done) { p->done = 1; return 1; }
        break;
    }
    return 0;
}
