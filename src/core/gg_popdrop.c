#include "gg_popdrop.h"
#include "arena.h"
#include "game.h"       /* IN_* */
#include "nameentry.h"  /* IN_LEFT, IN_RIGHT */

static int plat_w(const PdPlat *q) { return 16 * (2 + q->mids); }

static void bird_begin(PdBird *b)
{
    b->hits = 0; b->stun = 0; b->shield = 0; b->shield_count = 0; b->crash = 0; b->land = -1; b->prev_in = 0;
    b->pop_t = 0; b->catch_t = 0; b->bump_t = 0; b->bounce = 0; b->hop = 0; b->flaps = PD_FLAP_MAX; b->flap_t = 0; b->flip = 0;
    b->gums = 0; b->score = 0; b->pose_pick = PD_POSE_BELLY; b->landed = 0; b->pose = 0; b->size = 0;
    b->card[0] = b->card[1] = b->card[2] = 0; b->splash_t = 0; b->splash_f = 0; b->flop = 0;
}

static int16_t pool_surface(const GgPop *p) { return (int16_t)(PD_BIRD_Y + (int)(PD_POOL_DEPTH * 8u) - (int)(p->dist >> 4)); }

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
    p->trail_x = PD_BIRD_X >> 16; p->gap_n = 0;
    for (i = 0; i < PD_FALLERS; i++) p->fall[i].live = 0;
    rng_seed(&p->frng, seed ^ 0x5eedfa11u); p->fall_next = PD_FALLER_EVERY; p->pool_y = pool_surface(p);
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

static int16_t wrap_px(int x) { return (int16_t)(x < 0 ? x + ARENA_W : x >= ARENA_W ? x - ARENA_W : x); }   /* |x| off by < ARENA_W */

/* A new platform row at PD_SPAWN_Y and the gum trail into it. The trail's new gap point is the last one moved sideways by at most
 * 1 px per frame the bird takes to fall from the last row to this one (reachable at any speed), and the platform's centre is drawn
 * anywhere on the ring that keeps its hit box PD_TRAIL_CLEAR px off the whole trail segment. */
static void spawn(GgPop *p, const Flier *hero)
{
    int i, j, low = 0, y0, m, sh, lo, hi, c, half, aim = 0;
    PdPlat *q = 0;
    for (i = 0; i < PD_PLATS; i++) if (p->plat[i].live && p->plat[i].y > low) low = p->plat[i].y;
    if (low > PD_SPAWN_Y - 72) return;           /* the lowest platform has not cleared the gap yet */
    for (i = 0; i < PD_PLATS && !q; i++) if (!p->plat[i].live) q = &p->plat[i];
    if (!q || p->pool_y < PD_SPAWN_Y + PD_PLAT_H + PD_POOL_CLEAR) return;   /* the pool approach stays clear */
    q->kind = (uint8_t)rng_range(&p->rng, 3);
    q->mids = (uint8_t)(1 + rng_range(&p->rng, 3));
    y0 = low > PD_BIRD_Y ? low : PD_BIRD_Y;      /* the last row (the bird itself on the first) */
    m = (PD_SPAWN_Y - y0) * 16 / p->spd;         /* frames to fall to this row = px the trail may move */
    if (m > PD_TRAIL_SHIFT_MAX) m = PD_TRAIL_SHIFT_MAX;
    sh = (int)rng_range(&p->rng, (uint32_t)(2 * m + 1)) - m;
    lo = sh < 0 ? p->trail_x + sh : p->trail_x; hi = sh < 0 ? p->trail_x : p->trail_x + sh;
    half = plat_w(q) / 2;
    c = half + PD_BIRD_HALF_W + PD_TRAIL_CLEAR;  /* centre distance that keeps the bird box clear */
    {   /* aimed row (PD_AIM_SHARE of 4): the platform's near edge overlaps a bird's box by PD_AIM_OVERLAP px on the side away from the new gap point,
         * so a bird that does not steer is hit. Edge-on placement needs only |gap - bird| >= 16 + overlap, so the shift never has to exceed
         * the PD_STEER reach of the fall (2.5 px per frame): PD_TRAIL_SHIFT_MAX stays 48 and the width is not capped. No reachable shift: normal row. */
        uint32_t r = rng_range(&p->rng, 8);      /* bit 0: first sign, bits 1..2: aimed row when below PD_AIM_SHARE (of 4); always drawn so the layout stays deterministic */
        int bi = p->seq.players > 1 ? (int)rng_range(&p->rng, 2) : 0, reach = ((PD_SPAWN_Y - y0) * 16 / p->spd - 20) * 5 / 2, s, d = 0, bx;
        if (p->b[bi].crash) bi ^= 1;             /* aim at a live bird */
        bx = hero[bi].x >> 16;
        if (reach < 0) reach = 0;                /* steering ramps at PD_STEER_ACC: a full reversal (-2.5 to +2.5 px/frame) takes 20 frames and nets 0 px, so only the frames after them count */
        if (reach > PD_TRAIL_SHIFT_MAX) reach = PD_TRAIL_SHIFT_MAX;
        for (s = 0; (r >> 1 & 3) < PD_AIM_SHARE && s < 2 && !aim; s++) {
            int t = (r ^ (uint32_t)s) & 1 ? reach : -reach;
            d = arena_dx(p->trail_x + t, bx);
            if (d >= PD_TRAIL_CLEAR + PD_AIM_OVERLAP || d <= -(PD_TRAIL_CLEAR + PD_AIM_OVERLAP)) { aim = 1; sh = t; }
        }
        if (aim) {
            c = bx + (d > 0 ? -1 : 1) * (half + PD_BIRD_HALF_W - PD_AIM_OVERLAP);
            q->x = wrap_px(wrap_px(c - half + ARENA_W));
        } else {
            c = hi + c + (int)rng_range(&p->rng, (uint32_t)(ARENA_W - 2 * c - (hi - lo) + 1));
            q->x = wrap_px(wrap_px(c - half));   /* c - half < 2 * ARENA_W */
        }
    }
    q->y = PD_SPAWN_Y; q->live = 1; q->hit = 0;
    for (i = 0, j = 1; i < PD_GUMS && j <= PD_TRAIL_GUMS; i++) {
        PdGum *g = &p->gum[i];
        if (g->live) continue;
        g->bx = g->x = wrap_px(p->trail_x + sh * j / PD_TRAIL_GUMS);
        g->y = (int16_t)(y0 + (PD_SPAWN_Y - y0) * j / PD_TRAIL_GUMS);
        g->live = p->gap_n % PD_GUM_EVERY_GAPS == 0 ? 1 : 2;   /* 2 = hidden waypoint of a gum-less gap: no catch, not drawn, keeps the trail line for a follower */
        g->ph = (uint8_t)rng_range(&p->rng, PD_WOBBLE_PERIOD);
        j++;
    }
    p->gap_n++;
    p->trail_x = wrap_px(p->trail_x + sh);
}

