/* flier.c - see flier.h. Spec: thoughts/shared/research/2026-11-09_flier-reference-spec.md. */
#include "flier.h"
#include "arena.h"

/* 256-entry sine table, Q15 (amplitude 32767), one full turn. */
static const int16_t sin_tab[256] = {
    0, 804, 1608, 2410, 3212, 4011, 4808, 5602, 6393, 7179, 7962, 8739, 9512, 10278, 11039, 11793,
    12539, 13279, 14010, 14732, 15446, 16151, 16846, 17530, 18204, 18868, 19519, 20159, 20787, 21403, 22005, 22594,
    23170, 23731, 24279, 24811, 25329, 25832, 26319, 26790, 27245, 27683, 28105, 28510, 28898, 29268, 29621, 29956,
    30273, 30571, 30852, 31113, 31356, 31580, 31785, 31971, 32137, 32285, 32412, 32521, 32609, 32678, 32728, 32757,
    32767, 32757, 32728, 32678, 32609, 32521, 32412, 32285, 32137, 31971, 31785, 31580, 31356, 31113, 30852, 30571,
    30273, 29956, 29621, 29268, 28898, 28510, 28105, 27683, 27245, 26790, 26319, 25832, 25329, 24811, 24279, 23731,
    23170, 22594, 22005, 21403, 20787, 20159, 19519, 18868, 18204, 17530, 16846, 16151, 15446, 14732, 14010, 13279,
    12539, 11793, 11039, 10278, 9512, 8739, 7962, 7179, 6393, 5602, 4808, 4011, 3212, 2410, 1608, 804,
    0, -804, -1608, -2410, -3212, -4011, -4808, -5602, -6393, -7179, -7962, -8739, -9512, -10278, -11039, -11793,
    -12539, -13279, -14010, -14732, -15446, -16151, -16846, -17530, -18204, -18868, -19519, -20159, -20787, -21403, -22005, -22594,
    -23170, -23731, -24279, -24811, -25329, -25832, -26319, -26790, -27245, -27683, -28105, -28510, -28898, -29268, -29621, -29956,
    -30273, -30571, -30852, -31113, -31356, -31580, -31785, -31971, -32137, -32285, -32412, -32521, -32609, -32678, -32728, -32757,
    -32767, -32757, -32728, -32678, -32609, -32521, -32412, -32285, -32137, -31971, -31785, -31580, -31356, -31113, -30852, -30571,
    -30273, -29956, -29621, -29268, -28898, -28510, -28105, -27683, -27245, -26790, -26319, -25832, -25329, -24811, -24279, -23731,
    -23170, -22594, -22005, -21403, -20787, -20159, -19519, -18868, -18204, -17530, -16846, -16151, -15446, -14732, -14010, -13279,
    -12539, -11793, -11039, -10278, -9512, -8739, -7962, -7179, -6393, -5602, -4808, -4011, -3212, -2410, -1608, -804,
};

int16_t flier_sin(uint8_t a) { return sin_tab[a]; }
int16_t flier_cos(uint8_t a) { return sin_tab[(uint8_t)(a + 64)]; }

/* Move vx toward target by at most step, never past it. A reversal passes through 0 at the same step size. */
static int32_t ground_approach(int32_t vx, int32_t target, int32_t step) {
    if (vx < target) return (target - vx <= step) ? target : vx + step;
    if (vx > target) return (vx - target <= step) ? target : vx - step;
    return vx;
}

/* 0.1 * d: 0.0001 1001 1001 1001 1b, terms at 4,5,8,9,12,13,16,17 (parachute sway). */
static int32_t mul_0_1(int32_t d) {
    int32_t m = d < 0 ? -d : d, r;
    r = (m >> 4) + (m >> 5) + (m >> 8) + (m >> 9) + (m >> 12) + (m >> 13) + (m >> 16) + (m >> 17);
    return d < 0 ? -r : r;
}

/* int16 x int16 -> int32: one muls.w on the 68000. noinline: inlined, gcc sees through the int16 casts of
 * range-limited values and falls back to the 32x32 libgcc multiply (__mulsi3). */
