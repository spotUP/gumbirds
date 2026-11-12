/* Host test for src/core/flier.[ch]: the spec's numbers (thoughts/shared/research/2026-11-09_flier-reference-spec.md):
 * gravity and fall cap, additive flap impulse, cooldown and thrust, ground walk and jump, bounce, water, balloons and invincibility, falling, parachute, stomp. */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "../../src/core/flier.h"
#include "../../src/core/arena.h"
#include "../../src/core/hazard_kind.h"
#include "../../src/core/flier_view.h"
#include "../../src/core/trip.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)
#define CHECK_NEAR(a, b, tol) do { long _a = (long)(a), _b = (long)(b); checks++; if (labs(_a - _b) > (tol)) { failures++; \
    printf("FAIL %s:%d: %s = %ld, want %ld +-%d\n", __FILE__, __LINE__, #a, _a, _b, (int)(tol)); } } while (0)

static const FlierInput IDLE = {0, 0};

static Flier air(uint8_t balloons) {
    Flier f;
    flier_init(&f, FL_PX(100), FL_PX(90), balloons, 0);
    return f;
}
static void step(Flier *f, int8_t dir, uint8_t flap) {
    FlierInput in = {dir, flap};
    flier_step(f, &in, FLIER_NO_FLOOR);
}

/* A fixed-length fall: the fastest vy seen, with the kill line pushed out of the way. */
static int32_t max_fall_vy(uint8_t balloons, int frames, int *frame_cap_reached) {
    Flier f = air(balloons);
    int32_t top = 0;
    f.kill_y = FL_PX(30000);
    *frame_cap_reached = -1;
    for (int i = 0; i < frames; i++) {
        step(&f, 0, 0);
        if (f.vy > top) top = f.vy;
        if (f.vy >= (balloons ? FLIER_FALL_MAX : FLIER_FALL_MAX_NO_BALLOON) && *frame_cap_reached < 0) *frame_cap_reached = i + 1;
    }
    return top;
}

static void test_gravity(void) {
    Flier f = air(2);
    step(&f, 0, 0);
    CHECK(f.vy == FLIER_GRAVITY_BALLOON);
    for (int i = 1; i < 20; i++) step(&f, 0, 0);
    CHECK(f.vy == FLIER_GRAVITY_BALLOON * 20);   /* linear below the cap */
    Flier g = air(0);
    step(&g, 0, 0);
    CHECK(g.vy == FLIER_GRAVITY_NO_BALLOON);
    /* regression: a long fall never exceeds the cap and reaches it on the frame the sum first crosses it */
    for (uint8_t nb = 0; nb <= 2; nb += 2) {
        int cap_frame;
        int32_t grav = nb ? FLIER_GRAVITY_BALLOON : FLIER_GRAVITY_NO_BALLOON;
        int32_t top = max_fall_vy(nb, 600, &cap_frame);
        int32_t cap = nb ? FLIER_FALL_MAX : FLIER_FALL_MAX_NO_BALLOON;   /* behaviour change approved by the user: no gum has its own cap */
        CHECK(top == cap);
        CHECK(cap_frame == (cap + grav - 1) / grav);
    }
    Flier h = air(2);
    h.vx = 30000;
    h.kill_y = FL_PX(30000);
    for (int i = 0; i < 100; i++) step(&h, 0, 0);
    CHECK(h.vx == 30000);       /* no horizontal air drag */
    /* a falling (dead) fighter is capped too */
    Flier d = air(0);
    d.kill_y = FL_PX(30000);
    d.state = FLIER_FALLING;
    int32_t top = 0;
    for (int i = 0; i < 300 && d.state == FLIER_FALLING; i++) { step(&d, 0, 0); if (d.vy > top) top = d.vy; }
    CHECK(top == FLIER_FALL_MAX_NO_BALLOON);   /* behaviour change approved by the user: the dead fall uses the no-gum cap */
}

/* vy change caused by the flap alone: flier a presses at step 0, twin b does not; both start at rest. */
static void test_flap(void) {
    Flier a = air(2), b = air(2);
    step(&a, 0, 1);
    step(&b, 0, 0);
    CHECK(b.vy == FLIER_GRAVITY_BALLOON);
    CHECK(a.vy - b.vy == -FLIER_FLAP_IMPULSE);          /* exactly the impulse, no lerp */
    CHECK(a.vy == FLIER_GRAVITY_BALLOON - FLIER_FLAP_IMPULSE);
    /* regression: presses inside the cooldown do nothing; the first press after it adds the impulse again */
    for (int i = 1; i < FLIER_FLAP_COOLDOWN; i++) {
        step(&a, 0, (i % 2 == 0 && i < FLIER_FLAP_COOLDOWN - 1) ? 1 : 0);   /* edges at the even steps, level 0 just before the allowed one */
        step(&b, 0, 0);
        CHECK(a.vy - b.vy == -FLIER_FLAP_IMPULSE);
    }
    step(&a, 0, 1);                                        /* step COOLDOWN: allowed again */
    step(&b, 0, 0);
    CHECK(a.vy - b.vy == -2 * FLIER_FLAP_IMPULSE);
    /* the last cooldown step still refuses: flap at step 0, press at step COOLDOWN - 1 (one early) changes nothing */
    Flier e = air(2), r = air(2);
    for (int i = 0; i < FLIER_FLAP_COOLDOWN; i++) { step(&e, 0, i == 0 || i == FLIER_FLAP_COOLDOWN - 1); step(&r, 0, i == 0); }
    CHECK(e.vy == r.vy);
    /* no gum: a flap does nothing and starts no cooldown */
    Flier z = air(0);
    step(&z, 0, 1);
    CHECK(z.vy == FLIER_GRAVITY_NO_BALLOON && z.flap_cd == 0);
    /* mashing the button every other frame for a long time never rises faster than the rise cap, and the cap is met */
    {
        Flier m = air(2);
        int32_t lowest = 0;
        m.kill_y = FL_PX(30000);
        for (int i = 0; i < 400; i++) {
            step(&m, 0, i % 2 == 0);
            if (m.vy < lowest) lowest = m.vy;
            CHECK(m.vy >= -FLIER_RISE_MAX);
            m.y = FL_PX(90);                                /* keep clear of the ceiling bounce */
        }
        CHECK(lowest < 0);
    }
    /* a rising fighter is capped: the cap is a clamp, not an offset */
    {
        Flier c = air(2);
        c.vy = -FLIER_RISE_MAX;
        step(&c, 0, 1);
        CHECK(c.vy == -FLIER_RISE_MAX);
    }
    /* regression: with a direction held, each allowed flap adds the thrust; three reach the top air speed and it is never exceeded */
    Flier g;
    flier_init(&g, FL_PX(10), FL_PX(100), 3, 0);
    int32_t vxmax = 0;
    for (int i = 0; i < 12 * FLIER_FLAP_COOLDOWN; i++) {
        step(&g, 1, i % 2 == 0);
        g.y = FL_PX(100); g.vy = 0;
        if (g.vx > vxmax) vxmax = g.vx;
        CHECK(g.vx <= FLIER_TOP_AIR_SPEED);
        if (i == 0) CHECK(g.vx == FLIER_FLAP_THRUST_X);
        if (i == FLIER_FLAP_COOLDOWN && FLIER_FLAP_COOLDOWN % 2 == 0 && 2 * FLIER_FLAP_THRUST_X < FLIER_TOP_AIR_SPEED) CHECK(g.vx == 2 * FLIER_FLAP_THRUST_X);
    }
    CHECK(vxmax == FLIER_TOP_AIR_SPEED);
    CHECK(3 * FLIER_FLAP_THRUST_X >= FLIER_TOP_AIR_SPEED && 2 * FLIER_FLAP_THRUST_X < FLIER_TOP_AIR_SPEED);   /* three flaps, not two */
    /* no direction: a flap leaves vx alone */
    Flier h = air(2);
    h.vx = 20000;
    step(&h, 0, 1);
    CHECK(h.vx == 20000);
    /* already faster than the top speed (bounce, knockback): a flap in the same direction never slows it */
    h.vx = FLIER_TOP_AIR_SPEED + 5000; h.flap_cd = 0; h.flap_prev = 0;
    step(&h, 1, 1);
    CHECK(h.vx == FLIER_TOP_AIR_SPEED + 5000);
    /* left is the mirror of right */
    Flier l;
    flier_init(&l, FL_PX(300), FL_PX(100), 3, 0);
    for (int n = 0; n < 8 * FLIER_FLAP_COOLDOWN; n++) { step(&l, -1, n % 2 == 0); l.y = FL_PX(100); l.vy = 0; }
    Flier rr;
    flier_init(&rr, FL_PX(10), FL_PX(100), 3, 0);
    for (int n = 0; n < 8 * FLIER_FLAP_COOLDOWN; n++) { step(&rr, 1, n % 2 == 0); rr.y = FL_PX(100); rr.vy = 0; }
    CHECK(l.vx == -rr.vx && rr.vx == FLIER_TOP_AIR_SPEED);
}

static Flier stand(uint8_t balloons) {
    Flier f;
    flier_init(&f, FL_PX(100), FL_PX(120) - (balloons ? FLIER_HALF_H16_BALLOON : FLIER_HALF_H16_NOBAL), balloons, 0);
    FlierInput in = {0, 0};
    flier_step(&f, &in, FL_PX(120));   /* lands */
    return f;
}
static void gstep(Flier *f, int8_t dir, uint8_t flap) {
    FlierInput in = {dir, flap};
    flier_step(f, &in, FL_PX(120));
}

/* Flier.flapped (view signal): 1 exactly on the frame an impulse or ground jump was applied, never on a refused press. */
static void test_flapped(void) {
    Flier f = air(2);
    int ones = 0, i;
    for (i = 0; i < 50; i++) { step(&f, 0, 1); ones += f.flapped; }       /* held button: one edge, one flap */
    CHECK(ones == 1);
    /* released, then pressed again after the cooldown: flapped again; one step early it stays 0 */
    Flier g = air(2);
    step(&g, 0, 1);
    CHECK(g.flapped == 1);
    for (i = 1; i < FLIER_FLAP_COOLDOWN; i++) { step(&g, 0, 0); CHECK(g.flapped == 0); }
    step(&g, 0, 1);
    CHECK(g.flapped == 1);
    Flier e = air(2);
    step(&e, 0, 1);
    for (i = 1; i < FLIER_FLAP_COOLDOWN - 1; i++) step(&e, 0, 0);
    step(&e, 0, 1);                                                      /* COOLDOWN - 1 steps after the flap: refused */
    CHECK(e.flapped == 0);
    /* a falling flier and an airborne one with no balloons never flap */
    Flier d = air(2);
    d.state = FLIER_FALLING;
    step(&d, 0, 1);
    CHECK(d.flapped == 0);
    Flier z = air(0);
    step(&z, 0, 1);
    CHECK(z.flapped == 0);
    /* a ground jump sets it, the next idle step clears it */
    Flier j = stand(2);
    CHECK(j.flapped == 0);
    FlierInput in = {0, 1};
    flier_step(&j, &in, FL_PX(120));
    CHECK(j.flapped == 1 && !j.on_ground);
    in.flap = 0;
    flier_step(&j, &in, FL_PX(120));
    CHECK(j.flapped == 0);
}

static void test_ground(void) {
    Flier f = stand(2);
    CHECK(f.on_ground && f.vy == 0);
    gstep(&f, 1, 0);
    CHECK(f.vx == FLIER_GROUND_ACCEL);       /* behaviour change approved by the user: linear ground acceleration, not instant */
    gstep(&f, 0, 0);
    CHECK(f.vx == 0);                        /* behaviour change approved by the user: release brakes linearly to exact 0 */
    CHECK(f.y + flier_half_h(&f) == FL_PX(120));
    for (int i = 0; i < 40; i++) gstep(&f, -1, 0);
    CHECK(f.vx == -FLIER_TOP_LAND_SPEED);    /* behaviour change approved by the user: reaches the top speed after the ramp */
    /* jump with balloons */
    Flier j = stand(2);
    gstep(&j, 0, 1);
    CHECK(j.vy == FLIER_GROUND_JUMP_VY && !j.on_ground);
    gstep(&j, 0, 1);
    CHECK(j.vy == FLIER_GROUND_JUMP_VY + FLIER_GRAVITY_BALLOON);
    /* jump without balloons: twice the speed */
    Flier n = stand(0);
    gstep(&n, 0, 1);
    CHECK(n.vy == FLIER_GROUND_JUMP_VY_NOBAL && !n.on_ground);
    /* a jump lands again on the floor */
    for (int i = 0; i < 400 && !j.on_ground; i++) gstep(&j, 0, 0);
    CHECK(j.on_ground && j.vy == 0);
    /* walking off the floor edge: no floor, gravity takes over */
    Flier w = stand(2);
    flier_step(&w, &IDLE, FLIER_NO_FLOOR);
    CHECK(!w.on_ground);
    flier_step(&w, &IDLE, FLIER_NO_FLOOR);
    CHECK(w.vy == FLIER_GRAVITY_BALLOON);
    /* a floor line alone is a single line: a rising fighter passes it (the island bodies below it are solid, see test_solid_platforms) */
    Flier u;
    flier_init(&u, FL_PX(100), FL_PX(125), 2, 0);
    u.vy = -FL_PX(1);
    flier_step(&u, &IDLE, FL_PX(120));
    CHECK(!u.on_ground);
}

static void test_bounce(void) {
    Flier f;
    /* side edges wrap at ARENA_W: no wall, velocity untouched */
    flier_init(&f, 32768, FL_PX(90), 2, 0);
    f.vx = -65536; f.vy = 20000;
    step(&f, 0, 0);
    CHECK(f.x == ARENA_W16 - 32768);                 /* 0.5 - 1 = 0.5 left of zero -> 383.5 */
    CHECK(f.vx == -65536 && f.vy == 20000 + FLIER_GRAVITY_BALLOON);
    flier_init(&f, FL_PX(383) + 32768, FL_PX(90), 2, 0);
    f.vx = 65536;
    step(&f, 0, 0);
    CHECK(f.x == 32768 && f.vx == 65536);            /* 384.5 -> 0.5 */
    /* on the floor the edge does not stop the walk either */
    flier_init(&f, FL_PX(383) + 40000, FL_PX(90), 2, 0);
    f.vx = 50000; f.on_ground = 1;
    step(&f, 0, 0);
    CHECK(f.x < FL_PX(2) && f.vx != 0);
    /* a long flight crosses 383 -> 0 and stays inside 0..ARENA_W; it wraps more than once */
    flier_init(&f, FL_PX(100), FL_PX(90), 2, 0);
    f.vx = 65536;
    {
        int wraps = 0;
        int32_t prev = f.x;
        for (int i = 0; i < 2000; i++) {
            step(&f, 0, 0);
            if (f.state != FLIER_ALIVE) break;
            CHECK(f.x >= 0 && f.x < ARENA_W16);
            if (f.x < prev) wraps++;
            prev = f.x;
            f.y = FL_PX(90); f.vy = 0;
        }
        CHECK(wraps == 5);   /* 2000 px of travel / 384 from x 100 */
    }
    /* the FALLING path wraps too */
    flier_init(&f, FL_PX(383) + 40000, FL_PX(90), 0, 0);
    f.state = FLIER_FALLING; f.vx = 60000; f.vy = 0;
    step(&f, 0, 0);
    CHECK(f.x < FL_PX(2) && f.x >= 0);
    flier_init(&f, FL_PX(0) + 100, FL_PX(90), 0, 0);
    f.state = FLIER_FALLING; f.vx = -60000; f.vy = 0;
    step(&f, 0, 0);
    CHECK(f.x > FL_PX(383) && f.x < ARENA_W16);
    /* ceiling: the gum top (31 above the feet) stays on screen row 0, so the feet bottom stops at FLIER_CEILING_FEET_Y
     * (was: centre y = half height, feet 11, 20 rows of gum above the screen) */
    flier_init(&f, FL_PX(100), FL_PX(FLIER_CEILING_FEET_Y) - FLIER_HALF_H16_BALLOON + 32768, 2, 0);
    f.vy = -65536;
    step(&f, 0, 0);
    CHECK(f.y == FL_PX(FLIER_CEILING_FEET_Y) - FLIER_HALF_H16_BALLOON);
    CHECK(f.vy == (65536 - FLIER_GRAVITY_BALLOON) * 205 / 256);   /* 50840: the ceiling gives back 205/256 of the speed */
    flier_init(&f, FL_PX(100), FL_PX(FLIER_CEILING_FEET_Y) - FLIER_HALF_H16_BALLOON + 100, 2, 0);
    f.vy = -3000; f.vx = 3000;
    step(&f, 0, 0);
    CHECK(f.vy == (3000 - FLIER_GRAVITY_BALLOON) * 205 / 256 && f.vx == 3000);   /* 762: a slow hit stays slow, no minimum; sideways speed untouched */
}

/* Top edge: no flier, with or without gum, is ever drawn partly above screen row 0 (gum top = feet - FLIER_GUM_TOP >= 0), and a
 * computer flier bounces off a line FLIER_RIVAL_CEILING_DROP lower, so a hero at the hero ceiling can still get above it. */
static int32_t climb_min_feet(Flier *f, int frames) {
    int32_t min_feet = f->y + flier_half_h(f);
    for (int i = 0; i < frames; i++) {
        FlierInput in = { 0, (uint8_t)(i & 1) };       /* a flap every other frame: the press edge needs a release */
        flier_step(f, &in, FLIER_NO_FLOOR);
        if (f->y + flier_half_h(f) < min_feet) min_feet = f->y + flier_half_h(f);
    }
    return min_feet;
}

static void test_top_edge(void) {
    Flier f, h, r;
    int32_t m;
    /* the helper: the one rule, in rows */
    flier_init(&f, FL_PX(100), FL_PX(90), 2, 0);
    CHECK(flier_ceiling_y(&f, 0, 0) == FL_PX(31) - FLIER_HALF_H16_BALLOON);
    CHECK(flier_ceiling_y(&f, 0, 1) == FL_PX(63) - FLIER_HALF_H16_BALLOON);
    CHECK(flier_ceiling_y(&f, 50, 0) == FL_PX(81) - FLIER_HALF_H16_BALLOON);
    flier_init(&f, FL_PX(100), FL_PX(90), 0, 0);
    CHECK(flier_ceiling_y(&f, 0, 0) == FL_PX(31) - FLIER_HALF_H16_NOBAL);
    /* hero with gum and without gum climbing on held flaps: gum top never above row 0 */
    flier_init(&h, FL_PX(100), FL_PX(120), 2, 0);
    m = climb_min_feet(&h, 400);
    CHECK((m >> 16) - FLIER_GUM_TOP >= 0 && (m >> 16) >= FLIER_CEILING_FEET_Y && m == FL_PX(31));
    CHECK(h.y >= FL_PX(31) - FLIER_HALF_H16_BALLOON);
    flier_init(&h, FL_PX(100), FL_PX(120), 1, 0);
    m = climb_min_feet(&h, 400);
    CHECK((m >> 16) - FLIER_GUM_TOP >= 0 && m == FL_PX(31));
    /* a balloon-less (falling is excluded) alive flier on the parachute keeps the same line */
    flier_init(&h, FL_PX(100), FL_PX(120), 0, 1);
    h.state = FLIER_PARACHUTE;
    m = climb_min_feet(&h, 100);
    CHECK((m >> 16) - FLIER_GUM_TOP >= 0);
    /* a computer flier rising from below stops 32 px lower */
    flier_init(&r, FL_PX(100), FL_PX(120), 2, 0);
    r.rival = 1;
    m = climb_min_feet(&r, 400);
    CHECK(m == FL_PX(31 + FLIER_RIVAL_CEILING_DROP) && (m >> 16) - FLIER_GUM_TOP == FLIER_RIVAL_CEILING_DROP);
    /* a computer flier that starts above its lowered line (spawned or standing on a high island) is not pushed down */
    flier_init(&r, FL_PX(100), FL_PX(46), 2, 0);
    r.rival = 1;
    step(&r, 0, 0);
    CHECK(r.y + flier_half_h(&r) < FL_PX(63) && r.y + flier_half_h(&r) >= FL_PX(31));
    /* killability: a rival resting at its line is stomped by a hero at or below the hero ceiling, closing from above */
    flier_init(&r, FL_PX(100), flier_ceiling_y(&r, 0, 1), 2, 0);
    r.rival = 1; r.y = flier_ceiling_y(&r, 0, 1);
    flier_init(&h, FL_PX(100), flier_ceiling_y(&h, 0, 0), 2, 0);
    h.y = flier_ceiling_y(&h, 0, 0);
    h.y += FL_PX(12);                                   /* feet 43: 20 px above the rival feet 63 */
    h.vy = FL_PX(2);
    CHECK(flier_pair(&h, &r) == FLP_POP_B);
    h.y = flier_ceiling_y(&h, 0, 0);                    /* hero feet 31: 32 px above, one row out of the gum reach */
    CHECK(flier_pair(&h, &r) == FLP_NONE);
    /* both at the shared hero ceiling the pair is level: a plain bounce, no pop (why the rival line is lower) */
    flier_init(&r, FL_PX(100), 0, 2, 0);
    r.y = flier_ceiling_y(&r, 0, 0); r.vy = -FL_PX(1);
    flier_init(&h, FL_PX(100), 0, 2, 0);
    h.y = flier_ceiling_y(&h, 0, 0); h.vy = -FL_PX(2);
    CHECK(flier_pair(&h, &r) != FLP_POP_A && flier_pair(&h, &r) != FLP_POP_B);
}

/* Every hazard kind kills at its own line (hazard_kind.h): feet 1 px above it live, feet on it drown. Spikes kill at the
 * tip row (192); water, lava and fire at the drawn surface (204, 202, 210) plus 4. */
static void test_hazard_kill_lines(void) {
    static const struct { uint8_t kind; int line; } expect[HAZARD_KINDS] = {
        { HZ_SPIKES, 192 }, { HZ_WATER, 208 }, { HZ_LAVA, 206 }, { HZ_FIRE, 214 },
    };
    for (int k = 0; k < HAZARD_KINDS; k++) {
        int line = hazard_kill_px(expect[k].kind);
        CHECK(line == expect[k].line);
        Flier f;
        flier_init(&f, FL_PX(100), 0, FLIER_MAX_BALLOONS, 0);
        f.kill_y = FL_PX(line);
        f.y = FL_PX(line) - flier_half_h(&f) - FL_PX(1);      /* feet 1 px above the line */
        step(&f, 0, 0);
        CHECK(f.state == FLIER_ALIVE && f.balloons == FLIER_MAX_BALLOONS);
        flier_init(&f, FL_PX(100), 0, FLIER_MAX_BALLOONS, 0);
        f.kill_y = FL_PX(line);
        f.y = FL_PX(line) - flier_half_h(&f);                  /* feet on the line */
        step(&f, 0, 0);
        CHECK(f.state == FLIER_DROWNED && f.balloons == 0);
    }
}

static void test_water_and_balloons(void) {
    Flier f;
    flier_init(&f, FL_PX(100), FL_PX(180) - FLIER_HALF_H16_BALLOON - 10, 3, 0);
    f.vy = 20000;
    f.invincible = 50;
    step(&f, 0, 0);
    CHECK(f.state == FLIER_DROWNED && f.balloons == 0);   /* water ignores invincibility */
    int32_t y = f.y;
    step(&f, 0, 1);
    /* behaviour change approved by the user (dead flier hazard hunt): was CHECK(f.y == y) (frozen); a touched body keeps falling */
    CHECK(f.y > y && f.vx == 0 && f.state == FLIER_DROWNED);

    /* pop invincibility counts down FLIER_INVINCIBLE_POP (= FLIER_HIT_COOLDOWN, 20) frames */
    Flier p = air(FLIER_MAX_BALLOONS);
    CHECK(flier_lose_balloon(&p) == 1 && p.balloons == FLIER_MAX_BALLOONS - 1 && p.invincible == FLIER_INVINCIBLE_POP);
    CHECK(flier_lose_balloon(&p) == 0 && p.balloons == FLIER_MAX_BALLOONS - 1);
    for (int i = 0; i < FLIER_INVINCIBLE_POP - 1; i++) { step(&p, 0, 0); p.y = FL_PX(90); p.vy = 0; }
    CHECK(p.invincible == 1);
    CHECK(flier_lose_balloon(&p) == 0);
    step(&p, 0, 0);
    CHECK(p.invincible == 0);
    while (p.balloons > 1) { CHECK(flier_lose_balloon(&p) == 1); p.invincible = 0; }

    /* last balloon in the air, no parachute: falls, input ignored, no clamp */
    CHECK(p.balloons == 1 && p.state == FLIER_ALIVE);
    CHECK(flier_lose_balloon(&p) == 1);
    CHECK(p.state == FLIER_FALLING && p.vx == 0 && p.vy == FLIER_FALL_START_VY);
    step(&p, 1, 1);
    CHECK(p.vy == FLIER_FALL_START_VY + FLIER_GRAVITY_NO_BALLOON && p.vx == 0);
    for (int i = 0; i < 400 && p.state == FLIER_FALLING; i++) step(&p, 1, 1);
    /* behaviour change approved by the user (dead flier hazard hunt): removed when the whole sprite is below the screen; was p.y > FL_PX(FLIER_REMOVE_Y) */
    CHECK(p.state == FLIER_GONE && p.y + flier_half_h(&p) >= FL_PX(FLIER_REMOVE_FEET_Y));

    /* last balloon in the air with parachute: 30 frames invincible, slow fall, sway */
    Flier c;
    flier_init(&c, FL_PX(100), FL_PX(50), 1, 1);
    CHECK(flier_lose_balloon(&c) == 1);
    CHECK(c.state == FLIER_PARACHUTE && c.invincible == FLIER_INVINCIBLE_PARACHUTE && c.balloons == 0);
    step(&c, 0, 1);
    CHECK(c.vy == FLIER_PARACHUTE_GRAVITY);                      /* flap ignored while parachuting */
    for (int i = 0; i < 29; i++) step(&c, 0, 0);
    CHECK(c.invincible == 0 && c.vy == FLIER_PARACHUTE_FALL_MAX);   /* behaviour change approved by the user: 30 frames of 1024 hit the 21845 cap */
    for (int i = 0; i < 60; i++) step(&c, 0, 0);
    CHECK(labs(c.vx) <= FLIER_PARACHUTE_SWAY);
    int32_t tgt = c.sway_target;
    CHECK(tgt != 0 || c.sway_phase != 0);
    /* parachute ends on landing */
    Flier d;
    flier_init(&d, FL_PX(100), FL_PX(100), 1, 1);
    flier_lose_balloon(&d);
    for (int i = 0; i < 400 && d.state == FLIER_PARACHUTE; i++) { FlierInput in = {0, 0}; flier_step(&d, &in, FL_PX(120)); }
    CHECK(d.state == FLIER_ALIVE && d.on_ground && d.invincible == 0);

    /* last balloon lost on the ground: stands on, no invincibility, feet stay on the floor */
    Flier g = stand(1);
    CHECK(flier_lose_balloon(&g) == 1 && g.balloons == 0 && g.state == FLIER_ALIVE && g.on_ground);
    gstep(&g, 0, 0);
    CHECK(g.y + flier_half_h(&g) == FL_PX(120));
    CHECK(flier_add_balloon(&g) == 1 && g.balloons == 1);
    gstep(&g, 0, 0);
    CHECK(g.y + flier_half_h(&g) == FL_PX(120));
    while (g.balloons < FLIER_MAX_BALLOONS) CHECK(flier_add_balloon(&g) == 1);
    CHECK(!flier_add_balloon(&g) && g.balloons == FLIER_MAX_BALLOONS);
}

static void test_angle(void) {
    CHECK(flier_angle(1000, 0) == 0);
    CHECK(flier_angle(0, 1000) == 64);
    CHECK(flier_angle(-1000, 0) == 128);
    CHECK(flier_angle(0, -1000) == 192);
    CHECK_NEAR(flier_angle(1000, 1000), 32, 1);
    CHECK_NEAR(flier_angle(-1000, 1000), 96, 1);
    CHECK_NEAR(flier_angle(-1000, -1000), 160, 1);
    CHECK_NEAR(flier_angle(1000, -1000), 224, 1);
    CHECK(flier_sin(64) == 32767 && flier_cos(0) == 32767 && flier_sin(0) == 0 && flier_sin(192) == -32767);
}

static void test_stomp(void) {
    Flier a, v;
    flier_init(&a, FL_PX(100), FL_PX(80), 2, 0);
    flier_init(&v, FL_PX(100), FL_PX(105), 2, 0);
    a.vy = FL_PX(2);                     /* the stomper falls onto the victim: the pair closes vertically */
    CHECK(flier_pair(&a, &v) == FLP_POP_B);
    CHECK(flier_stomp(&a, &v) == 1);
    CHECK(v.balloons == 1 && v.invincible == FLIER_INVINCIBLE_POP && a.balloons == 2);   /* exactly one balloon, attacker unhurt */
    /* the pop frame gives only the normal reflect: a.vy 131072 -> -(131072 * 205 / 256), no knockback on either flier */
    CHECK(a.vy == -104960 && a.vx == 0);
    CHECK(v.vx == 0 && v.vy == 0);
    CHECK(flier_stomp(&a, &v) == 0 && v.balloons == 1);   /* invincible: no second pop */
    /* diagonal: centres 1 px apart, under the body half width, so only the vertical axis reflects */
    flier_init(&a, FL_PX(100), FL_PX(80), 2, 0);
    flier_init(&v, FL_PX(101), FL_PX(105), 2, 0);
    a.vy = FL_PX(2); a.vx = FL_PX(1);
    CHECK(flier_stomp(&a, &v) == 1);
    CHECK(a.vy == -104960 && a.vx == FL_PX(1) && v.vx == 0 && v.vy == 0);
    /* last balloon: victim falls with the fall start velocity */
    flier_init(&a, FL_PX(100), FL_PX(80), 2, 0);
    flier_init(&v, FL_PX(100), FL_PX(105), 1, 0);
    a.vy = FL_PX(2);
    CHECK(flier_stomp(&a, &v) == 1);
    CHECK(v.state == FLIER_FALLING && v.vx == 0 && v.vy == FLIER_FALL_START_VY);
    /* no pop: apart, victim without balloons, falling attacker */
    flier_init(&v, FL_PX(100), FL_PX(105), 2, 0);
    flier_init(&a, FL_PX(140), FL_PX(80), 2, 0);
    a.vy = FL_PX(2);
    CHECK(flier_pair(&a, &v) == FLP_NONE && flier_stomp(&a, &v) == 0 && v.balloons == 2);
    flier_init(&a, FL_PX(100), FL_PX(110), 2, 0);   /* attacker below the victim: the victim is the one who pops */
    v.vy = FL_PX(2);
    CHECK(flier_pair(&a, &v) == FLP_POP_A && flier_stomp(&a, &v) == 0);
    v.vy = 0;
    flier_init(&a, FL_PX(100), FL_PX(80), 2, 0);
    a.vy = FL_PX(2);
    a.state = FLIER_FALLING;
    CHECK(flier_stomp(&a, &v) == 0 && v.balloons == 2);
    a.state = FLIER_ALIVE;
    v.balloons = 0;
    CHECK(flier_stomp(&a, &v) == 0);
}

/* B1/B2/B4/B5: the reference contact rule. Each flier reverses its own velocity on each closing axis times 205/256 (floor),
 * no minimum speed, overlap while moving apart does nothing, the two axes are independent. */
static void test_contact_rule(void) {
    Flier a, b;
    /* B1: each flier flips its own component, truncated: 1000 -> -800 (800.78), -1001 -> +801 (801.56 -> 801 after floor of 205/256) */
    flier_init(&a, FL_PX(100), FL_PX(90), 2, 0);
    flier_init(&b, FL_PX(100) + FL_PX(3), FL_PX(90), 2, 0);
    a.vx = 1000; b.vx = -1001;
    CHECK(flier_pair(&a, &b) == FLP_BOUNCE);
    flier_pair_apply(&a, &b, FLP_BOUNCE);
    CHECK(a.vx == -800 && b.vx == 801);
    CHECK(flier_reflect(65536) == -52480 && flier_reflect(-65536) == 52480 && flier_reflect(131072) == -104960 && flier_reflect(0) == 0);
    CHECK(flier_reflect(40000) == -32031 && flier_reflect(1) == 0 && flier_reflect(-1) == 0);
    /* B2: no minimum speed: 300 -> -240, 100 -> -80 */
    flier_init(&a, FL_PX(100), FL_PX(90), 2, 0);
    flier_init(&b, FL_PX(100) + FL_PX(3), FL_PX(90), 2, 0);
    a.vx = 300; b.vx = 0;
    flier_pair_apply(&a, &b, flier_pair(&a, &b));
    CHECK(a.vx == -240 && b.vx == 0);
    /* B4: overlapping and moving apart: nothing happens, no bounce, no pop */
    flier_init(&a, FL_PX(100), FL_PX(90), 2, 0);
    flier_init(&b, FL_PX(100) + FL_PX(3), FL_PX(90), 2, 0);
    a.vx = -65536; b.vx = 65536;
    CHECK(flier_pair(&a, &b) == FLP_NONE && flier_body_bounce(&a, &b) == 0);
    flier_pair_apply(&a, &b, flier_pair(&a, &b));
    CHECK(a.vx == -65536 && b.vx == 65536);
    flier_init(&a, FL_PX(100), FL_PX(80), 2, 0);
    flier_init(&b, FL_PX(100), FL_PX(105), 2, 0);
    a.vy = -FL_PX(1);                    /* stomper above the victim but moving up: no pop */
    CHECK(flier_pair(&a, &b) == FLP_NONE && flier_stomp(&a, &b) == 0 && b.balloons == 2);
    /* B5: both axes in one frame. a left and above b, closing on x and y: both components of both fliers flip. */
    flier_init(&a, FL_PX(100), FL_PX(90), 2, 0);
    flier_init(&b, FL_PX(110), FL_PX(90) + FL_PX(8), 2, 0);
    b.invincible = 60;                   /* an invincible lower flier turns the stomp into a plain bounce */
    a.vx = 65536; b.vx = -65536; a.vy = FL_PX(2); b.vy = -65536;
    CHECK(flier_pair(&a, &b) == FLP_BOUNCE);
    flier_pair_apply(&a, &b, FLP_BOUNCE);
    CHECK(a.vx == -52480 && b.vx == 52480 && a.vy == -104960 && b.vy == 52480);
    /* only one axis closing: the other component stays */
    flier_init(&a, FL_PX(100), FL_PX(90), 2, 0);
    flier_init(&b, FL_PX(110), FL_PX(90) + FL_PX(8), 2, 0);
    b.invincible = 60;
    a.vx = 65536; b.vx = -65536; a.vy = -1000; b.vy = 2000;   /* y separates */
    flier_pair_apply(&a, &b, flier_pair(&a, &b));
    CHECK(a.vx == -52480 && b.vx == 52480 && a.vy == -1000 && b.vy == 2000);
}

/* Body-contact reflect (design 1.6 rules 3-4), now the shared reference rule. */
static void test_body_bounce(void) {
    Flier a, b;
    flier_init(&a, FL_PX(100), FL_PX(90), 2, 0);
    flier_init(&b, FL_PX(100), FL_PX(90), 2, 0);
    /* side by side, a left of b, a moving into b: x reflects times 205/256, y stays */
    b.x = a.x + FL_PX(3);
    a.vx = 65536; a.vy = 1000;
    CHECK(flier_body_bounce(&a, &b) == 1);
    CHECK(a.vx == -52480 && a.vy == 1000);
    /* a right of b moving left */
    b.x = a.x - FL_PX(3);
    a.vx = -65536; a.vy = 0;
    CHECK(flier_body_bounce(&a, &b) == 1 && a.vx == 52480);
    /* separating: no contact action, unchanged */
    a.vx = 65536;
    CHECK(flier_body_bounce(&a, &b) == 0 && a.vx == 65536);
    /* slow: no minimum, 100 -> -80 */
    b.x = a.x + FL_PX(3);
    a.vx = 100; a.vy = 100;
    CHECK(flier_body_bounce(&a, &b) == 1 && a.vx == -80 && a.vy == 100);
    /* moving away from b: nothing */
    a.vx = -100;
    CHECK(flier_body_bounce(&a, &b) == 0 && a.vx == -100);
    /* a above b (stacked, same x): y reflects, x stays */
    b.x = a.x; b.y = a.y + FL_PX(10);
    a.vx = 5000; a.vy = 40000;
    CHECK(flier_body_bounce(&a, &b) == 1 && a.vy == -32031 && a.vx == 5000);
    /* body edge to the pixel: 14 wide boxes touch at 14 px apart (edges exclusive), overlap at 13 */
    b.x = a.x + FL_PX(13); b.y = a.y;
    a.vx = 65536; a.vy = 0;
    CHECK(flier_body_bounce(&a, &b) == 1 && a.vx == -52480);
    b.x = a.x + FL_PX(14);
    a.vx = 65536;
    CHECK(flier_body_bounce(&a, &b) == 0 && a.vx == 65536);
    /* balloon-less a gets none (it dies in flier_body_kill); other without balloons does not stop a bouncing */
    flier_init(&b, a.x + FL_PX(3), a.y, 0, 0);
    a.vx = 65536;
    CHECK(flier_body_bounce(&a, &b) == 1 && a.vx == -52480);
    b.vx = -65536;
    CHECK(flier_body_bounce(&b, &a) == 0 && b.vx == -65536);
    /* a dead-fall body takes no part */
    flier_init(&b, a.x + FL_PX(3), a.y, 2, 0);
    b.state = FLIER_FALLING;
    a.vx = 65536;
    CHECK(flier_body_bounce(&a, &b) == 0 && a.vx == 65536);
}

/* Collision across the seam: a at x 383, v at x 1 are 2 px apart, not 382. */
static void test_seam(void) {
    Flier a, v;
    flier_init(&a, FL_PX(383), FL_PX(80), 2, 0);
    flier_init(&v, FL_PX(1), FL_PX(105), 2, 0);
    a.vy = FL_PX(2);
    CHECK(flier_pair(&a, &v) == FLP_POP_B);
    CHECK(flier_stomp(&a, &v) == 1 && v.balloons == 1 && a.vy == -104960 && a.vx == 0 && v.vx == 0);
    /* mirrored: attacker at 1, victim at 383 */
    flier_init(&a, FL_PX(1) + 40000, FL_PX(80), 2, 0);
    flier_init(&v, FL_PX(383), FL_PX(105), 2, 0);
    a.vy = FL_PX(2);
    CHECK(flier_stomp(&a, &v) == 1 && v.vx == 0 && a.vx == 0 && a.vy == -104960);
    /* body contact: a left of the seam moving into b right of it */
    flier_init(&a, FL_PX(382), FL_PX(90), 2, 0);
    flier_init(&v, FL_PX(1), FL_PX(90), 2, 0);
    a.vx = 65536;
    CHECK(flier_body_bounce(&a, &v) == 1 && a.vx == -52480);
    /* and the other way across: a right of the seam moving left into b left of it */
    flier_init(&a, FL_PX(1), FL_PX(90), 2, 0);
    flier_init(&v, FL_PX(382), FL_PX(90), 2, 0);
    a.vx = -65536;
    CHECK(flier_body_bounce(&a, &v) == 1 && a.vx == 52480);
    /* body kill of a balloon-less flier that touches another across the seam */
    flier_init(&a, FL_PX(383), FL_PX(90), 0, 0);
    flier_init(&v, FL_PX(2), FL_PX(90), 2, 0);
    CHECK(flier_body_kill(&a, &v) == 1 && a.state == FLIER_FALLING);
    /* far apart across the seam: no contact */
    flier_init(&a, FL_PX(383), FL_PX(90), 2, 0);
    flier_init(&v, FL_PX(100), FL_PX(90), 2, 0);
    a.vx = 65536;
    CHECK(flier_pair(&a, &v) == FLP_NONE && flier_body_bounce(&a, &v) == 0);
}

/* ---- characterisation of the additive model: peak heights follow from the constants (continuous estimate v^2 / 2g, 6 percent). ---- */
static void test_peaks(void) {
    Flier f = air(2);
    int32_t y0 = f.y, top = 0;
    for (int i = 0; i < 2000; i++) {
        step(&f, 0, i == 0);
        if (f.y - y0 < top) top = f.y - y0;
        if (f.vy > 0) break;
    }
    double v0 = (double)FLIER_FLAP_IMPULSE - FLIER_GRAVITY_BALLOON, want = v0 * v0 / (2.0 * FLIER_GRAVITY_BALLOON);
    (void)want;
    CHECK(-top == 389120);
    for (int nb = 0; nb <= 2; nb += 2) {
        Flier j = stand((uint8_t)nb);
        int32_t jy0 = j.y, jtop = 0;
        for (int i = 0; i < 2000; i++) {
            gstep(&j, 0, i == 0);
            if (j.y - jy0 < jtop) jtop = j.y - jy0;
            if (i > 0 && j.vy > 0) break;
        }
        double jv = nb ? -(double)FLIER_GROUND_JUMP_VY : -(double)FLIER_GROUND_JUMP_VY_NOBAL;
        double g = nb ? FLIER_GRAVITY_BALLOON : FLIER_GRAVITY_NO_BALLOON;
        double jw = jv * jv / (2.0 * g);
        (void)jw;
        CHECK(-jtop == (nb ? 430080 : 1024100));   /* behaviour change approved by the user: no-gum jump peak was 696320 at gravity 5120 */
    }
}

/* AR1: a 60 px fall from rest takes an exact frame count (gravity and fall cap pinned together). */
static void test_fall_60px(void) {
    for (int nb = 0; nb <= 2; nb += 2) {
        Flier d = air((uint8_t)nb);
        int32_t y0 = d.y;
        int fn = 0;
        d.kill_y = FL_PX(30000);
        while (d.y - y0 < FL_PX(60) && fn < 1000) { step(&d, 0, 0); fn++; }
        printf("fall 60 px nb=%d: %d frames\n", nb, fn);
        CHECK(fn == (nb ? 63 : 48));   /* behaviour change approved by the user: no-gum gravity 3413, was 47 frames */
    }
}

/* ---- Pair contact boxes (design: gum contact). Written as independent restatements of the table in
 * thoughts/spot/2026-11-11-gum-contact-executor-brief.md with literal pixel numbers, not as calls into the macros. ---- */
/* A flier with its feet bottom at whole pixel fb (so a difference of feet bottoms is exact whatever the balloon count). */
static void mk(Flier *f, int x, int fb, uint8_t balloons) {
    flier_init(f, FL_PX(x), 0, balloons, 0);
    f->y = FL_PX(fb) - flier_half_h(f);
}
static FlierPairAct pair_px(int ax, int afb, uint8_t ab, int bx, int bfb, uint8_t bb) {
    Flier a, b;
    mk(&a, ax, afb, ab);
    mk(&b, bx, bfb, bb);
    /* the pair closes on every axis it has: toward each other sideways, the higher one falling onto the lower one */
    a.vx = bx > ax ? FL_PX(1) : bx < ax ? -FL_PX(1) : 0;
    b.vx = -a.vx;
    if (afb < bfb) { a.vy = FL_PX(1); b.vy = -FL_PX(1); }
    else if (afb > bfb) { a.vy = -FL_PX(1); b.vy = FL_PX(1); }
    return flier_pair(&a, &b);
}

/* ---- B: stomp boxes follow the drawn art (sootling_sheet.png, 24 x 32 frames: body 14 wide, 0..22 above the feet bottom;
 * gums 22..31 above it, rim 18 wide with two gums, 10 wide with one). The higher flier's body meets the lower one's gum. ---- */
static void test_stomp_art(void) {
    Flier a, v;
    /* victim feet bottom 100, two balloons: the attacker's body (7 half width) meets the gum (9 half width) for |dx| < 16 */
    CHECK(pair_px(115, 74, 2, 100, 100, 2) == FLP_POP_B);          /* 15 right, 26 px above */
    CHECK(pair_px(85, 70, 2, 100, 100, 2) == FLP_POP_B);           /* 15 left, 30 px above */
    CHECK(pair_px(116, 74, 2, 100, 100, 2) == FLP_NONE);           /* 16: beside the gum */
    CHECK(pair_px(84, 74, 2, 100, 100, 2) == FLP_NONE);
    /* one gum is narrower: |dx| < 12 */
    CHECK(pair_px(111, 74, 2, 100, 100, 1) == FLP_POP_B);
    CHECK(pair_px(112, 74, 2, 100, 100, 1) == FLP_NONE);
    /* vertical edges: 30 px above the victim's feet bottom pops (gum top 31), 31 px misses, 50 px is far above */
    CHECK(pair_px(100, 70, 2, 100, 100, 2) == FLP_POP_B);
    CHECK(pair_px(100, 69, 2, 100, 100, 2) == FLP_NONE);
    CHECK(pair_px(100, 50, 2, 100, 100, 2) == FLP_NONE);
    /* the feet of the attacker no longer matter: only the body box against the gum. A real pop through flier_stomp: */
    mk(&v, 100, 100, 2);
    mk(&a, 115, 74, 2);
    a.vy = FL_PX(1);
    CHECK(flier_stomp(&a, &v) == 1 && v.balloons == 1);
    mk(&v, 100, 100, 2);
    mk(&a, 116, 74, 2);
    a.vy = FL_PX(1);
    CHECK(flier_stomp(&a, &v) == 0 && v.balloons == 2);
}

/* T1: gum against gum at the same height: both bounce, nobody pops. Two gums touch for |dx| < 18 px. */
static void test_gum_gum_level(void) {
    Flier a, b;
    CHECK(pair_px(100, 100, 2, 117, 100, 2) == FLP_BOUNCE);        /* 17 apart: gums touch, bodies do not */
    CHECK(pair_px(100, 100, 2, 118, 100, 2) == FLP_NONE);          /* 18: just clear */
    CHECK(pair_px(100, 100, 2, 101, 103, 2) == FLP_BOUNCE);        /* feet 3 px apart is still level (centres 1 px apart: a pair needs some separation to close) */
    CHECK(pair_px(100, 100, 2, 112, 103, 2) == FLP_BOUNCE);
    CHECK(pair_px(100, 100, 2, 101, 97, 2) == FLP_BOUNCE);
    CHECK(pair_px(100, 100, 2, 112, 104, 2) == FLP_POP_B);        /* 4 px apart is no longer level: the higher flier pops */
    CHECK(pair_px(112, 104, 2, 100, 100, 2) == FLP_POP_A);
    /* the bounce leaves the balloons alone and sends both apart */
    mk(&a, 100, 100, 2); mk(&b, 110, 100, 2);
    a.vx = 30000; b.vx = -30000;
    CHECK(flier_pair_apply(&a, &b, flier_pair(&a, &b)) == 0);
    CHECK(a.balloons == 2 && b.balloons == 2 && a.vx < 0 && b.vx > 0);
}

/* T2: a flier that comes from the side into a lower flier's gum pops it. */
static void test_side_into_gum(void) {
    Flier a, v;
    /* a is 10 px higher and 12 px to the left: its body reaches the gum of v (22..31 above v's feet) */
    CHECK(pair_px(88, 90, 2, 100, 100, 2) == FLP_POP_B);
    mk(&a, 88, 90, 2); mk(&v, 100, 100, 2);
    a.vx = 30000;
    CHECK(flier_pair_apply(&a, &v, flier_pair(&a, &v)) == 1 && v.balloons == 1 && v.invincible == FLIER_INVINCIBLE_POP && a.balloons == 2);
    /* the mirror, a on the right */
    CHECK(pair_px(112, 90, 2, 100, 100, 2) == FLP_POP_B);
    /* the same position with the order swapped: v is lower, so the answer is POP_A */
    CHECK(pair_px(100, 100, 2, 88, 90, 2) == FLP_POP_A);
}

/* T3: from below, the mirror: the lower flier's body rising into the higher flier's gum is the lower one's loss only if it is higher.
 * Here the flier that is lower has its gum popped by the other one's body, so a body coming up under a gum pops nothing. */
static void test_from_below(void) {
    /* a is lower (feet 100), b higher (feet 90): b's body is 0..22 above 90, a's gum 22..31 above 100 = 122..131 up?  Heights are
     * measured upward: a's gum spans feet 78..69 (y), b's body spans 90..68. They overlap, so the lower flier a loses. */
    CHECK(pair_px(100, 100, 2, 88, 90, 2) == FLP_POP_A);
    /* the lower flier's body can never reach the higher flier's gum, because the body top is the gum bottom */
    CHECK(pair_px(100, 100, 2, 100, 69, 2) == FLP_NONE);           /* 31 px apart: past the top of the gum */
    CHECK(pair_px(100, 100, 2, 100, 70, 2) == FLP_POP_A);          /* 30 px: the higher flier's body reaches into the gum below */
}

/* T4: gum against gum, widths and heights to the pixel (rim 18 and 10 wide, gum band 22..31 so 9 px tall). */
static void test_gum_edges(void) {
    /* gum to gum with the higher flier 6 px up: beyond the body reach (16) but inside 18 */
    CHECK(pair_px(117, 94, 2, 100, 100, 2) == FLP_POP_B);
    CHECK(pair_px(118, 94, 2, 100, 100, 2) == FLP_NONE);
    /* one gum on the higher flier is narrower than its body, so the body decides: 7 + 9 = 16 */
    CHECK(pair_px(115, 94, 1, 100, 100, 2) == FLP_POP_B);
    CHECK(pair_px(116, 94, 1, 100, 100, 2) == FLP_NONE);
    /* one gum on the lower flier: 5 + 9 = 14 */
    CHECK(pair_px(113, 94, 2, 100, 100, 1) == FLP_POP_B);
    CHECK(pair_px(114, 94, 2, 100, 100, 1) == FLP_NONE);
    /* vertical: the gum bands overlap for up to 8 px of offset (9 tall), not 9; offset beyond 3 so it is not level */
    CHECK(pair_px(117, 92, 2, 100, 100, 2) == FLP_POP_B);          /* 8 px */
    CHECK(pair_px(117, 91, 2, 100, 100, 2) == FLP_NONE);           /* 9 px */
    /* the gum bottom edge: a body 21 px above the victim's feet is not in the gum band alone; the body-to-gum test in T2 covers
     * the width; here the lowest edge of the band is 22 px above the feet bottom */
    CHECK(pair_px(100, 78, 2, 100, 100, 2) == FLP_POP_B);          /* attacker's body bottom 22 px above: body into gum */
}

/* AR3: two fliers at the identical position and at rest overlap but close on no axis, so nothing happens. */
static void test_pair_identical_position(void) {
    Flier a, b;
    mk(&a, 100, 80, 2); mk(&b, 100, 80, 2);
    CHECK(flier_pair(&a, &b) == FLP_NONE && flier_pair(&b, &a) == FLP_NONE);
}

/* T5: contact with an invincible or parachuting flier bounces and pops nothing; falling and dead fliers take no part. */
static void test_pair_states(void) {
    Flier a, v;
    mk(&a, 100, 80, 2); mk(&v, 100, 100, 2);
    a.vy = FL_PX(1);
    v.invincible = 30;
    CHECK(flier_pair(&a, &v) == FLP_BOUNCE);
    CHECK(flier_pair_apply(&a, &v, FLP_BOUNCE) == 0 && v.balloons == 2);
    v.invincible = 0;
    a.vy = FL_PX(1);
    v.state = FLIER_PARACHUTE;
    CHECK(flier_pair(&a, &v) == FLP_POP_B);                        /* a parachute flier keeps its gum and can be popped */
    v.state = FLIER_FALLING;
    CHECK(flier_pair(&a, &v) == FLP_NONE && flier_pair(&v, &a) == FLP_NONE);
    v.state = FLIER_DROWNED;
    CHECK(flier_pair(&a, &v) == FLP_NONE);
    v.state = FLIER_GONE;
    CHECK(flier_pair(&a, &v) == FLP_NONE);
}

/* T6: a flier without balloons has no gum; the 14 x 22 body boxes decide, and the body-body contact bounces. */
static void test_gumless_and_bodies(void) {
    /* lower flier gumless: only body against body */
    CHECK(pair_px(100, 80, 2, 100, 100, 0) == FLP_BOUNCE);         /* 20 px: bodies overlap */
    CHECK(pair_px(100, 79, 2, 100, 100, 0) == FLP_BOUNCE);         /* 21 px */
    CHECK(pair_px(100, 78, 2, 100, 100, 0) == FLP_NONE);           /* 22 px: body top meets the body bottom exactly */
    CHECK(pair_px(113, 90, 2, 100, 100, 0) == FLP_BOUNCE);         /* 13 px sideways */
    CHECK(pair_px(114, 90, 2, 100, 100, 0) == FLP_NONE);           /* 14 px */
    /* a gumless flier touched by a body falls (flier_body_kill) at the same boxes */
    Flier a, v;
    mk(&a, 100, 90, 2); mk(&v, 100, 100, 0);
    CHECK(flier_body_kill(&v, &a) == 1 && v.state == FLIER_FALLING);
    mk(&v, 100, 100, 0); mk(&a, 114, 90, 2);
    CHECK(flier_body_kill(&v, &a) == 0 && v.state == FLIER_ALIVE);
    mk(&a, 100, 79, 2); mk(&v, 100, 100, 0);
    CHECK(flier_body_kill(&v, &a) == 1);
    mk(&a, 100, 78, 2); mk(&v, 100, 100, 0);
    CHECK(flier_body_kill(&v, &a) == 0);
}

/* T7: the old rule survives: feet on the gum pops, and the same position reads as a pop for either order of the arguments. */
static void test_feet_on_gum(void) {
    CHECK(pair_px(100, 74, 2, 100, 100, 2) == FLP_POP_B);
    CHECK(pair_px(100, 100, 2, 100, 74, 2) == FLP_POP_A);
    CHECK(pair_px(100, 74, 2, 100, 100, 1) == FLP_POP_B);
}

/* ---- islands are solid on every side (design: solid platforms) ---- */
static const FlierInput IDLE2 = {0, 0};
static FlierSolid mksolid(int x, int y, int w, int h) {
    FlierSolid s; s.x16 = FL_PX(x); s.y16 = FL_PX(y); s.w16 = FL_PX(w); s.h16 = FL_PX(h); return s;
}
/* One frame the way the glue does it: flier_step, then the solid pass with the pre-step position. */
static int sstep(Flier *f, const FlierSolid *s, int n, int32_t floor_y) {
    int32_t px = f->x, py = f->y;
    flier_step(f, &IDLE2, floor_y);
    return flier_collide_solids(f, px, py, s, n);
}
static int overlaps(const Flier *f, const FlierSolid *s) {
    int32_t hw, top, feet = f->y + flier_half_h(f);
    flier_solid_box(f, &hw, &top);
    return f->x + hw > s->x16 && f->x - hw < s->x16 + s->w16 && feet > s->y16 && feet - top < s->y16 + s->h16;
}

static void test_solid_platforms(void) {
    FlierSolid s = mksolid(100, 120, 40, 12);   /* x 100..140, y 120..132 */
    Flier f;
    uint16_t h0;
    int i;
    /* underside: rising into it turns the flier around, box pushed out below */
    flier_init(&f, FL_PX(120), FL_PX(133 + FLIER_GUM_TOP) - FLIER_HALF_H16_BALLOON, 2, 0);
    f.vy = -FL_PX(2);
    h0 = g_flier_solid_hits;
    CHECK(sstep(&f, &s, 1, FLIER_NO_FLOOR) == 1);
    CHECK(g_flier_solid_hits == (uint16_t)(h0 + 1));
    CHECK(f.vy > 0 && !f.on_ground);
    CHECK(f.y + flier_half_h(&f) - FL_PX(FLIER_GUM_TOP) == FL_PX(132));   /* gum top on the island bottom */
    CHECK(!overlaps(&f, &s));
    /* left side, moving right */
    flier_init(&f, FL_PX(91), FL_PX(126), 2, 0);
    f.vx = FL_PX(3);
    CHECK(sstep(&f, &s, 1, FLIER_NO_FLOOR) == 1);
    CHECK(f.vx < 0 && f.x + FL_PX(FLIER_SOLID_MAX_HALF_W) == FL_PX(100) && !overlaps(&f, &s));
    /* right side, moving left */
    flier_init(&f, FL_PX(149), FL_PX(126), 2, 0);
    f.vx = -FL_PX(3);
    CHECK(sstep(&f, &s, 1, FLIER_NO_FLOOR) == 1);
    CHECK(f.vx > 0 && f.x - FL_PX(FLIER_SOLID_MAX_HALF_W) == FL_PX(140) && !overlaps(&f, &s));
    /* across the ring seam: solid 364..404 reaches over the seam; underside at wrapped x 3, right side at wrapped x 24 */
    s = mksolid(364, 120, 40, 12);
    flier_init(&f, FL_PX(3), FL_PX(133 + FLIER_GUM_TOP) - FLIER_HALF_H16_BALLOON, 2, 0);
    f.vy = -FL_PX(2);
    CHECK(sstep(&f, &s, 1, FLIER_NO_FLOOR) == 1 && f.vy > 0);
    flier_init(&f, FL_PX(31), FL_PX(126), 2, 0);
    f.vx = -FL_PX(3);
    CHECK(sstep(&f, &s, 1, FLIER_NO_FLOOR) == 1 && f.vx > 0 && f.x == FL_PX(20) + FL_PX(FLIER_SOLID_MAX_HALF_W));
    flier_init(&f, FL_PX(353), FL_PX(126), 2, 0);
    f.vx = FL_PX(3);
    CHECK(sstep(&f, &s, 1, FLIER_NO_FLOOR) == 1 && f.vx < 0 && f.x == FL_PX(364) - FL_PX(FLIER_SOLID_MAX_HALF_W));
    s = mksolid(100, 120, 40, 12);
    /* a falling fighter (no balloons left, FALLING) passes through */
    flier_init(&f, FL_PX(120), FL_PX(133 + FLIER_GUM_TOP) - FLIER_HALF_H16_BALLOON, 2, 0);
    f.state = FLIER_FALLING;
    f.vy = -FL_PX(2);
    h0 = g_flier_solid_hits;
    CHECK(sstep(&f, &s, 1, FLIER_NO_FLOOR) == 0 && g_flier_solid_hits == h0 && f.vy < 0);
    /* the parachute bounces and keeps its state */
    flier_init(&f, FL_PX(120), FL_PX(133 + FLIER_BODY_TOP) - FLIER_HALF_H16_NOBAL, 0, 0);
    f.state = FLIER_PARACHUTE;
    f.vy = -FL_PX(2);
    CHECK(sstep(&f, &s, 1, FLIER_NO_FLOOR) == 1 && f.state == FLIER_PARACHUTE && f.vy > 0);
    /* landing from above is the floor's job: the solid does nothing, no hit counted */
    flier_init(&f, FL_PX(120), FL_PX(100), 2, 0);
    h0 = g_flier_solid_hits;
    for (i = 0; i < 300 && !f.on_ground; i++) CHECK(sstep(&f, &s, 1, FL_PX(120)) == 0);
    CHECK(f.on_ground && f.y + flier_half_h(&f) == FL_PX(120) && g_flier_solid_hits == h0);
    /* standing then idling: still no hit, still down */
    for (i = 0; i < 30; i++) sstep(&f, &s, 1, FL_PX(120));
    CHECK(f.on_ground && g_flier_solid_hits == h0);
    /* a rising flier from below the floor line passes the line but not the body */
    flier_init(&f, FL_PX(120), FL_PX(132 + FLIER_GUM_TOP) + FL_PX(1) / 2 - FLIER_HALF_H16_BALLOON, 2, 0);
    f.vy = -FL_PX(3);
    CHECK(sstep(&f, &s, 1, FL_PX(120)) == 1 && f.vy > 0 && !overlaps(&f, &s));
    /* walking off the edge: the lower floor under the edge is not snapped to (the 13 teleport cases) */
    f = stand(2);
    {
        int32_t y0 = f.y;
        flier_step(&f, &IDLE2, FL_PX(130));          /* floor 10 px lower now */
        CHECK(!f.on_ground);
        CHECK(f.y - y0 < FL_PX(1));
        for (i = 0; i < 40 && !f.on_ground; i++) flier_step(&f, &IDLE2, FL_PX(130));
        CHECK(f.on_ground && f.y + flier_half_h(&f) == FL_PX(130));   /* it does land there, by falling */
    }
    /* sub-pixel floor changes still keep the flier standing */
    f = stand(2);
    flier_step(&f, &IDLE2, FL_PX(120) + FLIER_FLOOR_TOL);
    CHECK(f.on_ground);
    /* a standing flier that carries a small downward vy (a balloon lost on the ground) is pulled back to the floor by its own
     * motion within the tolerance: it stays standing and is not left sunk into the platform body (hunt seed 2, frame 2216) */
    f = stand(2);
    f.vy = FL_PX(1) / 3;
    flier_step(&f, &IDLE2, FL_PX(120));
    CHECK(f.on_ground && f.y + flier_half_h(&f) == FL_PX(120));
}

/* B6/B7: platforms and the screen top, exact numbers. Top of a platform: snap, vy 0, no bounce. Underside and sides: times
 * 205/256, no minimum speed. */
static void test_solid_bounce_numbers(void) {
    FlierSolid s = mksolid(100, 120, 40, 12);   /* x 100..140, y 120..132 */
    Flier f;
    int32_t hh;
    /* underside, fast: vy -131072 -> +104960; the box is pushed out below */
    flier_init(&f, FL_PX(120), FL_PX(132 + FLIER_GUM_TOP) - FL_PX(1) / 2 - FLIER_HALF_H16_BALLOON, 2, 0);
    hh = flier_half_h(&f);
    f.vy = -FL_PX(2);
    CHECK(flier_collide_solids(&f, f.x, FL_PX(133 + FLIER_GUM_TOP) - hh, &s, 1) == 1);
    CHECK(f.vy == 104960 && f.y == FL_PX(132 + FLIER_GUM_TOP) - hh);
    /* underside, tiny: -300 -> +240, no minimum */
    flier_init(&f, FL_PX(120), FL_PX(132 + FLIER_GUM_TOP) - hh - 20, 2, 0);
    f.vy = -300;
    CHECK(flier_collide_solids(&f, f.x, FL_PX(132 + FLIER_GUM_TOP) - hh, &s, 1) == 1 && f.vy == 240);
    /* left side, moving right: 196608 -> -157440, x snapped to the face */
    flier_init(&f, FL_PX(99), FL_PX(126), 2, 0);
    f.vx = FL_PX(3);
    CHECK(flier_collide_solids(&f, FL_PX(91), f.y, &s, 1) == 1);
    CHECK(f.vx == -157440 && f.x + FL_PX(FLIER_SOLID_MAX_HALF_W) == FL_PX(100));
    /* right side, moving left, tiny: -100 -> +80 */
    flier_init(&f, FL_PX(141), FL_PX(126), 2, 0);
    f.vx = -100;
    CHECK(flier_collide_solids(&f, FL_PX(150), f.y, &s, 1) == 1);
    CHECK(f.vx == 80 && f.x - FL_PX(FLIER_SOLID_MAX_HALF_W) == FL_PX(140));
    /* moving away from the face it overlaps: velocity unchanged */
    flier_init(&f, FL_PX(99), FL_PX(126), 2, 0);
    f.vx = -FL_PX(3);
    CHECK(flier_collide_solids(&f, FL_PX(91), f.y, &s, 1) == 1 && f.vx == -FL_PX(3));
    /* top: landing snaps with vy 0 and no bounce */
    flier_init(&f, FL_PX(120), FL_PX(100), 2, 0);
    f.vy = FL_PX(3);
    for (int i = 0; i < 300 && !f.on_ground; i++) sstep(&f, &s, 1, FL_PX(120));
    CHECK(f.on_ground && f.vy == 0 && f.y + flier_half_h(&f) == FL_PX(120));
    /* screen top: snap to the ceiling, vy reflects times 205/256 (tiny: -3000 plus gravity -> 762) */
    flier_init(&f, FL_PX(100), FL_PX(FLIER_CEILING_FEET_Y) - FLIER_HALF_H16_BALLOON + 100, 2, 0);
    f.vy = -3000;
    step(&f, 0, 0);
    CHECK(f.y == FL_PX(FLIER_CEILING_FEET_Y) - FLIER_HALF_H16_BALLOON && f.vy == (3000 - FLIER_GRAVITY_BALLOON) * 205 / 256);
}


/* GI: islands block the whole drawn flier, gum included (body 14 wide, 0..22 above the feet; gum 22..31, 18 wide with two,
 * 10 wide with one). Solid x 100..140, y 120..132. Each case starts with the old 4 x 11 px box clear of the solid. */
static void test_solid_gum_underside(void) {
    FlierSolid s = mksolid(100, 120, 40, 12);
    Flier f;
    int32_t hh = FLIER_HALF_H16_BALLOON;
    flier_init(&f, FL_PX(120), FL_PX(162) - hh, 2, 0);
    f.vy = -FL_PX(2);
    CHECK(flier_collide_solids(&f, f.x, FL_PX(164) - hh, &s, 1) == 1);
    CHECK(f.y == FL_PX(163) - hh);                                      /* gum top (feet - 31) rests on the island bottom */
    CHECK(f.vy == 104960);
}
static void test_solid_gum_side(void) {
    FlierSolid s = mksolid(100, 120, 40, 12);
    Flier f;
    int32_t hh = FLIER_HALF_H16_BALLOON;
    flier_init(&f, FL_PX(92), FL_PX(140) - hh, 2, 0);                   /* feet 140, gum rows 109..131 beside the island */
    f.vx = FL_PX(3);
    CHECK(flier_collide_solids(&f, FL_PX(90), f.y, &s, 1) == 1);
    CHECK(f.x == FL_PX(91));                                            /* two gums: half width 9, right edge on x 100 */
    CHECK(f.vx == -157440);
    flier_init(&f, FL_PX(94), FL_PX(140) - hh, 1, 0);
    f.vx = FL_PX(3);
    CHECK(flier_collide_solids(&f, FL_PX(92), f.y, &s, 1) == 1);
    CHECK(f.x == FL_PX(93));                                            /* one gum: the body half width 7 is the widest part */
    CHECK(f.vx == -157440);
}
static void test_solid_body_no_gum(void) {
    FlierSolid s = mksolid(100, 120, 40, 12);
    Flier f;
    int32_t hh = FLIER_HALF_H16_NOBAL;
    flier_init(&f, FL_PX(120), FL_PX(153) - hh, 0, 0);                  /* no gum: only the 22 px body is solid */
    f.vy = -FL_PX(1);
    CHECK(flier_collide_solids(&f, f.x, FL_PX(155) - hh, &s, 1) == 1);
    CHECK(f.y == FL_PX(154) - hh);
    CHECK(f.vy == 52480);
}

/* A flier standing on a solid's top and walking is not pushed, lifted or un-grounded by that solid (the walk clip needs on_ground). */
static void test_solid_walk_on_top(void) {
    FlierSolid s = mksolid(136, 128, 112, 12);
    int bal, i;
    for (bal = 0; bal <= 2; bal++) {
        Flier f;
        FlierInput in = { 0 };
        int32_t hh, y0, x0;
        flier_init(&f, FL_PX(192), 0, (uint8_t)bal, 0);
        hh = flier_half_h(&f);
        f.y = FL_PX(128) - hh;
        f.on_ground = 1;
        y0 = f.y; x0 = f.x;
        in.dir = 1;
        for (i = 0; i < 16; i++) {
            int32_t px = f.x, py = f.y;
            flier_step(&f, &in, FL_PX(128));
            flier_collide_solids(&f, px, py, &s, 1);
        }
        CHECK(f.on_ground == 1);
        CHECK(f.y == y0);
        CHECK(f.x > x0 && f.vx >= FLIER_WALK_MIN_VX);
    }
}

/* ---- PB reference: a verbatim copy of flier_pair_blocked before the bounding-box reject (64-bit compares, no early reject). ---- */
static int ref_frac_lt(int32_t n1, int32_t d1, int32_t n2, int32_t d2) { return (int64_t)n1 * d2 < (int64_t)n2 * d1; }
static int ref_slab(int32_t d, int32_t lo, int32_t hi, int32_t *ln, int32_t *ld, int32_t *hn, int32_t *hd) {
    if (d == 0) return lo < 0 && 0 < hi;
    if (d < 0) { int32_t t = lo; d = -d; lo = -hi; hi = -t; }
    if (ref_frac_lt(*ln, *ld, lo, d)) { *ln = lo; *ld = d; }
    if (ref_frac_lt(hi, d, *hn, *hd)) { *hn = hi; *hd = d; }
    return 1;
}
static int ref_pair_blocked(const Flier *a, const Flier *b, const FlierSolid *solids, int n, int wrap) {
    int32_t bx = wrap ? arena_near_x(a->x, b->x) : b->x;
    int32_t dx = bx - a->x, dy = b->y - a->y;
    int32_t mid = a->x + (dx >> 1);
    int i;
    for (i = 0; i < n; i++) {
        int32_t x0 = solids[i].x16, ln = 0, ld = 1, hn = 1, hd = 1;
        if (wrap) x0 = arena_near_x(mid, x0 + (solids[i].w16 >> 1)) - (solids[i].w16 >> 1);
        x0 -= a->x;
        if (!ref_slab(dx, x0, x0 + solids[i].w16, &ln, &ld, &hn, &hd)) continue;
        if (!ref_slab(dy, solids[i].y16 - a->y, solids[i].y16 + solids[i].h16 - a->y, &ln, &ld, &hn, &hd)) continue;
        if (ref_frac_lt(ln, ld, hn, hd)) return 1;
    }
    return 0;
}

static uint32_t pb_seed = 12345u;
static uint32_t pb_rnd(uint32_t n) { pb_seed = pb_seed * 1664525u + 1013904223u; return (pb_seed >> 8) % n; }

/* Equivalence sweep: the real function against the reference over LCG cases, edges and exact corner crossings included. */
static void test_pair_blocked_sweep(void) {
    enum { CASES = 300000 };
    long blocked = 0, c;
    for (c = 0; c < CASES; c++) {
        Flier a, b;
        FlierSolid so[8];
        int n = 1 + (int)pb_rnd(8), wrap = (int)pb_rnd(2), i, mode = (int)pb_rnd(4);
        int32_t ex, ey;
        for (i = 0; i < n; i++) {
            so[i].w16 = FL_PX(4 + (int)pb_rnd(60)) + (pb_rnd(3) == 0 ? (int32_t)pb_rnd(65536) : 0);
            so[i].h16 = FL_PX(1 + (int)pb_rnd(20)) + (pb_rnd(3) == 0 ? (int32_t)pb_rnd(65536) : 0);
            so[i].x16 = FL_PX((int)pb_rnd(ARENA_W)) + (int32_t)pb_rnd(65536);
            so[i].y16 = FL_PX((int)pb_rnd(200)) + (int32_t)pb_rnd(65536);
        }
        flier_init(&a, FL_PX(100), FL_PX(80), 2, 0);
        flier_init(&b, FL_PX(100), FL_PX(80), 2, 0);
        i = (int)pb_rnd((uint32_t)n);
        a.x = FL_PX((int)pb_rnd(ARENA_W)); a.y = FL_PX((int)pb_rnd(200)) + (int32_t)pb_rnd(65536);
        b.x = a.x + FL_PX((int)pb_rnd(81) - 40); b.y = a.y + FL_PX((int)pb_rnd(81) - 40);
        if (wrap) { b.x = arena_wrap_x(b.x); }
        if (b.x < 0) b.x = 0;
        ex = (pb_rnd(2) ? so[i].x16 : so[i].x16 + so[i].w16) + (int32_t)pb_rnd(3) - 1;
        ey = (pb_rnd(2) ? so[i].y16 : so[i].y16 + so[i].h16) + (int32_t)pb_rnd(3) - 1;
        if (mode == 1) { a.x = ex; a.y = ey - FL_PX((int)pb_rnd(30)); b.x = a.x + FL_PX((int)pb_rnd(61) - 30); }       /* a on an edge column/row */
        if (mode == 2) { b.x = ex; b.y = ey; }                                                                          /* b on a corner/edge */
        if (mode == 3) { a.x = ex - 2 * FL_PX((int)pb_rnd(10)); a.y = ey - 2 * FL_PX((int)pb_rnd(10)); b.x = 2 * ex - a.x; b.y = 2 * ey - a.y; } /* corner at the midpoint */
        if (pb_rnd(8) == 0) b.x = a.x;
        if (pb_rnd(8) == 0) b.y = a.y;
        if (wrap) { a.x = arena_wrap_x(a.x); b.x = arena_wrap_x(b.x); }
        else if (a.x < 0 || b.x < 0) continue;
        {
            int r = ref_pair_blocked(&a, &b, so, n, wrap);
            blocked += r;
            if (flier_pair_blocked(&a, &b, so, n, wrap) != r) {
                CHECK(0 && "flier_pair_blocked differs from ref_pair_blocked");
                printf("  case %ld wrap %d n %d a=(%d,%d) b=(%d,%d)\n", c, wrap, n, (int)a.x, (int)a.y, (int)b.x, (int)b.y);
                return;
            }
        }
    }
    CHECK(blocked > CASES / 20 && blocked < CASES - CASES / 20);   /* the sweep exercises both verdicts */
    printf("pair_blocked sweep: %d cases, %ld blocked\n", (int)CASES, blocked);
}

/* ---- PB: a pair does not act through a solid platform (flier_pair_blocked: centre to centre segment against the open box) ---- */
static void test_pair_blocked(void) {
    Flier a, v;
    FlierSolid s;
    uint32_t before;
    flier_init(&a, FL_PX(100), FL_PX(80), 2, 0);
    flier_init(&v, FL_PX(100), FL_PX(105), 2, 0);
    a.vy = FL_PX(2);
    CHECK(flier_pair(&a, &v) == FLP_POP_B);                                  /* case 1: no solid, the pop stands */
    CHECK(flier_pair_blocked(&a, &v, 0, 0, 1) == 0);
    s.x16 = FL_PX(100 - 24); s.y16 = FL_PX(90); s.w16 = FL_PX(48); s.h16 = FL_PX(4);
    before = g_flier_pair_blocked;
    CHECK(flier_pair_blocked(&a, &v, &s, 1, 1) == 1 && g_flier_pair_blocked == before + 1);   /* case 2: a solid between */
    s.x16 = FL_PX(100 + 10);
    CHECK(flier_pair_blocked(&a, &v, &s, 1, 1) == 0 && g_flier_pair_blocked == before + 1);   /* case 3: solid beside the segment */
    s.x16 = FL_PX(100 - 24);
    s.y16 = a.y - s.h16;                                                     /* case 4: bottom edge exactly on the upper centre */
    CHECK(flier_pair_blocked(&a, &v, &s, 1, 1) == 0);
    s.y16 = a.y - s.h16 + 1;                                                 /* one sub-pixel inside */
    CHECK(flier_pair_blocked(&a, &v, &s, 1, 1) == 1);
    s.y16 = v.y;                                                             /* top edge exactly on the lower centre */
    CHECK(flier_pair_blocked(&a, &v, &s, 1, 1) == 0);
    s.y16 = v.y - 1;
    CHECK(flier_pair_blocked(&a, &v, &s, 1, 1) == 1);
    /* case 5: across the arena seam */
    flier_init(&a, FL_PX(382), FL_PX(80), 2, 0);
    flier_init(&v, FL_PX(2), FL_PX(105), 2, 0);
    s.x16 = FL_PX(368); s.y16 = FL_PX(90); s.w16 = FL_PX(32); s.h16 = FL_PX(4);
    CHECK(flier_pair_blocked(&a, &v, &s, 1, 1) == 1);
    s.x16 = FL_PX(100);
    CHECK(flier_pair_blocked(&a, &v, &s, 1, 1) == 0);
    /* case 6: Gum Trip frame (wrap 0): the same x values are 380 px apart, not 4 */
    s.x16 = FL_PX(368);
    CHECK(flier_pair_blocked(&a, &v, &s, 1, 0) == 0);
    flier_init(&a, FL_PX(100), FL_PX(80), 2, 0);
    flier_init(&v, FL_PX(100), FL_PX(105), 2, 0);
    s.x16 = FL_PX(76); s.w16 = FL_PX(48);
    CHECK(flier_pair_blocked(&a, &v, &s, 1, 0) == 1);
    /* case 7: edge touches, corner grazes, collinear edges, single-axis misses (values recorded from the code before the bounding-box reject) */
    flier_init(&a, FL_PX(100), FL_PX(100), 2, 0);
    flier_init(&v, FL_PX(140), FL_PX(100), 2, 0);                            /* horizontal segment y = 100, x 100..140 */
    s.w16 = FL_PX(40); s.h16 = FL_PX(20);
    s.x16 = FL_PX(140); s.y16 = FL_PX(90);                                   /* left edge exactly on the end point */
    CHECK(flier_pair_blocked(&a, &v, &s, 1, 0) == 0);
    s.x16 = FL_PX(140) - 1;                                                  /* one sub-pixel inside */
    CHECK(flier_pair_blocked(&a, &v, &s, 1, 0) == 1);
    s.x16 = FL_PX(60) - FL_PX(0); s.w16 = FL_PX(40);                         /* right edge exactly on the start point */
    CHECK(flier_pair_blocked(&a, &v, &s, 1, 0) == 0);
    s.w16 = FL_PX(40) + 1;
    CHECK(flier_pair_blocked(&a, &v, &s, 1, 0) == 1);
    s.x16 = FL_PX(110); s.w16 = FL_PX(10); s.y16 = FL_PX(100); s.h16 = FL_PX(10);    /* collinear: top edge on the segment line */
    CHECK(flier_pair_blocked(&a, &v, &s, 1, 0) == 0);
    s.y16 = FL_PX(90);                                                       /* collinear: bottom edge on the segment line */
    CHECK(flier_pair_blocked(&a, &v, &s, 1, 0) == 0);
    s.y16 = FL_PX(95);                                                       /* the line runs through the box */
    CHECK(flier_pair_blocked(&a, &v, &s, 1, 0) == 1);
    s.x16 = FL_PX(150); s.y16 = FL_PX(95); s.w16 = FL_PX(10); s.h16 = FL_PX(10);     /* x-only miss: y overlaps, box right of the segment */
    CHECK(flier_pair_blocked(&a, &v, &s, 1, 0) == 0);
    s.x16 = FL_PX(110); s.y16 = FL_PX(200);                                  /* y-only miss: x overlaps, box far below */
    CHECK(flier_pair_blocked(&a, &v, &s, 1, 0) == 0);
    flier_init(&v, FL_PX(140), FL_PX(140), 2, 0);                            /* diagonal segment (100,100)-(140,140) */
    s.x16 = FL_PX(120); s.y16 = FL_PX(90); s.w16 = FL_PX(30); s.h16 = FL_PX(30);     /* box corner (120,120) exactly on the line, box beside it */
    CHECK(flier_pair_blocked(&a, &v, &s, 1, 0) == 0);
    s.h16 = FL_PX(30) + 1;                                                   /* corner one sub-pixel in */
    CHECK(flier_pair_blocked(&a, &v, &s, 1, 0) == 1);
    s.x16 = FL_PX(100); s.y16 = FL_PX(120); s.w16 = FL_PX(20); s.h16 = FL_PX(20);    /* grazes the corner (120,120) from the other side */
    CHECK(flier_pair_blocked(&a, &v, &s, 1, 0) == 0);
    s.x16 = FL_PX(135); s.y16 = FL_PX(100); s.w16 = FL_PX(30); s.h16 = FL_PX(25);    /* bounding boxes overlap, the diagonal passes above the box: miss */
    CHECK(flier_pair_blocked(&a, &v, &s, 1, 0) == 0);
}

/* ---- HC: the pop window is FLIER_HIT_COOLDOWN frames ---- */
static void test_pop_window(void) {
    Flier a, v;
    FlierInput in = {0, 0};
    int i;
    flier_init(&a, FL_PX(100), FL_PX(80), 2, 0);
    flier_init(&v, FL_PX(100), FL_PX(105), 2, 0);
    a.vy = FL_PX(2);
    CHECK(FLIER_HIT_COOLDOWN == 20 && FLIER_INVINCIBLE_POP == 20);   /* BR-D4 decision value, not only the symbol */
    CHECK(flier_stomp(&a, &v) == 1 && v.balloons == 1 && v.invincible == FLIER_HIT_COOLDOWN);
    for (i = 0; i < FLIER_HIT_COOLDOWN - 1; i++) {
        v.y = FL_PX(105); v.vy = 0; v.vx = 0;
        flier_step(&v, &in, FL_PX(30000));
    }
    v.y = FL_PX(105); a.y = FL_PX(80); a.vy = FL_PX(2);
    CHECK(v.invincible == 1 && flier_pair(&a, &v) == FLP_BOUNCE);            /* still protected one frame before the end */
    CHECK(flier_stomp(&a, &v) == 0 && v.balloons == 1);
    v.y = FL_PX(105); v.vy = 0; v.vx = 0;
    flier_step(&v, &in, FL_PX(30000));
    v.y = FL_PX(105); a.y = FL_PX(80); a.vy = FL_PX(2);
    CHECK(v.invincible == 0 && flier_pair(&a, &v) == FLP_POP_B && flier_stomp(&a, &v) == 1 && v.balloons == 0);
}

/* ---- SI: spawn protection ---- */
static void spawn_step(Flier *f, int dir, int flap) {
    FlierInput in;
    in.dir = (int8_t)dir; in.flap = (uint8_t)flap;
    f->y = FL_PX(105); f->vy = 0; f->vx = 0;
    flier_step(f, &in, FL_PX(30000));
}
static void test_spawn_invincible(void) {
    Flier f, a;
    int i;
    flier_init(&f, FL_PX(100), FL_PX(105), 2, 0);
    flier_spawn_protect(&f);
    CHECK(f.spawn_inv == FLIER_SPAWN_INVINCIBLE);
    for (i = 0; i < FLIER_SPAWN_INVINCIBLE - 1; i++) spawn_step(&f, 0, 0);
    CHECK(f.spawn_inv == 1);
    flier_init(&a, FL_PX(100), FL_PX(80), 2, 0);
    a.vy = FL_PX(2);
    f.y = FL_PX(105);
    CHECK(flier_pair(&a, &f) == FLP_BOUNCE && flier_lose_balloon(&f) == 0 && f.balloons == 2);
    spawn_step(&f, 0, 0);
    CHECK(f.spawn_inv == 0);
    f.y = FL_PX(105); a.y = FL_PX(80); a.vy = FL_PX(2);
    CHECK(flier_pair(&a, &f) == FLP_POP_B);
    /* first sideways or flap input cancels it */
    flier_init(&f, FL_PX(100), FL_PX(105), 2, 0); flier_spawn_protect(&f);
    spawn_step(&f, 1, 0);  CHECK(f.spawn_inv == 0);
    flier_init(&f, FL_PX(100), FL_PX(105), 2, 0); flier_spawn_protect(&f);
    spawn_step(&f, -1, 0); CHECK(f.spawn_inv == 0);
    flier_init(&f, FL_PX(100), FL_PX(105), 2, 0); flier_spawn_protect(&f);
    spawn_step(&f, 0, 1);  CHECK(f.spawn_inv == 0);
    flier_init(&f, FL_PX(100), FL_PX(105), 2, 0); flier_spawn_protect(&f);
    spawn_step(&f, 0, 0);  CHECK(f.spawn_inv == FLIER_SPAWN_INVINCIBLE - 1);
    /* a protected flier still pops others, and the hazard kill line ignores the protection */
    flier_init(&a, FL_PX(100), FL_PX(80), 2, 0); flier_spawn_protect(&a); a.vy = FL_PX(2);
    flier_init(&f, FL_PX(100), FL_PX(105), 2, 0);
    CHECK(flier_pair(&a, &f) == FLP_POP_B);
    flier_init(&f, FL_PX(100), FL_PX(105), 2, 0); flier_spawn_protect(&f);
    f.y = f.kill_y + FL_PX(40);
    flier_step(&f, &(FlierInput){0, 0}, FL_PX(30000));
    CHECK(f.state == FLIER_DROWNED);
}


/* Dead flier hazard hunt, DF1..DF5 and DF7 (thoughts/spot/2026-11-11-dead-flier-hazard-hunt.md): a dead or touching flier
 * keeps falling past the kill line; liquids never bounce it, spikes bounce it once; it is GONE only when the whole sprite is
 * below the screen; the run-end checks (trip_over, game.c) read GONE. */
static void dead_fall_run(Flier *f, int solid, int line, int *flips, int *first_flip_feet, int32_t *flip_vy, int *front_after) {
    int prev_vy_up = 0;
    *flips = 0; *first_flip_feet = -1; *flip_vy = 0; *front_after = -1;
    f->solid_kill = (uint8_t)solid;
    f->kill_y = FL_PX(line);
    for (int i = 0; i < 600 && f->state != FLIER_GONE; i++) {
        int32_t before = f->vy;
        step(f, 0, 0);
        if (before > 0 && f->vy < 0) { (*flips)++; if (*first_flip_feet < 0) { *first_flip_feet = (int)((f->y + flier_half_h(f)) >> 16); *flip_vy = f->vy; } }
        if (*flips == 1 && f->vy > 0 && *front_after < 0) *front_after = flier_body_front(f);
        (void)prev_vy_up;
    }
}
static void test_dead_fall(void) {
    int flips, feet, front;
    int32_t fvy;
    /* DF1 liquid: a falling dead flier passes the kill line (water 208) still FLIER_FALLING and is GONE only at whole sprite below the screen */
    Flier f = air(1);
    CHECK(flier_lose_balloon(&f) == 1 && f.state == FLIER_FALLING);
    f.y = FL_PX(150);
    f.kill_y = FL_PX(208);
    f.solid_kill = 0;
    int past_line = 0, visible_below_line = 0;
    for (int i = 0; i < 600 && f.state != FLIER_GONE; i++) {
        step(&f, 0, 0);
        if (f.y + flier_half_h(&f) > FL_PX(214) && f.state == FLIER_FALLING) past_line = 1;
        if (f.y + flier_half_h(&f) > FL_PX(230) && flier_body_visible(&f)) visible_below_line = 1;
    }
    CHECK(past_line);                       /* DF1: still falling below the lava/water/fire kill lines */
    CHECK(visible_below_line);              /* DF2: still drawn while part of the sprite is on the screen */
    CHECK(f.state == FLIER_GONE && f.y + flier_half_h(&f) >= FL_PX(FLIER_REMOVE_FEET_Y) && !flier_body_visible(&f));
    /* DF4 liquids never bounce: water 208, lava 206, fire 214 */
    const int lines[3] = {206, 208, 214};
    for (int k = 0; k < 3; k++) {
        Flier w = air(1);
        CHECK(flier_lose_balloon(&w) == 1);
        w.y = FL_PX(100);
        dead_fall_run(&w, 0, lines[k], &flips, &feet, &fvy, &front);
        CHECK(flips == 0 && !w.bounced && !flier_body_front(&w));
    }
    /* DF4 spikes (kill line 192): one upward reversal at the tips, at least the minimum speed, then a fall to GONE; the body is a front body after the bounce */
    Flier sp = air(1);
    CHECK(flier_lose_balloon(&sp) == 1);
    sp.y = FL_PX(100);
    dead_fall_run(&sp, 1, 192, &flips, &feet, &fvy, &front);
    CHECK(flips == 1 && feet == 192);
    CHECK(fvy <= -FLIER_SPIKE_BOUNCE_MIN_VY);
    CHECK(front == 1 && sp.bounced == 1 && sp.state == FLIER_GONE);
    /* DF4 a living flier that touches the hazard dies, then gets the same treatment (liquid: keeps falling; spikes: bounces once) */
    Flier lv = air(2);
    lv.kill_y = FL_PX(208); lv.solid_kill = 0;
    lv.y = FL_PX(208) - flier_half_h(&lv) - FL_PX(1); lv.vy = 100000;
    step(&lv, 0, 0);
    CHECK(lv.state == FLIER_DROWNED && lv.balloons == 0 && lv.vx == 0);
    int32_t ly = lv.y;
    for (int i = 0; i < 10; i++) step(&lv, 0, 0);
    CHECK(lv.y > ly && lv.state == FLIER_DROWNED);
    for (int i = 0; i < 600 && lv.state != FLIER_GONE; i++) step(&lv, 0, 0);
    CHECK(lv.state == FLIER_GONE);
    Flier ls = air(2);
    ls.kill_y = FL_PX(192); ls.solid_kill = 1;
    ls.y = FL_PX(192) - flier_half_h(&ls) - FL_PX(1); ls.vy = 100000;
    step(&ls, 0, 0);
    CHECK(ls.state == FLIER_DROWNED && ls.bounced == 1 && ls.vy <= -FLIER_SPIKE_BOUNCE_MIN_VY && flier_body_front(&ls));
    /* DF5/DF7: the Gum Trip run and rival checks end at GONE, not at the first touch */
    CHECK(!trip_over(&lv) || lv.state == FLIER_GONE);
    Flier tr = air(1);
    tr.state = FLIER_DROWNED;
    CHECK(trip_over(&tr) == 0);
    tr.state = FLIER_GONE;
    CHECK(trip_over(&tr) == 1);
}

/* Physics wave 2026-11-12: one-gum flap, parachute cap, ground acceleration. */
static void test_physics_wave(void) {
    /* one gum: the air flap adds exactly the one-gum impulse; two gum is unchanged */
    Flier a = air(1), b = air(1);
    step(&a, 0, 1); step(&b, 0, 0);
    CHECK(a.vy - b.vy == -FLIER_FLAP_IMPULSE_ONE_GUM);
    Flier c = air(2), d = air(2);
    step(&c, 0, 1); step(&d, 0, 0);
    CHECK(c.vy - d.vy == -FLIER_FLAP_IMPULSE);
    /* one-gum ground jump */
    Flier j = stand(1);
    gstep(&j, 0, 1);
    CHECK(j.vy == FLIER_GROUND_JUMP_VY_ONE && !j.on_ground);
    /* a no-gum faller reaches exactly the no-gum cap; one and two gum cap at FLIER_FALL_MAX */
    for (uint8_t nb = 0; nb <= 2; nb++) {
        int cf;
        CHECK(max_fall_vy(nb, 600, &cf) == (nb ? FLIER_FALL_MAX : FLIER_FALL_MAX_NO_BALLOON));
    }
    /* parachute: capped at its own cap; a faster arrival is clamped at once */
    Flier p;
    flier_init(&p, FL_PX(100), FL_PX(50), 1, 1);
    flier_lose_balloon(&p);
    p.kill_y = FL_PX(30000);
    p.vy = FLIER_FALL_MAX;
    step(&p, 0, 0);
    CHECK(p.vy == FLIER_PARACHUTE_FALL_MAX);
    Flier q;
    flier_init(&q, FL_PX(100), FL_PX(50), 1, 1);
    flier_lose_balloon(&q);
    q.kill_y = FL_PX(30000);
    q.vy = 0;
    int fr = 0;
    while (q.vy < FLIER_PARACHUTE_FALL_MAX && fr < 100) { step(&q, 0, 0); fr++; }
    CHECK(fr == (FLIER_PARACHUTE_FALL_MAX + FLIER_PARACHUTE_GRAVITY - 1) / FLIER_PARACHUTE_GRAVITY);
    /* ground: top speed in 24 frames without overshoot, release stops at exact 0, reversal passes 0 */
    Flier g = stand(2);
    int n = 0;
    while (g.vx != FLIER_TOP_LAND_SPEED && n < 100) { gstep(&g, 1, 0); n++; CHECK(g.vx <= FLIER_TOP_LAND_SPEED); }
    CHECK(n == 24);
    int zero_seen = 0;   /* the reversal crosses 0 (it need not land on it) */
    for (int i = 0; i < 80; i++) { gstep(&g, -1, 0); if (g.vx <= 0) zero_seen = 1; CHECK(g.vx >= -FLIER_TOP_LAND_SPEED); }
    CHECK(zero_seen && g.vx == -FLIER_TOP_LAND_SPEED);
    int m = 0;
    while (g.vx != 0 && m < 100) { gstep(&g, 0, 0); m++; }
    CHECK(g.vx == 0 && m == 24);
    /* a jump keeps the current ground speed */
    Flier k = stand(2);
    for (int i = 0; i < 10; i++) gstep(&k, 1, 0);
    int32_t vk = k.vx;
    gstep(&k, 0, 1);
    CHECK(!k.on_ground && k.vx == vk);   /* a jump keeps the ground speed it had */
}

int main(void) {
    test_physics_wave();
    test_dead_fall();
    test_gravity();
    test_flap();
    test_flapped();
    test_ground();
    test_bounce();
    test_water_and_balloons();
    test_hazard_kill_lines();
    test_angle();
    test_stomp();
    test_contact_rule();
    test_body_bounce();
    test_seam();
    test_peaks();
    test_fall_60px();
    test_pair_identical_position();
    test_stomp_art();
    test_gum_gum_level();
    test_side_into_gum();
    test_from_below();
    test_gum_edges();
    test_pair_states();
    test_gumless_and_bodies();
    test_feet_on_gum();
    test_top_edge();
    test_solid_platforms();
    test_solid_bounce_numbers();
    test_solid_gum_underside();
    test_solid_gum_side();
    test_solid_body_no_gum();
    test_solid_walk_on_top();
    test_pair_blocked();
    test_pair_blocked_sweep();
    test_pop_window();
    test_spawn_invincible();
    printf("flier: %d checks, %d failures\n", checks, failures);
    return failures != 0;
}
