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

/* 0.2 * d as shift-add: 0.2 = 0.0011 0011 0011 0011b, terms at 3,4,7,8,11,12,15,16 (spec 2.2, extended to
 * eight terms: -65536 -> -13107 exactly). Sign-magnitude so left and right behave identically. */
static int32_t mul_0_2(int32_t d) {
    int32_t m = d < 0 ? -d : d, r;
    r = (m >> 3) + (m >> 4) + (m >> 7) + (m >> 8) + (m >> 11) + (m >> 12) + (m >> 15) + (m >> 16);
    return d < 0 ? -r : r;
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

int flier_lose_balloon(Flier *f) {
    if (f->invincible || f->balloons == 0) return 0;
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

/* Body boxes overlap (whole pixels, inclusive edges): fills the centre offset a - b and the penetration on each axis. */
static int body_overlap(const Flier *a, const Flier *b, int *dx, int *dy, int *pen_x, int *pen_y) {
    int ah = (int)(flier_half_h(a) >> 16) + 1, bh = (int)(flier_half_h(b) >> 16) + 1;
    *dx = arena_dx((int)(a->x >> 16), (int)(b->x >> 16));
    *dy = (int)(a->y >> 16) - (int)(b->y >> 16);
    if (*dx > 2 * FLIER_HALF_W || *dx < -2 * FLIER_HALF_W) return 0;
    if (*dy > ah + bh || *dy < -(ah + bh)) return 0;
    *pen_x = 2 * FLIER_HALF_W - (*dx < 0 ? -*dx : *dx);
    *pen_y = ah + bh - (*dy < 0 ? -*dy : *dy);
    return 1;
}

int flier_body_kill(Flier *victim, const Flier *other) {
    int dx, dy, px, py;
    if (victim->balloons != 0 || victim->state != FLIER_ALIVE || other->state > FLIER_PARACHUTE) return 0;
    if (!body_overlap(victim, other, &dx, &dy, &px, &py)) return 0;
    start_falling(victim);
    return 1;
}

int flier_add_balloon(Flier *f) {
    if (f->balloons >= FLIER_MAX_BALLOONS || f->state > FLIER_PARACHUTE) return 0;
    if (f->balloons == 0 && f->on_ground) f->y -= FL_PX(2);
    f->balloons++;
    return 1;
}

/* Reflect-and-minimum bounce (spec 3.6): v already holds the reflected velocity; if its speed is below the
 * minimum the whole vector becomes minimum x normal. Speed test without sqrt or 32-bit multiply: any
 * component at or above the minimum settles it, else both fit int16 and the squares compare. */
static void bounce_min(Flier *f, int8_t nx, int8_t ny) {
    int32_t ax = f->vx < 0 ? -f->vx : f->vx;
    int32_t ay = f->vy < 0 ? -f->vy : f->vy;
    int slow;
    if (ax >= FLIER_MIN_BOUNCE_SPEED || ay >= FLIER_MIN_BOUNCE_SPEED) {
        slow = 0;
    } else {
        int16_t sx = (int16_t)ax, sy = (int16_t)ay, m = (int16_t)FLIER_MIN_BOUNCE_SPEED;
        slow = (m16(sx, sx) + m16(sy, sy)) < m16(m, m);
    }
    if (slow) {
        f->vx = nx > 0 ? FLIER_MIN_BOUNCE_SPEED : nx < 0 ? -FLIER_MIN_BOUNCE_SPEED : 0;
        f->vy = ny > 0 ? FLIER_MIN_BOUNCE_SPEED : ny < 0 ? -FLIER_MIN_BOUNCE_SPEED : 0;
    }
}

int flier_body_bounce(Flier *a, const Flier *b) {
    int dx, dy, px, py;
    int8_t nx = 0, ny = 0;
    if (a->balloons == 0 || a->state > FLIER_PARACHUTE || b->state > FLIER_PARACHUTE) return 0;
    if (!body_overlap(a, b, &dx, &dy, &px, &py)) return 0;
    /* Contact normal: the axis of least penetration, pointing from b to a (ties go to the horizontal axis). */
    if (px <= py) nx = dx >= 0 ? 1 : -1;
    else ny = dy >= 0 ? 1 : -1;
    /* Reflect the component into b (restitution 1, tangential speed kept), then the minimum bounce (spec 3.6). */
    if (nx > 0 && a->vx < 0) a->vx = -a->vx;
    if (nx < 0 && a->vx > 0) a->vx = -a->vx;
    if (ny > 0 && a->vy < 0) a->vy = -a->vy;
    if (ny < 0 && a->vy > 0) a->vy = -a->vy;
    bounce_min(a, nx, ny);
    if (a->vy < 0) a->on_ground = 0;
    return 1;
}

void flier_step(Flier *f, const FlierInput *in, int32_t floor_y) {
    uint8_t edge = (uint8_t)(in->flap && !f->flap_prev);
    f->flap_prev = in->flap ? 1 : 0;
    if (in->dir) f->facing = in->dir > 0;
    if (f->state >= FLIER_DROWNED) return;
    if (f->invincible) f->invincible--;

    if (f->state == FLIER_FALLING) {
        f->vy += FLIER_GRAVITY_NO_BALLOON;
        f->x = arena_wrap_x(f->x + f->vx);
        f->y += f->vy;
        if (f->y > FL_PX(FLIER_REMOVE_Y)) f->state = FLIER_GONE;
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
                f->vy = f->balloons ? FLIER_GROUND_JUMP_VY : FLIER_GROUND_JUMP_VY_NOBAL;
                f->on_ground = 0;
            }
            if (in->dir) f->vx = in->dir > 0 ? FLIER_TOP_LAND_SPEED : -FLIER_TOP_LAND_SPEED;
            else f->vx -= mul_0_2(f->vx);
        } else if (edge && f->balloons) {
            f->vy += mul_0_2(FLIER_FLAP_TARGET_VY - f->vy);
            if (in->dir) {
                int32_t t = in->dir > 0 ? FLIER_TOP_AIR_SPEED : -FLIER_TOP_AIR_SPEED;
                f->vx += mul_0_2(t - f->vx);
            }
        }
    }

    /* move */
    int32_t bottom_before = f->y + flier_half_h(f);
    f->x += f->vx;
    f->y += f->vy;
    int32_t hh = flier_half_h(f);

    /* floor (not for a rising fighter) */
    if (f->on_ground) {
        if (floor_y != FLIER_NO_FLOOR && f->vy >= 0) f->y = floor_y - hh;
        else f->on_ground = 0;
    } else if (floor_y != FLIER_NO_FLOOR && f->vy >= 0 && bottom_before <= floor_y && f->y + hh >= floor_y) {
        f->y = floor_y - hh;
        f->vy = 0;
        f->on_ground = 1;
        if (f->state == FLIER_PARACHUTE) { f->state = FLIER_ALIVE; f->invincible = 0; }
    }

    /* the hazard kills regardless of balloons or invincibility (4.3 item 6), where the drawn surface is (kill_y) */
    if (f->y + hh >= f->kill_y) {
        f->state = FLIER_DROWNED;
        f->vx = f->vy = 0;
        f->balloons = 0;
        f->on_ground = 0;
        return;
    }

    /* side edges wrap (arena.h); the ceiling is an elastic bounce with minimum speed (3.6) */
    f->x = arena_wrap_x(f->x);
    if (f->y < hh) {
        f->y = hh;
        if (f->vy < 0) f->vy = -f->vy;
        bounce_min(f, 0, 1);
    }
}