__attribute__((noinline)) static int32_t m16(int16_t a, int16_t b) { return (int32_t)a * (int32_t)b; }

int32_t flier_half_h(const Flier *f) {
    return f->balloons ? FLIER_HALF_H16_BALLOON : FLIER_HALF_H16_NOBAL;
}

volatile uint32_t g_flier_ceiling_hits;        /* flier_step ceiling bounces (test sentinel, read by MAME) */
volatile uint32_t g_flier_ceiling_rival_hits;  /* of those, on the lowered computer flier line */

int32_t flier_ceiling_y(const Flier *f, int top_px, int drop) {
    return FL_PX(top_px + FLIER_CEILING_FEET_Y + (drop ? FLIER_RIVAL_CEILING_DROP : 0)) - flier_half_h(f);
}

void flier_init(Flier *f, int32_t x, int32_t y, uint8_t balloons, uint8_t has_parachute) {
    Flier z = {0};
    *f = z;
    f->x = x; f->y = y;
    f->balloons = balloons > FLIER_MAX_BALLOONS ? FLIER_MAX_BALLOONS : balloons;
    f->has_parachute = has_parachute;
    f->facing = 1;
    f->kill_y = FL_PX(FLIER_WATER_Y);
}

static void start_falling(Flier *f) {
    f->state = FLIER_FALLING;
    f->vx = 0;
    f->vy = FLIER_FALL_START_VY;
    f->on_ground = 0;
}

/* Spike tips (Flier.solid_kill): the dead body reflects its downward speed once, never slower than FLIER_SPIKE_BOUNCE_MIN_VY, so a
 * bounce always shows. Uses the shared bounce rule (flier_reflect, FLIER_BOUNCE_RESTITUTION). */
static void spike_bounce(Flier *f) {
    int32_t v = flier_reflect(f->vy);
    f->vy = v > -FLIER_SPIKE_BOUNCE_MIN_VY ? -FLIER_SPIKE_BOUNCE_MIN_VY : v;
    f->bounced = 1;
}

void flier_spawn_protect(Flier *f) {
    f->spawn_inv = FLIER_SPAWN_INVINCIBLE;
}

int flier_lose_balloon(Flier *f) {
    if (f->invincible || f->spawn_inv || f->balloons == 0) return 0;
    if (f->state != FLIER_ALIVE && f->state != FLIER_PARACHUTE) return 0;
    f->balloons--;
    if (f->balloons > 0) {
        f->invincible = FLIER_INVINCIBLE_POP;
    } else if (f->on_ground) {
        f->y += FL_PX(2); /* smaller box: keep the feet on the floor */
    } else if (f->has_parachute) {
        f->state = FLIER_PARACHUTE;
        f->invincible = FLIER_INVINCIBLE_PARACHUTE;
        f->sway_tick = 0;
        f->sway_phase = 0;
        f->sway_target = 0;
    } else {
        start_falling(f);
    }
    return 1;
}

/* Pair geometry in half pixels (x >> 15, the unit the contact boxes are compared in): dx is b's x relative to a's across
 * the arena seam, d is b's feet bottom minus a's (positive when a is higher). Both boxes hang from the feet bottom
 * (y + half height), where the art is anchored. */
static void pair_geo(const Flier *a, const Flier *b, int *dx, int *d) {
    *dx = (int)((arena_near_x(a->x, b->x) >> 15) - (a->x >> 15));
    *d = (int)((b->y + flier_half_h(b)) >> 15) - (int)((a->y + flier_half_h(a)) >> 15);
}

static int iabs(int v) { return v < 0 ? -v : v; }

/* Gum half width in pixels for a flier with balloons. */
static int gum_hw(const Flier *f) { return f->balloons >= 2 ? FLIER_GUM_HALF_W2 : FLIER_GUM_HALF_W1; }

/* Body boxes overlap (edges exclusive): fills the geometry of pair_geo. */
static int body_overlap(const Flier *a, const Flier *b, int *dx, int *d) {
    pair_geo(a, b, dx, d);
    return iabs(*dx) < 4 * FLIER_BODY_HALF_W && iabs(*d) < 2 * FLIER_BODY_TOP;
}

