#include "gg_popdrop.h"
#include "arena.h"
#include "game.h"       /* IN_* */
#include "nameentry.h"  /* IN_LEFT, IN_RIGHT */

static int plat_w(const PdPlat *q) { return 16 * (2 + q->mids); }

static void bird_begin(PdBird *b)
{
    b->hits = 0; b->stun = 0; b->shield = 0; b->shield_count = 0; b->crash = 0; b->prev_in = 0;
    b->pop_t = 0; b->catch_t = 0; b->bump_t = 0; b->bounce = 0; b->hop = 0; b->flaps = PD_FLAP_MAX; b->flap_t = 0; b->flip = 0;
    b->gums = 0; b->score = 0;
}

void gp_init(GgPop *p, Flier *hero, uint32_t seed)
{
    int i;
    p->done = 0; p->end_t = 0; p->last_score = 0;
    rng_seed(&p->rng, seed);
    gg_seq_start(&p->seq, GG_POP_DROP, 1);
    p->seq.tickets[0] = 1;
    for (i = 0; i < PD_PLATS; i++) p->plat[i].live = 0;
    for (i = 0; i < PD_GUMS; i++) p->gum[i].live = 0;
    bird_begin(&p->b[0]); bird_begin(&p->b[1]);
    p->phase = PD_FALL; p->brake_t = 0;
    p->timer = 0; p->dist = 0; p->depth = 0; p->spd = PD_SPEED_START;
    flier_init(hero, PD_BIRD_X, FL_PX(PD_BIRD_Y), 0, 0);
}

