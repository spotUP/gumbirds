/* arcade.c - arcade mode core (see arcade.h). Portable C99, no malloc, no float. */
#include "arcade.h"
#include "score_table.h" /* SCORE_CAP, the one 6 digit cap */

typedef struct { const char *name; int layout; } ArcStage;
/* Draft order R01 R02 N05 | N03 N06 N04 | N08 N02 N09 | R10 R07 R12b. Layout ids are the stage.c table indices (stage n = layout n - 1). */
static const ArcStage stages[ARC_STAGE_COUNT] = {
    { "R01", ARC_LAYOUT_BASE + 0 }, { "R02", ARC_LAYOUT_BASE + 1 }, { "N05", ARC_LAYOUT_BASE + 2 },
    { "N03", ARC_LAYOUT_BASE + 3 }, { "N06", ARC_LAYOUT_BASE + 4 }, { "N04", ARC_LAYOUT_BASE + 5 },
    { "N08", ARC_LAYOUT_BASE + 6 }, { "N02", ARC_LAYOUT_BASE + 7 }, { "N09", ARC_LAYOUT_BASE + 8 },
    { "R10", ARC_LAYOUT_BASE + 9 }, { "R07", ARC_LAYOUT_BASE + 10 }, { "R12b", ARC_LAYOUT_BASE + 11 },
};
/* Rank per stage (data); each completed loop adds one, capped. */
static const uint8_t stage_rank[ARC_STAGE_COUNT] = { 1, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3 };
static const ArcRank ranks[ARC_RANK_MAX] = { { 150, 500, 1000 }, { 120, 750, 1500 }, { 90, 1000, 2000 } };

static int clamp_stage(int s) { return s < 1 ? 1 : (s > ARC_STAGE_COUNT ? ARC_STAGE_COUNT : s); }
const char *arc_stage_name(int stage) { return stages[clamp_stage(stage) - 1].name; }
int arc_stage_layout(int stage) { return stages[clamp_stage(stage) - 1].layout; }
int arc_rank_for(int stage, int loops) {
    int r = stage_rank[clamp_stage(stage) - 1] + (loops > 0 ? loops : 0);
    return r > ARC_RANK_MAX ? ARC_RANK_MAX : r;
}
const ArcRank *arc_rank(int rank) { return &ranks[(rank < 1 ? 1 : (rank > ARC_RANK_MAX ? ARC_RANK_MAX : rank)) - 1]; }

void arc_start(ArcRun *r) {
    r->stage = 1; r->loops = 0; r->bonus_no = 0; r->state = ARC_PLAY; r->timer = 0; r->gum = ARC_GUM_HEAL;
}
void arc_stage_cleared(ArcRun *r) {
    if (r->state != ARC_PLAY) return;
    r->state = ARC_CLEAR; r->timer = ARC_CLEAR_FRAMES;
}
int arc_next_stage(int stage) { return stage >= ARC_STAGE_COUNT ? ARC_LOOP_STAGE : stage + 1; }

static void go_next(ArcRun *r) {
    if (r->stage >= ARC_STAGE_COUNT) r->loops++;
    r->stage = arc_next_stage(r->stage);
    r->state = ARC_PLAY;
}
int arc_step(ArcRun *r) {
    if (r->state != ARC_CLEAR) return 0;
    if (--r->timer > 0) return 0;
    if (r->stage % ARC_BONUS_EVERY == 0) {
        r->bonus_no++; r->gum = arc_gum_on_bonus(); r->state = ARC_BONUS;
        return 0;
    }
    go_next(r);
    return 1;
}
void arc_bonus_done(ArcRun *r) {
    if (r->state == ARC_BONUS) go_next(r);
}

int arc_gum_after_stage(int gum) { return gum < 0 ? 0 : (gum > ARC_GUM_MAX ? ARC_GUM_MAX : gum); }
int arc_gum_on_bonus(void) { return ARC_GUM_HEAL; }
int arc_gum_on_new_life(void) { return ARC_GUM_HEAL; }