int flier_body_touching(const Flier *victim, const Flier *other) {
    int dx, d;
    if (victim->balloons != 0 || victim->state != FLIER_ALIVE || other->state > FLIER_PARACHUTE) return 0;
    return body_overlap(victim, other, &dx, &d);
}

int flier_body_kill(Flier *victim, const Flier *other) {
    if (!flier_body_touching(victim, other)) return 0;
    start_falling(victim);
    return 1;
}

int flier_add_balloon(Flier *f) {
    if (f->balloons >= FLIER_MAX_BALLOONS || f->state > FLIER_PARACHUTE) return 0;
    if (f->balloons == 0 && f->on_ground) f->y -= FL_PX(2);
    f->balloons++;
    return 1;
}

int32_t flier_reflect(int32_t v) {
    uint32_t m = (uint32_t)(v < 0 ? -v : v);
    /* floor(m * k / 256) without a 32-bit multiply: (m >> 8) * k + ((m & 255) * k >> 8) is exact */
    int32_t r = m16((int16_t)(m >> 8), (int16_t)FLIER_BOUNCE_RESTITUTION) + (m16((int16_t)(m & 255u), (int16_t)FLIER_BOUNCE_RESTITUTION) >> 8);
    return v < 0 ? r : -r;
}

/* Axes on which a and b close (bit 0 vertical, bit 1 horizontal), from the pair geometry (dx, d as pair_geo gives them) and
 * the velocities. An axis closes when the separation along it is nonzero and the relative velocity shrinks it. The vertical
 * axis only counts when the pair is not level; the horizontal axis counts when level or when the centres are at least one
 * body half width apart (a stack with the centres lined up does not flip sideways). */
#define PAIR_AXIS_V 1u
#define PAIR_AXIS_H 2u
static unsigned pair_axes(const Flier *a, const Flier *b, int dx, int d) {
    unsigned axes = 0;
    int level = iabs(d) < 2 * FLIER_PAIR_LEVEL_PX;
    if (!level && ((d > 0 && b->vy < a->vy) || (d < 0 && b->vy > a->vy))) axes |= PAIR_AXIS_V;
    if ((level || iabs(dx) >= 2 * FLIER_BODY_HALF_W) && ((dx > 0 && b->vx < a->vx) || (dx < 0 && b->vx > a->vx))) axes |= PAIR_AXIS_H;
    return axes;
}

/* a reverses its own velocity on each closing axis, times the restitution (a balloon-less a gets none: it dies by flier_body_kill). */
static int bounce_off(Flier *a, unsigned axes) {
    if (a->balloons == 0 || a->state > FLIER_PARACHUTE) return 0;
    if (axes & PAIR_AXIS_V) a->vy = flier_reflect(a->vy);
    if (axes & PAIR_AXIS_H) a->vx = flier_reflect(a->vx);
    if (a->vy < 0) a->on_ground = 0;
    return 1;
}

int flier_body_bounce(Flier *a, const Flier *b) {
    int dx, d;
    unsigned axes;
    if (a->balloons == 0 || a->state > FLIER_PARACHUTE || b->state > FLIER_PARACHUTE) return 0;
    if (!body_overlap(a, b, &dx, &d)) return 0;
    axes = pair_axes(a, b, dx, d);
    if (!axes) return 0;
    return bounce_off(a, axes);
}

volatile uint16_t g_flier_solid_hits;

/* The solid box of the drawn flier above its feet: body 14 wide and 22 tall, plus the gum (18 wide with two, the body width
 * with one, 31 tall) while the flier has any. The same numbers the pair contact boxes use. */
static int32_t solid_top(const Flier *f) { return FL_PX(f->balloons ? FLIER_GUM_TOP : FLIER_BODY_TOP); }
static int32_t solid_hw(const Flier *f) {
    int hw = FLIER_BODY_HALF_W;
    if (f->balloons >= 2 && FLIER_GUM_HALF_W2 > hw) hw = FLIER_GUM_HALF_W2;
    return FL_PX(hw);
}
void flier_solid_box(const Flier *f, int32_t *hw, int32_t *top) {
    *hw = solid_hw(f);
    *top = solid_top(f);
}