void gp_add_p2(GgPop *p, Flier *hero, Flier *hero2)
{
    p->seq.players = 2;
    p->seq.tickets[1] = 1;
    bird_begin(&p->b[1]);
    flier_init(hero, PD_BIRD_X - FL_PX(PD_P2_GAP / 2), FL_PX(PD_BIRD_Y), 0, 0);
    flier_init(hero2, PD_BIRD_X + FL_PX(PD_P2_GAP / 2), FL_PX(PD_BIRD_Y), 0, 0);
    hero2->facing = 0; p->b[1].flip = 1;     /* the pair face each other */
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

static int all_crashed(const GgPop *p) { return p->b[0].crash && (p->seq.players < 2 || p->b[1].crash); }

static void hit(GgPop *p, PdBird *b)
{
    if (b->shield) { b->shield = 0; b->pop_t = 1; return; }
    b->hits++;
    b->stun = PD_STUN; b->bounce = PD_BOUNCE_START;
    p->spd = (uint16_t)(p->spd > PD_SPEED_START + PD_SPEED_HIT_LOSS ? p->spd - PD_SPEED_HIT_LOSS : PD_SPEED_START);
    if (b->gums) b->gums--;
    if (b->hits >= PD_HITS_MAX) { b->crash = 1; if (all_crashed(p)) { p->phase = PD_CRASH; p->timer = 0; } }
}

/* Both scores go to their own GgSeq slot (the seq turn hands over after each call). */
static void attempt_end(GgPop *p)
{
    int i;
    p->last_score = 0;
    for (i = 0; i < p->seq.players; i++) {
        uint32_t stage = p->b[i].score / PD_STAGE_SCORE;
        if (stage > 255) stage = 255;
        if (p->b[i].score > p->last_score) p->last_score = p->b[i].score;
        gg_seq_attempt(&p->seq, p->b[i].score, (uint8_t)stage, p->b[i].score >= PD_QUALIFY);
    }
    p->phase = PD_RESULT; p->timer = 0;
}

/* Steering and the brake hop of one bird (a ghost steers too). */
static void bird_steer(GgPop *p, PdBird *b, Flier *hero, uint8_t in)
{
    uint8_t edge = (uint8_t)(in & ~b->prev_in);   /* A press, new this frame */
    int dir = ((in & IN_RIGHT) ? 1 : 0) - ((in & IN_LEFT) ? 1 : 0);
    b->prev_in = in;
    if (b->stun) { b->stun--; dir = 0; }
    else if ((edge & IN_A) && b->flaps) {
        b->flaps--;
        if (p->seq.players == 2) b->hop = -PD_HOP_PX_2P;      /* 2P: the shared scroll is not slowed */
        else { b->hop = -PD_HOP_PX; p->brake_t = PD_BRAKE_FRAMES; }
    }
    if (b->flaps < PD_FLAP_MAX && ++b->flap_t >= PD_FLAP_REFILL) { b->flaps++; b->flap_t = 0; }
    if (b->flaps == PD_FLAP_MAX) b->flap_t = 0;
    if (dir) { hero->vx += dir * PD_STEER_ACC; b->flip = (uint8_t)(dir < 0); }
    else if (hero->vx > PD_STEER_ACC) hero->vx -= PD_STEER_ACC / 2;
    else if (hero->vx < -PD_STEER_ACC) hero->vx += PD_STEER_ACC / 2;
    else hero->vx = 0;
    if (hero->vx > PD_STEER) hero->vx = PD_STEER;
    if (hero->vx < -PD_STEER) hero->vx = -PD_STEER;
    hero->x = arena_wrap_x(hero->x + hero->vx);
    hero->facing = (uint8_t)!b->flip;
}

/* Bird-bird bump (2P, both alive): equal-mass bounce along x, so the faster mover hands the slower its speed (pushes harder);
 * both leave at PD_PUSH_KICK or more and are moved out of the overlap. No damage; an island hit after a shove is a normal hit. */
static void push_apart(GgPop *p, Flier *h)
{
    int dx = arena_dx(h[1].x >> 16, h[0].x >> 16), dy = p->b[1].hop - p->b[0].hop, s, adx, push;
    int32_t v;
    adx = dx < 0 ? -dx : dx;
    if (adx >= 2 * PD_BIRD_HALF_W || dy >= 2 * PD_BIRD_HALF_H || dy <= -2 * PD_BIRD_HALF_H) return;
    s = dx < 0 ? -1 : 1;                                  /* direction from bird 0 to bird 1 */
    if ((h[0].vx - h[1].vx) * s > 0) { v = h[0].vx; h[0].vx = h[1].vx; h[1].vx = v; }
    if (h[1].vx * s < PD_PUSH_KICK) h[1].vx = s * PD_PUSH_KICK;
    if (h[0].vx * s > -PD_PUSH_KICK) h[0].vx = -s * PD_PUSH_KICK;
    push = (2 * PD_BIRD_HALF_W - adx + 1) / 2;
    h[0].x = arena_wrap_x(h[0].x - FL_PX(s * push));
    h[1].x = arena_wrap_x(h[1].x + FL_PX(s * push));
    p->b[0].bump_t = 1; p->b[1].bump_t = 1;               /* hook: squawk + feather puff (no sound id or art yet) */
}

static void fall_step(GgPop *p, Flier *hero, uint8_t in1, uint8_t in2)
{
    int i, k, step, n = p->seq.players == 2 ? 2 : 1;
    uint32_t before = p->dist >> 4;

    for (k = 0; k < n; k++) bird_steer(p, &p->b[k], &hero[k], k ? in2 : in1);
    if (n == 2 && !p->b[0].crash && !p->b[1].crash) push_apart(p, hero);

    p->timer++;
    if (p->spd < PD_SPEED_MAX && p->timer % PD_SPEED_RAMP == 0) p->spd++;
    if (p->brake_t) { p->brake_t--; p->dist += p->spd >> 1; } else p->dist += p->spd;
    step = (int)((p->dist >> 4) - before);
    p->depth = (uint16_t)(p->dist >> 7);
    for (i = 0; i < PD_PLATS; i++) {
        PdPlat *q = &p->plat[i];
        if (!q->live) continue;
        q->y = (int16_t)(q->y - step);
        if (q->y < -PD_PLAT_H) q->live = 0;
    }
    for (i = 0; i < PD_GUMS; i++) {
        PdGum *g = &p->gum[i];
        if (!g->live) continue;
        g->y = (int16_t)(g->y - step);
        if (g->y < -16) g->live = 0;
    }

    for (k = 0; k < n; k++) {
        PdBird *b = &p->b[k];
        int bx = hero[k].x >> 16, by = PD_BIRD_Y + b->hop;
        if (b->bounce < 0) b->bounce++;
        if (b->hop < 0) b->hop++;   /* sinks back after the frame it was set */
        if (b->pop_t && ++b->pop_t > 24) b->pop_t = 0;
        if (b->catch_t && ++b->catch_t > 16) b->catch_t = 0;
        if (b->bump_t && ++b->bump_t > 16) b->bump_t = 0;
        if (b->crash) continue;     /* a ghost (or the crashed 1P bird) touches nothing */
        for (i = 0; i < PD_PLATS; i++) {
            PdPlat *q = &p->plat[i];
            int half, d;
            if (!q->live || q->hit || b->stun) continue;
            if (q->y < by + PD_BIRD_HALF_H && q->y + PD_PLAT_H > by - PD_BIRD_HALF_H) {
                half = plat_w(q) / 2;
                d = arena_dx(bx, q->x + half);
                if (d < 0) d = -d;
                if (d < half + PD_BIRD_HALF_W) { q->hit = 1; hit(p, b); }   /* shortcut: q->hit is shared, so the other bird passes through a platform already hit; give PdPlat a hit bit per bird if play-tests show it */
            }
        }
        for (i = 0; i < PD_GUMS; i++) {
            PdGum *g = &p->gum[i];
            int d;
            if (!g->live || b->crash) continue;
            d = arena_dx(bx, g->x); if (d < 0) d = -d;
            if (d < PD_BIRD_HALF_W + 8 && g->y > by - PD_BIRD_HALF_H - 8 && g->y < by + PD_BIRD_HALF_H + 8) {
                g->live = 0; b->gums++; b->catch_t = 1;
                if (++b->shield_count >= PD_SHIELD_EVERY) { b->shield_count = 0; b->shield = 1; }
            }
        }
        b->score = (uint16_t)(p->depth + b->gums);
    }
    if (p->phase == PD_FALL) spawn(p);
}

int gp_step(GgPop *p, Flier *hero, uint8_t in1, uint8_t in2)
{
    switch (p->phase) {
    case PD_FALL:
        fall_step(p, hero, in1, in2);
        break;
    case PD_CRASH:
        if (++p->timer >= PD_CRASH_FRAMES) attempt_end(p);
        break;
    case PD_RESULT:
        p->end_t++;
        if (++p->timer >= PD_RESULT_FRAMES && !p->done) { p->done = 1; return 1; }
        break;
    }
    return 0;
}
