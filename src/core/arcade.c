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

/* Reference (Balloon Fight bonus, thoughts/spot/2026-11-13-bonus-ref.md): one rise speed per bonus number, 0.500 / 0.5625 / 0.59375 / 0.625 / 0.65625 px per frame in 16.16. */
static const int32_t speed16[5] = { 32768, 36864, 38912, 40960, 43008 };
static const int value[5] = { 300, 500, 700, 700, 700 };
static const int perfect[5] = { 10000, 15000, 20000, 25000, 30000 };
#define BONUS_IDX(n) ((n) < 1 ? 0 : ((n) > 5 ? 4 : (n) - 1))
int32_t arc_bonus_speed16(int number) { return speed16[BONUS_IDX(number)]; }
int arc_bonus_value(int number) { return value[BONUS_IDX(number)]; }
int arc_bonus_perfect(int number) { return perfect[BONUS_IDX(number)]; }

/* Nozzle columns: the reference's 4 columns (x 32, 80, 160, 208 of its 256 px screen) scaled x1.5 to our 384 px world, nozzle left edge; heights 24, 40, 32, 36 (the art in assets/arcade). */
static const int16_t noz_x[ARC_NOZZLE_COUNT] = { 48, 120, 240, 312 };
static const uint8_t noz_h[ARC_NOZZLE_COUNT] = { 24, 40, 32, 36 };
int arc_nozzle_x(int i) { return noz_x[i & 3]; }
int arc_nozzle_top(int i) { return ARC_FLOOR_Y - noz_h[i & 3]; }

/* Sway: one 25 step sine (+-16), a step every 4 frames = period 100 frames; scaled by the bubble's random amplitude 1..16 (>> 4). Undamped. */
static const int8_t sway_tab[25] = { 0, 4, 8, 11, 14, 15, 16, 16, 14, 12, 9, 6, 2, -2, -6, -9, -12, -14, -16, -16, -15, -14, -11, -8, -4 };

void arc_bonus_init(ArcBonus *b, int number, uint32_t seed) {
    int i;
    rng_seed(&b->rng, seed);
    b->number = number < 1 ? 1 : number; b->frame = 0; b->caught = 0; b->spawned = 0; b->over = 0; b->perfect = 0; b->nlive = 0;
    b->timer = (int16_t)(ARC_BONUS_SPAWN_MIN + (int)(rng_next(&b->rng) & ARC_BONUS_SPAWN_MASK));
    for (i = 0; i < ARC_NOZZLE_COUNT; i++) b->puff[i] = 0;
    for (i = 0; i < ARC_BONUS_LIVE_MAX; i++) { ArcBubble *u = &b->b[i]; u->live = 0; u->age = 0; u->ph = 0; u->amp = 0; u->nozzle = 0; u->x = u->x0 = 0; u->y16 = 0; }
}

int arc_bonus_step(ArcBonus *b, int armed, int rx, int ry, int rw, int rh) {
    int i, popped = 0;
    if (b->over) return 0;
    b->frame++;
    for (i = 0; i < ARC_NOZZLE_COUNT; i++) if (b->puff[i]) b->puff[i]--;
    if (--b->timer <= 0) {
        b->timer = (int16_t)(ARC_BONUS_SPAWN_MIN + (int)(rng_next(&b->rng) & ARC_BONUS_SPAWN_MASK));
        if (b->spawned < ARC_BONUS_BUBBLES && b->nlive < ARC_BONUS_LIVE_MAX) {
            ArcBubble *u = b->b;
            while (u->live) u++;
            u->nozzle = (uint8_t)(rng_next(&b->rng) & 3u);
            u->x = u->x0 = (int16_t)(noz_x[u->nozzle] + (ARC_NOZZLE_W - ARC_BONUS_BOX) / 2);
            u->y16 = (int32_t)(ARC_FLOOR_Y - noz_h[u->nozzle]) * 65536;
            u->amp = (uint8_t)(1u + (rng_next(&b->rng) & 15u)); u->ph = 0; u->age = 0; u->live = 1;
            b->spawned++; b->nlive++; b->puff[u->nozzle] = ARC_BONUS_PUFF_FRAMES;
        }
    }
    for (i = 0; i < ARC_BONUS_LIVE_MAX; i++) {
        ArcBubble *u = &b->b[i];
        int y;
        if (!u->live) continue;
        u->y16 -= arc_bonus_speed16(b->number); u->age++;
        y = (int)(u->y16 >> 16);
        if (ARC_FLOOR_Y - noz_h[u->nozzle] - y > ARC_BONUS_STRAIGHT) {
            if (!(u->age & 3) && ++u->ph == 25) u->ph = 0;
            u->x = (int16_t)(u->x0 + ((sway_tab[u->ph] * u->amp) >> 4));
        }
        if (y + ARC_BONUS_BOX <= 0) { u->live = 0; b->nlive--; continue; } /* escaped 16 px past the top: freed silently */
        if (armed && u->x < rx + rw && rx < u->x + ARC_BONUS_BOX && y < ry + rh && ry < y + ARC_BONUS_BOX) {
            u->live = 0; b->nlive--; b->caught++; popped++; /* no score here: the result screen tallies caught x value + perfect */
        }
    }
    if (b->spawned == ARC_BONUS_BUBBLES && !b->nlive && !(b->frame & 255)) { /* the reference waits for its frame counter to wrap */
        b->over = 1;
        b->perfect = b->caught == ARC_BONUS_BUBBLES;
    }
    return popped;
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