int flier_collide_solids(Flier *f, int32_t prev_x, int32_t prev_y, const FlierSolid *solids, int n) {
    int hits = 0;
    int32_t hw = solid_hw(f), top = solid_top(f);
    if (f->state >= FLIER_FALLING) return 0;
    for (int i = 0; i < n; i++) {
        const FlierSolid *s = &solids[i];
        int32_t hh = flier_half_h(f);
        int32_t feet = f->y + hh, pfeet = prev_y + hh;
        int32_t L = s->x16, R = s->x16 + s->w16, T = s->y16, Bt = s->y16 + s->h16;
        int32_t cx = L + s->w16 / 2;
        int32_t x = f->x, px = prev_x;
        if (!f->no_wrap) {
            x = arena_near_x(cx, f->x);
            px = arena_near_x(cx, prev_x);
        }
        if (!(x + hw > L && x - hw < R && feet > T && feet - top < Bt)) continue;
        /* Landing from above belongs to the floor line: the box was over the top and over the solid before. */
        if (pfeet <= T && px + hw > L && px - hw < R) continue;
        {
            int32_t pen_b = Bt - (feet - top), pen_l = (x + hw) - L, pen_r = R - (x - hw);
            int below = pfeet - top >= Bt, left = px + hw <= L, right = px - hw >= R;
            int axis = 0;                       /* 1 below, 2 left, 3 right */
            int32_t best = 0x7fffffff;
            if (!below && !left && !right) { below = left = right = 1; }
            if (below && pen_b < best) { best = pen_b; axis = 1; }
            if (left && pen_l < best) { best = pen_l; axis = 2; }
            if (right && pen_r < best) { best = pen_r; axis = 3; }
            if (axis == 1) {
                f->y = Bt + top - hh;
                if (f->vy < 0) f->vy = flier_reflect(f->vy);
                f->on_ground = 0;
            } else if (axis == 2) {
                x = L - hw;
                if (f->vx > 0) f->vx = flier_reflect(f->vx);
            } else {
                x = R + hw;
                if (f->vx < 0) f->vx = flier_reflect(f->vx);
            }
            f->x = f->no_wrap ? x : arena_wrap_x(x);
        }
        g_flier_solid_hits++;
        hits++;
    }
    return hits;
}