static int all_crashed(const GgPop *p) { return p->b[0].crash && (p->seq.players < 2 || p->b[1].crash); }

static void hit(GgPop *p, PdBird *b, int plat)
{
    if (b->shield) { b->shield = 0; b->pop_t = 1; return; }
    b->hits++;
    b->stun = PD_STUN; b->bounce = PD_BOUNCE_START;
    if (p->seq.players < 2)   /* 2P: the scroll is shared, so one bird's hit must not slow the rival (same rule as the 2P hop) */
        p->spd = (uint16_t)(p->spd > PD_SPEED_START + PD_SPEED_HIT_LOSS ? p->spd - PD_SPEED_HIT_LOSS : PD_SPEED_START);
    if (b->gums) b->gums--;
    if (b->hits >= PD_HITS_MAX) { b->crash = 1; if (all_crashed(p)) { b->land = (int8_t)plat; p->phase = PD_CRASH; p->timer = 0; } }   /* only the last crash lies on its island; an earlier 2P crash stays a ghost */
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
    if (edge & IN_B) b->pose_pick = PD_POSE_CANNON;
    if (edge & IN_C) b->pose_pick = PD_POSE_FACE;
    if (edge & IN_D) b->pose_pick = PD_POSE_BELLY;
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

/* Move platforms and gums up by step px; drop the ones past the top. The gags rise at half that (they fall too; shortcut: step / 2 rounds down) and drift sideways. */
static void scroll_world(GgPop *p, int step)
{
    int i;
    p->pool_y = pool_surface(p);
    for (i = 0; i < PD_FALLERS; i++) {
        PdFaller *f = &p->fall[i];
        if (!f->live) continue;
        f->y = (int16_t)(f->y - (step >> 1));
        if ((p->timer & 3u) == 0) f->x = wrap_px(f->x + f->dx);
        if (f->y < -48) f->live = 0;
    }
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
        if (++g->ph >= PD_WOBBLE_PERIOD) g->ph = 0;
        {   /* triangle wobble: v 0..PD_WOBBLE_PERIOD/2 and back, centred, scaled to +-PD_WOBBLE_PX */
            int per = PD_WOBBLE_PERIOD, v = g->ph < per / 2 ? g->ph : per - g->ph;
            g->x = wrap_px(g->bx + (v - per / 4) * PD_WOBBLE_PX / (per / 4));
        }
    }
}

/* Card base by pose and splash size; judges differ by -1 / +1 / 0. A slow belly flop is a joke, a fast face-first dive is the best score. */
static const uint8_t card_base[3][3] = { { 3, 5, 6 }, { 4, 6, 8 }, { 2, 5, 9 } };
static const int8_t judge_off[PD_JUDGES] = { -1, 1, 0 };

static void spawn_faller(GgPop *p)
{
    int i;
    if (p->timer < p->fall_next) return;
    for (i = 0; i < PD_FALLERS; i++) {
        PdFaller *f = &p->fall[i];
        if (f->live) continue;
        f->kind = (uint8_t)rng_range(&p->frng, 3); f->x = (int16_t)rng_range(&p->frng, ARENA_W);
        f->dx = (int8_t)(rng_range(&p->frng, 2) ? 1 : -1); f->y = PD_SPAWN_Y; f->live = 1;
        break;
    }
    p->fall_next = (uint16_t)(p->timer + PD_FALLER_EVERY + rng_range(&p->frng, PD_FALLER_EVERY));
}