uint32_t arc_score_add(uint32_t score, uint32_t points) {
    if (score >= SCORE_CAP || points >= SCORE_CAP - score) return SCORE_CAP;
    return score + points;
}

/* 0.30 / 0.37 / 0.44 / 0.50 px per frame in 16.16 */
static const int32_t speed16[ARC_BONUS_STEPS] = { 19661, 24248, 28836, 32768 };
static const int value[ARC_BONUS_STEPS] = { 300, 500, 700, 900 };
int32_t arc_bonus_speed16(int step) { return speed16[step < 0 ? 0 : (step >= ARC_BONUS_STEPS ? ARC_BONUS_STEPS - 1 : step)]; }
int arc_bonus_value(int step) { return value[step < 0 ? 0 : (step >= ARC_BONUS_STEPS ? ARC_BONUS_STEPS - 1 : step)]; }

/* Nozzles on the floor strip (own numbers): left x about 15, 34, 65 and 84 percent of the 384 px world; heights 24, 40, 32, 36 (the art in assets/arcade). */
static const int16_t noz_x[ARC_NOZZLE_COUNT] = { 58, 130, 250, 322 };
static const uint8_t noz_h[ARC_NOZZLE_COUNT] = { 24, 40, 32, 36 };
int arc_nozzle_x(int i) { return noz_x[i & 3]; }
int arc_nozzle_top(int i) { return ARC_FLOOR_Y - noz_h[i & 3]; }

/* Speed ladder step per bubble; the seed rotates the start, later bonus numbers raise every step. */
static const uint8_t pat_step[ARC_BONUS_BUBBLES] = { 0, 0, 1, 0, 1, 2, 1, 0, 2, 1, 2, 0, 3, 1, 2, 3, 1, 3, 2, 3 };
/* Sway: 16 steps of a sine (+-8), scaled by an amplitude that damps from 12 px to 2 px with age. */
static const int8_t sway_tab[16] = { 0, 3, 6, 7, 8, 7, 6, 3, 0, -3, -6, -7, -8, -7, -6, -3 };

void arc_bonus_init(ArcBonus *b, int number, uint32_t seed) {
    Rng rng; int i, rot, at = 0, up = number > 1 ? number - 1 : 0;
    rng_seed(&rng, seed);
    rot = (int)rng_range(&rng, ARC_BONUS_BUBBLES);
    b->number = number < 1 ? 1 : number; b->frame = 0; b->caught = 0; b->score = 0; b->over = 0; b->perfect = 0; b->nlive = 0;
    for (i = 0; i < ARC_NOZZLE_COUNT; i++) b->puff[i] = 0;
    for (i = 0; i < ARC_BONUS_BUBBLES; i++) {
        int k = (i + rot) % ARC_BONUS_BUBBLES, s = pat_step[k] + up;
        ArcBubble *u = &b->b[i];
        u->nozzle = (uint8_t)(rng_next(&rng) & 3u);
        u->x0 = (int16_t)(noz_x[u->nozzle] + 8 + (int)(rng_next(&rng) & 7u)); /* the 16 px box stays inside the 32 px mouth */
        u->x = u->x0; u->y16 = (int32_t)(ARC_FLOOR_Y - noz_h[u->nozzle]) * 65536;
        at += ARC_BONUS_GAP_MIN + (int)(rng_next(&rng) & ARC_BONUS_GAP_MASK);
        u->delay = (int16_t)at; u->step = (uint8_t)(s >= ARC_BONUS_STEPS ? ARC_BONUS_STEPS - 1 : s);
        u->live = 0; u->done = 0; u->age = 0;
    }
}