void flier_step(Flier *f, const FlierInput *in, int32_t floor_y) {
    f->flapped = 0;
    uint8_t edge = (uint8_t)(in->flap && !f->flap_prev);
    f->flap_prev = in->flap ? 1 : 0;
    if (in->dir) f->facing = in->dir > 0;
    if (f->state == FLIER_GONE) return;
    if (f->invincible) f->invincible--;
    if (f->spawn_inv) {
        if (in->dir || in->flap) f->spawn_inv = 0;
        else f->spawn_inv--;
    }
    if (f->flap_cd) f->flap_cd--;

    if (f->state >= FLIER_FALLING) { /* dead: FALLING after a kill, DROWNED after the hazard; same fall, no collisions */
        int32_t hh = flier_half_h(f);
        f->vy += FLIER_GRAVITY_NO_BALLOON;
        if (f->vy > FLIER_FALL_MAX_NO_BALLOON) f->vy = FLIER_FALL_MAX_NO_BALLOON;
        f->x = f->no_wrap ? f->x + f->vx : arena_wrap_x(f->x + f->vx);
        f->y += f->vy;
        if (f->solid_kill && !f->bounced && f->vy > 0 && f->y + hh >= f->kill_y) { /* spike tips: one bounce, then it falls on */
            f->y = f->kill_y - hh;
            spike_bounce(f);
        }
        if (f->y + hh >= FL_PX(FLIER_REMOVE_FEET_Y)) f->state = FLIER_GONE;
        return;
    }

    /* gravity, one branch (3.5) */
    if (f->state == FLIER_PARACHUTE) {
        f->vy += FLIER_PARACHUTE_GRAVITY;
        if (f->sway_tick == 0) {
            f->sway_target = m16(sin_tab[(uint8_t)(f->sway_phase >> 8)], (int16_t)FLIER_PARACHUTE_SWAY) >> 15;
            f->sway_phase += FLIER_SWAY_PHASE_STEP;
        }
        if (++f->sway_tick >= FLIER_SWAY_PERIOD) f->sway_tick = 0;
        f->vx += mul_0_1(f->sway_target - f->vx);
    } else if (!f->on_ground) {
        f->vy += f->balloons ? FLIER_GRAVITY_BALLOON : FLIER_GRAVITY_NO_BALLOON;
    }

    /* flap and horizontal control (3.2, 3.3) */
    if (f->state == FLIER_ALIVE) {
        if (f->on_ground) {
            if (edge) {
                f->vy = f->balloons >= 2 ? FLIER_GROUND_JUMP_VY : f->balloons == 1 ? FLIER_GROUND_JUMP_VY_ONE : FLIER_GROUND_JUMP_VY_NOBAL;
                f->on_ground = 0;
                f->flap_cd = FLIER_FLAP_COOLDOWN;
                f->flapped = 1;
            } else { /* a jump frame keeps the current vx */
                f->vx = ground_approach(f->vx, in->dir > 0 ? FLIER_TOP_LAND_SPEED : in->dir < 0 ? -FLIER_TOP_LAND_SPEED : 0, FLIER_GROUND_ACCEL);
            }
        } else if (edge && f->balloons && f->flap_cd == 0) {
            f->flap_cd = FLIER_FLAP_COOLDOWN;
            f->vy -= f->balloons == 1 ? FLIER_FLAP_IMPULSE_ONE_GUM : FLIER_FLAP_IMPULSE;
            f->flapped = 1;
            if (in->dir) {
                int32_t nv = f->vx + (in->dir > 0 ? FLIER_FLAP_THRUST_X : -FLIER_FLAP_THRUST_X);
                /* clamp to the top air speed, but never slow a flier that is already faster (bounce, knockback) */
                if (in->dir > 0 && nv > FLIER_TOP_AIR_SPEED) nv = f->vx > FLIER_TOP_AIR_SPEED ? f->vx : FLIER_TOP_AIR_SPEED;
                if (in->dir < 0 && nv < -FLIER_TOP_AIR_SPEED) nv = f->vx < -FLIER_TOP_AIR_SPEED ? f->vx : -FLIER_TOP_AIR_SPEED;
                f->vx = nv;
            }
        }
    }
    /* speed caps in the air (alive and parachute; a standing flier has vy 0) */
    if (!f->on_ground) {
        int32_t fall_max = f->state == FLIER_PARACHUTE ? FLIER_PARACHUTE_FALL_MAX : f->balloons ? FLIER_FALL_MAX : FLIER_FALL_MAX_NO_BALLOON;
        if (f->vy > fall_max) f->vy = fall_max;
        if (f->vy < -FLIER_RISE_MAX) f->vy = -FLIER_RISE_MAX;
    }

    /* move */
    int32_t bottom_before = f->y + flier_half_h(f);
    f->x += f->vx;
    f->y += f->vy;
    int32_t hh = flier_half_h(f);

    /* floor (not for a rising fighter) */
    if (f->on_ground) {
        /* Keep standing only while the floor is within FLIER_FLOOR_TOL of the feet, above or below (a small vy can sink the
         * feet a fraction of a pixel); a lower floor means the flier walked off an edge and falls, it is not snapped down. */
        int32_t gap = floor_y - (f->y + hh);
        if (floor_y != FLIER_NO_FLOOR && f->vy >= 0 && gap >= -FLIER_FLOOR_TOL && gap <= FLIER_FLOOR_TOL) f->y = floor_y - hh;
        else f->on_ground = 0;
    } else if (floor_y != FLIER_NO_FLOOR && f->vy >= 0 && bottom_before <= floor_y && f->y + hh >= floor_y) {
        f->y = floor_y - hh;
        f->vy = 0;
        f->on_ground = 1;
        if (f->state == FLIER_PARACHUTE) { f->state = FLIER_ALIVE; f->invincible = 0; }
    }

    /* the hazard kills regardless of balloons or invincibility (4.3 item 6), where the drawn surface is (kill_y) */
    if (f->y + hh >= f->kill_y) {
        f->state = FLIER_DROWNED; /* dies and keeps moving: the dead fall above */
        f->vx = 0;
        if (f->vy < 0) f->vy = 0;
        f->balloons = 0;
        f->on_ground = 0;
        f->bounced = 0;
        if (f->solid_kill) {
            f->y = f->kill_y - flier_half_h(f);
            spike_bounce(f);
        }
        return;
    }

    /* side edges wrap (arena.h); the ceiling reflects vy times the restitution */
    if (!f->no_wrap) f->x = arena_wrap_x(f->x);
    {
        /* A computer flier that starts the step above its lowered line (spawned or standing on a high island) keeps the hero line:
         * the lowered line would push it down into the island. It bounces off the lowered line only when rising from below it. */
        int low = f->rival && bottom_before >= FL_PX(FLIER_CEILING_FEET_Y + FLIER_RIVAL_CEILING_DROP);
        int32_t ceil = flier_ceiling_y(f, 0, low);
        if (f->y < ceil) {
            g_flier_ceiling_hits++;
            if (low) g_flier_ceiling_rival_hits++;
            f->y = ceil;
            if (f->vy < 0) f->vy = flier_reflect(f->vy);
        }
    }
}

