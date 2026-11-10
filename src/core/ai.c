#include "ai.h"

/* int16 x int16 -> int32 as one muls.w; see flier.c. */
__attribute__((noinline)) static int32_t m16(int16_t a, int16_t b) { return (int32_t)a * (int32_t)b; }

static int16_t px(int32_t v) { return (int16_t)(v >> 16); }

static int32_t dist2(const Flier *a, const Flier *b) {
    int16_t dx = (int16_t)(px(a->x) - px(b->x)), dy = (int16_t)(px(a->y) - px(b->y));
    return m16(dx, dx) + m16(dy, dy);
}

static uint16_t next_timer(Rng *r) {
    /* 0..2*JITTER from the top byte of the generator: byte * (2J+1) >> 8, no divide. */
    uint16_t b = (uint16_t)((rng_next(r) >> 16) & 0xFFu);
    int32_t j = m16((int16_t)b, (int16_t)(2 * AI_THINK_JITTER + 1)) >> 8;
    return (uint16_t)(AI_THINK_FRAMES + (int)j - AI_THINK_JITTER);
}

void ai_init(Ai *a, Rng *r) {
    Ai z = {0};
    *a = z;
    a->state = AI_CHASE;
    a->timer = next_timer(r);
}

const Flier *ai_nearest(const Flier *self, const Flier *player, const Flier *cpus, int cpu_count) {
    const Flier *best = 0;
    int32_t bd = 0;
    int i;
    for (i = -1; i < cpu_count; i++) {
        const Flier *c = i < 0 ? player : &cpus[i];
        int32_t d;
        if (c == self || c->state > FLIER_PARACHUTE) continue;
        d = dist2(self, c);
        if (!best || d < bd) { best = c; bd = d; }
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

void ai_step(Ai *a, Rng *r, const Flier *self, const Flier *target, FlierInput *out) {
    out->flap = 0;
    if (a->timer > 0) a->timer--;
    if (a->timer == 0) {
        a->timer = next_timer(r);
        a->thinks++;
        a->dir = 0;
        if (target) {
            AiState s = ai_decide(self, target);
            a->state = (uint8_t)s;
            if (s != AI_FILL) {
                uint8_t ang = flier_angle((int32_t)(px(target->x) - px(self->x)), (int32_t)(px(target->y) - px(self->y)));
                int16_t cx = flier_cos(ang), cy = flier_sin(ang);
                if (s == AI_FLEE) { cx = (int16_t)-cx; cy = (int16_t)-cy; }
                if (cx > AI_STEER_MIN) a->dir = 1;
                else if (cx < -AI_STEER_MIN) a->dir = -1;
                if (cy < AI_FLAP_MAX) out->flap = 1;
            }
        }
    }
    out->dir = a->dir;
}