uint32_t arc_bonus_step(ArcBonus *b, int rx, int ry, int rw, int rh) {
    uint32_t won = 0; int i, open = 0;
    if (b->over) return 0;
    b->frame++;
    for (i = 0; i < ARC_NOZZLE_COUNT; i++) if (b->puff[i]) b->puff[i]--;
    for (i = 0; i < ARC_BONUS_BUBBLES; i++) {
        ArcBubble *u = &b->b[i];
        if (u->done) continue;
        if (!u->live) {
            if (b->frame < u->delay || b->nlive >= ARC_BONUS_LIVE_MAX) { open = 1; continue; }
            u->live = 1; b->nlive++; b->puff[u->nozzle] = ARC_BONUS_PUFF_FRAMES;
        }
        u->y16 -= arc_bonus_speed16(u->step); u->age++;
        {
            int y = (int)(u->y16 >> 16), rise = ARC_FLOOR_Y - noz_h[u->nozzle] - y;
            if (rise > ARC_BONUS_STRAIGHT) {
                int amp = 12 - (int)(u->age >> 6); /* shifts, no division */
                u->x = (int16_t)(u->x0 + ((sway_tab[(u->age >> 3) & 15] * (amp < 2 ? 2 : amp)) >> 3));
            }
            if (y + ARC_BONUS_BOX <= 0) { u->done = 1; u->live = 0; b->nlive--; continue; } /* escaped off the top */
            if (u->x < rx + rw && rx < u->x + ARC_BONUS_BOX && y < ry + rh && ry < y + ARC_BONUS_BOX) {
                u->done = 1; u->live = 0; b->nlive--; b->caught++; won += (uint32_t)arc_bonus_value(u->step);
                continue;
            }
        }
        open = 1;
    }
    if (!open || b->frame >= ARC_BONUS_FRAMES) {
        b->over = 1;
        if (b->caught == ARC_BONUS_BUBBLES) { b->perfect = 1; won += ARC_BONUS_PERFECT_UNIT * (uint32_t)b->number; }
    }
    b->score += won;
    return won;
}

void arc_pump_start(ArcPump *p, int rank, int grounded) {
    p->rank = (uint8_t)(rank < 1 ? 1 : (rank > ARC_RANK_MAX ? ARC_RANK_MAX : rank)); p->frame = 0;
    p->state = grounded ? ARC_PUMP_PUMPING : ARC_PUMP_FLYING;
}
void arc_pump_step(ArcPump *p) {
    if (p->state != ARC_PUMP_PUMPING) return;
    if (++p->frame >= arc_rank(p->rank)->pump_frames) p->state = ARC_PUMP_FLYING;
}
int arc_pump_in_window(const ArcPump *p) { return p->state == ARC_PUMP_PUMPING; }
uint32_t arc_pump_resolve(ArcPump *p) {
    if (p->state != ARC_PUMP_PUMPING) return 0;
    p->state = ARC_PUMP_DEFEATED;
    return arc_rank(p->rank)->defeat_score;
}
int arc_pump_progress(const ArcPump *p) {
    /* floor(frame * STAGES / pump_frames) clamped to STAGES, by compares: this runs per pumping rival per frame
       and a 32-bit divide is a libgcc call on the 68000. */
    int pf = arc_rank(p->rank)->pump_frames, t = p->frame * ARC_PUMP_STAGES, n = 0, acc = pf;
    while (n < ARC_PUMP_STAGES && t >= acc) { n++; acc += pf; }
    return n;
}

void arc_lives_start(ArcLives *l) {
    l->lives = ARC_LIVES_START; l->gum = ARC_GUM_HEAL; l->score = 0; l->state = ARC_LIFE_PLAY; l->countdown = 0;
}
void arc_lose_life(ArcLives *l) {
    if (l->state != ARC_LIFE_PLAY) return;
    if (--l->lives > 0) { l->gum = arc_gum_on_new_life(); return; }
    l->lives = 0; l->state = ARC_LIFE_CONTINUE; l->countdown = ARC_CONTINUE_FRAMES;
}
int arc_continue_step(ArcLives *l, int start_pressed, int credits) {
    if (l->state != ARC_LIFE_CONTINUE) return 0;
    if (start_pressed && credits > 0) {
        l->lives = ARC_LIVES_START; l->gum = arc_gum_on_new_life(); l->score = 0; l->state = ARC_LIFE_PLAY; l->countdown = 0;
        return 1;
    }
    if (--l->countdown <= 0) { l->countdown = 0; l->state = ARC_LIFE_ENDED; }
    return 0;
}
int arc_continue_seconds(const ArcLives *l) { return (l->countdown + 59) / 60; }