uint8_t flier_angle(int32_t dx, int32_t dy) {
    if (dx == 0 && dy == 0) return 0;
    uint8_t base = 0;
    if (dy < 0) { dx = -dx; dy = -dy; base = 128; }
    if (dy == 0) return (uint8_t)(base + (dx < 0 ? 128 : 0)); /* exactly on the axis */
    while (dx > 20000 || dx < -20000 || dy > 20000) { dx >>= 1; dy >>= 1; } /* fit int16 for the products */
    int16_t px = (int16_t)dx, py = (int16_t)dy;
    uint8_t a = 0;
    for (uint8_t step = 64; step; step >>= 1) {
        uint8_t c = (uint8_t)(a + step);
        /* d is counter-clockwise of candidate c (cross >= 0): angle is at least c */
        int32_t cross = m16(flier_cos(c), py) - m16(flier_sin(c), px);
        if (cross >= 0) a = c;
    }
    return (uint8_t)(base + a);
}

volatile uint32_t g_flier_pair_calls;

FlierPairAct flier_pair(const Flier *a, const Flier *b) {
    int dx, d, adx, ad;
    const Flier *hi, *lo;
    FlierPairAct act = FLP_NONE;
    g_flier_pair_calls++;
    if (a->state > FLIER_PARACHUTE || b->state > FLIER_PARACHUTE) return FLP_NONE;
    pair_geo(a, b, &dx, &d);
    adx = iabs(dx); ad = iabs(d);
    if (adx >= FLIER_PAIR_REACH_HALF) return FLP_NONE;
    if (ad < 2 * FLIER_PAIR_LEVEL_PX) {
        /* Same height: body meets body, or gum meets gum. A body never reaches a gum here (the body top is the gum bottom). */
        if (adx < 4 * FLIER_BODY_HALF_W) act = FLP_BOUNCE;
        else if (a->balloons && b->balloons && adx < 2 * (gum_hw(a) + gum_hw(b))) act = FLP_BOUNCE;
    } else {
        hi = d > 0 ? a : b;
        lo = d > 0 ? b : a;
        /* The higher flier's body (or gum) against the lower flier's gum. */
        if (lo->balloons &&
            ((ad < 2 * FLIER_GUM_TOP && adx < 2 * (FLIER_BODY_HALF_W + gum_hw(lo))) ||
             (hi->balloons && ad < 2 * (FLIER_GUM_TOP - FLIER_GUM_BOTTOM) && adx < 2 * (gum_hw(hi) + gum_hw(lo))))) {
            act = (lo->invincible || lo->spawn_inv) ? FLP_BOUNCE : (hi == a ? FLP_POP_B : FLP_POP_A);
        } else if (adx < 4 * FLIER_BODY_HALF_W && ad < 2 * FLIER_BODY_TOP) {
            act = FLP_BOUNCE;
        }
    }
    /* A bounce or pop needs the pair to close on at least one axis; two fliers that overlap and move apart do nothing. */
    if (act != FLP_NONE && !pair_axes(a, b, dx, d)) return FLP_NONE;
    return act;
}

