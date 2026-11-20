#include "ai.h"
#include "stage.h"
#include "arena.h"

/* int16 x int16 -> int32 as one muls.w; see flier.c. */
__attribute__((noinline)) static int32_t m16(int16_t a, int16_t b) { return (int32_t)a * (int32_t)b; }

static int16_t px(int32_t v) { return (int16_t)(v >> 16); }

static int32_t dist2(const Flier *a, const Flier *b) {
    int16_t dx = (int16_t)arena_dx(px(a->x), px(b->x)), dy = (int16_t)(px(a->y) - px(b->y));
    return m16(dx, dx) + m16(dy, dy);
}

static uint16_t next_timer(const Ai *a, Rng *r) {
    /* 0..2*JITTER from the top byte of the generator: byte * (2J+1) >> 8, no divide. */
    uint16_t b = (uint16_t)((rng_next(r) >> 16) & 0xFFu);
    int32_t j = m16((int16_t)b, (int16_t)(2 * AI_THINK_JITTER + 1)) >> 8;
    return (uint16_t)(AI_THINK_FRAMES + (int)j - AI_THINK_JITTER - a->think_cut);
}

void ai_init(Ai *a, Rng *r, int rank) {
    Ai z = {0};
    *a = z;
    a->state = AI_CHASE;
    a->think_cut = (int8_t)((rank - 1) * AI_RANK_THINK_STEP);
    a->timer = next_timer(a, r);
}

/* Nearest live flier, first minimum wins. Cull before the multiplies: with bm = max(|bdx|,|bdy|) of the best so far, bd <= 2*bm^2.
 * A candidate with |dx| or |dy| >= cut = bm + bm/2 + 1 > 1.5*bm has d >= cut^2 > 2.25*bm^2 >= bd, so it cannot be strictly
 * nearer (ties keep the first) and is skipped. The +1 covers the integer floor of bm/2. tests/host/test_ai.c checks it. */
const Flier *ai_nearest(const Flier *self, const Flier *humans, int human_count, const Flier *cpus, int cpu_count) {
    const Flier *best = 0;
    int32_t bd = 0;
    int16_t cut = 0;
    int i;
    for (i = -human_count; i < cpu_count; i++) {
        const Flier *c = i < 0 ? &humans[human_count + i] : &cpus[i];
        int16_t dx, dy, ax, ay;
        int32_t d;
        if (c == self || c->state > FLIER_PARACHUTE) continue;
        dx = (int16_t)arena_dx(px(self->x), px(c->x));
        dy = (int16_t)(px(self->y) - px(c->y));
        ax = dx < 0 ? -dx : dx;
        ay = dy < 0 ? -dy : dy;
        if (best && (ax >= cut || ay >= cut)) continue;
        d = m16(dx, dx) + m16(dy, dy);
        if (!best || d < bd) {
            int16_t bm = ax > ay ? ax : ay;
            best = c; bd = d; cut = (int16_t)(bm + (bm >> 1) + 1);
        }
    }
    return best;
}

AiState ai_decide(const Flier *self, const Flier *target) {
    int32_t d2 = dist2(self, target);
    if (self->balloons == 0) {
        return d2 > m16(AI_FILL_DIST, AI_FILL_DIST) ? AI_FILL : AI_FLEE;
    }
    if (d2 < m16(AI_FLEE_DIST, AI_FLEE_DIST) && !(px(self->y) <= px(target->y) - AI_ABOVE_MARGIN)) return AI_FLEE;
    return AI_CHASE;
}

/* Steering at a think: dir.x of the angle to the target (Q15 cosine, negated when fleeing) against +-AI_STEER_MIN. The angle search
 * of flier_angle is not needed: with the target folded below (dy > 0) the angle a in [0,128) is at least c exactly when
 * cross(c) >= 0, cos(a) > AI_STEER_MIN holds for a < AI_STEER_A1 and cos(a) < -AI_STEER_MIN for a >= AI_STEER_A2 (the table is
 * antisymmetric, so the fold's half turn only flips the sign). dy == 0 is on the axis. tests/host/test_ai.c checks it against
 * the angle search. */
#define AI_STEER_A1 54
#define AI_STEER_A2 75
static int cross_ge(uint8_t c, int16_t x, int16_t y) { return m16(flier_cos(c), y) - m16(flier_sin(c), x) >= 0; }