/* Attacker's feet box against the victim's gum box, both from the named constants in flier.h (art measured, same
 * for player and computer). Compared in 1/2 pixel units (value >> 15) so the half pixel hh of a balloon body is
 * exact; both boxes hang from the feet bottom (y + half height), where the art is anchored. */
int flier_feet_hit(const Flier *a, const Flier *v) {
    /* Vertical test first: it is plain integer arithmetic and rejects most pairs the broad phase in game.c lets through
       (the feet must be 16 to 41 px above the victim's feet bottom), so the arena fold of the horizontal test runs
       rarely. The result is the same box overlap in either order. */
    int16_t afb = (int16_t)((a->y + flier_half_h(a)) >> 15); /* attacker feet bottom */
    int16_t vfb = (int16_t)((v->y + flier_half_h(v)) >> 15); /* victim feet bottom */
    int16_t ft = (int16_t)(afb - 2 * FLIER_FEET_H), fb = afb;
    int16_t gt = (int16_t)(vfb - 2 * FLIER_GUM_TOP), gb = (int16_t)(vfb - 2 * FLIER_GUM_BOTTOM);
    if (!(ft < gb && fb > gt)) return 0;
    int16_t ax = (int16_t)(a->x >> 15);
    int16_t vx = (int16_t)(arena_near_x(a->x, v->x) >> 15);
    int16_t gw = (int16_t)(2 * (v->balloons >= 2 ? FLIER_GUM_HALF_W2 : FLIER_GUM_HALF_W1));
    int16_t fl = (int16_t)(ax - 2 * FLIER_FEET_HALF_W), fr = (int16_t)(ax + 2 * FLIER_FEET_HALF_W);
    int16_t gl = (int16_t)(vx - gw), gr = (int16_t)(vx + gw);
    return fl < gr && fr > gl;
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

int flier_stomp(Flier *a, Flier *v) {
    if (a->state > FLIER_PARACHUTE) return 0;         /* a falling attacker pops nothing */
    if (v->invincible || v->balloons == 0 || v->state > FLIER_PARACHUTE) return 0;
    if (!flier_feet_hit(a, v)) return 0;
    uint8_t ang = flier_angle((arena_near_x(a->x, v->x) - a->x) >> 8, (v->y - a->y) >> 8);
    int16_t c = flier_cos(ang), s = flier_sin(ang);
    /* victim away at 40 px/s, attacker away at 75 px/s (75 raw 40960 = c * 20480 >> 14) */
    v->vx = m16(c, (int16_t)FLIER_KNOCKBACK_VICTIM) >> 15;
    v->vy = m16(s, (int16_t)FLIER_KNOCKBACK_VICTIM) >> 15;
    a->vx = -(m16(c, 20480) >> 14);
    a->vy = -(m16(s, 20480) >> 14);
    if (v->vy < 0) v->on_ground = 0;
    if (a->vy < 0) a->on_ground = 0;
    return flier_lose_balloon(v); /* the last balloon overwrites the victim velocity with the fall start */
}