/* The feet touch the surface: every bird still alive flops and the world brakes (spd decays, the birds sink a few px). */
static uint16_t bird_impact_spd(const GgPop *p, const PdBird *b)
{
    unsigned loss = p->seq.players < 2 ? 0u : b->hits * PD_SPEED_HIT_LOSS;
    return (uint16_t)(p->spd > PD_SPEED_START + loss ? p->spd - loss : (p->spd < PD_SPEED_START ? p->spd : PD_SPEED_START));
}

static void pool_land(GgPop *p, int n)
{
    int k, j;
    p->phase = PD_POOL; p->timer = 0; p->depth = PD_POOL_DEPTH;
    for (k = 0; k < n; k++) {
        PdBird *b = &p->b[k];
        if (b->crash) continue;
        b->landed = 1; b->pose = b->pose_pick;
        { uint16_t v = bird_impact_spd(p, b); b->size = v >= PD_SIZE_BIG ? PD_SPLASH_BIG : v >= PD_SIZE_MEDIUM ? PD_SPLASH_MEDIUM : PD_SPLASH_SMALL; }
        b->flop = 0;
        for (j = 0; j < PD_JUDGES; j++) {
            int c = card_base[b->pose][b->size] + judge_off[j];
            b->card[j] = (uint8_t)(c < 1 ? 1 : c > 10 ? 10 : c);
            b->flop = (uint16_t)(b->flop + b->card[j] * PD_FLOP_MULT);
        }
        b->score = (uint16_t)(PD_POOL_DEPTH + b->gums + b->flop);
    }
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
    scroll_world(p, step);

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
            if (!q->live || (q->hit >> k & 1) || b->stun) continue;
            if (q->y < by + PD_BIRD_HALF_H && q->y + PD_PLAT_H > by - PD_BIRD_HALF_H) {
                half = plat_w(q) / 2;
                d = arena_dx(bx, q->x + half);
                if (d < 0) d = -d;
                if (d < half + PD_BIRD_HALF_W) { q->hit |= (uint8_t)(1u << k); hit(p, b, i); }   /* one hit bit per bird: the rival still hits this platform */
            }
        }
        for (i = 0; i < PD_GUMS; i++) {
            PdGum *g = &p->gum[i];
            int d;
            if (g->live != 1 || b->crash) continue;
            d = arena_dx(bx, g->x); if (d < 0) d = -d;
            if (d < PD_BIRD_HALF_W + 8 && g->y > by - PD_BIRD_HALF_H - 8 && g->y < by + PD_BIRD_HALF_H + 8) {
                g->live = 0; b->gums++; b->catch_t = 1;
                if (++b->shield_count >= PD_SHIELD_EVERY) { b->shield_count = 0; b->shield = 1; }
            }
        }
        b->score = (uint16_t)(p->depth + b->gums);
    }
    if (p->phase == PD_FALL && p->pool_y <= PD_BIRD_Y + PD_BIRD_HALF_H) pool_land(p, n);
    if (p->phase == PD_FALL) { spawn(p, hero); spawn_faller(p); }
}

int gp_step(GgPop *p, Flier *hero, uint8_t in1, uint8_t in2)
{
    switch (p->phase) {
    case PD_FALL:
        fall_step(p, hero, in1, in2);
        break;
    case PD_CRASH:
        {   /* the world scrolls on at the crash speed (depth frozen): the crashed bird lies on its island and rides off with it */
            uint32_t before = p->dist >> 4;
            p->dist += p->spd;
            scroll_world(p, (int)((p->dist >> 4) - before));
        }
        if (++p->timer >= PD_CRASH_FRAMES) attempt_end(p);
        break;
    case PD_POOL:
        {   /* the world keeps scrolling while the speed bleeds off, so the birds sink into the pool */
            uint32_t before = p->dist >> 4;
            p->dist += p->spd;
            p->spd = (uint16_t)(p->spd - p->spd / 8 - (p->spd > 0));
            scroll_world(p, (int)((p->dist >> 4) - before));
        }
        { int k; for (k = 0; k < p->seq.players; k++) { PdBird *b = &p->b[k]; if (b->landed && b->splash_t < 255) b->splash_t++;
            b->splash_f = (uint8_t)(b->splash_t / PD_SPLASH_TICKS); if (b->splash_f >= PD_SPLASH_LEN(b->size)) b->splash_f = (uint8_t)(PD_SPLASH_LEN(b->size) - 1); } }
        if (++p->timer >= PD_POOL_FRAMES) attempt_end(p);
        break;
    case PD_RESULT:
        p->end_t++;
        if (++p->timer >= PD_RESULT_FRAMES && !p->done) { p->done = 1; return 1; }
        break;
    }
    return 0;
}