int ai_steer_dir(AiState s, int32_t dx, int32_t dy) {
    int d, flip = s == AI_FLEE;
    if (dy == 0) d = dx < 0 ? -1 : 1;
    else {
        if (dy < 0) { dx = -dx; dy = -dy; flip ^= 1; }
        while (dx > 20000 || dx < -20000 || dy > 20000) { dx >>= 1; dy >>= 1; }
        d = !cross_ge(AI_STEER_A1, (int16_t)dx, (int16_t)dy) ? 1 : cross_ge(AI_STEER_A2, (int16_t)dx, (int16_t)dy) ? -1 : 0;
    }
    return flip ? -d : d;
}

/* aim()'s flap test, dir.y < AI_FLAP_MAX, without the 7-step angle search (about 5 raster lines a rival a frame on the 68000).
 * y is down: a target above (chase) or below (flee) gives dir.y <= 0, always a flap. Otherwise dir.y >= 0.5 means
 * flier_angle in [AI_FLAP_A0, AI_FLAP_A1] (sin_tab[22] is the first entry >= AI_FLAP_MAX), and the angle search returns
 * at least c exactly when cross(c) >= 0, so two products decide. tests/host/test_ai.c checks it against the angle search. */
#define AI_FLAP_A0 22
#define AI_FLAP_A1 106
static int32_t cross(uint8_t c, int16_t x, int16_t y) { return m16(flier_cos(c), y) - m16(flier_sin(c), x); }

int ai_flap_wanted(AiState s, int32_t dx, int32_t dy) {
    if (dy == 0 || (dy < 0) != (s == AI_FLEE)) return 1;
    if (dy < 0) { dx = -dx; dy = -dy; } /* fleeing a target above: flier_angle's half turn, and the flee negation undoes it */
    while (dx > 20000 || dx < -20000 || dy > 20000) { dx >>= 1; dy >>= 1; } /* as flier_angle */
    return cross(AI_FLAP_A0, (int16_t)dx, (int16_t)dy) < 0 || cross(AI_FLAP_A1 + 1, (int16_t)dx, (int16_t)dy) >= 0;
}

/* AI_HOLD: per frame, no thinks. The target rests where a standing flier's centre rests. */
static void ai_hold_step(Ai *a, const Flier *self, const Flier *target, FlierInput *out) {
    int dx = arena_dx(px(target->x), px(self->x)), dy = px(target->y) - px(self->y); /* dy > 0: the target is below */
    int far = dx > AI_HOLD_NEAR_PX || dx < -AI_HOLD_NEAR_PX;
    a->state = AI_HOLD;
    a->dir = (int8_t)(dx > AI_HOLD_STEER_MIN ? 1 : dx < -AI_HOLD_STEER_MIN ? -1 : 0);
    out->dir = a->dir;
    if (self->flap_cd == 0 && !self->flap_prev) {
        int want;
        if (self->on_ground) want = far || dy < -AI_HOLD_LIFT_PX;
        else want = far ? dy < AI_HOLD_CRUISE_PX : dy < -AI_HOLD_LAND_PX;
        if (want) {
            int8_t away = (int8_t)stage_overhead_edge_dir(self->x, self->y - flier_half_h(self));
            out->flap = 1;
            if (away) out->dir = away;
        }
    }
}

/* The flap decision runs every frame (additive flight model: one flap cancels only part of a think period of gravity):
 * flap on a fresh press while the target is above (dir.y < AI_FLAP_MAX) and the cooldown has run out. */
void ai_flap_step(const Ai *a, const Flier *self, const Flier *target, FlierInput *out) {
    out->flap = 0;
    if (target && a->state != AI_FILL && self->flap_cd == 0 && !self->flap_prev) {
        if (ai_flap_wanted((AiState)a->state, arena_dx(px(target->x), px(self->x)), (int32_t)(px(target->y) - px(self->y)))) {
            /* Flapping up into the underside of an island only bounces: steer out from under it first. */
            int8_t away = (int8_t)stage_overhead_edge_dir(self->x, self->y - flier_half_h(self));
            out->flap = 1;
            if (away) out->dir = away;
        }
    }
}

void ai_step(Ai *a, Rng *r, const Flier *self, const Flier *target, FlierInput *out) {
    out->flap = 0;
    if (a->hold && target) { ai_hold_step(a, self, target, out); return; }
    if (a->timer > 0) a->timer--;
    if (a->timer == 0) {
        a->timer = next_timer(a, r);
        a->thinks++;
        a->dir = 0;
        if (target) {
            AiState s = a->flee ? AI_FLEE : ai_decide(self, target);
            a->state = (uint8_t)s;
            if (s != AI_FILL) a->dir = (int8_t)ai_steer_dir(s, arena_dx(px(target->x), px(self->x)), (int32_t)(px(target->y) - px(self->y)));
        }
    }
    out->dir = a->dir;
    ai_flap_step(a, self, target, out);
}