/* Pops one balloon of v. Both fliers reflect on the closing axes like any bounce (no knockback); the last balloon of v
 * overwrites its velocity with the fall start. */
static int stomp_apply(Flier *a, Flier *v) {
    int dx, d;
    unsigned axes;
    pair_geo(a, v, &dx, &d);
    axes = pair_axes(a, v, dx, d);
    bounce_off(a, axes);
    bounce_off(v, axes);
    return flier_lose_balloon(v);
}

int flier_pair_apply(Flier *a, Flier *b, FlierPairAct act) {
    int dx, d;
    unsigned axes;
    if (act == FLP_POP_B) return stomp_apply(a, b);
    if (act == FLP_POP_A) return stomp_apply(b, a);
    if (act != FLP_BOUNCE) return 0;
    pair_geo(a, b, &dx, &d);
    axes = pair_axes(a, b, dx, d);
    bounce_off(a, axes);
    bounce_off(b, axes);
    return 0;
}

int flier_stomp(Flier *a, Flier *v) {
    if (flier_pair(a, v) != FLP_POP_B) return 0;
    return stomp_apply(a, v);
}

volatile uint32_t g_flier_pair_blocked;

/* Parameter t (a over den, den > 0) as a fraction: n1/d1 < n2/d2. 64-bit cross products; only candidate pairs get here. */
static int frac_lt(int32_t n1, int32_t d1, int32_t n2, int32_t d2) { return (int64_t)n1 * d2 < (int64_t)n2 * d1; }

/* One slab of the open box interior along a segment axis: moving by d from 0, the open interval (lo, hi) is crossed for t in
 * (lo/d, hi/d). Narrows the running window [lo_n/lo_d, hi_n/hi_d]; returns 0 when this axis can never be inside. */
static int slab(int32_t d, int32_t lo, int32_t hi, int32_t *ln, int32_t *ld, int32_t *hn, int32_t *hd) {
    if (d == 0) return lo < 0 && 0 < hi;
    if (d < 0) { int32_t t = lo; d = -d; lo = -hi; hi = -t; }
    if (frac_lt(*ln, *ld, lo, d)) { *ln = lo; *ld = d; }
    if (frac_lt(hi, d, *hn, *hd)) { *hn = hi; *hd = d; }
    return 1;
}

/* Integer reject: the open interval (lo, hi) cannot meet the segment's extent [min(0,d), max(0,d)]. The slab test is open on both ends
 * (touching returns 0), so equality rejects too: same result as slab + final frac_lt, with no multiply. */
static int span_misses(int32_t d, int32_t lo, int32_t hi) { return hi <= (d < 0 ? d : 0) || lo >= (d < 0 ? 0 : d); }

int flier_pair_blocked(const Flier *a, const Flier *b, const FlierSolid *solids, int n, int wrap) {
    int32_t bx = wrap ? arena_near_x(a->x, b->x) : b->x;
    int32_t dx = bx - a->x, dy = b->y - a->y;
    int32_t mid = a->x + (dx >> 1);
    int i;
    for (i = 0; i < n; i++) {
        int32_t x0 = solids[i].x16, ln = 0, ld = 1, hn = 1, hd = 1;
        if (wrap) x0 = arena_near_x(mid, x0 + (solids[i].w16 >> 1)) - (solids[i].w16 >> 1);
        x0 -= a->x;
        if (span_misses(dx, x0, x0 + solids[i].w16) || span_misses(dy, solids[i].y16 - a->y, solids[i].y16 + solids[i].h16 - a->y)) continue;
        if (!slab(dx, x0, x0 + solids[i].w16, &ln, &ld, &hn, &hd)) continue;
        if (!slab(dy, solids[i].y16 - a->y, solids[i].y16 + solids[i].h16 - a->y, &ln, &ld, &hn, &hd)) continue;
        if (frac_lt(ln, ld, hn, hd)) { g_flier_pair_blocked++; return 1; }
    }
    return 0;
}
